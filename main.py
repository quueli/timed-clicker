"""Timed Clicker, entry point."""

from __future__ import annotations

import ctypes
import sys


def _enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> int:
    _enable_dpi_awareness()

    from PySide6.QtWidgets import QApplication

    from app.main_window import MainWindow
    from app.time_logic import get_timezone

    test_mode = "--test-mode" in sys.argv
    auto_seconds = None
    tz_name = None
    for arg in sys.argv:
        if arg.startswith("--auto-start="):
            auto_seconds = int(arg.split("=", 1)[1])
        elif arg.startswith("--tz="):
            tz_name = arg.split("=", 1)[1]

    app = QApplication(sys.argv)
    app.setApplicationName("TimedClicker")

    window = MainWindow(
        timezone=get_timezone(tz_name),
        test_mode=test_mode,
        auto_start_seconds=auto_seconds,
    )
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
