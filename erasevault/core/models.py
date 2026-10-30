"""
Data models and enumeration definitions for EraseVault.
Includes support for SSD/NVMe, Magnetic HDD, Removable USB Flash, and USB-Connected Phone Internal Storage.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any


class MediaType(str, Enum):
    HDD = "HDD (Magnetic Rotational)"
    SSD_NVME = "SSD / NVMe (Solid State)"
    REMOVABLE_FLASH = "Removable USB / Flash"
    USB_PHONE_STORAGE = "USB Phone Internal Storage (UFS / eMMC)"
    VIRTUAL = "Virtual / Loopback Disk"
    UNKNOWN = "Unknown Storage Media"

    @property
    def is_solid_state_or_flash(self) -> bool:
        return self in (
            MediaType.SSD_NVME,
            MediaType.REMOVABLE_FLASH,
            MediaType.USB_PHONE_STORAGE,
        )

    @property
    def is_usb_phone(self) -> bool:
        return self == MediaType.USB_PHONE_STORAGE


class OperationType(str, Enum):
    ERASE_FILES = "Erase Files"
    ERASE_DRIVE = "Erase Drives"
    ERASE_PHONE_STORAGE = "Erase USB Phone Internal Storage"
    WIPE_FREE_SPACE = "Wipe Free Space"
    VERIFY_ONLY = "Verify Data Removal"


class OperationStatus(str, Enum):
    COMPLETED = "Completed"
    COMPLETED_WITH_WARNINGS = "Completed (With Hardware Caveats)"
    PARTIAL_FAILURE = "Partially Failed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class VerificationLevel(str, Enum):
    VERIFIED_OVERWRITTEN = "Verified Overwritten"
    CLEARED_WITH_SSD_CAVEAT = "Cleared (SSD/Flash Wear-Leveling Caveat)"
    VERIFICATION_FAILED = "Verification Failed"
    NOT_VERIFIED = "Not Verified"


@dataclass(frozen=True)
class ErasureMethod:
    id: str
    display_name: str
    short_description: str
    detailed_description: str
    passes: Tuple[str, ...]  # 'zero', 'ones', 'random', or hex byte like 'hex:96'
    verify_after: bool
    ssd_recommended: bool
    standard_reference: str

    @property
    def pass_count(self) -> int:
        return len(self.passes)


# Gutmann 35-pass deterministic central patterns (passes 5..31) surrounded by 4 random passes on each side
GUTMANN_PATTERNS: Tuple[str, ...] = (
    "random", "random", "random", "random",
    "hex:555555", "hex:AAAAAA", "hex:924924", "hex:492492", "hex:249249",
    "zero", "hex:111111", "hex:222222", "hex:333333", "hex:444444",
    "hex:555555", "hex:666666", "hex:777777", "hex:888888", "hex:999999",
    "hex:AAAAAA", "hex:BBBBBB", "hex:CCCCCC", "hex:DDDDDD", "hex:EEEEEE",
    "ones", "hex:924924", "hex:492492", "hex:249249", "hex:6DB6DB",
    "hex:B6DB6D", "hex:DB6DB6",
    "random", "random", "random", "random",
)


ERASURE_METHODS: Tuple[ErasureMethod, ...] = (
    ErasureMethod(
        id="quick_erase",
        display_name="Quick Erase",
        short_description="1 pass zero-fill + metadata scrub",
        detailed_description=(
            "Overwrites data once with zeros (0x00), scrubs metadata & filenames, "
            "and verifies removal. Fast baseline for everyday SSD and flash cleanup."
        ),
        passes=("zero",),
        verify_after=True,
        ssd_recommended=True,
        standard_reference="NIST SP 800-88 Rev. 1 Clear (Zero-Fill)",
    ),
    ErasureMethod(
        id="nist_clear",
        display_name="NIST 800-88 Clear",
        short_description="1 pass cryptographic random + verify",
        detailed_description=(
            "Overwrites all blocks with cryptographic random bytes (CSPRNG), scrubs metadata, "
            "shreds unallocated phone/flash blocks when applicable, and verifies removal."
        ),
        passes=("random",),
        verify_after=True,
        ssd_recommended=True,
        standard_reference="NIST SP 800-88 Rev. 1 (CSPRNG Clear)",
    ),
    ErasureMethod(
        id="dod_3pass",
        display_name="DoD 5220.22-M (3-Pass)",
        short_description="3 passes (0x00, 0xFF, Random + Verify)",
        detailed_description=(
            "Overwrites targets in 3 passes (0x00, 0xFF, CSPRNG random) with read-back "
            "verification. Recommended for magnetic HDDs and deep partition wiping."
        ),
        passes=("zero", "ones", "random"),
        verify_after=True,
        ssd_recommended=False,
        standard_reference="US DoD 5220.22-M (E)",
    ),
    ErasureMethod(
        id="dod_7pass",
        display_name="DoD 5220.22-M ECE (7-Pass)",
        short_description="7 passes (Extended DoD magnetic standard)",
        detailed_description=(
            "Overwrites magnetic sectors across 7 passes (0x00, 0xFF, Random, 0x96, "
            "0x00, 0xFF, Random) with hardware cache flush after every pass."
        ),
        passes=("zero", "ones", "random", "hex:96", "zero", "ones", "random"),
        verify_after=True,
        ssd_recommended=False,
        standard_reference="US DoD 5220.22-M (ECE)",
    ),
    ErasureMethod(
        id="schneier_7pass",
        display_name="Schneier (7-Pass)",
        short_description="7 passes (0xFF, 0x00 + 5 CSPRNG passes)",
        detailed_description=(
            "Overwrites sectors with 0xFF, 0x00, and 5 consecutive cryptographically "
            "random CSPRNG passes to defeat forensic magnetic recovery."
        ),
        passes=("ones", "zero", "random", "random", "random", "random", "random"),
        verify_after=True,
        ssd_recommended=False,
        standard_reference="Bruce Schneier (Applied Cryptography)",
    ),
    ErasureMethod(
        id="gutmann_35pass",
        display_name="Gutmann (35-Pass Legacy)",
        short_description="35 passes (legacy magnetic media only)",
        detailed_description=(
            "Executes all 35 Peter Gutmann deterministic & random passes for legacy "
            "magnetic drives. Not needed for modern SSDs or flash media."
        ),
        passes=GUTMANN_PATTERNS,
        verify_after=True,
        ssd_recommended=False,
        standard_reference="Peter Gutmann (1996 Magnetic Media Paper)",
    ),
)

ERASURE_METHOD_MAP: Dict[str, ErasureMethod] = {m.id: m for m in ERASURE_METHODS}


def get_erasure_method(method_id_or_name: str) -> ErasureMethod:
    if method_id_or_name in ERASURE_METHOD_MAP:
        return ERASURE_METHOD_MAP[method_id_or_name]
    for m in ERASURE_METHODS:
        if m.display_name.lower() == method_id_or_name.lower():
            return m
    return ERASURE_METHODS[0]


@dataclass
class DriveInfo:
    device_id: str
    mountpoint: str
    label: str
    filesystem: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    media_type: MediaType
    bus_type: str = "SATA/NVMe"
    model: str = "Local Storage Volume"
    is_system_drive: bool = False
    is_boot_drive: bool = False
    is_removable: bool = False
    is_read_only: bool = False
    trim_supported: bool = False
    protection_reason: str = ""

    @property
    def is_protected(self) -> bool:
        return self.is_system_drive or self.is_boot_drive or bool(self.protection_reason)

    @property
    def display_title(self) -> str:
        lbl = f" ({self.label})" if self.label else ""
        sys_tag = " [SYSTEM PROTECTED]" if self.is_protected else ""
        return f"{self.mountpoint}{lbl} — {format_bytes(self.total_bytes)} [{self.media_type.value}]{sys_tag}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["media_type"] = self.media_type.value
        return d


@dataclass
class TargetItem:
    path: str
    item_type: str  # 'file', 'folder', 'drive', 'free_space'
    size_bytes: int = 0
    file_count: int = 0
    folder_count: int = 0
    media_type: MediaType = MediaType.UNKNOWN
    drive_mount: str = ""
    is_symlink: bool = False
    is_valid: bool = True
    validation_error: str = ""
    ssd_warning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["media_type"] = self.media_type.value
        return d


@dataclass
class ProgressSnapshot:
    operation_type: OperationType
    phase: str
    current_target: str
    current_pass: int
    total_passes: int
    bytes_processed: int
    total_bytes: int
    items_processed: int
    total_items: int
    throughput_mbps: float = 0.0
    percent: float = 0.0
    can_cancel: bool = True


@dataclass
class VerificationResult:
    verified: bool
    verification_level: VerificationLevel
    summary: str
    path_removed: bool
    bytes_sampled: int
    zero_ratio: float
    entropy_bits_per_byte: float
    residual_signatures_found: List[str] = field(default_factory=list)
    hardware_caveat: str = ""
    checked_paths: List[str] = field(default_factory=list)
    certificate_sha256: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["verification_level"] = self.verification_level.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationResult":
        lvl_str = data.get("verification_level", VerificationLevel.NOT_VERIFIED.value)
        lvl = VerificationLevel.NOT_VERIFIED
        for item in VerificationLevel:
            if item.value == lvl_str or item.name == lvl_str:
                lvl = item
                break
        return cls(
            verified=bool(data.get("verified", False)),
            verification_level=lvl,
            summary=str(data.get("summary", "")),
            path_removed=bool(data.get("path_removed", False)),
            bytes_sampled=int(data.get("bytes_sampled", 0)),
            zero_ratio=float(data.get("zero_ratio", 0.0)),
            entropy_bits_per_byte=float(data.get("entropy_bits_per_byte", 0.0)),
            residual_signatures_found=list(data.get("residual_signatures_found", [])),
            hardware_caveat=str(data.get("hardware_caveat", "")),
            checked_paths=list(data.get("checked_paths", [])),
            certificate_sha256=str(data.get("certificate_sha256", "")),
        )


@dataclass
class OperationRecord:
    op_id: str
    timestamp_start: str
    timestamp_end: str
    operation_type: str
    method_id: str
    method_name: str
    passes_completed: int
    targets: List[str]
    total_bytes_processed: int
    files_erased: int
    folders_removed: int
    status: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    verification: Optional[VerificationResult] = None
    media_summary: str = ""
    host_info: Dict[str, str] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        from datetime import datetime
        try:
            t1 = datetime.fromisoformat(self.timestamp_start)
            t2 = datetime.fromisoformat(self.timestamp_end)
            return max(0.0, (t2 - t1).total_seconds())
        except Exception:
            return 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.verification is not None:
            d["verification"] = self.verification.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperationRecord":
        ver_raw = data.get("verification")
        ver = VerificationResult.from_dict(ver_raw) if isinstance(ver_raw, dict) else None
        return cls(
            op_id=str(data.get("op_id", "")),
            timestamp_start=str(data.get("timestamp_start", "")),
            timestamp_end=str(data.get("timestamp_end", "")),
            operation_type=str(data.get("operation_type", "")),
            method_id=str(data.get("method_id", "")),
            method_name=str(data.get("method_name", "")),
            passes_completed=int(data.get("passes_completed", 0)),
            targets=list(data.get("targets", [])),
            total_bytes_processed=int(data.get("total_bytes_processed", 0)),
            files_erased=int(data.get("files_erased", 0)),
            folders_removed=int(data.get("folders_removed", 0)),
            status=str(data.get("status", "")),
            errors=list(data.get("errors", [])),
            warnings=list(data.get("warnings", [])),
            verification=ver,
            media_summary=str(data.get("media_summary", "")),
            host_info=dict(data.get("host_info", {})),
        )


def format_bytes(num_bytes: float) -> str:
    if num_bytes < 0:
        num_bytes = 0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(num_bytes)} B"
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"
