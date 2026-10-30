"""
Background QThread workers for non-blocking execution of file erasure,
free-space wiping, drive sanitization, and on-demand verification.
"""

from __future__ import annotations

import threading
from typing import List, Optional

from ..core.models import (
    DriveInfo,
    ErasureMethod,
    MediaType,
    OperationRecord,
    ProgressSnapshot,
    VerificationResult,
)
from ..core.sanitizer import SanitizationEngine
from ..core.verifier import VerificationEngine
from .qt_compat import QThread, Signal


class FileErasureWorker(QThread):
    progress_updated = Signal(object)       # ProgressSnapshot
    operation_completed = Signal(object)    # OperationRecord
    operation_failed = Signal(str)

    def __init__(
        self,
        engine: SanitizationEngine,
        paths: List[str],
        method: ErasureMethod,
        verify_after: bool = True,
        obfuscate_metadata: bool = True,
        pad_cluster_slack: bool = True,
        parent: Optional[ object ] = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.paths = list(paths)
        self.method = method
        self.verify_after = verify_after
        self.obfuscate_metadata = obfuscate_metadata
        self.pad_cluster_slack = pad_cluster_slack
        self.cancel_event = threading.Event()
        self.last_record: Optional[OperationRecord] = None

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            rec = self.engine.erase_files_and_folders(
                paths=self.paths,
                method=self.method,
                verify_after=self.verify_after,
                obfuscate_metadata=self.obfuscate_metadata,
                pad_cluster_slack=self.pad_cluster_slack,
                progress_cb=lambda snap: self.progress_updated.emit(snap),
                cancel_event=self.cancel_event,
            )
            self.last_record = rec
            self.operation_completed.emit(rec)
        except Exception as exc:
            self.operation_failed.emit(str(exc))


class FreeSpaceWipeWorker(QThread):
    progress_updated = Signal(object)       # ProgressSnapshot
    operation_completed = Signal(object)    # OperationRecord
    operation_failed = Signal(str)

    def __init__(
        self,
        engine: SanitizationEngine,
        target_dir: str,
        method: ErasureMethod,
        reserve_bytes: int = 64 * 1024 * 1024,
        max_wipe_bytes: Optional[int] = None,
        flush_mft_slack: bool = True,
        use_windows_cipher: bool = False,
        parent: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.target_dir = target_dir
        self.method = method
        self.reserve_bytes = reserve_bytes
        self.max_wipe_bytes = max_wipe_bytes
        self.flush_mft_slack = flush_mft_slack
        self.use_windows_cipher = use_windows_cipher
        self.cancel_event = threading.Event()
        self.last_record: Optional[OperationRecord] = None

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            rec = self.engine.wipe_free_space(
                target_dir=self.target_dir,
                method=self.method,
                reserve_bytes=self.reserve_bytes,
                max_wipe_bytes=self.max_wipe_bytes,
                flush_mft_slack=self.flush_mft_slack,
                use_windows_cipher=self.use_windows_cipher,
                progress_cb=lambda snap: self.progress_updated.emit(snap),
                cancel_event=self.cancel_event,
            )
            self.last_record = rec
            self.operation_completed.emit(rec)
        except Exception as exc:
            self.operation_failed.emit(str(exc))


class DriveSanitizeWorker(QThread):
    progress_updated = Signal(object)       # ProgressSnapshot
    operation_completed = Signal(object)    # OperationRecord
    operation_failed = Signal(str)

    def __init__(
        self,
        engine: SanitizationEngine,
        drive: DriveInfo,
        method: ErasureMethod,
        free_space_limit_bytes: Optional[int] = 16 * 1024 * 1024,
        parent: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.drive = drive
        self.method = method
        self.free_space_limit_bytes = free_space_limit_bytes
        self.cancel_event = threading.Event()
        self.last_record: Optional[OperationRecord] = None

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            rec = self.engine.sanitize_drive(
                drive=self.drive,
                method=self.method,
                free_space_wipe_limit_bytes=self.free_space_limit_bytes,
                progress_cb=lambda snap: self.progress_updated.emit(snap),
                cancel_event=self.cancel_event,
            )
            self.last_record = rec
            self.operation_completed.emit(rec)
        except Exception as exc:
            self.operation_failed.emit(str(exc))


class OnDemandVerificationWorker(QThread):
    verification_completed = Signal(object)  # VerificationResult
    verification_failed = Signal(str)

    def __init__(
        self,
        target_path: str,
        media_type: MediaType = MediaType.SSD_NVME,
        parent: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self.target_path = target_path
        self.media_type = media_type
        self.last_result: Optional[VerificationResult] = None

    def run(self) -> None:
        try:
            res = VerificationEngine.verify_target_on_demand(
                self.target_path, media_type=self.media_type
            )
            self.last_result = res
            self.verification_completed.emit(res)
        except Exception as exc:
            self.verification_failed.emit(str(exc))
