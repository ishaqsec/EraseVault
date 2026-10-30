"""
Color palettes, theme tokens, and Qt Style Sheet (QSS) builders for EraseVault.
- Uses zero vertical padding (`padding: 0px ...`) on fixed-height controls so text never clips or shows half.
- Uses a single-outline dropdown design with smooth hover styles.
- Uses a sleek Royal Blue gradient (`#096DFD` -> `#1D4ED8`) for both the Start button and Progress Bar,
  with the completion percentage centered inside the progress bar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Reference Light Theme Constants
COLOR_OUTER_FRAME = "#F3F7FD"
COLOR_TOPBAR_BG = "#FAFCFD"
COLOR_SIDEBAR_BG = "#F6F9FD"
COLOR_SIDEBAR_ACTIVE_BLUE = "#267EFD"
COLOR_SIDEBAR_HOVER_BG = "#EAF2FD"
COLOR_SIDEBAR_TEXT_INACTIVE = "#0F172A"
COLOR_SIDEBAR_TEXT_ACTIVE = "#FFFFFF"

COLOR_MAIN_BG = "#F3F7FD"
COLOR_TITLE_DARK = "#061937"
COLOR_TITLE_BLUE = "#096DFD"
COLOR_SUBTITLE_GRAY = "#40547D"

COLOR_CARD_ACTIVE_BG = "#ECF4FE"
COLOR_CARD_ACTIVE_BORDER = "#3B83FF"
COLOR_CARD_INACTIVE_BG = "#FBFCFD"
COLOR_CARD_INACTIVE_BORDER = "#E3ECF8"
COLOR_CARD_CIRCLE_ACTIVE = "#1675FD"
COLOR_CARD_CIRCLE_INACTIVE = "#ECF3FD"

COLOR_WORKSPACE_PANEL_BG = "#FAFCFE"
COLOR_WORKSPACE_PANEL_BORDER = "#E3ECF8"
COLOR_DROPZONE_BG = "#FBFCFD"
COLOR_DROPZONE_BORDER = "#CBD9EC"

COLOR_PRIMARY_BLUE = "#1171FD"
COLOR_PRIMARY_BLUE_HOVER = "#0B5ED7"
COLOR_BROWSE_BLUE = "#0F71FD"
COLOR_SECONDARY_BTN_BG = "#FFFFFF"
COLOR_SECONDARY_BTN_BORDER = "#D5E2F4"
COLOR_SAFETY_NOTICE_BG = "#F1F7FE"
COLOR_SAFETY_NOTICE_BORDER = "#DCE9FA"
COLOR_SAFETY_NOTICE_TEXT = "#47597A"


@dataclass(frozen=True)
class ThemeColors:
    is_dark: bool
    outer_frame: str
    app_shell_bg: str
    app_shell_border: str
    topbar_bg: str
    topbar_border: str
    sidebar_bg: str
    sidebar_border: str
    sidebar_active_bg: str
    sidebar_hover_bg: str
    sidebar_text_inactive: str
    sidebar_text_active: str
    title_primary: str
    title_accent: str
    subtitle_text: str
    muted_text: str
    card_active_bg: str
    card_active_border: str
    card_inactive_bg: str
    card_inactive_border: str
    card_hover_bg: str
    card_hover_border: str
    workspace_bg: str
    workspace_border: str
    subcard_bg: str
    subcard_border: str
    dropzone_bg: str
    dropzone_border: str
    input_bg: str
    input_border: str
    input_hover_bg: str
    input_hover_border: str
    primary_blue: str
    primary_blue_hover: str
    secondary_btn_bg: str
    secondary_btn_border: str
    secondary_btn_hover: str
    safety_bg: str
    safety_border: str
    safety_text: str
    table_bg: str
    table_alt_bg: str
    table_header_bg: str
    table_grid: str
    table_selection_bg: str
    table_hover_bg: str


LIGHT_THEME = ThemeColors(
    is_dark=False,
    outer_frame="#F3F7FD",
    app_shell_bg="#F3F7FD",
    app_shell_border="#D5E2F2",
    topbar_bg="#FAFCFD",
    topbar_border="#E6EFFA",
    sidebar_bg="#F6F9FD",
    sidebar_border="#E4EEF9",
    sidebar_active_bg="#267EFD",
    sidebar_hover_bg="#EAF2FD",
    sidebar_text_inactive="#0F172A",
    sidebar_text_active="#FFFFFF",
    title_primary="#061937",
    title_accent="#096DFD",
    subtitle_text="#40547D",
    muted_text="#556987",
    card_active_bg="#ECF4FE",
    card_active_border="#3B83FF",
    card_inactive_bg="#FFFFFF",
    card_inactive_border="#E3ECF8",
    card_hover_bg="#F0F7FF",
    card_hover_border="#60A5FA",
    workspace_bg="#FFFFFF",
    workspace_border="#DCE7F5",
    subcard_bg="#F8FBFF",
    subcard_border="#DCE7F5",
    dropzone_bg="#FBFCFD",
    dropzone_border="#CBD9EC",
    input_bg="#FFFFFF",
    input_border="#CBD9EC",
    input_hover_bg="#F0F7FF",
    input_hover_border="#2563EB",
    primary_blue="#096DFD",
    primary_blue_hover="#0B5ED7",
    secondary_btn_bg="#FFFFFF",
    secondary_btn_border="#CBD9EC",
    secondary_btn_hover="#EFF6FF",
    safety_bg="#F1F7FE",
    safety_border="#DCE9FA",
    safety_text="#47597A",
    table_bg="#FFFFFF",
    table_alt_bg="#F8FAFC",
    table_header_bg="#F1F6FD",
    table_grid="#E8EFF8",
    table_selection_bg="#DBEAFE",
    table_hover_bg="#F0F7FF",
)

DARK_THEME = ThemeColors(
    is_dark=True,
    outer_frame="#0B1120",
    app_shell_bg="#0B1120",
    app_shell_border="#1E293B",
    topbar_bg="#0F172A",
    topbar_border="#1E293B",
    sidebar_bg="#111827",
    sidebar_border="#1E293B",
    sidebar_active_bg="#2563EB",
    sidebar_hover_bg="#1E293B",
    sidebar_text_inactive="#E2E8F0",
    sidebar_text_active="#FFFFFF",
    title_primary="#F8FAFC",
    title_accent="#3B82F6",
    subtitle_text="#94A3B8",
    muted_text="#94A3B8",
    card_active_bg="#172554",
    card_active_border="#3B82F6",
    card_inactive_bg="#151F32",
    card_inactive_border="#26354D",
    card_hover_bg="#1E293B",
    card_hover_border="#60A5FA",
    workspace_bg="#111827",
    workspace_border="#1E293B",
    subcard_bg="#151F32",
    subcard_border="#26354D",
    dropzone_bg="#0F172A",
    dropzone_border="#334155",
    input_bg="#0F172A",
    input_border="#334155",
    input_hover_bg="#1E293B",
    input_hover_border="#60A5FA",
    primary_blue="#2563EB",
    primary_blue_hover="#1D4ED8",
    secondary_btn_bg="#1E293B",
    secondary_btn_border="#334155",
    secondary_btn_hover="#283548",
    safety_bg="#172554",
    safety_border="#1E3A8A",
    safety_text="#BFDBFE",
    table_bg="#0F172A",
    table_alt_bg="#131C31",
    table_header_bg="#1E293B",
    table_grid="#1E293B",
    table_selection_bg="#1E3A8A",
    table_hover_bg="#172554",
)


def get_theme(mode: str = "light") -> ThemeColors:
    return DARK_THEME if str(mode).lower() == "dark" else LIGHT_THEME


def build_combo_stylesheet(
    theme: ThemeColors = LIGHT_THEME,
    chevron_icon_path: Optional[str] = None,
) -> str:
    """
    Builds a single-outline stylesheet for QComboBox with zero vertical padding
    so dropdown text is vertically centered and never cuts off.
    """
    down_arrow_rule = ""
    if chevron_icon_path:
        clean_path = chevron_icon_path.replace("\\", "/")
        down_arrow_rule = f"""
