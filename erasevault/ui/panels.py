"""
Optimized, Modern Workspace Panels for EraseVault:
1. HomeWorkspacePanel (Main Menu — Optimized UI/UX:
   - Tier 1: 3 Target Selection Cards (Select Files, Select Folder, Select Drive/USB Phone).
   - Tier 2: Unified Sanitization & Execution Card (expands to fill workspace height):
     * Top Section:
       - Row 1: Active Target Pill + Clear button on left; Auto-Detected Storage Media badge on right.
       - Row 2: Select Erase Method (single-outline dropdown showing '— Auto' on the auto-selected method) + '★ Auto' tag + '?' guide button.
     * Vertical Stretch (`ex_layout.addStretch(1)`) pushing the Progress Bar and Start/Stop buttons down to the bottom of the card!
     * Bottom Execution Section (`bottom_exec_box` with `0px` horizontal margins so the Progress Bar and Buttons are 100% left- and right-justified with each other):
       - Status readout line above the Progress Bar
       - Slim `18px` Royal Blue Progress Bar with **centered percentage (`%p%`)** spanning the exact start-to-end width of the buttons below it
       - Action Buttons Row directly below the Progress Bar: Wide `Start` button + `Stop` button!)
2. ReportsWorkspacePanel (Session Operation History & Reports UI)
3. SettingsWorkspacePanel (Minimal, clutter-free essential settings)
4. AboutWorkspacePanel (Concise About card with proportional icons and essential tool info)
"""

from __future__ import annotations

import os
import shutil
import threading
from typing import List, Optional, Tuple

from .. import __version__
from ..core.history import HistoryManager
from ..core.models import (
    DriveInfo,
    ErasureMethod,
    MediaType,
    OperationRecord,
    ProgressSnapshot,
    TargetItem,
    format_bytes,
    get_erasure_method,
)
from ..core.reports import ReportGenerator
from ..core.sanitizer import SanitizationEngine
from ..core.settings import SettingsManager
from .assets import AssetManager
from .components import ErasureMethodSelector, SelectTargetCardButton
from .dialogs import (
    MethodInfoDialog,
    OperationReportDialog,
)
from .qt_compat import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSize,
    QSizePolicy,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    Signal,
)
from .styles import LIGHT_THEME, ThemeColors


class DrivePickerDialog(QDialog):
    """
    Modern modal dialog for selecting a non-system drive/partition, USB flash drive,
    or USB-connected Phone Internal Storage when the user clicks 'Select Drive'.
    """

    def __init__(
        self,
        engine: SanitizationEngine,
        theme: ThemeColors,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.theme = theme
        self.selected_drive_info: Optional[DriveInfo] = None
        self._drives: List[DriveInfo] = []

        self.setWindowTitle("Select Drive or USB Phone Storage — EraseVault")
        self.setMinimumSize(680, 390)
        self.setStyleSheet(
            f"QDialog {{ background-color: {theme.app_shell_bg}; color: {theme.title_primary}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        hdr = QLabel("Select a Drive, Partition, or USB Phone Internal Storage", self)
        hdr.setStyleSheet(
            f"font-size: 17px; font-weight: 800; color: {theme.title_primary}; background: transparent;"
        )
        layout.addWidget(hdr)

        sub = QLabel(
            "System drives are locked for safety. USB-connected phones use 3-stage anti-recovery block shredding.",
            self,
        )
        sub.setStyleSheet(
            f"font-size: 12.5px; color: {theme.subtitle_text}; background: transparent;"
        )
        layout.addWidget(sub)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(
            ["Mount / Device", "Label & Filesystem", "Storage Media Type", "Capacity", "Status"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            f"QTableWidget {{ background-color: {theme.table_bg}; alternate-background-color: {theme.table_alt_bg}; "
            f"color: {theme.title_primary}; border: 1px solid {theme.subcard_border}; border-radius: 10px; "
            f"gridline-color: {theme.table_grid}; selection-background-color: {theme.table_selection_bg}; "
            f"selection-color: {theme.title_primary}; }}"
        )
        th = self.table.horizontalHeader()
        th.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        th.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in (2, 3, 4):
            th.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        sec_css = (
            f"QPushButton {{ background-color: {theme.secondary_btn_bg}; color: {theme.title_primary}; "
            f"border: 1px solid {theme.secondary_btn_border}; border-radius: 9px; "
            f"padding: 0px 12px; font-size: 12.5px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {theme.secondary_btn_hover}; border-color: #3B82F6; }}"
        )

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.connect_phone_btn = QPushButton("+ Connect USB Phone Storage...", self)
        self.connect_phone_btn.setFixedHeight(36)
        self.connect_phone_btn.setCursor(Qt.PointingHandCursor)
        self.connect_phone_btn.setStyleSheet(sec_css)
        self.connect_phone_btn.clicked.connect(self._on_connect_usb_phone_storage)
        btn_row.addWidget(self.connect_phone_btn)

        self.browse_vol_btn = QPushButton("+ Browse Drive / Volume...", self)
        self.browse_vol_btn.setFixedHeight(36)
        self.browse_vol_btn.setCursor(Qt.PointingHandCursor)
        self.browse_vol_btn.setStyleSheet(sec_css)
        self.browse_vol_btn.clicked.connect(self._on_browse_custom_volume)
        btn_row.addWidget(self.browse_vol_btn)

        btn_row.addStretch(1)

        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.setFixedSize(92, 36)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(sec_css)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.select_btn = QPushButton("Select Target", self)
        self.select_btn.setFixedSize(136, 36)
        self.select_btn.setCursor(Qt.PointingHandCursor)
        self.select_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #096DFD, stop:1 #1D4ED8); "
            "color: #FFFFFF; border: none; border-radius: 9px; font-size: 13px; font-weight: 700; padding: 0px 14px; }"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1E40AF); }"
        )
        self.select_btn.clicked.connect(self._on_confirm_selection)
        btn_row.addWidget(self.select_btn)

        layout.addLayout(btn_row)
        self._populate_drives()

    def _populate_drives(self) -> None:
        self._drives = self.engine.storage.list_drives(refresh=True)
        self.table.setRowCount(len(self._drives))
        first_eligible = 0
        found_eligible = False
        for idx, d in enumerate(self._drives):
            self.table.setItem(idx, 0, QTableWidgetItem(d.mountpoint))
            self.table.setItem(idx, 1, QTableWidgetItem(f"{d.label} ({d.filesystem})"))
            self.table.setItem(idx, 2, QTableWidgetItem(d.media_type.value))
            self.table.setItem(idx, 3, QTableWidgetItem(format_bytes(d.total_bytes)))
            st_text = "System Protected" if d.is_protected else "Ready"
            self.table.setItem(idx, 4, QTableWidgetItem(st_text))
            if not d.is_protected and not found_eligible:
                first_eligible = idx
                found_eligible = True
        if self._drives:
            self.table.selectRow(first_eligible)

    def _on_connect_usb_phone_storage(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Mounted USB Phone Internal Storage Folder"
        )
        if not folder:
            return
        abs_f = os.path.abspath(folder)
        is_prot, reason = self.engine.validator.is_protected_system_path(abs_f)
        if is_prot:
            QMessageBox.critical(self, "System-Drive Protection", reason)
            return
        drv = self.engine.storage.register_usb_phone_storage(
            abs_f,
            label=os.path.basename(abs_f) or "USB Phone Internal Storage",
            model="USB-Connected Smartphone (UFS / eMMC)",
        )
        self.selected_drive_info = drv
        self.accept()

    def _on_browse_custom_volume(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Non-System Volume Mount or Partition Folder"
        )
        if not folder:
            return
        abs_f = os.path.abspath(folder)
        is_prot, reason = self.engine.validator.is_protected_system_path(abs_f)
        if is_prot:
            QMessageBox.critical(self, "System-Drive Protection", reason)
            return
        usage = shutil.disk_usage(abs_f)
        is_phone = self.engine.storage.is_phone_label_or_path(abs_f)
        drv = DriveInfo(
            device_id=f"VOL:{os.path.basename(abs_f)}",
            mountpoint=abs_f,
            label=os.path.basename(abs_f) or "External Volume",
            filesystem="F2FS / Flash" if is_phone else ("NTFS" if os.name == "nt" else "ext4"),
            total_bytes=usage.total,
            used_bytes=usage.used,
            free_bytes=usage.free,
            media_type=MediaType.USB_PHONE_STORAGE if is_phone else MediaType.REMOVABLE_FLASH,
            bus_type="USB Cable",
            model="USB Phone Storage" if is_phone else "Mounted Volume",
            is_system_drive=False,
            is_boot_drive=False,
            is_removable=True,
            trim_supported=True,
        )
        self.engine.storage.register_custom_drive(drv)
        self.selected_drive_info = drv
        self.accept()

    def _on_confirm_selection(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self._drives):
            drv = self._drives[row]
            if drv.is_protected:
                QMessageBox.critical(
                    self,
                    "System-Drive Safeguard",
                    f"'{drv.mountpoint}' is a protected system/boot drive and cannot be erased.",
                )
                return
            self.selected_drive_info = drv
            self.accept()


