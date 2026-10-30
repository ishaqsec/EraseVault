"""
Unit and integration test suite for EraseVault:
- Core sanitization algorithms (Quick 1-pass, NIST Clear, DoD 3-pass, DoD 7-pass, Schneier 7-pass, Gutmann 35-pass)
- Read-only file handling, nested directory erasure, and symlink non-traversal safety
- Strict system-drive and critical directory safeguards (Windows C:\\, C:\\Windows & POSIX /)
- Free-space wiping and guaranteed temporary container cleanup (normal & cancelled)
- Supported non-system drive, raw disk image, and USB-Connected Phone Internal Storage sanitization
  (with 3-stage anti-recovery: multi-pass CSPRNG/Zero overwrite + filename obfuscation + flash block shredding + verification)
- Post-erasure verification, signature scanning, Shannon entropy, and honest SSD wear-leveling caveats
- Persistent SQLite history & tamper-evident SHA-256 HTML/JSON/TXT audit reports (with previous records cleared on fresh app startup)
- Optimized Main Menu:
  * Larger 44x34 window controls (18x18 icons)
  * Wider default window (REF_WIDTH=1440) with native mouse edge/corner resizing (WM_NCHITTEST + QSizeGrip)
  * 'Auto' indicator shown directly on the auto-selected method in the dropdown
  * Centered completion percentage (%p%) inside the Royal Blue Progress Bar
  * Progress Bar and Start/Stop buttons moved down to the bottom of the workspace card and 100% left/right justified
"""

from __future__ import annotations

import os
import stat
import tempfile
import threading
import unittest

from erasevault.core import (
    DriveInfo,
    HistoryManager,
    MediaType,
    OperationStatus,
    ReportGenerator,
    SanitizationEngine,
    SettingsManager,
    StorageInspector,
    SystemDriveProtectionError,
    TargetValidator,
    VerificationEngine,
    VerificationLevel,
    get_erasure_method,
)
from erasevault.ui.dialogs import DestructiveConfirmationDialog, MethodInfoDialog
from erasevault.ui.main_window import EraseVaultMainWindow, REF_WIDTH
from erasevault.ui.panels import HomeWorkspacePanel
from erasevault.ui.qt_compat import QApplication, QFileDialog, QFrame, QScreen, Qt
from erasevault.ui.styles import DARK_THEME, LIGHT_THEME