QComboBox::down-arrow, QComboBox#ErasureMethodCombo::down-arrow {{
    image: url("{clean_path}");
    width: 12px;
    height: 12px;
}}
"""
    popup_hover_bg = "#2563EB" if theme.is_dark else "#096DFD"
    popup_hover_fg = "#FFFFFF"
    popup_sel_bg = "#1E3A8A" if theme.is_dark else "#DBEAFE"
    popup_sel_fg = "#F8FAFC" if theme.is_dark else "#061937"
    drop_hover_bg = "#26354D" if theme.is_dark else "#DCEBFE"

    return f"""
QComboBox, QComboBox#ErasureMethodCombo {{
    background-color: {theme.input_bg};
    border: 1px solid {theme.input_border};
    border-radius: 9px;
    padding: 0px 34px 0px 12px;
    color: {theme.title_primary};
    font-size: 13.5px;
    font-weight: 600;
    outline: none;
}}
QComboBox:hover, QComboBox#ErasureMethodCombo:hover {{
    background-color: {theme.input_hover_bg};
    border: 1px solid {theme.input_hover_border};
}}
QComboBox:on, QComboBox#ErasureMethodCombo:on,
QComboBox:focus, QComboBox#ErasureMethodCombo:focus {{
    background-color: {theme.input_hover_bg};
    border: 1px solid {theme.title_accent};
    outline: none;
}}
QComboBox::drop-down, QComboBox#ErasureMethodCombo::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    border: none;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    width: 30px;
    background: transparent;
}}
QComboBox::drop-down:hover, QComboBox#ErasureMethodCombo::drop-down:hover {{
    background-color: {drop_hover_bg};
}}
{down_arrow_rule}
QComboBoxPrivateContainer {{
    background-color: {theme.workspace_bg};
    border: 1px solid {theme.input_hover_border};
    border-radius: 8px;
    padding: 2px;
}}
QComboBox QAbstractItemView {{
    background-color: {theme.workspace_bg};
    color: {theme.title_primary};
    border: none;
    outline: none;
    padding: 2px;
    selection-background-color: {popup_hover_bg};
    selection-color: {popup_hover_fg};
}}
QComboBox QAbstractItemView::item {{
    min-height: 30px;
    padding: 4px 10px;
    border-radius: 6px;
    border: none;
    color: {theme.title_primary};
    background-color: transparent;
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {popup_sel_bg};
    color: {popup_sel_fg};
    font-weight: 700;
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: {popup_hover_bg};
    color: {popup_hover_fg};
    font-weight: 700;
}}
"""


def build_global_stylesheet(
    theme: ThemeColors = LIGHT_THEME,
    chevron_icon_path: Optional[str] = None,
) -> str:
    combo_css = build_combo_stylesheet(theme, chevron_icon_path)
    prog_track_bg = "#0F172A" if theme.is_dark else "#E2ECF8"
    prog_track_bd = "#26354D" if theme.is_dark else "#C5D6EC"
    return f"""
