"""
Persistent operation history storage for EraseVault backed by SQLite3 with automatic
fallback for network/virtualized filesystems where POSIX/Win32 byte-range locking is restricted.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from typing import List, Optional

from .models import OperationRecord


class HistoryManager:
    """Stores and retrieves sanitization operation records in SQLite3 (with JSON mirror fallback)."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            base_dir = self._default_data_dir()
            os.makedirs(base_dir, exist_ok=True)
            db_path = os.path.join(base_dir, "erasevault_history.db")
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._json_fallback_path = self.db_path + ".json"
        self._use_json_fallback = False
        self._init_db()

    @staticmethod
    def _default_data_dir() -> str:
        if os.name == "nt":
            appdata = os.environ.get("LOCALAPPDATA")
            if appdata and os.access(appdata, os.W_OK):
                return os.path.join(appdata, "EraseVault")
        # Prefer local app data directory or system temp dir
        app_local = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
        try:
            os.makedirs(app_local, exist_ok=True)
            return app_local
        except OSError:
            return os.path.join(tempfile.gettempdir(), "EraseVault")

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=MEMORY;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS operations (
                        op_id TEXT PRIMARY KEY,
                        timestamp_start TEXT NOT NULL,
                        timestamp_end TEXT NOT NULL,
                        operation_type TEXT NOT NULL,
                        method_id TEXT NOT NULL,
                        method_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        total_bytes INTEGER NOT NULL,
                        files_erased INTEGER NOT NULL,
                        record_json TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
        except sqlite3.OperationalError:
            # Fallback to temp directory SQLite or JSON store if filesystem blocks SQLite locks
            alt_dir = os.path.join(tempfile.gettempdir(), "EraseVault")
            os.makedirs(alt_dir, exist_ok=True)
            alt_db = os.path.join(alt_dir, os.path.basename(self.db_path))
            try:
                self.db_path = alt_db
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("PRAGMA journal_mode=MEMORY;")
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS operations (
                            op_id TEXT PRIMARY KEY,
                            timestamp_start TEXT NOT NULL,
                            timestamp_end TEXT NOT NULL,
                            operation_type TEXT NOT NULL,
                            method_id TEXT NOT NULL,
                            method_name TEXT NOT NULL,
                            status TEXT NOT NULL,
                            total_bytes INTEGER NOT NULL,
                            files_erased INTEGER NOT NULL,
                            record_json TEXT NOT NULL
                        )
                        """
                    )
                    conn.commit()
            except Exception:
                self._use_json_fallback = True
                if not os.path.exists(self._json_fallback_path):
                    with open(self._json_fallback_path, "w", encoding="utf-8") as f:
                        json.dump([], f)

    def record_operation(self, record: OperationRecord) -> None:
        if self._use_json_fallback:
            items = [r.to_dict() for r in self.list_operations()]
            items = [it for it in items if it.get("op_id") != record.op_id]
            items.insert(0, record.to_dict())
            with open(self._json_fallback_path, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
            return

        payload = json.dumps(record.to_dict(), ensure_ascii=False)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            conn.execute(
                """
                INSERT OR REPLACE INTO operations (
                    op_id, timestamp_start, timestamp_end, operation_type,
                    method_id, method_name, status, total_bytes, files_erased, record_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.op_id,
                    record.timestamp_start,
                    record.timestamp_end,
                    record.operation_type,
                    record.method_id,
                    record.method_name,
                    record.status,
                    record.total_bytes_processed,
                    record.files_erased,
                    payload,
                ),
            )
            conn.commit()

    def list_operations(self, limit: int = 200) -> List[OperationRecord]:
        if self._use_json_fallback:
            try:
                with open(self._json_fallback_path, "r", encoding="utf-8") as f:
                    raw_list = json.load(f)
                return [OperationRecord.from_dict(d) for d in raw_list[:limit]]
            except Exception:
                return []

        records: List[OperationRecord] = []
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT record_json FROM operations ORDER BY timestamp_start DESC LIMIT ?",
                (limit,),
            )
            for (raw_json,) in cur.fetchall():
                try:
                    data = json.loads(raw_json)
                    records.append(OperationRecord.from_dict(data))
                except Exception:
                    pass
        return records

    def get_operation(self, op_id: str) -> Optional[OperationRecord]:
        if self._use_json_fallback:
            for r in self.list_operations():
                if r.op_id == op_id:
                    return r
            return None

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT record_json FROM operations WHERE op_id = ?", (op_id,)
            )
            row = cur.fetchone()
            if row:
                return OperationRecord.from_dict(json.loads(row[0]))
        return None

    def delete_operation(self, op_id: str) -> bool:
        if self._use_json_fallback:
            items = [r.to_dict() for r in self.list_operations() if r.op_id != op_id]
            with open(self._json_fallback_path, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2)
            return True

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            cur = conn.execute("DELETE FROM operations WHERE op_id = ?", (op_id,))
            conn.commit()
            return cur.rowcount > 0

    def clear_history(self) -> None:
        if self._use_json_fallback:
            with open(self._json_fallback_path, "w", encoding="utf-8") as f:
                json.dump([], f)
            return

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            conn.execute("DELETE FROM operations")
            conn.commit()
