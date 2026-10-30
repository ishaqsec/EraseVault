"""
Modal dialogs for EraseVault with modern, responsive layouts and full Light/Dark Theme adaptation:
1. DestructiveConfirmationDialog — streamlined 1-click confirmation (no 'I accept' checkbox barrier).
2. OperationProgressDialog — live progress tracking with pass/target status, MB/s, and cancel button.
3. MethodInfoDialog — modern, concise Sanitization Methods & Hardware Guide (Light in Light Mode, Dark in Dark Mode, necessary info only).
4. OperationReportDialog — detailed audit report and verification certificate viewer with export actions.
"""

from __future__ import annotations

import os
from typing import List, Optional

from ..core.models import (
    ERASURE_METHODS,
    ErasureMethod,
    OperationRecord,
    ProgressSnapshot,
    format_bytes,
)
from ..core.reports import ReportGenerator
from .qt_compat import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    Qt,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from .styles import LIGHT_THEME, ThemeColors


def _resolve_dialog_theme(parent: Optional[QWidget], theme: Optional[ThemeColors] = None) -> ThemeColors:
    if theme is not None:
        return theme
    curr = parent
    while curr is not None:
        if hasattr(curr, "theme") and isinstance(getattr(curr, "theme"), ThemeColors):
            return getattr(curr, "theme")
        curr = getattr(curr, "_parent", None) or (curr.parentWidget() if hasattr(curr, "parentWidget") else None)
    return LIGHT_THEME


class DestructiveConfirmationDialog(QDialog):
    """
    Streamlined confirmation dialog without any 'I accept / I understand' checkbox verification.
    """

    def __init__(
        self,
        operation_title: str,
        targets_summary: List[str],
        total_bytes: int,
        method: ErasureMethod,
        hardware_warning: str = "",
        require_typed_token: Optional[str] = None,
        parent: Optional[QWidget] = None,
        theme: Optional[ThemeColors] = None,
    ) -> None:
        super().__init__(parent)
        self.theme = _resolve_dialog_theme(parent, theme)
        t = self.theme
        self.setWindowTitle(f"Confirm {operation_title} — EraseVault")
        self.setMinimumSize(540, 340)
        self.confirmed = False

        self.setStyleSheet(
            f"QDialog {{ background-color: {t.app_shell_bg}; color: {t.title_primary}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        title_lbl = QLabel(f"Confirm {operation_title}", self)
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #EF4444; background: transparent;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            f"Permanently erase selected target(s) using <b>{method.display_name}</b> "
            f"({method.pass_count} {'pass' if method.pass_count == 1 else 'passes'}) — "
            f"Total size: <b>{format_bytes(total_bytes)}</b>.",
            self,
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"font-size: 13px; color: {t.subtitle_text}; background: transparent;")
        layout.addWidget(desc_lbl)

        manifest_box = QTextBrowser(self)
        manifest_box.setMinimumHeight(90)
        manifest_box.setStyleSheet(
            f"QTextBrowser {{ background-color: {t.workspace_bg}; color: {t.title_primary}; "
            f"border: 1px solid {t.workspace_border}; border-radius: 10px; padding: 8px; }}"
        )
        manifest_lines = "<br>".join(f"&bull; <code>{item}</code>" for item in targets_summary[:25])
        if len(targets_summary) > 25:
            manifest_lines += f"<br><i>... and {len(targets_summary) - 25} additional item(s)</i>"
        manifest_box.setHtml(f"<div style='font-size:12.5px; color:{t.title_primary};'>{manifest_lines}</div>")
        layout.addWidget(manifest_box, 1)

        if hardware_warning:
            warn_bg = "#1E293B" if t.is_dark else "#EFF6FF"
            warn_bd = "#3B82F6" if t.is_dark else "#BFDBFE"
            warn_fg = "#93C5FD" if t.is_dark else "#1E3A8A"
            warn_frame = QFrame(self)
            warn_frame.setObjectName("WarnBox")
            warn_frame.setStyleSheet(
                f"QFrame#WarnBox {{ background-color: {warn_bg}; border: 1px solid {warn_bd}; "
                f"border-radius: 10px; padding: 8px; }}"
            )
            warn_layout = QVBoxLayout(warn_frame)
            warn_layout.setContentsMargins(10, 6, 10, 6)
            warn_lbl = QLabel(hardware_warning, warn_frame)
            warn_lbl.setWordWrap(True)
            warn_lbl.setStyleSheet(f"font-size: 12px; color: {warn_fg}; border: none; background: transparent;")
            warn_layout.addWidget(warn_lbl)
            layout.addWidget(warn_frame)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setFixedSize(110, 38)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setStyleSheet(
            f"QPushButton {{ background-color: {t.secondary_btn_bg}; color: {t.title_primary}; "
            f"border: 1px solid {t.secondary_btn_border}; border-radius: 9px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {t.secondary_btn_hover}; border-color: #3B82F6; }}"
        )
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton(f"Start {operation_title}", self)
        self.confirm_btn.setEnabled(True)
        self.confirm_btn.setMinimumSize(180, 38)
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.setStyleSheet(
            "QPushButton { background-color: #DC2626; border: none; border-radius: 9px; "
            "padding: 8px 18px; font-size: 13.5px; font-weight: 700; color: #FFFFFF; }"
            "QPushButton:hover { background-color: #B91C1C; }"
        )
        self.confirm_btn.clicked.connect(self._on_confirm_clicked)
        btn_row.addWidget(self.confirm_btn)

        layout.addLayout(btn_row)

    def _on_confirm_clicked(self) -> None:
        self.confirmed = True
        self.accept()


