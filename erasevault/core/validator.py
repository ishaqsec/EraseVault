"""
Strict target validation and system-drive protection safeguards for EraseVault.
Prevents accidental erasure of Windows/POSIX operating system roots, boot volumes,
critical system directories, pagefiles, or the running EraseVault installation.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import List, Set, Tuple

from .models import DriveInfo, ErasureMethod, MediaType, TargetItem
from .storage import StorageInspector


class ValidationError(Exception):
    """Raised when a target path or drive fails validation."""


class SystemDriveProtectionError(ValidationError):
    """Raised when an operation attempts to destructively erase a protected system or boot drive/path."""


class TargetValidator:
    """Validates file, folder, free-space, and drive targets against safety policies."""

    WINDOWS_CRITICAL_NAMES: Set[str] = {
        "windows",
        "program files",
        "program files (x86)",
        "programdata",
        "system volume information",
        "$recycle.bin",
        "recovery",
        "boot",
        "efi",
        "pagefile.sys",
        "hiberfil.sys",
        "swapfile.sys",
        "bootmgr",
        "ntldr",
    }

    POSIX_CRITICAL_PATHS: Set[str] = {
        "/",
        "/bin",
        "/boot",
        "/dev",
        "/etc",
        "/lib",
        "/lib64",
        "/proc",
        "/root",
        "/run",
        "/sbin",
        "/sys",
        "/usr",
        "/var",
    }

    def __init__(self, storage: StorageInspector) -> None:
        self.storage = storage
        self.app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def is_protected_system_path(self, path: str) -> Tuple[bool, str]:
        """Returns (is_protected, reason) if `path` is an OS root, system directory, or EraseVault itself."""
        if not path or not path.strip():
            return (True, "Target path cannot be empty.")

        raw_clean = path.strip()
        if raw_clean.startswith("adb://"):
            return (False, "")

        raw_win_norm = raw_clean.replace("/", "\\").rstrip("\\").lower()
        sys_drive = os.environ.get("SystemDrive", "C:").upper().rstrip("\\").lower()

        if len(raw_win_norm) >= 2 and raw_win_norm[1] == ":":
            parts = [p for p in raw_win_norm.split("\\") if p]
            if parts and parts[0] == sys_drive:
                if len(parts) == 1:
                    return (
                        True,
                        f"System-drive safeguard: '{path}' is the active Windows system drive ({sys_drive.upper()}\\).",
                    )
                if len(parts) >= 2 and parts[1] in self.WINDOWS_CRITICAL_NAMES:
                    return (
                        True,
                        f"System directory safeguard: '{path}' is a protected Windows system path.",
                    )
                if len(parts) == 2 and parts[1] == "users":
                    return (
                        True,
                        f"System directory safeguard: Cannot erase the entire '{path}' profiles root.",
                    )

        abs_path = os.path.abspath(raw_clean)

        if abs_path == self.app_root or self.app_root.startswith(abs_path + os.sep):
            return (
                True,
                f"Safeguard triggered: '{abs_path}' contains or is part of the running EraseVault application.",
            )

        posix_norm = abs_path.rstrip("/") or "/"
        if posix_norm in self.POSIX_CRITICAL_PATHS:
            return (
                True,
                f"System-drive safeguard: '{posix_norm}' is a protected operating system directory.",
            )

        return (False, "")

    def inspect_and_validate_file_targets(
        self, paths: List[str], method: ErasureMethod
    ) -> List[TargetItem]:
        results: List[TargetItem] = []
        seen: Set[str] = set()

        for raw_path in paths:
            if not raw_path:
                continue
            is_prot, prot_reason = self.is_protected_system_path(raw_path)
            abs_path = raw_path if (len(raw_path) >= 2 and raw_path[1] == ":" and os.name != "nt") else os.path.abspath(raw_path)
            if abs_path in seen:
                continue
            seen.add(abs_path)

            if is_prot:
                results.append(
                    TargetItem(
                        path=abs_path,
                        item_type="protected",
                        is_valid=False,
                        validation_error=prot_reason,
                    )
                )
                continue

            if not os.path.lexists(abs_path):
                results.append(
                    TargetItem(
                        path=abs_path,
                        item_type="missing",
                        is_valid=False,
                        validation_error=f"Target does not exist: {abs_path}",
                    )
                )
                continue

            drive_info = self.storage.get_drive_for_path(abs_path)
            is_link = os.path.islink(abs_path)
            ssd_warn = self._build_ssd_warning(drive_info.media_type, method)

            if is_link or os.path.isfile(abs_path):
                try:
                    st = os.lstat(abs_path)
                    sz = 0 if is_link else st.st_size
                except OSError as exc:
                    results.append(
                        TargetItem(
                            path=abs_path,
                            item_type="file",
                            media_type=drive_info.media_type,
                            drive_mount=drive_info.mountpoint,
                            is_valid=False,
                            validation_error=f"Cannot stat file: {exc}",
                        )
                    )
                    continue

                results.append(
                    TargetItem(
                        path=abs_path,
                        item_type="symlink" if is_link else "file",
                        size_bytes=sz,
                        file_count=1,
                        folder_count=0,
                        media_type=drive_info.media_type,
                        drive_mount=drive_info.mountpoint,
                        is_symlink=is_link,
                        is_valid=True,
                        ssd_warning=ssd_warn,
                    )
                )
            elif os.path.isdir(abs_path):
                total_sz = 0
                f_count = 0
                d_count = 1
                try:
                    for root, dirs, files in os.walk(abs_path, followlinks=False):
                        d_count += len(dirs)
                        for fn in files:
                            fp = os.path.join(root, fn)
                            f_count += 1
                            try:
                                if not os.path.islink(fp):
                                    total_sz += os.lstat(fp).st_size
                            except OSError:
                                pass
                except OSError as exc:
                    results.append(
                        TargetItem(
                            path=abs_path,
                            item_type="folder",
                            media_type=drive_info.media_type,
                            drive_mount=drive_info.mountpoint,
                            is_valid=False,
                            validation_error=f"Cannot traverse folder: {exc}",
                        )
                    )
                    continue

                results.append(
                    TargetItem(
                        path=abs_path,
                        item_type="folder",
                        size_bytes=total_sz,
                        file_count=f_count,
                        folder_count=d_count,
                        media_type=drive_info.media_type,
                        drive_mount=drive_info.mountpoint,
                        is_symlink=False,
                        is_valid=True,
                        ssd_warning=ssd_warn,
                    )
                )

        return results

    def validate_drive_target(self, drive: DriveInfo, method: ErasureMethod) -> Tuple[bool, str, str]:
        if drive.is_system_drive or drive.is_boot_drive:
            reason = (
                drive.protection_reason
                or f"Drive '{drive.mountpoint}' is an active system/boot volume and cannot be erased."
            )
            return (False, f"SAFEGUARD BLOCKED: {reason}", "")

        is_prot, prot_reason = self.is_protected_system_path(drive.mountpoint)
        if is_prot:
            return (False, f"SAFEGUARD BLOCKED: {prot_reason}", "")

        if drive.is_read_only:
            return (False, f"Volume '{drive.mountpoint}' is mounted Read-Only.", "")

        if not drive.mountpoint.startswith("adb://") and not os.path.exists(drive.mountpoint):
            return (False, f"Target volume or image '{drive.mountpoint}' is not accessible.", "")

        ssd_warning = self._build_ssd_warning(drive.media_type, method)
        return (True, "", ssd_warning)

    def validate_free_space_target(
        self, target_dir: str, reserve_bytes: int = 50 * 1024 * 1024
    ) -> Tuple[bool, str, DriveInfo, int]:
        if not target_dir or not os.path.exists(target_dir):
            return (False, f"Target directory does not exist: {target_dir}", self.storage.get_drive_for_path("."), 0)

        if not os.path.isdir(target_dir):
            return (
                False,
                f"Free-space target must be a directory or volume mountpoint: {target_dir}",
                self.storage.get_drive_for_path(target_dir),
                0,
            )

        if not os.access(target_dir, os.W_OK):
            return (
                False,
                f"Write permission denied on '{target_dir}'.",
                self.storage.get_drive_for_path(target_dir),
                0,
            )

        drive_info = self.storage.get_drive_for_path(target_dir)
        try:
            usage = shutil.disk_usage(target_dir)
            free_bytes = usage.free
        except OSError as exc:
            return (False, f"Cannot query free disk space: {exc}", drive_info, 0)

        wipeable = max(0, free_bytes - max(0, reserve_bytes))
        if wipeable <= 4096:
            return (
                False,
                f"Insufficient free space above safety reserve ({reserve_bytes // (1024*1024)} MB).",
                drive_info,
                0,
            )

        return (True, "", drive_info, wipeable)

    @staticmethod
    def _build_ssd_warning(media_type: MediaType, method: ErasureMethod) -> str:
        if media_type == MediaType.USB_PHONE_STORAGE:
            return (
                "USB Phone Internal Storage: EraseVault will execute multi-pass CSPRNG/Zero overwriting, "
                "inode filename scrubbing, mandatory unallocated flash block shredding, and TRIM discard "
                "so deleted data cannot be recovered."
            )
        if media_type.is_solid_state_or_flash:
            if method.pass_count > 1:
                return (
                    f"Hardware Notice ({media_type.value}): '{method.display_name}' uses {method.pass_count} "
                    "passes. Solid-state and flash drives use Flash Translation Layer (FTL) wear-leveling; "
                    "single-pass NIST Clear + TRIM is recommended."
                )
            return (
                f"Hardware Notice ({media_type.value}): Due to SSD/flash wear-leveling and FTL remapping, "
                "file-level overwriting clears logical blocks; combine with TRIM or full-disk encryption for hardware retirement."
            )
        return ""