QMainWindow, QWidget#RootContainer, QDialog {{
    background-color: {theme.app_shell_bg};
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    color: {theme.title_primary};
    border: none;
}}

QWidget#TransparentContainer, QFrame#TransparentContainer {{
    background: transparent;
    border: none;
}}

QFrame#AppShell {{
    background-color: {theme.app_shell_bg};
    border: 1px solid {theme.app_shell_border};
    border-radius: 0px;
}}

QFrame#TopBar {{
    background-color: {theme.topbar_bg};
    border-bottom: 1px solid {theme.topbar_border};
}}

QFrame#LeftSidebar {{
    background-color: {theme.sidebar_bg};
    border: 1px solid {theme.sidebar_border};
    border-radius: 16px;
}}

QFrame#WorkspacePanel, QFrame#FullPageCard {{
    background-color: {theme.workspace_bg};
    border: 1px solid {theme.workspace_border};
    border-radius: 16px;
}}

QFrame#SubSectionCard {{
    background-color: {theme.subcard_bg};
    border: 1px solid {theme.subcard_border};
    border-radius: 12px;
}}

QPushButton#SecondaryOutlineButton {{
    background-color: {theme.secondary_btn_bg};
    border: 1px solid {theme.secondary_btn_border};
    border-radius: 9px;
    color: {theme.title_primary};
    font-size: 13px;
    font-weight: 600;
    padding: 0px 14px;
}}
QPushButton#SecondaryOutlineButton:hover {{
    background-color: {theme.secondary_btn_hover};
    border-color: {theme.input_hover_border};
    color: {theme.title_accent};
}}