class OperationProgressDialog(QDialog):
    """Displays real-time sanitization progress, throughput, pass counter, and cancel control."""

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.theme = _resolve_dialog_theme(parent)
        t = self.theme
        self.setWindowTitle(f"{title} — EraseVault")
        self.setMinimumSize(520, 230)
        self.cancel_requested = False
        self._cancel_cb = None

        self.setStyleSheet(f"QDialog {{ background-color: {t.app_shell_bg}; color: {t.title_primary}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        self.header_lbl = QLabel(title, self)
        self.header_lbl.setStyleSheet(f"font-size: 17px; font-weight: 800; color: {t.title_primary};")
        layout.addWidget(self.header_lbl)

        self.phase_lbl = QLabel("Initializing sanitization engine...", self)
        self.phase_lbl.setStyleSheet(f"font-size: 13.5px; font-weight: 600; color: {t.title_accent};")
        layout.addWidget(self.phase_lbl)

        self.target_lbl = QLabel("Preparing target manifest...", self)
        self.target_lbl.setWordWrap(True)
        self.target_lbl.setStyleSheet(f"font-size: 12.5px; color: {t.subtitle_text};")
        layout.addWidget(self.target_lbl)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        layout.addWidget(self.progress_bar)

        self.stats_lbl = QLabel("0 B / 0 B  |  Pass 1/1  |  0.00 MB/s", self)
        self.stats_lbl.setStyleSheet(f"font-size: 12px; color: {t.subtitle_text};")
        layout.addWidget(self.stats_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.cancel_btn = QPushButton("Cancel Operation", self)
        self.cancel_btn.setFixedSize(145, 36)
        self.cancel_btn.setStyleSheet(
            "QPushButton { background-color: #FEE2E2; border: 1px solid #FCA5A5; border-radius: 8px; "
            "padding: 6px 14px; color: #991B1B; font-weight: 700; }"
            "QPushButton:hover { background-color: #FECACA; }"
        )
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)

    def bind_cancel_callback(self, cb) -> None:
        self._cancel_cb = cb

    def update_snapshot(self, snap: ProgressSnapshot) -> None:
        self.phase_lbl.setText(snap.phase)
        self.target_lbl.setText(f"Current Target: {snap.current_target}")
        self.progress_bar.setValue(int(snap.percent))
        self.stats_lbl.setText(
            f"{format_bytes(snap.bytes_processed)} / {format_bytes(snap.total_bytes)}  |  "
            f"Pass {snap.current_pass}/{snap.total_passes}  |  {snap.throughput_mbps:.2f} MB/s"
        )

    def _on_cancel(self) -> None:
        self.cancel_requested = True
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Cancelling safely...")
        if self._cancel_cb:
            self._cancel_cb()


class MethodInfoDialog(QDialog):
    """
    Modern, concise Sanitization Methods & Hardware Guide.
    Automatically adapts to Light Mode and Dark Mode and displays only essential information.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        theme: Optional[ThemeColors] = None,
    ) -> None:
        super().__init__(parent)
        self.theme = _resolve_dialog_theme(parent, theme)
        t = self.theme
        self.setWindowTitle("Sanitization Methods & Hardware Guide — EraseVault")
        self.setMinimumSize(680, 520)

        self.setStyleSheet(
            f"QDialog {{ background-color: {t.app_shell_bg}; color: {t.title_primary}; }}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        hdr_title = QLabel("Sanitization Methods & Hardware Guide", self)
        hdr_title.setStyleSheet(
            f"color: {t.title_primary}; font-size: 19px; font-weight: 800; background: transparent; border: none;"
        )
        root.addWidget(hdr_title)

        hdr_sub = QLabel(
            "Essential guide to storage hardware types and permanent erasure standards.",
            self,
        )
        hdr_sub.setStyleSheet(
            f"color: {t.subtitle_text}; font-size: 12.5px; background: transparent; border: none;"
        )
        root.addWidget(hdr_sub)

        hw_row = QHBoxLayout()
        hw_row.setSpacing(10)
        hw_specs = [
            (
                "SSD & NVMe",
                "Best: NIST 800-88 Clear (1 Pass)",
                "Uses 1-pass CSPRNG overwrite + TRIM. Multi-pass adds wear without extra security.",
            ),
            (
                "Magnetic HDD",
                "Best: DoD 5220.22-M (3 Passes)",
                "Overwrites physical magnetic sectors with 0x00, 0xFF, and CSPRNG random bytes.",
            ),
            (
                "USB Phone & Flash",
                "Best: NIST Clear + Block Shred",
                "Overwrites files and shreds unallocated flash blocks so data cannot recover.",
            ),
        ]
        for hw_title, hw_best, hw_desc in hw_specs:
            hcard = QFrame(self)
            hcard.setObjectName("HwGuideCard")
            hcard.setStyleSheet(
                f"QFrame#HwGuideCard {{ background-color: {t.workspace_bg}; "
                f"border: 1px solid {t.workspace_border}; border-radius: 12px; }}"
            )
            hl = QVBoxLayout(hcard)
            hl.setContentsMargins(12, 10, 12, 10)
            hl.setSpacing(3)

            lt = QLabel(hw_title, hcard)
            lt.setStyleSheet(
                f"color: {t.title_primary}; font-size: 13.5px; font-weight: 800; background: transparent; border: none;"
            )
            lb = QLabel(hw_best, hcard)
            lb.setStyleSheet(
                f"color: {t.title_accent}; font-size: 11.5px; font-weight: 700; background: transparent; border: none;"
            )
            ld = QLabel(hw_desc, hcard)
            ld.setWordWrap(True)
            ld.setStyleSheet(
                f"color: {t.subtitle_text}; font-size: 11.5px; background: transparent; border: none;"
            )
            hl.addWidget(lt)
            hl.addWidget(lb)
            hl.addWidget(ld)
            hw_row.addWidget(hcard, 1)

        root.addLayout(hw_row)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        list_container = QWidget(scroll)
        list_container.setObjectName("MethodsListContainer")
        list_container.setStyleSheet(
            f"QWidget#MethodsListContainer {{ background-color: {t.app_shell_bg}; border: none; }}"
        )
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 2, 4, 2)
        list_layout.setSpacing(8)

        badge_ssd_bg = "#064E3B" if t.is_dark else "#DCFCE7"
        badge_ssd_fg = "#34D399" if t.is_dark else "#15803D"
        badge_hdd_bg = "#451A03" if t.is_dark else "#FEF3C7"
        badge_hdd_fg = "#FBBF24" if t.is_dark else "#B45309"
        pass_bg = "#172554" if t.is_dark else "#ECF4FE"
        pass_fg = "#60A5FA" if t.is_dark else "#096DFD"

        for m in ERASURE_METHODS:
            mcard = QFrame(list_container)
            mcard.setObjectName(f"MethodCard_{m.id}")
            mcard.setStyleSheet(
                f"QFrame#MethodCard_{m.id} {{ background-color: {t.workspace_bg}; "
                f"border: 1px solid {t.workspace_border}; border-radius: 11px; }}"
            )
            ml = QVBoxLayout(mcard)
            ml.setContentsMargins(14, 10, 14, 10)
            ml.setSpacing(4)

            top_r = QHBoxLayout()
            top_r.setSpacing(8)
            name_lbl = QLabel(m.display_name, mcard)
            name_lbl.setStyleSheet(
                f"color: {t.title_primary}; font-size: 13.5px; font-weight: 800; background: transparent; border: none;"
            )
            top_r.addWidget(name_lbl)

            std_lbl = QLabel(m.standard_reference, mcard)
            std_lbl.setStyleSheet(
                f"color: {t.subtitle_text}; font-size: 11.5px; font-weight: 600; background: transparent; border: none;"
            )
            top_r.addWidget(std_lbl)
            top_r.addStretch(1)

            pass_lbl = QLabel(
                f"{m.pass_count} {'Pass' if m.pass_count == 1 else 'Passes'}",
                mcard,
            )
            pass_lbl.setStyleSheet(
                f"background-color: {pass_bg}; color: {pass_fg}; border-radius: 6px; "
                f"padding: 2px 8px; font-size: 11px; font-weight: 700; border: none;"
            )
            top_r.addWidget(pass_lbl)

            compat_txt = "SSD • Phone • HDD" if m.ssd_recommended else "Magnetic HDD Only"
            c_bg = badge_ssd_bg if m.ssd_recommended else badge_hdd_bg
            c_fg = badge_ssd_fg if m.ssd_recommended else badge_hdd_fg
            compat_lbl = QLabel(compat_txt, mcard)
            compat_lbl.setStyleSheet(
                f"background-color: {c_bg}; color: {c_fg}; border-radius: 6px; "
                f"padding: 2px 8px; font-size: 11px; font-weight: 700; border: none;"
            )
            top_r.addWidget(compat_lbl)
            ml.addLayout(top_r)

            desc_lbl = QLabel(m.detailed_description, mcard)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(
                f"color: {t.subtitle_text}; font-size: 12px; background: transparent; border: none;"
            )
            ml.addWidget(desc_lbl)
            list_layout.addWidget(mcard)

        list_layout.addStretch(1)
        scroll.setWidget(list_container)
        root.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.close_btn = QPushButton("Close Guide", self)
        self.close_btn.setFixedSize(150, 38)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #096DFD, stop:1 #1D4ED8); "
            "color: #FFFFFF; border: none; border-radius: 10px; font-size: 13.5px; font-weight: 700; }"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1E40AF); }"
        )
        self.close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.close_btn)
        root.addLayout(btn_row)


class OperationReportDialog(QDialog):
    """Displays the detailed audit certificate for an OperationRecord and exports HTML, JSON, or TXT."""

    def __init__(
        self,
        record: OperationRecord,
        default_export_dir: str = "",
        parent: Optional[QWidget] = None,
        theme: Optional[ThemeColors] = None,
    ) -> None:
        super().__init__(parent)
        self.record = record
        self.theme = _resolve_dialog_theme(parent, theme)
        t = self.theme
        self.default_export_dir = default_export_dir or os.path.expanduser("~")
        self.setWindowTitle(f"Sanitization Audit Certificate ({record.op_id}) — EraseVault")
        self.setMinimumSize(760, 540)

        self.setStyleSheet(
            f"QDialog {{ background-color: {t.app_shell_bg}; color: {t.title_primary}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        self.browser = QTextBrowser(self)
        self.browser.setStyleSheet(
            f"QTextBrowser {{ background-color: {t.workspace_bg}; color: {t.title_primary}; "
            f"border: 1px solid {t.workspace_border}; border-radius: 12px; }}"
        )
        self.browser.setHtml(ReportGenerator.generate_html_report(record))
        layout.addWidget(self.browser, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        sec_css = (
            f"QPushButton {{ background-color: {t.secondary_btn_bg}; color: {t.title_primary}; "
            f"border: 1px solid {t.secondary_btn_border}; border-radius: 9px; "
            f"padding: 6px 14px; font-size: 13px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {t.secondary_btn_hover}; border-color: #3B82F6; }}"
        )

        self.export_html_btn = QPushButton("Export HTML", self)
        self.export_html_btn.setFixedHeight(38)
        self.export_html_btn.setCursor(Qt.PointingHandCursor)
        self.export_html_btn.setStyleSheet(sec_css)
        self.export_html_btn.clicked.connect(self.export_html)
        btn_row.addWidget(self.export_html_btn)

        self.export_json_btn = QPushButton("Export JSON", self)
        self.export_json_btn.setFixedHeight(38)
        self.export_json_btn.setCursor(Qt.PointingHandCursor)
        self.export_json_btn.setStyleSheet(sec_css)
        self.export_json_btn.clicked.connect(self.export_json)
        btn_row.addWidget(self.export_json_btn)

        self.export_txt_btn = QPushButton("Export TXT", self)
        self.export_txt_btn.setFixedHeight(38)
        self.export_txt_btn.setCursor(Qt.PointingHandCursor)
        self.export_txt_btn.setStyleSheet(sec_css)
        self.export_txt_btn.clicked.connect(self.export_txt)
        btn_row.addWidget(self.export_txt_btn)

        btn_row.addStretch(1)

        self.close_btn = QPushButton("Done", self)
        self.close_btn.setFixedSize(110, 38)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #096DFD, stop:1 #1D4ED8); "
            "color: #FFFFFF; border: none; border-radius: 9px; font-size: 13.5px; font-weight: 700; }"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1E40AF); }"
        )
        self.close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.close_btn)

        layout.addLayout(btn_row)

    def export_html(self) -> Optional[str]:
        default_file = os.path.join(self.default_export_dir, f"{self.record.op_id}_certificate.html")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export HTML Sanitization Certificate", default_file, "HTML Files (*.html)"
        )
        if path:
            saved = ReportGenerator.export_html_report(self.record, path)
            QMessageBox.information(self, "Report Exported", f"HTML Certificate saved to:\n{saved}")
            return saved
        return None

    def export_json(self) -> Optional[str]:
        default_file = os.path.join(self.default_export_dir, f"{self.record.op_id}_report.json")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON Audit Report", default_file, "JSON Files (*.json)"
        )
        if path:
            saved = ReportGenerator.export_json_report(self.record, path)
            QMessageBox.information(self, "Report Exported", f"JSON Audit Report saved to:\n{saved}")
            return saved
        return None

    def export_txt(self) -> Optional[str]:
        default_file = os.path.join(self.default_export_dir, f"{self.record.op_id}_audit.txt")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Plain Text Audit Log", default_file, "Text Files (*.txt)"
        )
        if path:
            saved = ReportGenerator.export_text_report(self.record, path)
            QMessageBox.information(self, "Report Exported", f"Text Audit Log saved to:\n{saved}")
            return saved
        return None
