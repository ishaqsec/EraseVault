"""
Asset manager for EraseVault UI.
Loads both the original extracted UI asset crops (assets/ui_assets/...) and
the extracted transparent RGBA icons (assets/icons/...).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from .qt_compat import QIcon, QPixmap, QSize, Qt


class AssetManager:
    """Resolves and caches QPixmap and QIcon assets from the bundled assets/ directory."""

    def __init__(self, assets_root: Optional[str] = None) -> None:
        if assets_root is None:
            # Default: <repo_root>/assets
            assets_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "assets")
            )
        self.assets_root = assets_root
        self.icons_dir = os.path.join(self.assets_root, "icons")
        self.ui_assets_dir = os.path.join(self.assets_root, "ui_assets")

    def icon_path(self, filename: str) -> str:
        return os.path.join(self.icons_dir, filename)

    def ui_asset_path(self, rel_path: str) -> str:
        return os.path.join(self.ui_assets_dir, rel_path)

    @lru_cache(maxsize=128)
    def pixmap(
        self,
        rel_or_icon_name: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> QPixmap:
        # Check icons_dir first, then ui_assets_dir
        candidate = os.path.join(self.icons_dir, rel_or_icon_name)
        if not os.path.exists(candidate):
            candidate = os.path.join(self.ui_assets_dir, rel_or_icon_name)
        pix = QPixmap(candidate)
        if not pix.isNull() and width and height:
            return pix.scaled(
                QSize(width, height),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        return pix

    @lru_cache(maxsize=128)
    def icon(self, rel_or_icon_name: str) -> QIcon:
        pix = self.pixmap(rel_or_icon_name)
        return QIcon(pix)
