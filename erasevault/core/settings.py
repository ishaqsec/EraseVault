"""
Persistent application settings manager for EraseVault.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class AppSettings:
    default_method_id: str = "quick_erase"
    auto_select_best_method: bool = True
    confirm_before_erasure: bool = False
    verify_after_erasure: bool = True
    obfuscate_filenames: bool = True
    pad_cluster_slack: bool = True
    warn_on_ssd_multipass: bool = True
    free_space_reserve_mb: int = 128
    use_windows_cipher_when_available: bool = False
    auto_save_reports: bool = False
    reports_directory: str = ""
    theme_mode: str = "light"  # 'light' or 'dark'


class SettingsManager:
    """Loads and saves user preferences in JSON format."""

    def __init__(self, settings_path: Optional[str] = None) -> None:
        if settings_path is None:
            if os.name == "nt":
                base = os.path.join(
                    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                    "EraseVault",
                )
            else:
                base = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..", "data")
                )
            try:
                os.makedirs(base, exist_ok=True)
            except OSError:
                base = os.path.join(tempfile.gettempdir(), "EraseVault")
                os.makedirs(base, exist_ok=True)
            settings_path = os.path.join(base, "settings.json")
        self.settings_path = os.path.abspath(settings_path)
        self.settings = self.load()
        if not self.settings.reports_directory:
            self.settings.reports_directory = os.path.join(
                os.path.dirname(self.settings_path), "reports"
            )
            os.makedirs(self.settings.reports_directory, exist_ok=True)

    def load(self) -> AppSettings:
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                default_fields = asdict(AppSettings())
                filtered = {k: data[k] for k in default_fields if k in data}
                return AppSettings(**filtered)
            except Exception:
                pass
        return AppSettings()

    def save(self, settings: Optional[AppSettings] = None) -> None:
        if settings is not None:
            self.settings = settings
        os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self.settings), f, indent=2)
