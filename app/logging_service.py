"""Dual logging: UI signal + file with flush on every write."""

from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal


def _default_log_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "TimedClicker"
    base.mkdir(parents=True, exist_ok=True)
    return base / "timed_clicker.log"


class LoggingService(QObject):
    log_line = Signal(str)

    def __init__(self, log_path: Path | None = None) -> None:
        super().__init__()
        self._log_path = log_path or _default_log_path()
        self._file = open(self._log_path, "a", encoding="utf-8", buffering=1)
        self._closed = False

    @property
    def log_path(self) -> Path:
        return self._log_path

    def _write(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] {message}"
        self.log_line.emit(line)
        if not self._closed:
            self._file.write(line + "\n")
            self._file.flush()

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def exception(self, message: str) -> None:
        tb = traceback.format_exc()
        self._write("ERROR", f"{message}\n{tb}")

    def shutdown(self) -> None:
        if self._closed:
            return
        self.info("Log flushed to disk before shutdown")
        self._file.flush()
        self._file.close()
        self._closed = True