class HomeWorkspacePanel(QFrame):
    """
    Optimized Main Menu / Home Workspace Panel:
    - Tier 1: 3 Responsive Target Selection Cards (Select Files, Select Folder, Select Drive/Phone)
    - Tier 2: Unified Sanitization & Execution Card (expands to fill workspace height):
      * Top: Target Selection Pill + Clear button on left; Auto-Detected Storage Media badge on right.
      * Upper-Middle: Select Erase Method (single-outline dropdown showing '— Auto' on the auto-selected method) + '★ Auto' tag + '?' guide button.
      * Vertical Stretch (`ex_layout.addStretch(1)`) that pushes the Progress Bar and Start/Stop buttons down to the bottom!
      * Bottom Execution Block (0px horizontal margins so the Progress Bar left/right edges match the Start button's left edge and Stop button's right edge pixel-for-pixel):
        - Live phase & throughput status line
        - Slim `18px` Royal Blue Progress Bar with **centered completion percentage (`%p%`)**
        - Wide `Start` button + `Stop` button directly below the Progress Bar!
    """

    operation_recorded = Signal(object)  # OperationRecord

    def __init__(
        self,
        assets: AssetManager,
        engine: SanitizationEngine,
        history: HistoryManager,
        settings_mgr: SettingsManager,
        auto_confirm_in_tests: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.assets = assets
        self.engine = engine
        self.history = history
        self.settings_mgr = settings_mgr
        self.auto_confirm_in_tests = auto_confirm_in_tests
        self.theme: ThemeColors = LIGHT_THEME

        self._queued_paths: List[str] = []
        self._inspected_items: List[TargetItem] = []
        self._selected_drive: Optional[DriveInfo] = None
        self._detected_media_type: MediaType = MediaType.UNKNOWN
        self._recommended_method_id: str = self.settings_mgr.settings.default_method_id
        self._cancel_event: threading.Event = threading.Event()
        self._is_running: bool = False

        self.setObjectName("TransparentContainer")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(2, 2, 2, 2)
        root_layout.setSpacing(14)

        # 1. Tier 1: 3 Target Selection Cards (Select Files, Select Folder, Select Drive)
        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(0, 0, 0, 0)
        cards_row.setSpacing(14)

        self.select_files_card = SelectTargetCardButton(
            action_id="select_files",
            icon_name="card_erase_files_icon.png",
            title="Select Files",
            subtitle="Add individual files",
            assets=self.assets,
            active=True,
            parent=self,
        )
        self.select_files_card.card_clicked.connect(lambda _: self.on_add_files_clicked())
        cards_row.addWidget(self.select_files_card, 1)

        self.select_folder_card = SelectTargetCardButton(
            action_id="select_folder",
            icon_name="icon_select_folder.png",
            title="Select Folder",
            subtitle="Add an entire folder",
            assets=self.assets,
            active=False,
            parent=self,
        )
        self.select_folder_card.card_clicked.connect(lambda _: self.on_add_folder_clicked())
        cards_row.addWidget(self.select_folder_card, 1)

        self.select_drive_card = SelectTargetCardButton(
            action_id="select_drive",
            icon_name="card_erase_drives_icon.png",
            title="Select Drive",
            subtitle="Drive, USB or Phone",
            assets=self.assets,
            active=False,
            parent=self,
        )
        self.select_drive_card.card_clicked.connect(lambda _: self.on_select_drive_clicked())
        cards_row.addWidget(self.select_drive_card, 1)

        self.add_files_btn = self.select_files_card
        self.add_folder_btn = self.select_folder_card
        self.select_drive_btn = self.select_drive_card

        root_layout.addLayout(cards_row)

        # 2. Tier 2: Unified Sanitization & Execution Card (expands to fill vertical space so bottom controls sit down)
        self.exec_card = QFrame(self)
        self.exec_card.setObjectName("ExecWorkspaceCard")
        self.exec_card.setAttribute(Qt.WA_StyledBackground, True)
        ex_layout = QVBoxLayout(self.exec_card)
        ex_layout.setContentsMargins(22, 18, 22, 22)
        ex_layout.setSpacing(16)

        # Top Row of Card: Target Selection Pill + Clear Button on Left | Auto-Detection Badge on Right
        top_status_row = QHBoxLayout()
        top_status_row.setContentsMargins(0, 0, 0, 0)
        top_status_row.setSpacing(10)

        self.target_status_badge = QLabel("Target: No target selected", self.exec_card)
        self.target_status_badge.setMinimumHeight(28)
        top_status_row.addWidget(self.target_status_badge)

        self.clear_btn = QPushButton("Clear", self.exec_card)
        self.clear_btn.setObjectName("SecondaryOutlineButton")
        self.clear_btn.setFixedSize(72, 28)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_targets)
        top_status_row.addWidget(self.clear_btn)

        top_status_row.addStretch(1)

        self.drive_detect_badge = QLabel(
            "Auto-Detection: Waiting for target",
            self.exec_card,
        )
        self.drive_detect_badge.setMinimumHeight(28)
        top_status_row.addWidget(self.drive_detect_badge)

        ex_layout.addLayout(top_status_row)

        # Second Row of Card: Select Erase Method (Single-Outline Dropdown with '— Auto') + Best Method Badge + '?' Guide Button
        method_row = QHBoxLayout()
        method_row.setContentsMargins(0, 0, 0, 0)
        method_row.setSpacing(12)

        self.method_title_lbl = QLabel("Select Erase Method:", self.exec_card)
        self.method_title_lbl.setMinimumHeight(26)
        method_row.addWidget(self.method_title_lbl)

        self.method_selector = ErasureMethodSelector(self.assets, self.exec_card)
        self.method_selector.set_method_by_id(
            self.settings_mgr.settings.default_method_id,
            is_auto=self.settings_mgr.settings.auto_select_best_method,
        )
        self.method_selector.method_changed.connect(self._on_method_changed)
        method_row.addWidget(self.method_selector, 1)

        self.best_method_tag = QLabel("★ Auto", self.exec_card)
        self.best_method_tag.setMinimumHeight(28)
        method_row.addWidget(self.best_method_tag)

        self.method_help_btn = QPushButton("?", self.exec_card)
        self.method_help_btn.setFixedSize(30, 30)
        self.method_help_btn.setCursor(Qt.PointingHandCursor)
        self.method_help_btn.setToolTip("View Sanitization Methods & Hardware Guide")
        self.method_help_btn.clicked.connect(self.show_method_info_dialog)
        method_row.addWidget(self.method_help_btn)

        ex_layout.addLayout(method_row)

        # Vertical Stretch pushes the Progress Bar and Start/Stop buttons down to the bottom of the card!
        ex_layout.addStretch(1)

        # Bottom Execution Block: Status Row + Progress Bar + Start/Stop Buttons
        # Uses 0px left and 0px right margins so the Progress Bar start/end positions
        # are justified pixel-for-pixel with the Start button's start edge and Stop button's end edge!
        self.prog_box = QWidget(self.exec_card)
        self.prog_box.setObjectName("TransparentContainer")
        bottom_exec_layout = QVBoxLayout(self.prog_box)
        bottom_exec_layout.setContentsMargins(0, 0, 0, 0)
        bottom_exec_layout.setSpacing(10)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(10)
        self.progress_phase_lbl = QLabel(
            "Ready — Select files, a folder, or a drive above and click Start",
            self.prog_box,
        )
        self.progress_phase_lbl.setMinimumHeight(20)
        status_row.addWidget(self.progress_phase_lbl, 1)

        self.progress_stats_lbl = QLabel(
            "Auto-Verify: Ready",
            self.prog_box,
        )
        self.progress_stats_lbl.setMinimumHeight(20)
        status_row.addWidget(self.progress_stats_lbl)
        bottom_exec_layout.addLayout(status_row)

        # Slim 18px Full-Width Royal Blue Progress Bar with Centered Percentage (%p%)
        # Justified 100% with the Start and Stop buttons below it!
        self.progress_bar = QProgressBar(self.prog_box)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        if hasattr(self.progress_bar, "setAlignment"):
            self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom_exec_layout.addWidget(self.progress_bar)

        # Action Buttons Row Directly Below Progress Bar (0px left/right margins so edges align 100% with Progress Bar)
        action_btn_row = QHBoxLayout()
        action_btn_row.setContentsMargins(0, 2, 0, 0)
        action_btn_row.setSpacing(14)

        self.start_btn = QPushButton("  Start", self.prog_box)
        self.start_btn.setObjectName("EraseNowPrimaryButton")
        self.start_btn.setMinimumWidth(280)
        self.start_btn.setFixedHeight(46)
        self.start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.start_btn.setIcon(self.assets.icon("btn_start_white.png"))
        self.start_btn.setIconSize(QSize(16, 16))
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setToolTip("Start permanent data sanitization and automatic verification")
        self.start_btn.clicked.connect(self.on_start_clicked)
        action_btn_row.addWidget(self.start_btn, 3)

        self.stop_btn = QPushButton("  Stop", self.prog_box)
        self.stop_btn.setObjectName("StopOperationButton")
        self.stop_btn.setMinimumWidth(140)
        self.stop_btn.setFixedHeight(46)
        self.stop_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stop_btn.setIcon(self.assets.icon("btn_stop_red.png"))
        self.stop_btn.setIconSize(QSize(15, 15))
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setToolTip("Stop the active sanitization operation safely")
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        action_btn_row.addWidget(self.stop_btn, 1)

        self.erase_now_btn = self.start_btn
        bottom_exec_layout.addLayout(action_btn_row)

        ex_layout.addWidget(self.prog_box)
        root_layout.addWidget(self.exec_card, 1)

        self.apply_theme(LIGHT_THEME)

    @staticmethod
    def recommend_best_method_for_media(media_type: MediaType) -> ErasureMethod:
        if media_type in (
            MediaType.SSD_NVME,
            MediaType.REMOVABLE_FLASH,
            MediaType.USB_PHONE_STORAGE,
        ):
            return get_erasure_method("nist_clear")
        if media_type == MediaType.HDD:
            return get_erasure_method("dod_3pass")
        return get_erasure_method("quick_erase")

    def apply_theme(self, theme: ThemeColors) -> None:
        self.theme = theme
        self.select_files_card.apply_theme(theme)
        self.select_folder_card.apply_theme(theme)
        self.select_drive_card.apply_theme(theme)
        self.method_selector.apply_theme(theme)

        self.exec_card.setStyleSheet(
            f"QFrame#ExecWorkspaceCard {{ background-color: {theme.workspace_bg}; "
            f"border: 1px solid {theme.workspace_border}; border-radius: 16px; }}"
        )

        self.start_btn.setStyleSheet(
            "QPushButton#EraseNowPrimaryButton { "
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #096DFD, stop:0.5 #1D63F2, stop:1 #1D4ED8); "
            "color: #FFFFFF; border: none; border-radius: 11px; "
            "font-size: 15px; font-weight: 800; padding: 0px 24px; }"
            "QPushButton#EraseNowPrimaryButton:hover { "
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1E40AF); }"
            "QPushButton#EraseNowPrimaryButton:pressed { background-color: #1E3A8A; }"
            "QPushButton#EraseNowPrimaryButton:disabled { background: #64748B; color: #CBD5E1; }"
        )

        stop_dis_bg = "#1E293B" if theme.is_dark else "#F1F5F9"
        stop_dis_fg = "#64748B" if theme.is_dark else "#94A3B8"
        stop_dis_bd = "#334155" if theme.is_dark else "#CBD5E1"
        self.stop_btn.setStyleSheet(
            "QPushButton#StopOperationButton { "
            "background-color: #FEE2E2; color: #DC2626; border: 1px solid #FCA5A5; "
            "border-radius: 11px; font-size: 14.5px; font-weight: 800; padding: 0px 18px; }"
            "QPushButton#StopOperationButton:hover { "
            "background-color: #DC2626; color: #FFFFFF; border-color: #DC2626; }"
            f"QPushButton#StopOperationButton:disabled {{ "
            f"background-color: {stop_dis_bg}; color: {stop_dis_fg}; border: 1px solid {stop_dis_bd}; }}"
        )
        self.stop_btn.setIcon(
            self.assets.icon("btn_stop_red.png" if self.stop_btn.isEnabled() else "btn_stop_muted.png")
        )

        help_bg = "#1E293B" if theme.is_dark else "#E8F1FD"
        help_fg = "#60A5FA" if theme.is_dark else "#096DFD"
        help_bd = "#334155" if theme.is_dark else "#BFDBFE"
        help_hov = "#283548" if theme.is_dark else "#D0E4FC"
        self.method_help_btn.setStyleSheet(
            f"QPushButton {{ background-color: {help_bg}; color: {help_fg}; border: 1px solid {help_bd}; "
            f"border-radius: 15px; font-size: 13.5px; font-weight: 800; padding: 0px; }}"
            f"QPushButton:hover {{ background-color: {help_hov}; border-color: #3B82F6; }}"
        )

        self.clear_btn.setStyleSheet(
            f"QPushButton {{ background-color: {theme.secondary_btn_bg}; color: {theme.title_primary}; "
            f"border: 1px solid {theme.secondary_btn_border}; border-radius: 8px; "
            f"font-size: 12px; font-weight: 600; padding: 0px 10px; }}"
            f"QPushButton:hover {{ background-color: {theme.secondary_btn_hover}; border-color: #3B82F6; }}"
        )

        target_bg = "#1E293B" if theme.is_dark else "#F1F5F9"
        target_fg = "#E2E8F0" if theme.is_dark else "#0F172A"
        target_bd = "#334155" if theme.is_dark else "#CBD5E1"
        self.target_status_badge.setStyleSheet(
            f"background-color: {target_bg}; color: {target_fg}; border: 1px solid {target_bd}; "
            f"border-radius: 8px; padding: 0px 12px; font-size: 12.5px; font-weight: 700;"
        )

        badge_bg = "#172554" if theme.is_dark else "#ECF4FE"
        badge_fg = "#60A5FA" if theme.is_dark else "#096DFD"
        badge_bd = "#1E3A8A" if theme.is_dark else "#BFDBFE"
        self.drive_detect_badge.setStyleSheet(
            f"background-color: {badge_bg}; color: {badge_fg}; border: 1px solid {badge_bd}; "
            f"border-radius: 8px; padding: 0px 12px; font-size: 12px; font-weight: 700;"
        )
        self.best_method_tag.setStyleSheet(
            f"background-color: {badge_bg}; color: {badge_fg}; border: 1px solid {badge_bd}; border-radius: 8px; "
            f"padding: 0px 12px; font-size: 12px; font-weight: 700;"
        )
        self.method_title_lbl.setStyleSheet(
            f"color: {theme.title_primary}; font-size: 14px; font-weight: 800; border: none; background: transparent; padding: 0px;"
        )
        self.progress_phase_lbl.setStyleSheet(
            f"color: {theme.title_primary}; font-size: 12.5px; font-weight: 700; border: none; background: transparent; padding: 0px;"
        )
        self.progress_stats_lbl.setStyleSheet(
            f"color: {theme.title_accent}; font-size: 12.5px; font-weight: 800; border: none; background: transparent; padding: 0px;"
        )
        self._style_progress_bar()

    def _style_progress_bar(self) -> None:
        """
        Styles the 18px Progress Bar in Royal Blue matching the Start button
        (`#096DFD` -> `#1D63F2` -> `#1D4ED8`) with the percentage centered inside the bar.
        """
        t = self.theme
        track_bg = "#0F172A" if t.is_dark else "#E2ECF8"
        track_bd = "#26354D" if t.is_dark else "#C5D6EC"
        text_col = "#FFFFFF" if (self.progress_bar.value() >= 48 or t.is_dark) else "#061937"
        chunk_css = (
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #096DFD, stop:0.5 #1D63F2, stop:1 #1D4ED8); border-radius: 8px;"
        )
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{ background-color: {track_bg}; border: 1px solid {track_bd}; "
            f"border-radius: 9px; text-align: center; font-size: 11.5px; font-weight: 800; color: {text_col}; padding: 0px; }}"
            f"QProgressBar::chunk {{ {chunk_css} }}"
        )

    @property
    def queued_paths(self) -> List[str]:
        return list(self._queued_paths)

    @property
    def inspected_items(self) -> List[TargetItem]:
        return list(self._inspected_items)

    def _set_active_card(self, action_id: str) -> None:
        self.select_files_card.set_active(action_id == "select_files")
        self.select_folder_card.set_active(action_id == "select_folder")
        self.select_drive_card.set_active(action_id == "select_drive")

    def _on_method_changed(self, method: ErasureMethod) -> None:
        if method.id == self._recommended_method_id:
            if self._detected_media_type == MediaType.USB_PHONE_STORAGE:
                self.best_method_tag.setText("★ Auto (USB Phone)")
            elif self._detected_media_type != MediaType.UNKNOWN:
                short_m = self._detected_media_type.value.split()[0]
                self.best_method_tag.setText(f"★ Auto ({short_m})")
            else:
                self.best_method_tag.setText("★ Auto")
        else:
            self.best_method_tag.setText(f"{method.pass_count} {'Pass' if method.pass_count == 1 else 'Passes'}")

    def show_method_info_dialog(self) -> None:
        MethodInfoDialog(self, theme=self.theme).exec()

    def on_add_files_clicked(self) -> None:
        self._set_active_card("select_files")
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Securely Erase")
        if files:
            self._selected_drive = None
            self.add_target_paths(files)

    def on_add_folder_clicked(self) -> None:
        self._set_active_card("select_folder")
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Securely Erase")
        if folder:
            self._selected_drive = None
            self.add_target_paths([folder])

    def on_select_drive_clicked(self) -> Optional[DriveInfo]:
        self._set_active_card("select_drive")
        if self.auto_confirm_in_tests and QFileDialog._next_dir:
            folder = QFileDialog.getExistingDirectory(self, "Select Drive")
            abs_f = os.path.abspath(folder)
            is_prot, reason = self.engine.validator.is_protected_system_path(abs_f)
            if is_prot:
                QMessageBox.critical(self, "System-Drive Protection Safeguard", reason)
                return None
            usage = shutil.disk_usage(abs_f)
            is_phone = self.engine.storage.is_phone_label_or_path(abs_f)
            drv = DriveInfo(
                device_id=f"VOL:{os.path.basename(abs_f)}",
                mountpoint=abs_f,
                label=os.path.basename(abs_f) or "External Drive",
                filesystem="F2FS / Flash" if is_phone else ("NTFS" if os.name == "nt" else "ext4"),
                total_bytes=usage.total,
                used_bytes=usage.used,
                free_bytes=usage.free,
                media_type=MediaType.USB_PHONE_STORAGE if is_phone else MediaType.REMOVABLE_FLASH,
                is_system_drive=False,
                is_boot_drive=False,
                is_removable=True,
                trim_supported=True,
            )
            self.engine.storage.register_custom_drive(drv)
            self.set_drive_target(drv)
            return drv

        dlg = DrivePickerDialog(self.engine, self.theme, self)
        if dlg.exec() == DrivePickerDialog.Accepted and dlg.selected_drive_info is not None:
            self.set_drive_target(dlg.selected_drive_info)
            return dlg.selected_drive_info
        return None

    def set_drive_target(self, drv: DriveInfo) -> None:
        self._selected_drive = drv
        mp = drv.mountpoint if drv.mountpoint.startswith("adb://") else os.path.abspath(drv.mountpoint)
        self._queued_paths = [mp]
        self._detected_media_type = drv.media_type

        best = self.recommend_best_method_for_media(drv.media_type)
        self._recommended_method_id = best.id
        self.method_selector.set_auto_method_id(best.id)
        if self.settings_mgr.settings.auto_select_best_method:
            self.method_selector.set_method_by_id(best.id, is_auto=True)

        short_m = drv.media_type.value.split("(")[0].strip()
        self.drive_detect_badge.setText(
            f"Detected: {short_m}  •  Best: {best.display_name} (Auto)"
        )
        if drv.media_type == MediaType.USB_PHONE_STORAGE:
            self.best_method_tag.setText("★ Auto (USB Phone)")
        else:
            self.best_method_tag.setText(f"★ Auto ({short_m.split()[0]})")
        self._refresh_target_summary_for_drive(drv)

    def add_target_paths(self, paths: List[str]) -> List[TargetItem]:
        blocked_reasons: List[str] = []
        for raw_p in paths:
            if not raw_p:
                continue
            abs_p = os.path.abspath(raw_p)
            is_prot, reason = self.engine.validator.is_protected_system_path(abs_p)
            if is_prot:
                blocked_reasons.append(reason)
                continue
            if abs_p not in self._queued_paths:
                self._queued_paths.append(abs_p)

        self._auto_detect_drive_and_select_best_method()
        self._refresh_inspection()

        if blocked_reasons:
            QMessageBox.critical(
                self,
                "System-Drive Protection Safeguard",
                "\n\n".join(blocked_reasons),
            )
        return list(self._inspected_items)

    def _auto_detect_drive_and_select_best_method(self) -> None:
        if not self._queued_paths:
            self._detected_media_type = MediaType.UNKNOWN
            self._recommended_method_id = self.settings_mgr.settings.default_method_id
            self.method_selector.set_auto_method_id(self._recommended_method_id)
            self.drive_detect_badge.setText("Auto-Detection: Waiting for target")
            self.best_method_tag.setText("★ Auto")
            return

        drv = self.engine.storage.get_drive_for_path(self._queued_paths[0])
        self._detected_media_type = drv.media_type
        best = self.recommend_best_method_for_media(drv.media_type)
        self._recommended_method_id = best.id
        self.method_selector.set_auto_method_id(best.id)

        if self.settings_mgr.settings.auto_select_best_method:
            self.method_selector.set_method_by_id(best.id, is_auto=True)

        short_m = drv.media_type.value.split("(")[0].strip()
        self.drive_detect_badge.setText(
            f"Detected: {short_m} ({drv.mountpoint})  •  Best: {best.display_name} (Auto)"
        )
        if drv.media_type == MediaType.USB_PHONE_STORAGE:
            self.best_method_tag.setText("★ Auto (USB Phone)")
        else:
            self.best_method_tag.setText(f"★ Auto ({short_m.split()[0]})")

    def remove_target_path(self, path: str) -> None:
        abs_p = path if path.startswith("adb://") else os.path.abspath(path)
        self._queued_paths = [p for p in self._queued_paths if p != abs_p]
        if not self._queued_paths:
            self._selected_drive = None
        self._auto_detect_drive_and_select_best_method()
        self._refresh_inspection()

    def clear_targets(self) -> None:
        self._queued_paths.clear()
        self._inspected_items.clear()
        self._selected_drive = None
        self.select_files_card.set_subtitle(None)
        self.select_folder_card.set_subtitle(None)
        self.select_drive_card.set_subtitle(None)
        self.target_status_badge.setText("Target: No target selected")
        self._auto_detect_drive_and_select_best_method()
        self.progress_bar.setValue(0)
        self._style_progress_bar()
        self.progress_phase_lbl.setText(
            "Ready — Select files, a folder, or a drive above and click Start"
        )
        self.progress_stats_lbl.setText("Auto-Verify: Ready")

    def _refresh_target_summary_for_drive(self, drv: DriveInfo) -> None:
        kind_lbl = "USB Phone Storage" if drv.media_type == MediaType.USB_PHONE_STORAGE else "Drive"
        self.target_status_badge.setText(
            f"Target: {kind_lbl} ({drv.label} — {format_bytes(drv.used_bytes)})"
        )
        self.select_drive_card.set_subtitle(f"{drv.label} ({format_bytes(drv.used_bytes)})")
        self.progress_phase_lbl.setText(
            f"Ready to sanitize {kind_lbl.lower()}: {drv.mountpoint}"
        )

    def _refresh_inspection(self) -> None:
        if self._selected_drive is not None:
            self._refresh_target_summary_for_drive(self._selected_drive)
            return

        method = self.method_selector.current_method()
        self._inspected_items = self.engine.validator.inspect_and_validate_file_targets(
            self._queued_paths, method
        )
        valid_items = [it for it in self._inspected_items if it.is_valid]
        total_bytes = sum(it.size_bytes for it in valid_items)

        if not valid_items:
            self.target_status_badge.setText("Target: No target selected")
            self.select_files_card.set_subtitle(None)
            self.select_folder_card.set_subtitle(None)
            return

        first_name = os.path.basename(valid_items[0].path.rstrip("/\\")) or valid_items[0].path
        if len(valid_items) == 1:
            if valid_items[0].item_type == "folder":
                summary = f"Folder '{first_name}' ({valid_items[0].file_count} files, {format_bytes(total_bytes)})"
                self.select_folder_card.set_subtitle(f"{first_name} ({format_bytes(total_bytes)})")
            else:
                summary = f"File '{first_name}' ({format_bytes(total_bytes)})"
                self.select_files_card.set_subtitle(f"{first_name} ({format_bytes(total_bytes)})")
        else:
            summary = f"{len(valid_items)} targets ({format_bytes(total_bytes)}) — {first_name} +{len(valid_items) - 1} more"
            self.select_files_card.set_subtitle(f"{len(valid_items)} items ({format_bytes(total_bytes)})")

        self.target_status_badge.setText(f"Target: {summary}")
        self.progress_phase_lbl.setText(f"Ready to erase: {summary}")

    def _set_running_state(self, running: bool) -> None:
        self._is_running = running
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.stop_btn.setIcon(
            self.assets.icon("btn_stop_red.png" if running else "btn_stop_muted.png")
        )

    def on_stop_clicked(self) -> None:
        """Signals the active sanitization operation to stop immediately and safely."""
        if self._is_running:
            self._cancel_event.set()
            self.progress_phase_lbl.setText("Stopping operation safely...")
            QApplication.processEvents()

    def _on_live_progress(self, snap: ProgressSnapshot) -> None:
        """
        Safely updates the progress bar (with centered percentage) and status labels
        on the main GUI thread and pumps the Qt event loop.
        """
        try:
            pct = int(snap.percent)
            self.progress_bar.setValue(pct)
            self._style_progress_bar()
            if pct >= 96:
                self.progress_phase_lbl.setText(
                    f"Auto-Verifying Data Removal: {snap.current_target}..."
                )
            else:
                self.progress_phase_lbl.setText(
                    f"{snap.phase} — {snap.current_target}"
                )
            self.progress_stats_lbl.setText(
                f"{snap.throughput_mbps:.2f} MB/s  •  Auto-Verify: Active"
            )
            QApplication.processEvents()
        except Exception:
            pass

    def on_start_clicked(self) -> Optional[OperationRecord]:
        if not self._queued_paths and self._selected_drive is None:
            QMessageBox.warning(
                self,
                "No Target Selected",
                "Please select files, a folder, a drive, or USB phone storage before clicking Start.",
            )
            return None

        method = self.method_selector.current_method()
        self._cancel_event.clear()
        self.progress_bar.setValue(0)
        self._style_progress_bar()

        # Case A: Drive or USB Phone Internal Storage Sanitization
        if self._selected_drive is not None:
            drv = self._selected_drive
            allowed, err_msg, _ssd_warn = self.engine.validator.validate_drive_target(drv, method)
            if not allowed:
                QMessageBox.critical(self, "System-Drive Safeguard", err_msg)
                return None

            self._set_running_state(True)
            self.progress_phase_lbl.setText(f"Sanitizing {drv.mountpoint}...")
            QApplication.processEvents()
            try:
                rec = self.engine.sanitize_drive(
                    drive=drv,
                    method=method,
                    progress_cb=self._on_live_progress,
                    cancel_event=self._cancel_event,
                )
            except Exception as exc:
                self._set_running_state(False)
                self.progress_phase_lbl.setText(f"Error: {exc}")
                QMessageBox.critical(self, "Sanitization Error", str(exc))
                return None

            self._set_running_state(False)
            if self._cancel_event.is_set():
                self.progress_phase_lbl.setText("Operation stopped by user.")
                self.progress_stats_lbl.setText("Stopped")
                return rec
            return self._finalize_completed_operation(rec)

        # Case B: File & Folder Sanitization (with mandatory Auto-Verification & Phone Block Shredding)
        self._refresh_inspection()
        valid_items = [it for it in self._inspected_items if it.is_valid]
        if not valid_items:
            QMessageBox.critical(self, "Validation Error", "No valid targets to erase.")
            return None

        self._set_running_state(True)
        self.progress_phase_lbl.setText(f"Starting {method.display_name}...")
        QApplication.processEvents()

        try:
            rec = self.engine.erase_files_and_folders(
                paths=[it.path for it in valid_items],
                method=method,
                verify_after=True,
                obfuscate_metadata=self.settings_mgr.settings.obfuscate_filenames,
                pad_cluster_slack=self.settings_mgr.settings.pad_cluster_slack,
                progress_cb=self._on_live_progress,
                cancel_event=self._cancel_event,
            )
        except Exception as exc:
            self._set_running_state(False)
            self.progress_phase_lbl.setText(f"Error: {exc}")
            QMessageBox.critical(self, "Sanitization Error", str(exc))
            return None

        self._set_running_state(False)
        if self._cancel_event.is_set():
            self.progress_phase_lbl.setText("Operation stopped by user.")
            self.progress_stats_lbl.setText("Stopped")
            return rec
        return self._finalize_completed_operation(rec)

    on_erase_now_clicked = on_start_clicked

    def _finalize_completed_operation(self, rec: OperationRecord) -> OperationRecord:
        try:
            self.history.record_operation(rec)
        except Exception:
            pass

        self._queued_paths.clear()
        self._inspected_items.clear()
        self._selected_drive = None
        self.select_files_card.set_subtitle(None)
        self.select_folder_card.set_subtitle(None)
        self.select_drive_card.set_subtitle(None)
        self.target_status_badge.setText("Target: No target selected")

        self.progress_bar.setValue(100)
        self._style_progress_bar()

        self.progress_phase_lbl.setText(
            f"✓ Erased & Auto-Verified Clean ({rec.method_name}, 0 Residual Signatures)"
        )
        self.progress_stats_lbl.setText(
            f"{format_bytes(rec.total_bytes_processed)} Erased  •  Verified ✓"
        )
        try:
            self.operation_recorded.emit(rec)
        except Exception:
            pass
        return rec


