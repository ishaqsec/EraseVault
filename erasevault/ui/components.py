"""
Reusable custom PySide6 widgets for EraseVault:
- TopTitleBarWidget (62px height: 36x40 unclipped Shield Logo + 20px EraseVault Title & 11.5px Tagline on left;
  larger 44x34 Minimize/Maximize/Close buttons with 18x18 icons aligned to top-right).
- SidebarNavButton (46px height: 20x20 icon + 14.5px bold text with zero vertical padding).
- ThemeSwitchButton (44px height: 20x20 icon + 14px text).
- SelectTargetCardButton (Responsive 86px card button with 34x30 icon, 15px bold title, single-line subtitle, and 24x24 chevron).
- ErasureMethodSelector (Single-outline 42px QComboBox wrapper with 'Auto' indicator on the auto-selected method).
"""

from __future__ import annotations

from typing import Optional

from ..core.models import ERASURE_METHODS, ErasureMethod
from .assets import AssetManager
from .qt_compat import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMouseEvent,
    QPoint,
    QPushButton,
    QSize,
    QSizePolicy,
    QStyledItemDelegate,
    Qt,
    QVBoxLayout,
    QWidget,
    Signal,
)
from .styles import LIGHT_THEME, ThemeColors, build_combo_stylesheet


class TopTitleBarWidget(QFrame):
    """
    Integrated top header bar (62px height):
    - Left: Pristine 36x40 EraseVault shield logo inside a 40x44 container + 20px EraseVault title + 11.5px tagline.
    - Top-Right: Larger 44x34 Minimize, Maximize/Restore, and Close controls with 18x18 icons aligned to the top edge.
    """

    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, assets: AssetManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.assets = assets
        self.theme: ThemeColors = LIGHT_THEME
        self.setObjectName("TopBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(62)
        self.setMouseTracking(True)
        self._drag_offset: Optional[QPoint] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 4, 8, 4)
        layout.setSpacing(12)

        self.shield_lbl = QLabel(self)
        self.shield_lbl.setFixedSize(40, 44)
        self.shield_lbl.setAlignment(Qt.AlignCenter)
        self.shield_lbl.setStyleSheet("background: transparent; border: none; padding: 0px;")
        shield_pix = self.assets.pixmap("app_shield_logo.png", 36, 40)
        if not shield_pix.isNull():
            self.shield_lbl.setPixmap(shield_pix)
        layout.addWidget(self.shield_lbl, 0, Qt.AlignVCenter)

        brand_col = QVBoxLayout()
        brand_col.setContentsMargins(0, 2, 0, 2)
        brand_col.setSpacing(0)

        self.brand_title_lbl = QLabel(self)
        self.brand_title_lbl.setMinimumHeight(26)
        self.brand_tag_lbl = QLabel("Secure Data Sanitization", self)
        self.brand_tag_lbl.setMinimumHeight(17)
        brand_col.addWidget(self.brand_title_lbl)
        brand_col.addWidget(self.brand_tag_lbl)
        layout.addLayout(brand_col)

        self.brand_label = self.brand_title_lbl

        layout.addStretch(1)

        # Larger Window Controls (44x34 button size, 18x18 icon size) aligned to top-right
        ctrl_row = QHBoxLayout()
        ctrl_row.setContentsMargins(0, 0, 0, 0)
        ctrl_row.setSpacing(4)

        self.min_btn = QPushButton("", self)
        self.min_btn.setFixedSize(44, 34)
        self.min_btn.setIconSize(QSize(18, 18))
        self.min_btn.setCursor(Qt.PointingHandCursor)
        self.min_btn.setToolTip("Minimize")
        self.min_btn.clicked.connect(lambda: self.minimize_clicked.emit())
        ctrl_row.addWidget(self.min_btn, 0, Qt.AlignTop)

        self.max_btn = QPushButton("", self)
        self.max_btn.setFixedSize(44, 34)
        self.max_btn.setIconSize(QSize(18, 18))
        self.max_btn.setCursor(Qt.PointingHandCursor)
        self.max_btn.setToolTip("Maximize / Restore")
        self.max_btn.clicked.connect(lambda: self.maximize_clicked.emit())
        ctrl_row.addWidget(self.max_btn, 0, Qt.AlignTop)

        self.close_btn = QPushButton("", self)
        self.close_btn.setFixedSize(44, 34)
        self.close_btn.setIconSize(QSize(18, 18))
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setToolTip("Close EraseVault")
        self.close_btn.clicked.connect(lambda: self.close_clicked.emit())
        ctrl_row.addWidget(self.close_btn, 0, Qt.AlignTop)

        layout.addLayout(ctrl_row)

        self.apply_theme(LIGHT_THEME)

    def apply_theme(self, theme: ThemeColors) -> None:
        self.theme = theme
        self.setStyleSheet(
            f"QFrame#TopBar {{ background-color: {theme.topbar_bg}; "
            f"border-bottom: 1px solid {theme.topbar_border}; }}"
        )
        self.brand_title_lbl.setText(
            f"<span style='color:{theme.title_primary};font-weight:800;'>Erase</span>"
            f"<span style='color:{theme.title_accent};font-weight:800;'>Vault</span>"
        )
        self.brand_title_lbl.setStyleSheet(
            "font-size: 20px; background: transparent; border: none; padding: 0px;"
        )
        self.brand_tag_lbl.setStyleSheet(
            f"color: {theme.subtitle_text}; font-size: 11.5px; font-weight: 600; "
            f"background: transparent; border: none; padding: 0px;"
        )

        suffix = "_white.png" if theme.is_dark else ".png"
        self.min_btn.setIcon(self.assets.icon(f"win_minimize{suffix}"))
        self.max_btn.setIcon(self.assets.icon(f"win_maximize{suffix}"))
        self.close_btn.setIcon(self.assets.icon(f"win_close{suffix}"))

        hover_bg = "#1E293B" if theme.is_dark else "#E2ECFA"
        btn_css = (
            f"QPushButton {{ background: transparent; border: none; border-radius: 7px; padding: 0px; }}"
            f"QPushButton:hover {{ background: {hover_bg}; }}"
        )
        self.min_btn.setStyleSheet(btn_css)
        self.max_btn.setStyleSheet(btn_css)
        self.close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 7px; padding: 0px; }"
            "QPushButton:hover { background: #EF4444; }"
        )

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if hasattr(event, "button") and event.button() == Qt.LeftButton:
            self.maximize_clicked.emit()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if hasattr(event, "button") and event.button() == Qt.LeftButton:
            win = self.window() if hasattr(self, "window") else None
            if win is not None and hasattr(event, "globalPosition"):
                if win.isMaximized():
                    win.showNormal()
                self._drag_offset = event.globalPosition().toPoint() - win.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and hasattr(event, "globalPosition"):
            win = self.window() if hasattr(self, "window") else None
            if win is not None and not win.isMaximized():
                win.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None