QPushButton#BrowseFilesButton {{
    background-color: {theme.primary_blue};
    border: none;
    border-radius: 10px;
    color: #FFFFFF;
    font-size: 13.5px;
    font-weight: 700;
    padding: 0px 18px;
}}
QPushButton#BrowseFilesButton:hover {{
    background-color: {theme.primary_blue_hover};
}}

QPushButton#EraseNowPrimaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #096DFD, stop:0.5 #1D63F2, stop:1 #1D4ED8);
    border: none;
    border-radius: 11px;
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 800;
    padding: 0px 24px;
}}
QPushButton#EraseNowPrimaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1E40AF);
}}
QPushButton#EraseNowPrimaryButton:pressed {{
    background-color: #1E3A8A;
}}
QPushButton#EraseNowPrimaryButton:disabled {{
    background: #64748B;
    color: #CBD5E1;
}}

QFrame#SafetyNoticeBox {{
    background-color: {theme.safety_bg};
    border: 1px solid {theme.safety_border};
    border-radius: 10px;
}}

{combo_css}

QLineEdit, QSpinBox {{
    background-color: {theme.input_bg};
    border: 1px solid {theme.input_border};
    border-radius: 9px;
    padding: 0px 12px;
    color: {theme.title_primary};
    font-size: 13px;
}}
QLineEdit:hover, QSpinBox:hover {{
    border-color: {theme.input_hover_border};
    background-color: {theme.input_hover_bg};
}}
QLineEdit:focus, QSpinBox:focus {{
    border: 1.5px solid {theme.title_accent};
}}

QCheckBox {{
    color: {theme.title_primary};
    font-size: 13.5px;
    font-weight: 600;
    spacing: 8px;
    background: transparent;
}}

QProgressBar {{
    background-color: {prog_track_bg};
    border: 1px solid {prog_track_bd};
    border-radius: 9px;
    text-align: center;
    font-size: 11.5px;
    font-weight: 800;
    color: {theme.title_primary};
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #096DFD, stop:0.5 #1D63F2, stop:1 #1D4ED8);
    border-radius: 8px;
}}

QTableWidget, QTextBrowser {{
    background-color: {theme.table_bg};
    alternate-background-color: {theme.table_alt_bg};
    border: 1px solid {theme.subcard_border};
    border-radius: 10px;
    gridline-color: {theme.table_grid};
    font-size: 12.5px;
    color: {theme.title_primary};
    selection-background-color: {theme.table_selection_bg};
    selection-color: {theme.title_primary};
}}
QTableWidget::item {{
    padding: 6px 10px;
}}
QTableWidget::item:hover {{
    background-color: {theme.table_hover_bg};
}}
QHeaderView::section {{
    background-color: {theme.table_header_bg};
    color: {theme.subtitle_text};
    font-weight: 700;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid {theme.subcard_border};
    padding: 7px 10px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #94A3B8;
    border-radius: 4px;
    min-height: 24px;
}}
"""


GLOBAL_STYLESHEET = build_global_stylesheet(LIGHT_THEME)
