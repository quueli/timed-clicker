"""Main application window."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.clicker import ClickError, Clicker
from app.logging_service import LoggingService
from app.point_picker import PointPickerOverlay
from app.scheduler import Scheduler
from app.time_logic import (
    TimeParseError,
    format_datetime_tz,
    format_timedelta,
    now_in_tz,
    parse_time_hms,
    resolve_target_datetime,
)

STATUS_WAITING = "Waiting"
STATUS_READY = "Ready"
STATUS_DONE = "Done"
STATUS_ERROR = "Error"


class MainWindow(QMainWindow):
    def __init__(
        self,
        timezone: ZoneInfo,
        test_mode: bool = False,
        auto_start_seconds: int | None = None,
    ) -> None:
        super().__init__()
        self._tz = timezone
        self._tz_label = getattr(timezone, "key", str(timezone))
        self._test_mode = test_mode
        self._auto_start_seconds = auto_start_seconds
        self._point: tuple[int, int] | None = None
        self._target_str: str | None = None
        self._overlay: PointPickerOverlay | None = None
        self._last_countdown_logged = -1

        self._logger = LoggingService()
        self._clicker = Clicker(test_mode=test_mode)
        self._scheduler = Scheduler(click_fn=self._perform_click, parent=self)

        self.setWindowTitle("Timed Clicker")
        self.setFixedSize(400, 480)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        self._status_label = QLabel(STATUS_WAITING)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        status_layout.addWidget(self._status_label)
        root.addWidget(status_group)

        point_group = QGroupBox("Click point")
        point_layout = QGridLayout(point_group)
        self._pick_btn = QPushButton("Pick point")
        self._pick_btn.clicked.connect(self._on_pick_point)
        self._coord_label = QLabel("X: -   Y: -")
        point_layout.addWidget(self._pick_btn, 0, 0, 1, 2)
        point_layout.addWidget(self._coord_label, 1, 0, 1, 2)
        root.addWidget(point_group)

        time_group = QGroupBox(f"Trigger time ({self._tz_label})")
        time_layout = QGridLayout(time_group)
        self._time_edit = QLineEdit()
        self._time_edit.setPlaceholderText("14:30:00")
        self._time_edit.textChanged.connect(self._update_start_button)
        time_layout.addWidget(QLabel("HH:MM:SS"), 0, 0)
        time_layout.addWidget(self._time_edit, 0, 1)
        self._clock_label = QLabel("Now: -")
        self._countdown_label = QLabel("Countdown: -")
        time_layout.addWidget(self._clock_label, 1, 0, 1, 2)
        time_layout.addWidget(self._countdown_label, 2, 0, 1, 2)
        root.addWidget(time_group)

        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("Start")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(self._start_btn)
        root.addLayout(btn_row)

        log_group = QGroupBox("Event log")
        log_layout = QVBoxLayout(log_group)
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(500)
        log_layout.addWidget(self._log_view)
        root.addWidget(log_group, stretch=1)

        self._logger.log_line.connect(self._append_log)
        self._scheduler.tick.connect(self._on_tick)
        self._scheduler.triggered.connect(self._on_triggered)
        self._scheduler.error.connect(self._on_scheduler_error)
        self._scheduler.finished.connect(self._on_finished)

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()
        self._update_clock()

        self._logger.info("Application started")
        if self._test_mode:
            self._logger.info("Test mode (--test-mode): click is emulated")

        if self._auto_start_seconds is not None:
            QTimer.singleShot(100, self._auto_start_test_flow)