class SidebarNavButton(QPushButton):
    """
    Sidebar navigation item with 20x20 icon, 14.5px typography, 46px height,
    and zero vertical CSS padding (`padding: 0px 16px`) so text never clips or shows half.
    """

    nav_selected = Signal(str)

    def __init__(
        self,
        nav_id: str,
        label_text: str,
        assets: AssetManager,
        active: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(f"   {label_text}", parent)
        self.nav_id = nav_id
        self.label_text = label_text
        self.assets = assets
        self._is_active = active
        self.theme: ThemeColors = LIGHT_THEME

        self.setFixedHeight(46)
        self.setIconSize(QSize(20, 20))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        self.clicked.connect(lambda: self.nav_selected.emit(self.nav_id))
        self._refresh_visuals()

    def set_active(self, active: bool) -> None:
        self._is_active = active
        self._refresh_visuals()

    def apply_theme(self, theme: ThemeColors) -> None:
        self.theme = theme
        self._refresh_visuals()

    def _refresh_visuals(self) -> None:
        use_white_icon = self._is_active or self.theme.is_dark
        icon_file = f"nav_{self.nav_id}_{'white' if use_white_icon else 'dark'}.png"
        self.setIcon(self.assets.icon(icon_file))

        if self._is_active:
            self.setStyleSheet(
                f"QPushButton {{ background-color: {self.theme.sidebar_active_bg}; "
                f"color: {self.theme.sidebar_text_active}; border: none; border-radius: 11px; "
                f"font-size: 14.5px; font-weight: 700; text-align: left; padding: 0px 16px; }}"
            )
        else:
            self.setStyleSheet(
                f"QPushButton {{ background-color: transparent; "
                f"color: {self.theme.sidebar_text_inactive}; border: none; border-radius: 11px; "
                f"font-size: 14.5px; font-weight: 600; text-align: left; padding: 0px 16px; }}"
                f"QPushButton:hover {{ background-color: {self.theme.sidebar_hover_bg}; }}"
            )

    @property
    def is_active(self) -> bool:
        return self._is_active


class ThemeSwitchButton(QPushButton):
    """
    Bottom sidebar button with 20x20 icon, 44px height, and zero vertical padding.
    """

    theme_toggled = Signal()

    def __init__(self, assets: AssetManager, parent: Optional[QWidget] = None) -> None:
        super().__init__("   Switch to Dark", parent)
        self.assets = assets
        self.theme: ThemeColors = LIGHT_THEME

        self.setFixedHeight(44)
        self.setIconSize(QSize(20, 20))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        self.clicked.connect(lambda: self.theme_toggled.emit())
        self.apply_theme(LIGHT_THEME)

    def apply_theme(self, theme: ThemeColors) -> None:
        self.theme = theme
        if theme.is_dark:
            self.setIcon(self.assets.icon("theme_sun_gold.png"))
            self.setText("   Switch to Light")
            btn_bg, btn_border, fg = "#1E293B", "#334155", "#F8FAFC"
        else:
            self.setIcon(self.assets.icon("theme_moon_dark.png"))
            self.setText("   Switch to Dark")
            btn_bg, btn_border, fg = "#EEF4FC", "#D5E3F7", "#0F172A"

        self.setStyleSheet(
            f"QPushButton {{ background-color: {btn_bg}; color: {fg}; "
            f"border: 1px solid {btn_border}; border-radius: 11px; "
            f"font-size: 14px; font-weight: 700; text-align: left; padding: 0px 16px; }}"
            f"QPushButton:hover {{ background-color: {theme.sidebar_hover_bg}; border-color: #3B82F6; }}"
        )


class SelectTargetCardButton(QFrame):
    """
    Responsive 86px-high interactive card button in the Main Menu for:
    - Select Files
    - Select Folder
    - Select Drive (Drive, USB or Phone)
    """

    card_clicked = Signal(str)

    def __init__(
        self,
        action_id: str,
        icon_name: str,
        title: str,
        subtitle: str,
        assets: AssetManager,
        active: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.action_id = action_id
        self.icon_name = icon_name
        self.title = title
        self.default_subtitle = subtitle
        self.subtitle = subtitle
        self.assets = assets
        self._is_active = active
        self.theme: ThemeColors = LIGHT_THEME
        self.setObjectName(f"TargetCard_{action_id}")

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(84)
        self.setFixedHeight(86)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 10, 14, 10)
        row.setSpacing(12)

        self.icon_lbl = QLabel(self)
        self.icon_lbl.setFixedSize(38, 34)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        if hasattr(Qt, "WA_TransparentForMouseEvents"):
            self.icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        pix = self.assets.pixmap(icon_name, 34, 30)
        if not pix.isNull():
            self.icon_lbl.setPixmap(pix)
        row.addWidget(self.icon_lbl, 0, Qt.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        self.title_lbl = QLabel(title, self)
        self.title_lbl.setMinimumHeight(22)
        if hasattr(Qt, "WA_TransparentForMouseEvents"):
            self.title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.sub_lbl = QLabel(subtitle, self)
        self.sub_lbl.setMinimumHeight(18)
        if hasattr(Qt, "WA_TransparentForMouseEvents"):
            self.sub_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        text_col.addWidget(self.title_lbl)
        text_col.addWidget(self.sub_lbl)
        row.addLayout(text_col, 1)

        self.arrow_btn = QPushButton("", self)
        self.arrow_btn.setFixedSize(26, 26)
        self.arrow_btn.setIconSize(QSize(24, 24))
        self.arrow_btn.setCursor(Qt.PointingHandCursor)
        self.arrow_btn.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0px; }")
        self.arrow_btn.clicked.connect(lambda: self.card_clicked.emit(self.action_id))
        row.addWidget(self.arrow_btn, 0, Qt.AlignVCenter)

        self._refresh_visuals()

    def set_subtitle(self, text: Optional[str] = None) -> None:
        self.subtitle = text if text else self.default_subtitle
        self.sub_lbl.setText(self.subtitle)

    def set_active(self, active: bool) -> None:
        self._is_active = active
        self._refresh_visuals()

    def apply_theme(self, theme: ThemeColors) -> None:
        self.theme = theme
        self._refresh_visuals()

    def _refresh_visuals(self) -> None:
        if self._is_active:
            arrow_asset = "circle_arrow_active.png"
            bg = self.theme.card_active_bg
            bd = f"2px solid {self.theme.card_active_border}"
        else:
            arrow_asset = (
                "circle_arrow_inactive_dark.png"
                if self.theme.is_dark
                else "circle_arrow_inactive.png"
            )
            bg = self.theme.card_inactive_bg
            bd = f"1px solid {self.theme.card_inactive_border}"

        self.arrow_btn.setIcon(self.assets.icon(arrow_asset))
        obj_name = self.objectName()
        self.setStyleSheet(
            f"QFrame#{obj_name} {{ background-color: {bg}; border: {bd}; border-radius: 14px; }}"
            f"QFrame#{obj_name}:hover {{ border: 1.5px solid {self.theme.card_hover_border}; "
            f"background-color: {self.theme.card_hover_bg}; }}"
        )
        self.icon_lbl.setStyleSheet("background: transparent; border: none; padding: 0px;")
        self.title_lbl.setStyleSheet(
            f"color: {self.theme.title_primary}; font-size: 15px; font-weight: 800; "
            f"background: transparent; border: none; padding: 0px;"
        )
        self.sub_lbl.setStyleSheet(
            f"color: {self.theme.subtitle_text}; font-size: 12px; font-weight: 500; "
            f"background: transparent; border: none; padding: 0px;"
        )

    @property
    def is_active(self) -> bool:
        return self._is_active

    def click(self) -> None:
        self.card_clicked.emit(self.action_id)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.card_clicked.emit(self.action_id)


ActionCardWidget = SelectTargetCardButton


class ErasureMethodSelector(QWidget):
    """
    Single-outline 42px-high erasure method dropdown with a 16x18 shield icon,
    hover styling, and dynamic '(Auto)' indicator on the auto-selected method.
    """

    method_changed = Signal(object)  # ErasureMethod

    def __init__(self, assets: AssetManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.assets = assets
        self.theme: ThemeColors = LIGHT_THEME
        self._auto_method_id: Optional[str] = None
        self.setObjectName("TransparentContainer")
        self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.combo = QComboBox(self)
        self.combo.setObjectName("ErasureMethodCombo")
        self.combo.setFixedHeight(42)
        self.combo.setIconSize(QSize(16, 18))
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo.setCursor(Qt.PointingHandCursor)
        if hasattr(self.combo, "setItemDelegate"):
            self.combo.setItemDelegate(QStyledItemDelegate(self.combo))
        if hasattr(self.combo, "view"):
            try:
                view = self.combo.view()
                if view is not None and hasattr(view, "setFrameShape"):
                    view.setFrameShape(QFrame.NoFrame)
            except Exception:
                pass

        shield_ic = self.assets.icon("method_shield.png")
        for m in ERASURE_METHODS:
            self.combo.addItem(
                shield_ic,
                self._format_method_text(m, is_auto=False),
                m.id,
            )

        layout.addWidget(self.combo)
        self.combo.currentIndexChanged.connect(self._on_index_changed)
        self.apply_theme(LIGHT_THEME)

    @staticmethod
    def _format_method_text(m: ErasureMethod, is_auto: bool = False) -> str:
        base = f"  {m.display_name}  ({m.pass_count} {'Pass' if m.pass_count == 1 else 'Passes'})"
        return f"{base} — Auto" if is_auto else base

    def set_auto_method_id(self, auto_method_id: Optional[str]) -> None:
        """Marks `auto_method_id` with '— Auto' directly inside the dropdown items."""
        self._auto_method_id = auto_method_id
        if hasattr(self.combo, "setItemText"):
            for i, m in enumerate(ERASURE_METHODS):
                self.combo.setItemText(
                    i, self._format_method_text(m, is_auto=(m.id == auto_method_id))
                )

    def apply_theme(self, theme: ThemeColors) -> None:
        self.theme = theme
        icon_name = "method_shield_dark.png" if theme.is_dark else "method_shield.png"
        ic = self.assets.icon(icon_name)
        if hasattr(self.combo, "setItemIcon"):
            for i in range(self.combo.count()):
                self.combo.setItemIcon(i, ic)

        chevron_file = "dropdown_chevron_white.png" if theme.is_dark else "dropdown_chevron.png"
        self.combo.setStyleSheet(
            build_combo_stylesheet(theme, self.assets.icon_path(chevron_file))
        )

    def current_method(self) -> ErasureMethod:
        idx = self.combo.currentIndex()
        if 0 <= idx < len(ERASURE_METHODS):
            return ERASURE_METHODS[idx]
        return ERASURE_METHODS[0]

    def set_method_by_id(self, method_id: str, is_auto: bool = False) -> None:
        if is_auto:
            self.set_auto_method_id(method_id)
        for i, m in enumerate(ERASURE_METHODS):
            if m.id == method_id:
                self.combo.setCurrentIndex(i)
                return

    def _on_index_changed(self, idx: int) -> None:
        if 0 <= idx < len(ERASURE_METHODS):
            self.method_changed.emit(ERASURE_METHODS[idx])
