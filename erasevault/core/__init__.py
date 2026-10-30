"""
Core data sanitization, hardware detection, verification, and reporting modules for EraseVault.
"""

from .models import (
    ErasureMethod,
    ERASURE_METHODS,
    get_erasure_method,
    MediaType,
    OperationType,
    OperationStatus,
    VerificationLevel,
    DriveInfo,
    TargetItem,
    ProgressSnapshot,
    VerificationResult,
    OperationRecord,
)
from .storage import StorageInspector
from .validator import TargetValidator, ValidationError, SystemDriveProtectionError
from .sanitizer import SanitizationEngine
from .verifier import VerificationEngine
from .history import HistoryManager
from .reports import ReportGenerator
from .settings import SettingsManager

__all__ = [
    "ErasureMethod",
    "ERASURE_METHODS",
    "get_erasure_method",
    "MediaType",
    "OperationType",
    "OperationStatus",
    "VerificationLevel",
    "DriveInfo",
    "TargetItem",
    "ProgressSnapshot",
    "VerificationResult",
    "OperationRecord",
    "StorageInspector",
    "TargetValidator",
    "ValidationError",
    "SystemDriveProtectionError",
    "SanitizationEngine",
    "VerificationEngine",
    "HistoryManager",
    "ReportGenerator",
    "SettingsManager",
]
