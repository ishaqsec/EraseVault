#!/usr/bin/env python3
"""
EraseVault — Secure Data Sanitization Desktop Application for Windows
Entry Point (Python + PySide6)
- Hides any attached Windows console window so no black terminal panel appears behind the GUI.
- Prevents automatic application exit when dialogs or operations complete (`setQuitOnLastWindowClosed(False)`).
- Enforces a clean light Fusion palette by default with runtime Light/Dark theme switching.
- Automatically adjusts window dimensions and scaling to fit the active screen resolution.
"""

from __future__ import annotations

import ctypes
import os
import sys

from erasevault import __app_name__, __version__
from erasevault.ui.main_window import EraseVaultMainWindow
from erasevault.ui.qt_compat import QApplication, QColor, QFont, QPalette, Qt


def _configure_windows_desktop_environment() -> None:
    """
    1. Sets explicit Windows AppUserModelID for taskbar icon grouping.
    2. Hides any attached console window (SW_HIDE = 0) on Windows so launching via
       python.exe or a shortcut never leaves a black command-prompt window open.
    """
    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "EraseVault.SecureDataSanitization.Desktop.1.0"
            )
        except Exception:
            pass
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                SW_HIDE = 0
                ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
        except Exception:
            pass


def _apply_light_palette(app: QApplication) -> None:
    """Forces a crisp light color palette so OS dark themes never create black control panels."""
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(243, 247, 253))
    pal.setColor(QPalette.WindowText, QColor(6, 25, 55))
    pal.setColor(QPalette.Base, QColor(255, 255, 255))
    pal.setColor(QPalette.AlternateBase, QColor(248, 250, 252))
    pal.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    pal.setColor(QPalette.ToolTipText, QColor(15, 23, 42))
    pal.setColor(QPalette.Text, QColor(15, 23, 42))
    pal.setColor(QPalette.Button, QColor(251, 252, 254))
    pal.setColor(QPalette.ButtonText, QColor(15, 23, 42))
    pal.setColor(QPalette.BrightText, QColor(255, 255, 255))
    pal.setColor(QPalette.Highlight, QColor(38, 126, 253))
    pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(pal)


def main() -> int:
    _configure_windows_desktop_environment()

    # Enable smooth high-DPI fractional scaling when running under native PySide6
    if hasattr(QApplication, "setHighDpiScaleFactorRoundingPolicy") and hasattr(
        Qt, "HighDpiScaleFactorRoundingPolicy"
    ):
        try:
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("EraseVault Security")
    # Ensure closing a modal dialog or finishing an operation never auto-quits the application
    if hasattr(app, "setQuitOnLastWindowClosed"):
        app.setQuitOnLastWindowClosed(False)
    _apply_light_palette(app)

    default_font = QFont("Segoe UI" if os.name == "nt" else "Inter", 10)
    app.setFont(default_font)

    window = EraseVaultMainWindow()
    if hasattr(app, "quit"):
        window.top_bar.close_clicked.connect(app.quit)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