class TestEraseVaultCore(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = self.temp_dir.name
        self.storage = StorageInspector()
        self.validator = TargetValidator(self.storage)
        self.engine = SanitizationEngine(self.storage, self.validator)
        self.db_path = os.path.join(self.root, "test_history.db")
        self.history = HistoryManager(self.db_path)
        self.settings_path = os.path.join(self.root, "test_settings.json")
        self.settings_mgr = SettingsManager(self.settings_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_system_drive_and_critical_path_safeguards(self) -> None:
        """System drives and critical OS paths must be strictly blocked."""
        protected_candidates = [
            "C:\\",
            "C:\\Windows",
            "C:\\Windows\\System32",
            "C:\\Program Files",
            "/",
            "/boot",
            "/usr",
            "/etc",
            self.validator.app_root,
        ]
        for path in protected_candidates:
            is_prot, reason = self.validator.is_protected_system_path(path)
            self.assertTrue(is_prot, f"Expected {path} to be protected")
            self.assertTrue(len(reason) > 5)

        with self.assertRaises(SystemDriveProtectionError):
            self.engine.erase_files_and_folders(
                ["/etc"], method=get_erasure_method("quick_erase")
            )

        sys_drive = DriveInfo(
            device_id="\\\\.\\C:",
            mountpoint="C:\\",
            label="Windows OS",
            filesystem="NTFS",
            total_bytes=500 * 1024**3,
            used_bytes=200 * 1024**3,
            free_bytes=300 * 1024**3,
            media_type=MediaType.SSD_NVME,
            is_system_drive=True,
            is_boot_drive=True,
            protection_reason="Active Windows System Drive",
        )
        with self.assertRaises(SystemDriveProtectionError):
            self.engine.sanitize_drive(sys_drive, get_erasure_method("quick_erase"))

    def test_file_and_folder_erasure_methods_and_readonly(self) -> None:
        """All sanitization methods must overwrite, verify, obfuscate, and unlink files & folders."""
        for method_id in ("quick_erase", "nist_clear", "dod_3pass", "dod_7pass", "schneier_7pass", "gutmann_35pass"):
            sub = os.path.join(self.root, f"batch_{method_id}")
            nested = os.path.join(sub, "nested_dir")
            os.makedirs(nested, exist_ok=True)

            f1 = os.path.join(sub, "secret_doc.pdf")
            f2 = os.path.join(nested, "readonly_db.sqlite")
            with open(f1, "wb") as fh:
                fh.write(b"%PDF-1.7\nConfidential financial payload " * 64)
            with open(f2, "wb") as fh:
                fh.write(b"SQLite format 3\x00" + os.urandom(4096))
            os.chmod(f2, stat.S_IREAD)

            progress_events = []
            method = get_erasure_method(method_id)
            rec = self.engine.erase_files_and_folders(
                paths=[f1, nested],
                method=method,
                verify_after=True,
                obfuscate_metadata=True,
                progress_cb=lambda snap: progress_events.append(snap),
            )

            self.assertFalse(os.path.exists(f1))
            self.assertFalse(os.path.exists(f2))
            self.assertFalse(os.path.exists(nested))
            self.assertEqual(rec.files_erased, 2)
            self.assertEqual(rec.folders_removed, 1)
            self.assertEqual(rec.passes_completed, method.pass_count)
            self.assertTrue(len(progress_events) > 0)
            self.assertIsNotNone(rec.verification)
            self.assertTrue(rec.verification.verified)
            self.assertTrue(rec.verification.path_removed)
            self.assertEqual(rec.verification.residual_signatures_found, [])

    def test_cancellation_halts_operation_cleanly(self) -> None:
        """Setting cancel_event must cleanly stop file erasure or free-space wiping."""
        f_cancel = os.path.join(self.root, "cancel_target.bin")
        with open(f_cancel, "wb") as f:
            f.write(os.urandom(32768))

        cancel_ev = threading.Event()
        cancel_ev.set()

        rec = self.engine.erase_files_and_folders(
            paths=[f_cancel],
            method=get_erasure_method("dod_3pass"),
            cancel_event=cancel_ev,
        )
        self.assertEqual(rec.status, OperationStatus.CANCELLED.value)
        self.assertTrue(os.path.exists(f_cancel))

    def test_symlink_safety_does_not_erase_external_target(self) -> None:
        """Erasing a folder containing a symlink must unlink the symlink without touching the target."""
        external_dir = os.path.join(self.root, "external_keep")
        os.makedirs(external_dir, exist_ok=True)
        external_file = os.path.join(external_dir, "important.txt")
        with open(external_file, "wb") as f:
            f.write(b"DO NOT ERASE THIS EXTERNAL FILE")

        victim_dir = os.path.join(self.root, "victim_folder")
        os.makedirs(victim_dir, exist_ok=True)
        os.symlink(external_file, os.path.join(victim_dir, "link_to_file.txt"))
        os.symlink(external_dir, os.path.join(victim_dir, "link_to_dir"))

        rec = self.engine.erase_files_and_folders(
            paths=[victim_dir],
            method=get_erasure_method("quick_erase"),
        )
        self.assertFalse(os.path.exists(victim_dir))
        self.assertTrue(os.path.exists(external_file))
        with open(external_file, "rb") as f:
            self.assertEqual(f.read(), b"DO NOT ERASE THIS EXTERNAL FILE")
        self.assertEqual(rec.errors, [])

    def test_supported_drive_and_raw_image_sanitization(self) -> None:
        """Non-system drives and raw disk images must be sanitized and verified free of signatures."""
        img_path = os.path.join(self.root, "removable_disk.img")
        with open(img_path, "wb") as f:
            f.write(b"%PDF-1.5 secret header " + b"PK\x03\x04 archive " + os.urandom(128 * 1024))

        pre_ver = VerificationEngine.verify_target_on_demand(img_path, MediaType.HDD)
        self.assertFalse(pre_ver.verified)
        self.assertTrue(len(pre_ver.residual_signatures_found) >= 2)

        img_drive = DriveInfo(
            device_id="LOOP0",
            mountpoint=img_path,
            label="Test Disk Image",
            filesystem="RAW",
            total_bytes=os.path.getsize(img_path),
            used_bytes=os.path.getsize(img_path),
            free_bytes=0,
            media_type=MediaType.HDD,
            is_system_drive=False,
            is_boot_drive=False,
        )
        rec = self.engine.sanitize_drive(img_drive, get_erasure_method("quick_erase"))
        self.assertIsNotNone(rec.verification)
        self.assertTrue(rec.verification.verified)
        self.assertEqual(rec.verification.verification_level, VerificationLevel.VERIFIED_OVERWRITTEN)
        self.assertEqual(rec.verification.residual_signatures_found, [])

    def test_usb_phone_internal_storage_anti_recovery_erasure(self) -> None:
        """
        Erasing data from USB-connected phone internal storage must execute multi-pass
        overwriting + free-space NAND block shredding so deleted files cannot recover back.
        """
        phone_mount = os.path.join(self.root, "Galaxy_S24_Internal_Storage")
        dcim_dir = os.path.join(phone_mount, "DCIM", "Camera")
        os.makedirs(dcim_dir, exist_ok=True)

        photo_file = os.path.join(dcim_dir, "IMG_2026_PRIVATE.jpg")
        msg_db = os.path.join(phone_mount, "messages.sqlite")
        with open(photo_file, "wb") as f:
            f.write(b"\xff\xd8\xff\xe1" + b"PRIVATE CAMERA EXIF PAYLOAD " * 512)
        with open(msg_db, "wb") as f:
            f.write(b"SQLite format 3\x00" + b"PRIVATE CHAT HISTORY " * 512)

        phone_drv = self.storage.register_usb_phone_storage(
            phone_mount,
            label="Galaxy S24 Internal Storage",
            model="Samsung Galaxy S24 Ultra (USB)",
        )
        self.assertEqual(phone_drv.media_type, MediaType.USB_PHONE_STORAGE)

        rec_file = self.engine.erase_files_and_folders(
            paths=[photo_file],
            method=get_erasure_method("nist_clear"),
            verify_after=True,
        )
        self.assertFalse(os.path.exists(photo_file))
        self.assertTrue(rec_file.verification.verified)
        self.assertGreater(rec_file.total_bytes_processed, 256 * 1024)

        rec_phone = self.engine.sanitize_drive(
            phone_drv,
            method=get_erasure_method("nist_clear"),
            free_space_wipe_limit_bytes=512 * 1024,
        )
        self.assertFalse(os.path.exists(msg_db))
        self.assertFalse(os.path.exists(dcim_dir))
        self.assertEqual(os.listdir(phone_mount), [])
        self.assertTrue(rec_phone.verification.verified)
        self.assertEqual(rec_phone.verification.residual_signatures_found, [])

    def test_history_and_tamper_evident_reports(self) -> None:
        """Operation records must persist in SQLite and export verifiable HTML, JSON, and TXT reports."""
        f_path = os.path.join(self.root, "audit_target.txt")
        with open(f_path, "wb") as f:
            f.write(b"Audit test payload " * 100)

        rec = self.engine.erase_files_and_folders([f_path], get_erasure_method("quick_erase"))
        self.history.record_operation(rec)

        loaded = self.history.list_operations()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].op_id, rec.op_id)

        html_out = ReportGenerator.export_html_report(rec, os.path.join(self.root, "rep.html"))
        json_out = ReportGenerator.export_json_report(rec, os.path.join(self.root, "rep.json"))
        txt_out = ReportGenerator.export_text_report(rec, os.path.join(self.root, "rep.txt"))

        self.assertTrue(os.path.exists(html_out))
        self.assertTrue(os.path.exists(json_out))
        self.assertTrue(os.path.exists(txt_out))

        ok, msg = ReportGenerator.verify_json_report_integrity(json_out)
        self.assertTrue(ok, msg)

    def test_frameless_window_sidebar_tabs_theme_switch_and_resolutions(self) -> None:
        """
        Verifies:
        1. Larger window controls (44x34 buttons, 18x18 icons) and wider tool width (REF_WIDTH=1440)
           with native mouse edge/corner resizing (`nativeEvent` + `size_grip`).
        2. Auto-selected erase method in `ErasureMethodSelector` displays `Auto` in its text.
        3. Progress bar shows centered percentage (`isTextVisible() == True`, `text-align: center`)
           in Royal Blue (`#096DFD` -> `#1D4ED8`) and is justified with `Start` and `Stop` buttons below it.
        """
        _app = QApplication.instance() or QApplication([])
        self.assertEqual(REF_WIDTH, 1440)
        win = EraseVaultMainWindow(
            storage=self.storage,
            history=self.history,
            settings_mgr=self.settings_mgr,
            auto_confirm_in_tests=True,
            initial_size=(1440, 840),
        )

        self.assertEqual(list(win.nav_buttons.keys()), ["home", "reports", "settings", "about"])
        self.assertFalse(hasattr(win.top_bar, "safeguard_badge"))
        self.assertTrue(bool(win.windowFlags() & Qt.FramelessWindowHint))
        self.assertTrue(hasattr(win, "nativeEvent"))
        self.assertTrue(hasattr(win, "size_grip"))

        # Verify larger window control button and icon sizes (44x34, 18x18)
        for wbtn in (win.top_bar.min_btn, win.top_bar.max_btn, win.top_bar.close_btn):
            self.assertEqual(wbtn.width(), 44)
            self.assertEqual(wbtn.height(), 34)
            self.assertEqual(wbtn.iconSize().width(), 18)
            self.assertEqual(wbtn.iconSize().height(), 18)

        # Verify 'Auto' is shown in the selected auto method text inside the dropdown
        self.assertIn("Auto", win.home_panel.method_selector.combo.currentText())

        # Verify Progress Bar shows centered percentage and uses the Royal Blue gradient
        self.assertEqual(win.home_panel.progress_bar.height(), 18)
        self.assertTrue(win.home_panel.progress_bar.isTextVisible())
        pb_ss = win.home_panel.progress_bar.styleSheet()
        self.assertIn("text-align: center", pb_ss)
        self.assertIn("#096DFD", pb_ss)
        self.assertIn("#1D4ED8", pb_ss)

        # Verify Start button label is 'Start' (minWidth >= 280) and Stop button exists beside it
        self.assertTrue(win.home_panel.start_btn.isVisible())
        self.assertEqual(win.home_panel.start_btn.text().strip(), "Start")
        self.assertGreaterEqual(win.home_panel.start_btn.minimumWidth(), 280)
        self.assertTrue(hasattr(win.home_panel, "stop_btn"))
        self.assertEqual(win.home_panel.stop_btn.text().strip(), "Stop")
        self.assertGreaterEqual(win.home_panel.stop_btn.minimumWidth(), 140)

        # Verify single-outline dropdown
        self.assertFalse(isinstance(win.home_panel.method_selector, QFrame))
        combo_ss = win.home_panel.method_selector.combo.styleSheet()
        self.assertIn("QComboBox:hover", combo_ss)
        self.assertIn("padding: 0px 34px 0px 12px", combo_ss)
        self.assertIn("border: none;", combo_ss)

        # Verify MethodInfoDialog supports both Light Mode and Dark Mode
        dlg_light = MethodInfoDialog(win, theme=LIGHT_THEME)
        self.assertIn(LIGHT_THEME.app_shell_bg, dlg_light.styleSheet())
        dlg_dark = MethodInfoDialog(win, theme=DARK_THEME)
        self.assertIn(DARK_THEME.app_shell_bg, dlg_dark.styleSheet())

        # Test Theme Switch button at bottom of sidebar
        self.assertFalse(win.theme.is_dark)
        win.theme_switch_btn.click()
        self.assertTrue(win.theme.is_dark)
        self.assertEqual(self.settings_mgr.settings.theme_mode, "dark")
        win.theme_switch_btn.click()
        self.assertFalse(win.theme.is_dark)
        self.assertEqual(self.settings_mgr.settings.theme_mode, "light")

        # Test auto-adjustment across multiple screen resolutions
        for scr_w, scr_h, avail_h in [
            (1280, 720, 680),
            (1366, 768, 728),
            (1536, 864, 824),
            (1920, 1080, 1040),
            (2560, 1440, 1400),
        ]:
            mock_screen = QScreen(scr_w, scr_h, avail_h)
            adj_w, adj_h = win.auto_adjust_to_screen_resolution(mock_screen)
            self.assertLessEqual(adj_w, scr_w)
            self.assertLessEqual(adj_h, avail_h)

        # Verify fresh startup does not show previous sanitize records
        win_fresh = EraseVaultMainWindow(
            storage=self.storage,
            history=None,
            settings_mgr=self.settings_mgr,
            auto_confirm_in_tests=True,
        )
        self.assertEqual(len(win_fresh.reports_panel._records), 0)

    def test_streamlined_main_menu_auto_detect_and_auto_verify_workflow(self) -> None:
        """
        Tests the streamlined Main Menu workflow, confirming 'Auto' is added to the
        auto-selected method and the window stays open after completing consecutive operations.
        """
        _app = QApplication.instance() or QApplication([])
        win = EraseVaultMainWindow(
            storage=self.storage,
            history=self.history,
            settings_mgr=self.settings_mgr,
            auto_confirm_in_tests=False,
            initial_size=(1440, 840),
        )
        win.show()

        # 1. Select Files -> Auto-Detect Drive & Best Method (with '— Auto') -> Click Start -> Progress Bar + Auto-Verify
        target_file = os.path.join(self.root, "ui_erase_me.bin")
        with open(target_file, "wb") as f:
            f.write(b"UI workflow test payload " * 256)

        QFileDialog._next_files = [target_file]
        win.home_panel.select_files_card.click()
        self.assertIn(os.path.abspath(target_file), win.home_panel.queued_paths)
        self.assertIn("Auto", win.home_panel.method_selector.combo.currentText())

        rec = win.home_panel.on_start_clicked()
        self.assertIsNotNone(rec)
        self.assertFalse(os.path.exists(target_file))
        self.assertEqual(win.home_panel.progress_bar.value(), 100)
        self.assertTrue(rec.verification.verified)
        self.assertTrue(win.isVisible(), "Window must remain open after file erasure completes!")

        # 2. Select USB Phone Storage -> Auto-Selects NIST 800-88 Clear (— Auto) -> Click Start -> Window stays open
        custom_phone = os.path.join(self.root, "Android_Phone_Internal_Storage")
        os.makedirs(custom_phone, exist_ok=True)
        with open(os.path.join(custom_phone, "doc.txt"), "wb") as f:
            f.write(b"USB phone internal storage content")
        drv = self.storage.register_usb_phone_storage(custom_phone, label="Phone Internal Storage")
        win.home_panel.set_drive_target(drv)
        self.assertEqual(win.home_panel.method_selector.current_method().id, "nist_clear")
        self.assertIn("Auto", win.home_panel.method_selector.combo.currentText())

        rec_drv = win.home_panel.on_start_clicked()
        self.assertIsNotNone(rec_drv)
        self.assertEqual(os.listdir(custom_phone), [])
        self.assertEqual(win.home_panel.progress_bar.value(), 100)
        self.assertTrue(rec_drv.verification.verified)
        self.assertTrue(win.isVisible(), "Window must remain open after USB phone sanitization completes!")

        # 3. Verify Stop button cancellation mechanism
        win.home_panel._set_running_state(True)
        win.home_panel.on_stop_clicked()
        self.assertTrue(win.home_panel._cancel_event.is_set())
        win.home_panel._set_running_state(False)

        # 4. Verify Settings save workflow
        win.settings_panel.default_method_selector.set_method_by_id("dod_3pass")
        win.settings_panel.save_settings()
        self.assertEqual(self.settings_mgr.settings.default_method_id, "dod_3pass")


if __name__ == "__main__":
    unittest.main()