EraseFilesWorkspacePanel = HomeWorkspacePanel


class ReportsWorkspacePanel(QFrame):
    """
    Clean, Modern & Responsive Reports Section (shows only active session records).
    """

    def __init__(
        self,
        assets: AssetManager,
        history: HistoryManager,
        settings_mgr: SettingsManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.assets = assets
        self.history = history
        self.settings_mgr = settings_mgr
        self.theme: ThemeColors = LIGHT_THEME
        self.setObjectName("ReportsFullPageCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._all_records: List[OperationRecord] = []
        self._records: List[OperationRecord] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title_lbl = QLabel("Sanitization Reports", self)
        self.title_lbl.setMinimumHeight(26)
        self.subtitle_lbl = QLabel(
            "Current session audit reports & tamper-evident SHA-256 certificates",
            self,
        )
        self.subtitle_lbl.setMinimumHeight(18)
        title_col.addWidget(self.title_lbl)
        title_col.addWidget(self.subtitle_lbl)
        top_row.addLayout(title_col)
        top_row.addStretch(1)

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Search ID, target, or method...")
        self.search_edit.setFixedWidth(220)
        self.search_edit.setFixedHeight(36)
        self.search_edit.textChanged.connect(self._apply_filter)
        top_row.addWidget(self.search_edit)

        self.clear_history_btn = QPushButton("Clear", self)
        self.clear_history_btn.setFixedHeight(36)
        self.clear_history_btn.setCursor(Qt.PointingHandCursor)
        self.clear_history_btn.clicked.connect(self.on_clear_history)
        top_row.addWidget(self.clear_history_btn)

        layout.addLayout(top_row)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        self.kpi_cards: List[Tuple[QFrame, QLabel, QLabel]] = []
        for idx, (k_title, k_init) in enumerate(
            [
                ("SESSION OPERATIONS", "0"),
                ("DATA SANITIZED", "0 B"),
                ("VERIFICATION STATUS", "Ready"),
            ]
        ):
            card = QFrame(self)
            card.setObjectName(f"KpiCard_{idx}")
            card.setAttribute(Qt.WA_StyledBackground, True)
            card.setFixedHeight(72)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 8, 16, 8)
            cl.setSpacing(2)
            lbl_t = QLabel(k_title, card)
            lbl_t.setMinimumHeight(16)
            lbl_v = QLabel(k_init, card)
            lbl_v.setMinimumHeight(24)
            cl.addWidget(lbl_t)
            cl.addWidget(lbl_v)
            kpi_row.addWidget(card, 1)
            self.kpi_cards.append((card, lbl_t, lbl_v))
        layout.addLayout(kpi_row)

        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels(
            [
                "Operation ID",
                "Date & Time",
                "Sanitized Target",
                "Storage Media",
                "Erase Method",
                "Data Size",
                "Verification",
            ]
        )
        self.table.setAlternatingRowColors(True)
        th = self.table.horizontalHeader()
        th.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        th.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        th.setSectionResizeMode(2, QHeaderView.Stretch)
        for col_i in (3, 4, 5, 6):
            th.setSectionResizeMode(col_i, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(lambda _r, _c: self.on_view_report())
        layout.addWidget(self.table, 1)

        self.bottom_bar = QFrame(self)
        self.bottom_bar.setObjectName("ReportsBottomBar")
        self.bottom_bar.setAttribute(Qt.WA_StyledBackground, True)
        bb_layout = QHBoxLayout(self.bottom_bar)
        bb_layout.setContentsMargins(16, 10, 16, 10)
        bb_layout.setSpacing(8)

        self.summary_strip_lbl = QLabel(
            "Run an erasure operation on the Home tab to generate a verified certificate.",
            self.bottom_bar,
        )
        self.summary_strip_lbl.setWordWrap(True)
        bb_layout.addWidget(self.summary_strip_lbl, 1)

        self.export_txt_btn = QPushButton("Export TXT", self.bottom_bar)
        self.export_txt_btn.setFixedHeight(36)
        self.export_txt_btn.setCursor(Qt.PointingHandCursor)
        self.export_txt_btn.clicked.connect(self.on_export_txt)
        bb_layout.addWidget(self.export_txt_btn)

        self.export_json_btn = QPushButton("Export JSON", self.bottom_bar)
        self.export_json_btn.setFixedHeight(36)
        self.export_json_btn.setCursor(Qt.PointingHandCursor)
        self.export_json_btn.clicked.connect(self.on_export_json)
        bb_layout.addWidget(self.export_json_btn)

        self.export_html_btn = QPushButton("Export HTML", self.bottom_bar)
        self.export_html_btn.setFixedHeight(36)
        self.export_html_btn.setCursor(Qt.PointingHandCursor)
        self.export_html_btn.clicked.connect(self.on_export_html)
        bb_layout.addWidget(self.export_html_btn)

        self.view_btn = QPushButton("View Certificate", self.bottom_bar)
        self.view_btn.setFixedHeight(36)
        self.view_btn.setCursor(Qt.PointingHandCursor)
        self.view_btn.clicked.connect(self.on_view_report)
        bb_layout.addWidget(self.view_btn)

        layout.addWidget(self.bottom_bar)

        self.apply_theme(LIGHT_THEME)
        self.refresh_history()

    def apply_theme(self, theme: ThemeColors) -> None:
        self.theme = theme
        self.setStyleSheet(
            f"QFrame#ReportsFullPageCard {{ background-color: {theme.workspace_bg}; "
            f"border: 1px solid {theme.workspace_border}; border-radius: 16px; }}"
        )
        self.title_lbl.setStyleSheet(
            f"color: {theme.title_primary}; font-size: 20px; font-weight: 800; border: none; background: transparent; padding: 0px;"
        )
        self.subtitle_lbl.setStyleSheet(
            f"color: {theme.subtitle_text}; font-size: 12.5px; border: none; background: transparent; padding: 0px;"
        )
        self.search_edit.setStyleSheet(
            f"QLineEdit {{ background-color: {theme.input_bg}; color: {theme.title_primary}; "
            f"border: 1px solid {theme.input_border}; border-radius: 9px; padding: 0px 12px; font-size: 12.5px; }}"
            f"QLineEdit:hover {{ border-color: {theme.input_hover_border}; background-color: {theme.input_hover_bg}; }}"
            f"QLineEdit:focus {{ border: 1.5px solid {theme.title_accent}; }}"
        )

        sec_btn_css = (
            f"QPushButton {{ background-color: {theme.secondary_btn_bg}; color: {theme.title_primary}; "
            f"border: 1px solid {theme.secondary_btn_border}; border-radius: 9px; "
            f"padding: 0px 14px; font-size: 12.5px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {theme.secondary_btn_hover}; border-color: #3B82F6; color: {theme.title_accent}; }}"
        )
        for btn in (
            self.clear_history_btn,
            self.export_txt_btn,
            self.export_json_btn,
            self.export_html_btn,
        ):
            btn.setStyleSheet(sec_btn_css)

        self.view_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #096DFD, stop:1 #1D4ED8); "
            "color: #FFFFFF; border: none; border-radius: 9px; padding: 0px 16px; font-size: 13px; font-weight: 700; }"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1E40AF); }"
        )

        for idx, (card, lbl_t, lbl_v) in enumerate(self.kpi_cards):
            card.setStyleSheet(
                f"QFrame#KpiCard_{idx} {{ background-color: {theme.subcard_bg}; "
                f"border: 1px solid {theme.subcard_border}; border-left: 4px solid {theme.title_accent}; "
                f"border-radius: 12px; }}"
            )
            lbl_t.setStyleSheet(
                f"color: {theme.subtitle_text}; font-size: 11px; font-weight: 700; border: none; background: transparent; padding: 0px;"
            )
            lbl_v.setStyleSheet(
                f"color: {theme.title_primary}; font-size: 18px; font-weight: 800; border: none; background: transparent; padding: 0px;"
            )

        self.table.setStyleSheet(
            f"QTableWidget {{ background-color: {theme.table_bg}; alternate-background-color: {theme.table_alt_bg}; "
            f"color: {theme.title_primary}; border: 1px solid {theme.subcard_border}; border-radius: 10px; "
            f"gridline-color: {theme.table_grid}; selection-background-color: {theme.table_selection_bg}; "
            f"selection-color: {theme.title_primary}; }}"
        )

        self.bottom_bar.setStyleSheet(
            f"QFrame#ReportsBottomBar {{ background-color: {theme.subcard_bg}; "
            f"border: 1px solid {theme.subcard_border}; border-radius: 12px; }}"
        )
        self.summary_strip_lbl.setStyleSheet(
            f"color: {theme.subtitle_text}; font-size: 12px; font-weight: 600; border: none; background: transparent; padding: 0px;"
        )
        self._on_selection_changed()

    def refresh_history(self) -> List[OperationRecord]:
        self._all_records = self.history.list_operations()
        self._update_kpis()
        self._apply_filter()
        return list(self._records)

    def _update_kpis(self) -> None:
        total_ops = len(self._all_records)
        total_bytes = sum(r.total_bytes_processed for r in self._all_records)
        verified_ops = sum(1 for r in self._all_records if r.verification and r.verification.verified)
        rate_str = f"{verified_ops}/{total_ops} Verified ✓" if total_ops > 0 else "Ready"

        self.kpi_cards[0][2].setText(f"{total_ops}")
        self.kpi_cards[1][2].setText(format_bytes(total_bytes))
        self.kpi_cards[2][2].setText(rate_str)

    def _apply_filter(self) -> None:
        q = self.search_edit.text().strip().lower()
        if not q:
            self._records = list(self._all_records)
        else:
            self._records = [
                r
                for r in self._all_records
                if q in r.op_id.lower()
                or q in r.method_name.lower()
                or any(q in t.lower() for t in r.targets)
            ]

        self.table.setRowCount(len(self._records))
        for idx, rec in enumerate(self._records):
            target_summary = rec.targets[0] if rec.targets else "-"
            if len(rec.targets) > 1:
                target_summary += f" (+{len(rec.targets) - 1} more)"
            ver_lvl = rec.verification.verification_level.value if rec.verification else "Verified"

            self.table.setItem(idx, 0, QTableWidgetItem(rec.op_id))
            self.table.setItem(idx, 1, QTableWidgetItem(rec.timestamp_start[:19].replace("T", " ")))
            self.table.setItem(idx, 2, QTableWidgetItem(target_summary))
            self.table.setItem(idx, 3, QTableWidgetItem(rec.media_summary or "SSD / NVMe"))
            self.table.setItem(idx, 4, QTableWidgetItem(rec.method_name))
            self.table.setItem(idx, 5, QTableWidgetItem(format_bytes(rec.total_bytes_processed)))
            self.table.setItem(idx, 6, QTableWidgetItem(f"✓ {ver_lvl}"))

        if self._records:
            self.table.selectRow(0)
        else:
            self._on_selection_changed()

    def selected_record(self) -> Optional[OperationRecord]:
        row = self.table.currentRow()
        if 0 <= row < len(self._records):
            return self._records[row]
        return None

    def _on_selection_changed(self) -> None:
        rec = self.selected_record()
        if rec is None:
            self.summary_strip_lbl.setText(
                "Run an erasure operation on the Home tab to generate a verified certificate."
            )
            return
        digest = ReportGenerator.compute_report_digest(rec)
        ver = rec.verification
        ver_txt = ver.verification_level.value if ver else "Verified"
        self.summary_strip_lbl.setText(
            f"{rec.op_id}  •  {rec.method_name} ({rec.passes_completed} pass)  •  "
            f"{ver_txt}  •  SHA-256: {digest[:24]}..."
        )

    def on_view_report(self) -> None:
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(self, "No Report Selected", "Select an operation from the table first.")
            return
        OperationReportDialog(
            rec,
            default_export_dir=self.settings_mgr.settings.reports_directory,
            parent=self,
            theme=self.theme,
        ).exec()

    def on_export_html(self) -> Optional[str]:
        rec = self.selected_record()
        if not rec:
            return None
        default_p = os.path.join(self.settings_mgr.settings.reports_directory, f"{rec.op_id}_certificate.html")
        path, _ = QFileDialog.getSaveFileName(self, "Export HTML Certificate", default_p, "HTML Files (*.html)")
        if path:
            out = ReportGenerator.export_html_report(rec, path)
            QMessageBox.information(self, "Export Complete", f"Saved HTML Certificate to:\n{out}")
            return out
        return None

    def on_export_json(self) -> Optional[str]:
        rec = self.selected_record()
        if not rec:
            return None
        default_p = os.path.join(self.settings_mgr.settings.reports_directory, f"{rec.op_id}_report.json")
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON Report", default_p, "JSON Files (*.json)")
        if path:
            out = ReportGenerator.export_json_report(rec, path)
            QMessageBox.information(self, "Export Complete", f"Saved JSON Report to:\n{out}")
            return out
        return None

    def on_export_txt(self) -> Optional[str]:
        rec = self.selected_record()
        if not rec:
            return None
        default_p = os.path.join(self.settings_mgr.settings.reports_directory, f"{rec.op_id}_audit.txt")
        path, _ = QFileDialog.getSaveFileName(self, "Export TXT Audit Log", default_p, "Text Files (*.txt)")
        if path:
            out = ReportGenerator.export_text_report(rec, path)
            QMessageBox.information(self, "Export Complete", f"Saved TXT Audit Log to:\n{out}")
            return out
        return None

    def on_clear_history(self) -> None:
        self.history.clear_history()
        self.refresh_history()


