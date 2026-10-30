"""
Main Desktop Window for EraseVault.
- Wider default dimensions (`REF_WIDTH = 1440`, `REF_HEIGHT = 840`) that scale to the active screen resolution.
- Fully mouse-resizable across all 4 edges and 4 corners on Windows via native `WM_NCHITTEST` (`nativeEvent`),
  cross-platform mouse drag handlers (`RESIZE_GRIP_MARGIN = 8`), and a bottom-right `QSizeGrip`.
- Clears previous session sanitize records on normal startup so old records from prior runs are not shown.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from typing import Any, Dict, List, Optional, Tuple

from ..core.history import HistoryManager
from ..core.models import OperationRecord
from ..core.sanitizer import SanitizationEngine
from ..core.settings import SettingsManager
from ..core.storage import StorageInspector
from ..core.validator import TargetValidator
from .assets import AssetManager
from .components import (
    SidebarNavButton,
    ThemeSwitchButton,
    TopTitleBarWidget,
)
from .panels import (
    AboutWorkspacePanel,
    HomeWorkspacePanel,
    ReportsWorkspacePanel,
    SettingsWorkspacePanel,
)
from .qt_compat import (
    QApplication,
    QColor,
    QCursor,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMouseEvent,
    QPalette,
    QPoint,
    QRect,
    QResizeEvent,
    QScreen,
    QSizeGrip,
    QStackedWidget,
    Qt,
    QVBoxLayout,
    QWidget,
)
from .styles import (
    ThemeColors,
    build_global_stylesheet,
    get_theme,
)

REF_WIDTH = 1440
REF_HEIGHT = 840
RESIZE_GRIP_MARGIN = 8


class EraseVaultMainWindow(QMainWindow):
    """
    Frameless, edge-to-edge, screen-resolution-adaptive and mouse-resizable main application window
    with Light & Dark Theme support.
    """

    def __init__(
        self,
        storage: Optional[StorageInspector] = None,
        history: Optional[HistoryManager] = None,
        settings_mgr: Optional[SettingsManager] = None,
        assets: Optional[AssetManager] = None,
        auto_confirm_in_tests: bool = False,
        initial_size: Optional[Tuple[int, int]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.storage = storage or StorageInspector()
        self.validator = TargetValidator(self.storage)
        self.engine = SanitizationEngine(self.storage, self.validator)
        if history is None:
            self.history = HistoryManager()
            try:
                self.history.clear_history()
            except Exception:
                pass
        else:
            self.history = history
        self.settings_mgr = settings_mgr or SettingsManager()
        self.assets = assets or AssetManager()
        self.auto_confirm_in_tests = auto_confirm_in_tests
        self.theme: ThemeColors = get_theme(self.settings_mgr.settings.theme_mode)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Window
            | Qt.WindowMinMaxButtonsHint
            | Qt.WindowSystemMenuHint
        )
        self.setWindowTitle("EraseVault — Secure Data Sanitization")
        self.setWindowIcon(self.assets.icon("app_shield_logo.png"))
        self.setMouseTracking(True)

        self._resize_edge: Optional[str] = None
        self._resize_start_pos: Optional[QPoint] = None
        self._resize_start_geom: Optional[QRect] = None

        self.root_widget = QWidget(self)
        self.root_widget.setObjectName("RootContainer")
        self.root_widget.setAttribute(Qt.WA_StyledBackground, True)
        self.root_widget.setMouseTracking(True)
        self.setCentralWidget(self.root_widget)

        self.root_layout = QVBoxLayout(self.root_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.app_shell = QFrame(self.root_widget)
        self.app_shell.setObjectName("AppShell")
        self.app_shell.setAttribute(Qt.WA_StyledBackground, True)
        self.app_shell.setMouseTracking(True)
        self.root_layout.addWidget(self.app_shell, 1)

        self.shell_layout = QVBoxLayout(self.app_shell)
        self.shell_layout.setContentsMargins(0, 0, 0, 0)
        self.shell_layout.setSpacing(0)

        # 1. Top Title Bar (62px height, unclipped 36x40 shield logo + 20px EraseVault title + 44x34 window controls)
        self.top_bar = TopTitleBarWidget(self.assets, self.app_shell)
        self.top_bar.minimize_clicked.connect(self.showMinimized)
        self.top_bar.maximize_clicked.connect(self._toggle_maximize)
        self.top_bar.close_clicked.connect(self.close)
        self.shell_layout.addWidget(self.top_bar)

        # 2. Body Area: Left Sidebar + Right Main Content Stack
        self.body_widget = QWidget(self.app_shell)
        self.body_widget.setObjectName("TransparentContainer")
        self.body_widget.setMouseTracking(True)
        self.body_layout = QHBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(16, 12, 18, 14)
        self.body_layout.setSpacing(16)

        # Left Sidebar Panel
        self.sidebar_panel = QFrame(self.body_widget)
        self.sidebar_panel.setObjectName("LeftSidebar")
        self.sidebar_panel.setAttribute(Qt.WA_StyledBackground, True)
        self.sidebar_panel.setFixedWidth(234)
        self.sidebar_panel.setMouseTracking(True)

        sidebar_layout = QVBoxLayout(self.sidebar_panel)
        sidebar_layout.setContentsMargins(10, 12, 10, 12)
        sidebar_layout.setSpacing(6)

        self.nav_buttons: Dict[str, SidebarNavButton] = {}
        self._nav_specs: List[Tuple[str, str]] = [
            ("home", "Home"),
            ("reports", "Reports"),
            ("settings", "Settings"),
            ("about", "About"),
        ]
        for nav_id, nav_label in self._nav_specs:
            btn = SidebarNavButton(
                nav_id=nav_id,
                label_text=nav_label,
                assets=self.assets,
                active=(nav_id == "home"),
                parent=self.sidebar_panel,
            )
            btn.nav_selected.connect(self.navigate_to)
            sidebar_layout.addWidget(btn)
            self.nav_buttons[nav_id] = btn

        sidebar_layout.addStretch(1)

        self.theme_switch_btn = ThemeSwitchButton(self.assets, self.sidebar_panel)
        self.theme_switch_btn.theme_toggled.connect(self.toggle_theme)
        sidebar_layout.addWidget(self.theme_switch_btn)

        self.body_layout.addWidget(self.sidebar_panel)

        # Right Main Content Area: QStackedWidget for [0: Home, 1: Reports, 2: Settings, 3: About]
        self.main_page_stack = QStackedWidget(self.body_widget)
        self.main_page_stack.setObjectName("TransparentContainer")
        self.main_page_stack.setMouseTracking(True)
        self.body_layout.addWidget(self.main_page_stack, 1)
        self.shell_layout.addWidget(self.body_widget, 1)

        # --- Page 0: Optimized Home / Main Menu ---
        self.home_page = QWidget(self.main_page_stack)
        self.home_page.setObjectName("TransparentContainer")
        home_layout = QVBoxLayout(self.home_page)
        home_layout.setContentsMargins(2, 2, 2, 2)
        home_layout.setSpacing(12)

        # Hero Header
        self.hero_header = QWidget(self.home_page)
        self.hero_header.setObjectName("TransparentContainer")
        hero_layout = QVBoxLayout(self.hero_header)
        hero_layout.setContentsMargins(2, 0, 2, 2)
        hero_layout.setSpacing(2)

        self.hero_title_lbl = QLabel(self.hero_header)
        self.hero_title_lbl.setMinimumHeight(34)
        self.hero_subtitle_lbl = QLabel(
            "Select files, a folder, a drive, or USB phone storage — EraseVault auto-detects media, selects the best method, and verifies removal.",
            self.hero_header,
        )
        self.hero_subtitle_lbl.setMinimumHeight(20)
        self.hero_subtitle_lbl.setWordWrap(True)
        hero_layout.addWidget(self.hero_title_lbl)
        hero_layout.addWidget(self.hero_subtitle_lbl)
        home_layout.addWidget(self.hero_header)

        # Main Menu Workspace Panel
        self.home_panel = HomeWorkspacePanel(
            assets=self.assets,
            engine=self.engine,
            history=self.history,
            settings_mgr=self.settings_mgr,
            auto_confirm_in_tests=self.auto_confirm_in_tests,
            parent=self.home_page,
        )
        self.erase_files_panel = self.home_panel
        self.action_cards = {
            "select_files": self.home_panel.select_files_card,
            "select_folder": self.home_panel.select_folder_card,
            "select_drive": self.home_panel.select_drive_card,
        }

        home_layout.addWidget(self.home_panel, 1)
        self.main_page_stack.addWidget(self.home_page)              # page index 0

        # --- Page 1: Redesigned Reports View ---
        self.reports_panel = ReportsWorkspacePanel(
            assets=self.assets,
            history=self.history,
            settings_mgr=self.settings_mgr,
            parent=self.main_page_stack,
        )
        self.main_page_stack.addWidget(self.reports_panel)          # page index 1

        # --- Page 2: Redesigned Settings View ---
        self.settings_panel = SettingsWorkspacePanel(
            assets=self.assets,
            settings_mgr=self.settings_mgr,
            parent=self.main_page_stack,
        )
        self.main_page_stack.addWidget(self.settings_panel)         # page index 2

        # --- Page 3: Redesigned About View ---
        self.about_panel = AboutWorkspacePanel(
            assets=self.assets,
            engine=self.engine,
            parent=self.main_page_stack,
        )
        self.main_page_stack.addWidget(self.about_panel)            # page index 3

        # Bottom-right QSizeGrip so the user can also drag the bottom-right corner directly
        self.size_grip = QSizeGrip(self.app_shell)
        self.size_grip.setFixedSize(14, 14)
        self.size_grip.setStyleSheet("background: transparent; border: none;")

        self.home_panel.operation_recorded.connect(self._on_operation_completed)
        self.settings_panel.settings_updated.connect(self._on_settings_updated)

        self.current_nav_id = "home"
        self.apply_theme(self.theme)

        if initial_size is not None:
            self.setMinimumSize(min(820, initial_size[0]), min(480, initial_size[1]))
            self.resize(initial_size[0], initial_size[1])
        else:
            self.auto_adjust_to_screen_resolution()

        self._apply_windows_dwm_rounded_corners()

    def _apply_windows_dwm_rounded_corners(self) -> None:
        if os.name == "nt" and hasattr(self, "winId"):
            try:
                hwnd = int(self.winId())
                DWMWA_WINDOW_CORNER_PREFERENCE = 33
                DWMWCP_ROUND = ctypes.c_int(2)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_WINDOW_CORNER_PREFERENCE,
                    ctypes.byref(DWMWCP_ROUND),
                    ctypes.sizeof(DWMWCP_ROUND),
                )
            except Exception:
                pass

    def nativeEvent(self, eventType: Any, message: Any) -> Tuple[bool, int]:
        """
        Handles Windows WM_NCHITTEST (0x0084) so the frameless window can be smoothly
        resized via mouse from all 4 edges (left, right, top, bottom) and all 4 corners.
        """
        if os.name == "nt" and not self.isMaximized():
            try:
                msg = wintypes.MSG.from_address(int(message))
                WM_NCHITTEST = 0x0084
                if msg.message == WM_NCHITTEST:
                    x_pos = ctypes.c_short(msg.lParam & 0xFFFF).value
                    y_pos = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                    fg = self.frameGeometry()
                    lx = x_pos - fg.left()
                    ly = y_pos - fg.top()
                    w, h = fg.width(), fg.height()
                    m = RESIZE_GRIP_MARGIN

                    left = 0 <= lx < m
                    right = (w - m) <= lx <= w
                    top = 0 <= ly < m
                    bottom = (h - m) <= ly <= h

                    HTLEFT = 10
                    HTRIGHT = 11
                    HTTOP = 12
                    HTTOPLEFT = 13
                    HTTOPRIGHT = 14
                    HTBOTTOM = 15
                    HTBOTTOMLEFT = 16
                    HTBOTTOMRIGHT = 17

                    if top and left:
                        return (True, HTTOPLEFT)
                    if top and right:
                        return (True, HTTOPRIGHT)
                    if bottom and left:
                        return (True, HTBOTTOMLEFT)
                    if bottom and right:
                        return (True, HTBOTTOMRIGHT)
                    if left:
                        return (True, HTLEFT)
                    if right:
                        return (True, HTRIGHT)
                    if top:
                        return (True, HTTOP)
                    if bottom:
                        return (True, HTBOTTOM)
            except Exception:
                pass
        if hasattr(super(), "nativeEvent"):
            return super().nativeEvent(eventType, message)  # type: ignore[misc]
        return (False, 0)

    def apply_theme(self, theme: ThemeColors) -> None:
        self.theme = theme
        chevron_file = "dropdown_chevron_white.png" if theme.is_dark else "dropdown_chevron.png"
        self.setStyleSheet(build_global_stylesheet(theme, self.assets.icon_path(chevron_file)))

        self.sidebar_panel.setStyleSheet(
            f"QFrame#LeftSidebar {{ background-color: {theme.sidebar_bg}; "
            f"border: 1px solid {theme.sidebar_border}; border-radius: 16px; }}"
        )

        app = QApplication.instance()
        if app is not None and hasattr(app, "setPalette"):
            pal = QPalette()
            if theme.is_dark:
                pal.setColor(QPalette.Window, QColor(11, 17, 32))
                pal.setColor(QPalette.WindowText, QColor(248, 250, 252))
                pal.setColor(QPalette.Base, QColor(15, 23, 42))
                pal.setColor(QPalette.AlternateBase, QColor(21, 31, 50))
                pal.setColor(QPalette.Text, QColor(248, 250, 252))
                pal.setColor(QPalette.Button, QColor(30, 41, 59))
                pal.setColor(QPalette.ButtonText, QColor(248, 250, 252))
                pal.setColor(QPalette.Highlight, QColor(37, 99, 235))
                pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
            else:
                pal.setColor(QPalette.Window, QColor(243, 247, 253))
                pal.setColor(QPalette.WindowText, QColor(6, 25, 55))
                pal.setColor(QPalette.Base, QColor(255, 255, 255))
                pal.setColor(QPalette.AlternateBase, QColor(248, 250, 252))
                pal.setColor(QPalette.Text, QColor(15, 23, 42))
                pal.setColor(QPalette.Button, QColor(251, 252, 254))
                pal.setColor(QPalette.ButtonText, QColor(15, 23, 42))
                pal.setColor(QPalette.Highlight, QColor(38, 126, 253))
                pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
            app.setPalette(pal)

        self.top_bar.apply_theme(theme)
        for btn in self.nav_buttons.values():
            btn.apply_theme(theme)
        self.theme_switch_btn.apply_theme(theme)

        self.hero_title_lbl.setText(
            f"<span style='color:{theme.title_primary};font-weight:800;'>Securely Erase </span>"
            f"<span style='color:{theme.title_accent};font-weight:800;'>Your Data</span>"
        )
        self.hero_title_lbl.setStyleSheet(
            "font-size: 25px; background: transparent; border: none; padding: 0px;"
        )
        self.hero_subtitle_lbl.setStyleSheet(
            f"color: {theme.subtitle_text}; font-size: 13px; font-weight: 500; "
            f"background: transparent; border: none; padding: 0px;"
        )

        self.home_panel.apply_theme(theme)
        self.reports_panel.apply_theme(theme)
        self.settings_panel.apply_theme(theme)
        self.about_panel.apply_theme(theme)

    def toggle_theme(self) -> ThemeColors:
        new_mode = "dark" if not self.theme.is_dark else "light"
        self.settings_mgr.settings.theme_mode = new_mode
        try:
            self.settings_mgr.save()
        except Exception:
            pass
        new_theme = get_theme(new_mode)
        self.apply_theme(new_theme)
        return new_theme

    @staticmethod
    def calculate_optimal_window_size(avail_w: int, avail_h: int) -> Tuple[int, int]:
        max_w = max(860, int(avail_w * 0.93))
        max_h = max(500, int(avail_h * 0.86))
        scale = min(max_w / float(REF_WIDTH), max_h / float(REF_HEIGHT), 1.15)
        opt_w = max(min(920, avail_w), int(round(REF_WIDTH * scale)))
        opt_h = max(min(520, avail_h), int(round(REF_HEIGHT * scale)))
        return (min(opt_w, avail_w), min(opt_h, avail_h))

    def auto_adjust_to_screen_resolution(self, screen: Optional[QScreen] = None) -> Tuple[int, int]:
        if screen is None:
            try:
                screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
            except Exception:
                screen = QApplication.primaryScreen()

        if screen is not None:
            avail = screen.availableGeometry()
            avail_w, avail_h = avail.width(), avail.height()
            avail_x, avail_y = avail.x(), avail.y()
        else:
            avail_w, avail_h = REF_WIDTH, REF_HEIGHT
            avail_x, avail_y = 0, 0

        min_w = min(840, max(680, int(avail_w * 0.55)))
        min_h = min(480, max(440, int(avail_h * 0.55)))
        self.setMinimumSize(min_w, min_h)

        target_w, target_h = self.calculate_optimal_window_size(avail_w, avail_h)
        pos_x = avail_x + max(0, (avail_w - target_w) // 2)
        pos_y = avail_y + max(0, (avail_h - target_h) // 2)

        self.setGeometry(pos_x, pos_y, target_w, target_h)
        self.apply_responsive_layout(target_w, target_h)
        return (target_w, target_h)

    def resizeEvent(self, event: QResizeEvent) -> None:
        w, h = self.width(), self.height()
        if w > 0 and h > 0:
            self.apply_responsive_layout(w, h)

    def apply_responsive_layout(self, w: int, h: int) -> None:
        """
        Dynamically adapts sidebar width, card heights, size grip placement, and margins
        based on the current window / screen resolution so nothing ever clips or overflows.
        """
        self.root_widget.setGeometry(0, 0, w, h)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.app_shell.setGeometry(0, 0, w, h)
        self.size_grip.move(max(0, w - 16), max(0, h - 16))

        sx = w / float(REF_WIDTH)
        sy = h / float(REF_HEIGHT)

        sb_w = max(200, min(250, int(round(230 * sx))))
        self.sidebar_panel.setFixedWidth(sb_w)

        card_h = max(76, min(94, int(round(86 * sy))))
        for card in self.action_cards.values():
            card.setFixedHeight(card_h)

        margin_x = max(10, min(20, int(round(16 * sx))))
        margin_y = max(8, min(16, int(round(12 * sy))))
        self.body_layout.setContentsMargins(margin_x, margin_y, margin_x + 2, margin_y + 2)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self.apply_responsive_layout(self.width(), self.height())

    def _detect_resize_edge(self, pos: QPoint) -> Optional[str]:
        if self.isMaximized():
            return None
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = RESIZE_GRIP_MARGIN
        left = x <= m
        right = x >= w - m
        top = y <= m
        bottom = y >= h - m
        if top and left:
            return "top_left"
        if top and right:
            return "top_right"
        if bottom and left:
            return "bottom_left"
        if bottom and right:
            return "bottom_right"
        if left:
            return "left"
        if right:
            return "right"
        if top:
            return "top"
        if bottom:
            return "bottom"
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if hasattr(event, "button") and event.button() == Qt.LeftButton and hasattr(event, "position"):
            edge = self._detect_resize_edge(event.position().toPoint())
            if edge:
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._resize_edge
            and self._resize_start_pos is not None
            and self._resize_start_geom is not None
            and hasattr(event, "globalPosition")
        ):
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            g = self._resize_start_geom
            x, y, w, h = g.x(), g.y(), g.width(), g.height()
            min_w, min_h = self.minimumWidth(), self.minimumHeight()

            if "right" in self._resize_edge:
                w = max(min_w, g.width() + delta.x())
            if "bottom" in self._resize_edge:
                h = max(min_h, g.height() + delta.y())
            if "left" in self._resize_edge:
                new_w = max(min_w, g.width() - delta.x())
                x = g.x() + (g.width() - new_w)
                w = new_w
            if "top" in self._resize_edge:
                new_h = max(min_h, g.height() - delta.y())
                y = g.y() + (g.height() - new_h)
                h = new_h

            self.setGeometry(x, y, w, h)
            return

        if hasattr(event, "position"):
            edge = self._detect_resize_edge(event.position().toPoint())
            cursor_map = {
                "left": Qt.SizeHorCursor,
                "right": Qt.SizeHorCursor,
                "top": Qt.SizeVerCursor,
                "bottom": Qt.SizeVerCursor,
                "top_left": Qt.SizeFDiagCursor,
                "bottom_right": Qt.SizeFDiagCursor,
                "top_right": Qt.SizeBDiagCursor,
                "bottom_left": Qt.SizeBDiagCursor,
            }
            if edge in cursor_map:
                self.setCursor(cursor_map[edge])
            else:
                self.unsetCursor()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geom = None

    def navigate_to(self, nav_id: str) -> None:
        self.current_nav_id = nav_id
        for k, btn in self.nav_buttons.items():
            btn.set_active(k == nav_id)

        main_idx_map = {
            "home": 0,
            "reports": 1,
            "settings": 2,
            "about": 3,
        }
        idx = main_idx_map.get(nav_id, 0)
        if idx == 1:
            self.reports_panel.refresh_history()
        elif idx == 3:
            self.about_panel.apply_theme(self.theme)

        self.main_page_stack.setCurrentIndex(idx)

    def _on_operation_completed(self, record: OperationRecord) -> None:
        self.reports_panel.refresh_history()

    def _on_settings_updated(self) -> None:
        default_id = self.settings_mgr.settings.default_method_id
        if not self.home_panel.queued_paths:
            self.home_panel.method_selector.set_method_by_id(
                default_id,
                is_auto=self.settings_mgr.settings.auto_select_best_method,
            )
