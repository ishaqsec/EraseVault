"""
Hardware-aware storage and volume inspection + operating-system tool integration.
Supports:
- Windows (Win32 API, WMI/PowerShell Get-PhysicalDisk, cipher.exe, Optimize-Volume, fsutil)
- USB-connected Phone Internal Storages (ADB USB bridge `/sdcard` & `/storage/emulated/0`,
  Windows WPD/MTP & USB phone volume mounts, POSIX GVFS/MTP mounts, and user-mounted phone folders)
- Linux/macOS block device inspection and test harnesses.
"""

from __future__ import annotations

import ctypes
import glob
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .models import DriveInfo, MediaType

PHONE_KEYWORDS = (
    "phone",
    "android",
    "iphone",
    "ipad",
    "galaxy",
    "pixel",
    "xiaomi",
    "redmi",
    "poco",
    "oneplus",
    "realme",
    "oppo",
    "vivo",
    "huawei",
    "honor",
    "motorola",
    "nokia",
    "infinix",
    "tecno",
    "mtp",
    "internal shared storage",
    "internal storage",
)


class StorageInspector:
    """
    Inspects physical and logical storage devices, media types (SSD/NVMe, HDD, Removable Flash,
    and USB-Connected Phone Internal Storage), and system drive protection status.
    """

    def __init__(self) -> None:
        self._custom_drives: Dict[str, DriveInfo] = {}
        self._cached_drives: Optional[List[DriveInfo]] = None

    @staticmethod
    def is_phone_label_or_path(text: str) -> bool:
        low = (text or "").lower()
        return any(kw in low for kw in PHONE_KEYWORDS)

    def register_custom_drive(self, drive: DriveInfo) -> None:
        """Registers a virtual/test volume, removable mount, or USB phone internal storage."""
        norm = drive.mountpoint if drive.mountpoint.startswith("adb://") else os.path.abspath(drive.mountpoint)
        drive.mountpoint = norm
        self._custom_drives[norm] = drive
        self._cached_drives = None

    def register_usb_phone_storage(
        self,
        mountpoint: str,
        label: str = "Phone Internal Storage",
        model: str = "USB-Connected Smartphone (UFS / eMMC)",
        device_id: Optional[str] = None,
    ) -> DriveInfo:
        """
        Registers a USB-connected phone internal storage path (mounted folder, MTP mount, or ADB path)
        for multi-pass + free-space anti-recovery sanitization.
        """
        norm = mountpoint if mountpoint.startswith("adb://") else os.path.abspath(mountpoint)
        total, used, free = 64 * 1024**3, 16 * 1024**3, 48 * 1024**3
        if not norm.startswith("adb://") and os.path.exists(norm):
            try:
                usage = shutil.disk_usage(norm)
                total, used, free = usage.total, usage.used, usage.free
            except OSError:
                pass
        drv = DriveInfo(
            device_id=device_id or ("USB-PHONE:" + (os.path.basename(norm) or "INTERNAL")),
            mountpoint=norm,
            label=label,
            filesystem="F2FS / ext4 (Phone Flash)" if not norm.startswith("adb://") else "Android FBE / F2FS",
            total_bytes=total,
            used_bytes=used,
            free_bytes=free,
            media_type=MediaType.USB_PHONE_STORAGE,
            bus_type="USB Cable (MTP / ADB)",
            model=model,
            is_system_drive=False,
            is_boot_drive=False,
            is_removable=True,
            is_read_only=False,
            trim_supported=True,
        )
        self.register_custom_drive(drv)
        return drv

    def unregister_custom_drive(self, mountpoint: str) -> None:
        norm = mountpoint if mountpoint.startswith("adb://") else os.path.abspath(mountpoint)
        self._custom_drives.pop(norm, None)
        self._cached_drives = None

    def list_drives(self, refresh: bool = False) -> List[DriveInfo]:
        if self._cached_drives is not None and not refresh:
            return list(self._cached_drives)

        if os.name == "nt":
            drives = self._list_windows_drives()
        else:
            drives = self._list_posix_drives()

        # Discover USB-connected phones via ADB or MTP mounts
        usb_phones = self.detect_usb_connected_phones()
        existing_mounts = {
            (d.mountpoint if d.mountpoint.startswith("adb://") else os.path.abspath(d.mountpoint))
            for d in drives
        }
        for p_drv in usb_phones:
            key = p_drv.mountpoint if p_drv.mountpoint.startswith("adb://") else os.path.abspath(p_drv.mountpoint)
            if key not in existing_mounts:
                drives.append(p_drv)
                existing_mounts.add(key)

        # Merge registered custom/virtual/phone drives
        for mount, cdrive in self._custom_drives.items():
            if not mount.startswith("adb://") and os.path.exists(mount):
                try:
                    usage = shutil.disk_usage(mount)
                    cdrive.total_bytes = usage.total
                    cdrive.used_bytes = usage.used
                    cdrive.free_bytes = usage.free
                except OSError:
                    pass
            if mount in existing_mounts:
                drives = [
                    cdrive
                    if (d.mountpoint if d.mountpoint.startswith("adb://") else os.path.abspath(d.mountpoint)) == mount
                    else d
                    for d in drives
                ]
            else:
                drives.append(cdrive)

        self._cached_drives = drives
        return list(drives)

    def detect_usb_connected_phones(self) -> List[DriveInfo]:
        """
        Detects smartphones connected via USB cable:
        1. Android phones connected over USB with ADB (`adb devices -l`), querying `/sdcard` internal storage.
        2. Linux/POSIX GVFS MTP mounts (`/run/user/*/gvfs/mtp:host=*`) or `/media` / `/mnt` phone mounts.
        """
        phones: List[DriveInfo] = []

        # 1. Check ADB USB-connected Android phones
        adb_bin = shutil.which("adb")
        if adb_bin:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            try:
                res = subprocess.run(
                    [adb_bin, "devices", "-l"],
                    capture_output=True,
                    text=True,
                    timeout=1.5,
                    creationflags=creationflags,
                )
                if res.returncode == 0:
                    for line in res.stdout.splitlines()[1:]:
                        line = line.strip()
                        if not line or "offline" in line or "unauthorized" in line:
                            continue
                        parts = line.split()
                        if len(parts) >= 2 and parts[1] == "device":
                            serial = parts[0]
                            model = "Android Smartphone"
                            for tok in parts[2:]:
                                if tok.startswith("model:"):
                                    model = tok.split(":", 1)[1].replace("_", " ")
                            total_b, used_b, free_b = self._query_adb_phone_storage_usage(adb_bin, serial)
                            phones.append(
                                DriveInfo(
                                    device_id=f"ADB:{serial}",
                                    mountpoint=f"adb://{serial}/sdcard",
                                    label=f"{model} (Internal Storage)",
                                    filesystem="F2FS / ext4 (Android Internal)",
                                    total_bytes=total_b,
                                    used_bytes=used_b,
                                    free_bytes=free_b,
                                    media_type=MediaType.USB_PHONE_STORAGE,
                                    bus_type="USB Cable (ADB)",
                                    model=model,
                                    is_system_drive=False,
                                    is_boot_drive=False,
                                    is_removable=True,
                                    is_read_only=False,
                                    trim_supported=True,
                                )
                            )
            except Exception:
                pass

        # 2. Check GVFS MTP mounts on POSIX (`/run/user/*/gvfs/mtp*`)
        if os.name != "nt":
            for pattern in ("/run/user/*/gvfs/mtp*", "/run/user/*/gvfs/gphoto2*"):
                for mtp_dir in glob.glob(pattern):
                    if os.path.isdir(mtp_dir):
                        # Check if there is an 'Internal shared storage' or 'Internal storage' subfolder
                        target_mp = mtp_dir
                        try:
                            for sub in os.listdir(mtp_dir):
                                sub_full = os.path.join(mtp_dir, sub)
                                if os.path.isdir(sub_full) and ("internal" in sub.lower() or "storage" in sub.lower() or "phone" in sub.lower()):
                                    target_mp = sub_full
                                    break
                            usage = shutil.disk_usage(target_mp)
                            phones.append(
                                DriveInfo(
                                    device_id=f"MTP:{os.path.basename(mtp_dir)}",
                                    mountpoint=os.path.abspath(target_mp),
                                    label="USB Phone Internal Storage",
                                    filesystem="MTP / UFS Flash",
                                    total_bytes=usage.total,
                                    used_bytes=usage.used,
                                    free_bytes=usage.free,
                                    media_type=MediaType.USB_PHONE_STORAGE,
                                    bus_type="USB Cable (MTP)",
                                    model=os.path.basename(mtp_dir),
                                    is_system_drive=False,
                                    is_boot_drive=False,
                                    is_removable=True,
                                    trim_supported=True,
                                )
                            )
                        except OSError:
                            pass

        return phones

    @staticmethod
    def _query_adb_phone_storage_usage(adb_bin: str, serial: str) -> Tuple[int, int, int]:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            res = subprocess.run(
                [adb_bin, "-s", serial, "shell", "df", "-k", "/sdcard"],
                capture_output=True,
                text=True,
                timeout=1.5,
                creationflags=creationflags,
            )
            if res.returncode == 0:
                lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
                if len(lines) >= 2:
                    cols = lines[-1].split()
                    if len(cols) >= 4 and cols[1].isdigit() and cols[2].isdigit() and cols[3].isdigit():
                        total = int(cols[1]) * 1024
                        used = int(cols[2]) * 1024
                        free = int(cols[3]) * 1024
                        return (total, used, free)
        except Exception:
            pass
        return (64 * 1024**3, 16 * 1024**3, 48 * 1024**3)

    def get_drive_for_path(self, target_path: str) -> DriveInfo:
        """Resolves which mounted drive/volume or USB phone storage contains `target_path`."""
        if target_path.startswith("adb://"):
            for d in self.list_drives():
                if d.mountpoint == target_path or target_path.startswith(d.mountpoint.rstrip("/") + "/"):
                    return d
            return self.register_usb_phone_storage(target_path)

        abs_path = os.path.abspath(target_path)
        drives = self.list_drives()

        best_match: Optional[DriveInfo] = None
        best_len = -1
        for d in drives:
            if d.mountpoint.startswith("adb://"):
                continue
            mp = os.path.abspath(d.mountpoint)
            if os.name == "nt":
                if abs_path.lower().startswith(mp.lower()):
                    if len(mp) > best_len:
                        best_match = d
                        best_len = len(mp)
            else:
                if abs_path == mp or abs_path.startswith(mp.rstrip("/") + "/") or mp == "/":
                    if len(mp) > best_len:
                        best_match = d
                        best_len = len(mp)

        if best_match is not None:
            # If the path itself is inside a folder explicitly named as phone internal storage or MTP,
            # upgrade the detected media type to USB_PHONE_STORAGE
            if best_match.media_type != MediaType.USB_PHONE_STORAGE and (
                "mtp:" in abs_path.lower() or "internal shared storage" in abs_path.lower()
            ):
                return self.register_usb_phone_storage(abs_path)
            return best_match

        # Fallback drive info based on disk_usage
        try:
            probe = abs_path if os.path.exists(abs_path) else os.path.dirname(abs_path) or "."
            usage = shutil.disk_usage(probe)
            total, used, free = usage.total, usage.used, usage.free
        except OSError:
            total, used, free = 0, 0, 0

        root = os.path.splitdrive(abs_path)[0] + "\\" if os.name == "nt" else "/"
        return DriveInfo(
            device_id=root,
            mountpoint=root,
            label="System Volume",
            filesystem="NTFS" if os.name == "nt" else "ext4",
            total_bytes=total,
            used_bytes=used,
            free_bytes=free,
            media_type=MediaType.SSD_NVME,
            is_system_drive=True,
            is_boot_drive=True,
            trim_supported=True,
            protection_reason="Operating system root volume",
        )

    def _list_windows_drives(self) -> List[DriveInfo]:
        drives: List[DriveInfo] = []
        sys_drive = os.environ.get("SystemDrive", "C:").upper().rstrip("\\") + "\\"
        win_dir = os.environ.get("SystemRoot", r"C:\Windows").upper()

        phys_map = self._query_windows_physical_disks()
        trim_enabled = self._query_windows_trim_enabled()

        DRIVE_UNKNOWN = 0
        DRIVE_NO_ROOT_DIR = 1
        DRIVE_REMOVABLE = 2
        DRIVE_FIXED = 3
        DRIVE_REMOTE = 4
        DRIVE_CDROM = 5
        DRIVE_RAMDISK = 6

        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        except Exception:
            bitmask = 0b0100  # C: fallback

        for i in range(26):
            if not (bitmask & (1 << i)):
                continue
            letter = chr(ord("A") + i)
            mount = f"{letter}:\\"
            try:
                dtype = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(mount))
            except Exception:
                dtype = DRIVE_FIXED

            if dtype in (DRIVE_UNKNOWN, DRIVE_NO_ROOT_DIR, DRIVE_CDROM):
                continue

            try:
                usage = shutil.disk_usage(mount)
                total, used, free = usage.total, usage.used, usage.free
            except OSError:
                continue

            label, fs_name, is_ro = self._get_windows_volume_info(mount)
            info_meta = phys_map.get(letter, {})
            mtype_str = str(info_meta.get("MediaType", "")).upper()
            bus_str = str(info_meta.get("BusType", "SATA/NVMe"))
            model_str = str(info_meta.get("FriendlyName", "Windows Logical Volume"))

            if self.is_phone_label_or_path(label) or self.is_phone_label_or_path(model_str):
                media_type = MediaType.USB_PHONE_STORAGE
            elif dtype == DRIVE_REMOVABLE or "USB" in bus_str.upper():
                media_type = MediaType.REMOVABLE_FLASH
            elif "SSD" in mtype_str or "NVME" in bus_str.upper() or "SCM" in mtype_str:
                media_type = MediaType.SSD_NVME
            elif "HDD" in mtype_str:
                media_type = MediaType.HDD
            elif dtype == DRIVE_RAMDISK:
                media_type = MediaType.VIRTUAL
            else:
                media_type = MediaType.SSD_NVME

            is_sys = (mount.upper() == sys_drive) or win_dir.startswith(mount.upper())
            exe_drive = (os.path.splitdrive(sys.executable)[0] + "\\").upper()
            is_boot = is_sys or (mount.upper() == exe_drive and letter == "C")
            prot_reason = ""
            if is_sys:
                prot_reason = f"Active Windows System & Boot Volume ({mount})"
            elif is_ro:
                prot_reason = "Volume is mounted Read-Only"

            drives.append(
                DriveInfo(
                    device_id=f"\\\\.\\{letter}:",
                    mountpoint=mount,
                    label=label or ("Local Disk" if not is_sys else "Windows OS"),
                    filesystem=fs_name or "NTFS",
                    total_bytes=total,
                    used_bytes=used,
                    free_bytes=free,
                    media_type=media_type,
                    bus_type=bus_str,
                    model=model_str,
                    is_system_drive=is_sys,
                    is_boot_drive=is_boot,
                    is_removable=(dtype == DRIVE_REMOVABLE or media_type == MediaType.USB_PHONE_STORAGE),
                    is_read_only=is_ro,
                    trim_supported=(media_type.is_solid_state_or_flash and trim_enabled),
                    protection_reason=prot_reason,
                )
            )
        return drives

    def _get_windows_volume_info(self, mount: str) -> Tuple[str, str, bool]:
        if os.name != "nt":
            return ("", "NTFS", False)
        vol_name_buf = ctypes.create_unicode_buffer(261)
        fs_name_buf = ctypes.create_unicode_buffer(261)
        serial = ctypes.c_ulong(0)
        max_comp_len = ctypes.c_ulong(0)
        fs_flags = ctypes.c_ulong(0)
        FILE_READ_ONLY_VOLUME = 0x00080000
        try:
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(mount),
                vol_name_buf,
                ctypes.sizeof(vol_name_buf),
                ctypes.byref(serial),
                ctypes.byref(max_comp_len),
                ctypes.byref(fs_flags),
                fs_name_buf,
                ctypes.sizeof(fs_name_buf),
            )
            if ok:
                is_ro = bool(fs_flags.value & FILE_READ_ONLY_VOLUME)
                return (vol_name_buf.value, fs_name_buf.value, is_ro)
        except Exception:
            pass
        return ("", "NTFS", False)

    def _query_windows_physical_disks(self) -> Dict[str, Dict[str, str]]:
        if os.name != "nt":
            return {}
        ps_script = (
            "Get-Partition | Where-Object {$_.DriveLetter} | ForEach-Object { "
            "$dl = $_.DriveLetter; "
            "$d = Get-PhysicalDisk -DiskNumber $_.DiskNumber -ErrorAction SilentlyContinue; "
            "[PSCustomObject]@{DriveLetter=[string]$dl; FriendlyName=[string]$d.FriendlyName; "
            "MediaType=[string]$d.MediaType; BusType=[string]$d.BusType} "
            "} | ConvertTo-Json -Compress"
        )
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=3.0,
                creationflags=creationflags,
            )
            if res.returncode == 0 and res.stdout.strip():
                raw = json.loads(res.stdout.strip())
                items = raw if isinstance(raw, list) else [raw]
                out: Dict[str, Dict[str, str]] = {}
                for it in items:
                    dl = str(it.get("DriveLetter", "")).strip().upper()
                    if dl:
                        out[dl] = it
                return out
        except Exception:
            pass
        return {}

    def _query_windows_trim_enabled(self) -> bool:
        if os.name != "nt":
            return True
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            res = subprocess.run(
                ["fsutil", "behavior", "query", "DisableDeleteNotify"],
                capture_output=True,
                text=True,
                timeout=2.0,
                creationflags=creationflags,
            )
            if "DisableDeleteNotify = 0" in res.stdout:
                return True
        except Exception:
            pass
        return True

    def _list_posix_drives(self) -> List[DriveInfo]:
        drives: List[DriveInfo] = []
        seen_mounts = set()
        ignored_fs = {
            "proc", "sysfs", "devtmpfs", "devpts", "tmpfs", "cgroup", "cgroup2",
            "pstore", "bpf", "tracefs", "debugfs", "securityfs", "mqueue",
            "hugetlbfs", "fusectl", "configfs", "autofs", "squashfs", "nsfs",
        }
        mounts_file = "/proc/mounts" if os.path.exists("/proc/mounts") else None
        entries: List[Tuple[str, str, str, str]] = []
        if mounts_file:
            try:
                with open(mounts_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 4:
                            entries.append((parts[0], parts[1], parts[2], parts[3]))
            except OSError:
                pass

        if not entries:
            entries.append(("/dev/root", "/", "ext4", "rw"))

        for dev, mp, fstype, opts in entries:
            if fstype in ignored_fs and mp not in ("/", "/tmp"):
                continue
            if mp.startswith(("/proc", "/sys", "/dev", "/run")) and mp != "/":
                continue
            if mp in seen_mounts:
                continue
            seen_mounts.add(mp)

            try:
                usage = shutil.disk_usage(mp)
                if usage.total <= 0:
                    continue
            except OSError:
                continue

            media_type, bus_type, model, is_rem = self._probe_linux_block_device(dev)
            if self.is_phone_label_or_path(mp) or self.is_phone_label_or_path(model):
                media_type = MediaType.USB_PHONE_STORAGE
                is_rem = True

            is_ro = "ro" in opts.split(",")
            is_sys = mp in ("/", "/boot", "/usr", "/var", "/etc", "/working_dir") or os.path.abspath(
                __file__
            ).startswith(mp.rstrip("/") + "/") if mp != "/" else True

            prot_reason = ""
            if mp == "/":
                prot_reason = "Active Operating System Root Volume (/)"
            elif is_sys and mp != "/tmp":
                prot_reason = f"Protected System / Workspace Mount ({mp})"
            elif is_ro:
                prot_reason = "Volume is mounted Read-Only"

            label = "System Root" if mp == "/" else os.path.basename(mp.rstrip("/")) or mp
            drives.append(
                DriveInfo(
                    device_id=dev,
                    mountpoint=mp,
                    label=label,
                    filesystem=fstype,
                    total_bytes=usage.total,
                    used_bytes=usage.used,
                    free_bytes=usage.free,
                    media_type=media_type,
                    bus_type=bus_type,
                    model=model,
                    is_system_drive=(mp == "/" or is_sys),
                    is_boot_drive=(mp in ("/", "/boot")),
                    is_removable=is_rem,
                    is_read_only=is_ro,
                    trim_supported=media_type.is_solid_state_or_flash,
                    protection_reason=prot_reason,
                )
            )
        return drives

    def _probe_linux_block_device(self, dev: str) -> Tuple[MediaType, str, str, bool]:
        base = os.path.basename(dev)
        if base.startswith("nvme") and "p" in base:
            disk_name = base.rsplit("p", 1)[0]
        else:
            disk_name = base.rstrip("0123456789")

        sys_block = f"/sys/block/{disk_name}"
        is_rem = False
        if os.path.exists(f"{sys_block}/removable"):
            try:
                with open(f"{sys_block}/removable", "r") as f:
                    is_rem = f.read().strip() == "1"
            except OSError:
                pass

        model = "Solid State Volume"
        if os.path.exists(f"{sys_block}/device/model"):
            try:
                with open(f"{sys_block}/device/model", "r") as f:
                    model = f.read().strip() or model
            except OSError:
                pass

        if is_rem:
            return (MediaType.REMOVABLE_FLASH, "USB", model, True)
        if base.startswith("loop"):
            return (MediaType.VIRTUAL, "Loopback", "Virtual Disk Image", False)
        if base.startswith("nvme"):
            return (MediaType.SSD_NVME, "NVMe", model, False)

        rot_file = f"{sys_block}/queue/rotational"
        if os.path.exists(rot_file):
            try:
                with open(rot_file, "r") as f:
                    if f.read().strip() == "0":
                        return (MediaType.SSD_NVME, "SATA/NVMe", model, False)
                    else:
                        return (MediaType.HDD, "SATA", model or "Magnetic HDD", False)
            except OSError:
                pass

        return (MediaType.SSD_NVME, "Virtual/NVMe", model, False)

    @staticmethod
    def run_windows_cipher_wipe(
        target_dir: str,
        progress_cb: Optional[Callable[[str, float], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Tuple[bool, str]:
        if os.name != "nt":
            return (False, "Windows cipher.exe is only available on Windows hosts.")

        cipher_exe = shutil.which("cipher.exe") or r"C:\Windows\System32\cipher.exe"
        if not os.path.exists(cipher_exe):
            return (False, "cipher.exe was not found in System32.")

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.Popen(
                [cipher_exe, f"/w:{os.path.abspath(target_dir)}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=creationflags,
            )
            output_lines: List[str] = []
            while proc.poll() is None:
                if cancel_event and cancel_event.is_set():
                    proc.terminate()
                    return (False, "Windows cipher.exe free-space wipe cancelled by user.")
                if proc.stdout:
                    line = proc.stdout.readline()
                    if line:
                        clean = line.strip()
                        output_lines.append(clean)
                        if "0x00" in clean and progress_cb:
                            progress_cb("Windows cipher.exe: Writing 0x00 pass...", 20.0)
                        elif "0xFF" in clean and progress_cb:
                            progress_cb("Windows cipher.exe: Writing 0xFF pass...", 55.0)
                        elif "Random" in clean and progress_cb:
                            progress_cb("Windows cipher.exe: Writing Random Numbers pass...", 85.0)
            rc = proc.wait(timeout=5.0)
            if rc == 0:
                return (True, "\n".join(output_lines[-10:]))
            return (False, f"cipher.exe exited with code {rc}")
        except Exception as exc:
            return (False, f"Failed to execute cipher.exe: {exc}")

    @staticmethod
    def run_ssd_trim_optimize(mountpoint: str) -> Tuple[bool, str]:
        """Issues OS-level or ADB TRIM / ReTrim on a volume or USB phone storage if supported."""
        if mountpoint.startswith("adb://"):
            adb_bin = shutil.which("adb")
            if not adb_bin:
                return (False, "ADB binary not available for hardware fstrim.")
            rest = mountpoint[len("adb://"):]
            serial = rest.split("/", 1)[0]
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            try:
                res = subprocess.run(
                    [adb_bin, "-s", serial, "shell", "sm", "fstrim"],
                    capture_output=True,
                    text=True,
                    timeout=15.0,
                    creationflags=creationflags,
                )
                if res.returncode == 0:
                    return (True, f"USB Phone flash controller TRIM (sm fstrim) completed on {serial}.")
            except Exception as exc:
                return (False, f"Phone flash TRIM skipped: {exc}")
            return (False, "Phone flash TRIM requires ADB permissions.")

        if os.name == "nt":
            drive_letter = os.path.splitdrive(os.path.abspath(mountpoint))[0].rstrip(":")
            if not drive_letter:
                return (False, "Could not determine drive letter for Optimize-Volume.")
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            try:
                res = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        f"Optimize-Volume -DriveLetter {drive_letter} -ReTrim -ErrorAction Stop",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30.0,
                    creationflags=creationflags,
                )
                if res.returncode == 0:
                    return (True, f"Windows Optimize-Volume -ReTrim completed on {drive_letter}:.")
                return (
                    False,
                    f"Optimize-Volume -ReTrim skipped or requires elevation: {res.stderr.strip() or res.stdout.strip()}",
                )
            except Exception as exc:
                return (False, f"Optimize-Volume -ReTrim unavailable: {exc}")
        else:
            fstrim = shutil.which("fstrim")
            if not fstrim:
                return (False, "OS TRIM utility (fstrim) not installed or not applicable.")
            try:
                res = subprocess.run(
                    [fstrim, "-v", mountpoint],
                    capture_output=True,
                    text=True,
                    timeout=15.0,
                )
                if res.returncode == 0:
                    return (True, f"fstrim completed: {res.stdout.strip()}")
                return (False, f"fstrim requires root/device support: {res.stderr.strip()}")
            except Exception as exc:
                return (False, f"fstrim execution skipped: {exc}")