class SettingsWorkspacePanel(QFrame):
    """
    Redesigned Minimal, Clutter-Free Settings Section.
    """

    settings_updated = Signal()

    def __init__(
        self,
        assets: AssetManager,
        settings_mgr: SettingsManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.assets = assets
        self.settings_mgr = settings_mgr
        self.theme: ThemeColors = LIGHT_THEME
        self.setObjectName("SettingsFullPageCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        self.title_lbl = QLabel("Settings", self)
        self.title_lbl.setMinimumHeight(26)
        layout.addWidget(self.title_lbl)

        self.card = QFrame(self)
        self.card.setObjectName("SettingsInnerCard")
        self.card.setAttribute(Qt.WA_StyledBackground, True)
        c_layout = QVBoxLayout(self.card)
        c_layout.setContentsMargins(24, 22, 24, 22)
        c_layout.setSpacing(16)

        m_row = QHBoxLayout()
        self.m_lbl = QLabel("Default Erase Method", self.card)
        self.m_lbl.setMinimumHeight(26)
        m_row.addWidget(self.m_lbl)
        m_row.addStretch(1)
        self.default_method_selector = ErasureMethodSelector(self.assets, self.card)
        self.default_method_selector.setFixedWidth(360)
        self.default_method_selector.set_method_by_id(self.settings_mgr.settings.default_method_id)
        m_row.addWidget(self.default_method_selector)
        c_layout.addLayout(m_row)

        self.auto_method_chk = QCheckBox(
            "Auto-detect storage media (SSD, HDD, USB & Phone) and select best erase method",
            self.card,
        )
        self.auto_method_chk.setChecked(self.settings_mgr.settings.auto_select_best_method)
        c_layout.addWidget(self.auto_method_chk)

        self.obfuscate_chk = QCheckBox(
            "Obfuscate filenames and reset timestamps before deletion",
            self.card,
        )
        self.obfuscate_chk.setChecked(self.settings_mgr.settings.obfuscate_filenames)
        c_layout.addWidget(self.obfuscate_chk)

        self.slack_chk = QCheckBox(
            "Pad file tail to 4 KB cluster boundary to clear slack space",
            self.card,
        )
        self.slack_chk.setChecked(self.settings_mgr.settings.pad_cluster_slack)
        c_layout.addWidget(self.slack_chk)

        c_layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.reset_btn = QPushButton("Reset Defaults", self.card)
        self.reset_btn.setFixedSize(140, 40)
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_defaults)
        btn_row.addWidget(self.reset_btn)

        self.save_btn = QPushButton("Save Settings", self.card)
        self.save_btn.setFixedSize(160, 40)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_settings)
        btn_row.addWidget(self.save_btn)
        c_layout.addLayout(btn_row)

        layout.addWidget(self.card, 1)
        self.apply_theme(LIGHT_THEME)

    def apply_theme(self, theme: ThemeColors) -> None:
        self.theme = theme
        self.setStyleSheet(
            f"QFrame#SettingsFullPageCard {{ background-color: {theme.workspace_bg}; "
            f"border: 1px solid {theme.workspace_border}; border-radius: 16px; }}"
        )
        self.card.setStyleSheet(
            f"QFrame#SettingsInnerCard {{ background-color: {theme.subcard_bg}; "
            f"border: 1px solid {theme.subcard_border}; border-radius: 14px; }}"
        )
        self.title_lbl.setStyleSheet(
            f"color: {theme.title_primary}; font-size: 20px; font-weight: 800; border: none; background: transparent; padding: 0px;"
        )
        self.m_lbl.setStyleSheet(
            f"color: {theme.title_primary}; font-size: 14px; font-weight: 700; border: none; background: transparent; padding: 0px;"
        )
        for chk in (self.auto_method_chk, self.obfuscate_chk, self.slack_chk):
            chk.setStyleSheet(
                f"QCheckBox {{ color: {theme.title_primary}; font-size: 13.5px; font-weight: 600; background: transparent; padding: 2px 0px; }}"
            )
        sec_css = (
            f"QPushButton {{ background-color: {theme.secondary_btn_bg}; color: {theme.title_primary}; "
            f"border: 1px solid {theme.secondary_btn_border}; border-radius: 9px; font-size: 13px; font-weight: 600; padding: 0px 14px; }}"
            f"QPushButton:hover {{ background-color: {theme.secondary_btn_hover}; border-color: #3B82F6; }}"
        )
        self.reset_btn.setStyleSheet(sec_css)
        self.save_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #096DFD, stop:1 #1D4ED8); "
            "color: #FFFFFF; border: none; border-radius: 10px; font-size: 14px; font-weight: 700; padding: 0px 16px; }"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1E40AF); }"
        )
        self.default_method_selector.apply_theme(theme)

    def reset_defaults(self) -> None:
        self.default_method_selector.set_method_by_id("quick_erase")
        self.auto_method_chk.setChecked(True)
        self.obfuscate_chk.setChecked(True)
        self.slack_chk.setChecked(True)

    def save_settings(self) -> None:
        s = self.settings_mgr.settings
        s.default_method_id = self.default_method_selector.current_method().id
        s.auto_select_best_method = self.auto_method_chk.isChecked()
        s.obfuscate_filenames = self.obfuscate_chk.isChecked()
        s.pad_cluster_slack = self.slack_chk.isChecked()
        self.settings_mgr.save(s)
        self.settings_updated.emit()
        QMessageBox.information(self, "Settings Saved", "Settings have been saved.")


class AboutWorkspacePanel(QFrame):
    """
    Redesigned Clean & Concise About Section with unclipped shield logo & badge.
    """

    def __init__(
        self,
        assets: AssetManager,
        engine: SanitizationEngine,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.assets = assets
        self.engine = engine
        self.theme: ThemeColors = LIGHT_THEME
        self.setObjectName("AboutFullPageCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(10)
        self.about_hdr_icon = QLabel(self)
        self.about_hdr_icon.setFixedSize(28, 28)
        ab_pix = self.assets.pixmap("about_badge_blue.png", 26, 26)
        if not ab_pix.isNull():
            self.about_hdr_icon.setPixmap(ab_pix)
        self.about_hdr_icon.setStyleSheet("background: transparent; border: none; padding: 0px;")
        hdr_row.addWidget(self.about_hdr_icon)

        self.title_lbl = QLabel("About EraseVault", self)
        self.title_lbl.setMinimumHeight(26)
        hdr_row.addWidget(self.title_lbl)
        hdr_row.addStretch(1)
        layout.addLayout(hdr_row)

        self.card = QFrame(self)
        self.card.setObjectName("AboutInnerCard")
        self.card.setAttribute(Qt.WA_StyledBackground, True)
        c_layout = QVBoxLayout(self.card)
        c_layout.setContentsMargins(24, 20, 24, 20)
        c_layout.setSpacing(14)

        top_identity = QHBoxLayout()
        top_identity.setSpacing(14)

        self.logo_lbl = QLabel(self.card)
        self.logo_lbl.setFixedSize(40, 44)
        self.logo_lbl.setAlignment(Qt.AlignCenter)
        s_pix = self.assets.pixmap("app_shield_logo.png", 36, 40)
        if not s_pix.isNull():
            self.logo_lbl.setPixmap(s_pix)
        self.logo_lbl.setStyleSheet("background: transparent; border: none; padding: 0px;")
        top_identity.addWidget(self.logo_lbl)

        id_col = QVBoxLayout()
        id_col.setSpacing(2)
        self.app_name_lbl = QLabel(f"EraseVault v{__version__}", self.card)
        self.app_name_lbl.setMinimumHeight(26)
        self.app_tag_lbl = QLabel("Secure Data Sanitization Utility", self.card)
        self.app_tag_lbl.setMinimumHeight(18)
        id_col.addWidget(self.app_name_lbl)
        id_col.addWidget(self.app_tag_lbl)
        top_identity.addLayout(id_col, 1)
        c_layout.addLayout(top_identity)

        self.summary_lbl = QLabel(
            "EraseVault permanently sanitizes sensitive files, folders, external partitions, and "
            "USB-connected phone internal storage using hardware-aware erasure algorithms, "
            "free-space block shredding, and automatic post-erasure verification.",
            self.card,
        )
        self.summary_lbl.setWordWrap(True)
        c_layout.addWidget(self.summary_lbl)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)

        self.info_items: List[Tuple[QFrame, QLabel, QLabel]] = []
        specs = [
            ("Supported Targets", "Files, Folders, Drives & USB Phone Internal Storage"),
            ("Smart Media Detection", "Auto-Detects SSD / NVMe, HDD, USB Flash & Phone Storage"),
            ("Erase Standards", "Quick (1-Pass), NIST 800-88, DoD 5220.22-M, Schneier & Gutmann"),
            ("Anti-Recovery Protection", "Free-Space Block Shredding, Auto-Verification & System Lock"),
        ]
        for idx, (k_t, k_v) in enumerate(specs):
            box = QFrame(self.card)
            box.setObjectName(f"AboutInfoBox_{idx}")
            box.setAttribute(Qt.WA_StyledBackground, True)
            bl = QVBoxLayout(box)
            bl.setContentsMargins(16, 12, 16, 12)
            bl.setSpacing(4)
            lt = QLabel(k_t, box)
            lt.setMinimumHeight(18)
            lv = QLabel(k_v, box)
            lv.setWordWrap(True)
            lv.setMinimumHeight(20)
            bl.addWidget(lt)
            bl.addWidget(lv)
            grid.addWidget(box, idx // 2, idx % 2)
            self.info_items.append((box, lt, lv))

        c_layout.addLayout(grid)
        c_layout.addStretch(1)

        layout.addWidget(self.card, 1)
        self.apply_theme(LIGHT_THEME)

    def apply_theme(self, theme: ThemeColors) -> None:
        self.theme = theme
        self.setStyleSheet(
            f"QFrame#AboutFullPageCard {{ background-color: {theme.workspace_bg}; "
            f"border: 1px solid {theme.workspace_border}; border-radius: 16px; }}"
        )
        self.card.setStyleSheet(
            f"QFrame#AboutInnerCard {{ background-color: {theme.subcard_bg}; "
            f"border: 1px solid {theme.subcard_border}; border-radius: 14px; }}"
        )
        self.title_lbl.setStyleSheet(
            f"color: {theme.title_primary}; font-size: 20px; font-weight: 800; border: none; background: transparent; padding: 0px;"
        )
        self.app_name_lbl.setStyleSheet(
            f"color: {theme.title_primary}; font-size: 20px; font-weight: 800; border: none; background: transparent; padding: 0px;"
        )
        self.app_tag_lbl.setStyleSheet(
            f"color: {theme.title_accent}; font-size: 13px; font-weight: 600; border: none; background: transparent; padding: 0px;"
        )
        self.summary_lbl.setStyleSheet(
            f"color: {theme.subtitle_text}; font-size: 13.5px; line-height: 1.45; border: none; background: transparent; padding: 0px;"
        )
        for idx, (box, lt, lv) in enumerate(self.info_items):
            box.setStyleSheet(
                f"QFrame#AboutInfoBox_{idx} {{ background-color: {theme.workspace_bg}; "
                f"border: 1px solid {theme.workspace_border}; border-radius: 10px; }}"
            )
            lt.setStyleSheet(
                f"color: {theme.title_accent}; font-size: 12.5px; font-weight: 700; border: none; background: transparent; padding: 0px;"
            )
            lv.setStyleSheet(
                f"color: {theme.title_primary}; font-size: 13px; font-weight: 600; border: none; background: transparent; padding: 0px;"
            )
