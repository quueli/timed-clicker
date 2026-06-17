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

from app.clicker import Clicker, ClickError
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

EXIT_DELAY_MS = 1500


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
        self._shutting_down = False
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

    def _append_log(self, line: str) -> None:
        self._log_view.appendPlainText(line)

    def _set_status(self, status: str) -> None:
        self._status_label.setText(status)

    def _update_clock(self) -> None:
        self._clock_label.setText(f"Now: {format_datetime_tz(now_in_tz(self._tz), self._tz)}")

    def _update_start_button(self) -> None:
        if self._scheduler.is_running or self._shutting_down:
            return
        has_point = self._point is not None
        has_time = bool(self._time_edit.text().strip())
        self._start_btn.setEnabled(has_point and has_time)

    def _set_inputs_enabled(self, enabled: bool) -> None:
        self._pick_btn.setEnabled(enabled)
        self._time_edit.setEnabled(enabled)
        self._start_btn.setEnabled(enabled and self._point is not None and bool(self._time_edit.text().strip()))

    def _on_pick_point(self) -> None:
        if self._overlay is not None:
            return
        self._logger.info("Point picker opened")
        self.hide()
        self._overlay = PointPickerOverlay()
        self._overlay.point_selected.connect(self._on_point_selected)
        self._overlay.cancelled.connect(self._on_point_cancelled)
        self._overlay.destroyed.connect(self._on_overlay_destroyed)
        self._overlay.show_on_all_screens()

    def _on_overlay_destroyed(self) -> None:
        self._overlay = None

    def _on_point_selected(self, x: int, y: int) -> None:
        self._point = (x, y)
        self._coord_label.setText(f"X: {x}   Y: {y}")
        self._logger.info(f"Point selected: X={x}, Y={y}")
        self.show()
        self.raise_()
        self.activateWindow()
        self._set_status(STATUS_WAITING)
        self._update_start_button()

    def _on_point_cancelled(self) -> None:
        self._logger.info("Point picking cancelled")
        self.show()
        self.raise_()
        self.activateWindow()
        self._set_status(STATUS_WAITING)
        self._update_start_button()

    def _on_start(self) -> None:
        if self._point is None:
            self._show_error("Pick a point on the screen first")
            return

        try:
            trigger_time = parse_time_hms(self._time_edit.text())
        except TimeParseError as exc:
            self._show_error(str(exc))
            return

        self._logger.info(f"Time entered: {self._time_edit.text().strip()}")

        if self._test_mode and self._auto_start_seconds is not None:
            target = datetime.now(self._tz) + timedelta(seconds=self._auto_start_seconds)
        else:
            target = resolve_target_datetime(trigger_time, self._tz)

        self._target_str = format_datetime_tz(target, self._tz)
        self._logger.info(f"Target moment: {self._target_str}")
        self._last_countdown_logged = -1

        self._set_inputs_enabled(False)
        self._set_status(STATUS_READY)
        self._scheduler.start(target)

    def _on_tick(self, remaining: float) -> None:
        self._countdown_label.setText(f"Countdown: {format_timedelta(remaining)}")
        whole = int(remaining)
        if whole != self._last_countdown_logged and whole % 10 == 0:
            self._logger.info(f"Countdown: {format_timedelta(remaining)}")
            self._last_countdown_logged = whole

    def _perform_click(self) -> None:
        if self._point is None:
            raise ClickError("No point selected")
        x, y = self._point
        self._logger.info(f"Performing click at ({x}, {y})")
        self._clicker.click_once(x, y)

    def _on_triggered(self) -> None:
        self._logger.info("Trigger moment reached")

    def _on_finished(self) -> None:
        self._set_status(STATUS_DONE)
        self._countdown_label.setText("Countdown: 00:00:00")
        self._logger.info("Click performed successfully")
        self._logger.info("Shutting down successfully")
        self._begin_shutdown()

    def _on_scheduler_error(self, message: str) -> None:
        self._show_error(message)

    def _show_error(self, message: str) -> None:
        self._logger.error(message)
        self._set_status(STATUS_ERROR)
        self._scheduler.stop()
        self._set_inputs_enabled(True)
        self._update_start_button()

    def _begin_shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        self._scheduler.stop()
        self._destroy_overlay()
        self._set_inputs_enabled(False)
        QTimer.singleShot(EXIT_DELAY_MS, self._finalize_exit)

    def _finalize_exit(self) -> None:
        self._scheduler.stop()
        self._destroy_overlay()
        self._logger.shutdown()
        self.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()
        sys.exit(0)

    def _destroy_overlay(self) -> None:
        if self._overlay is not None:
            self._overlay.destroy_overlay()
            self._overlay = None

    def _auto_start_test_flow(self) -> None:
        self._point = (100, 200)
        self._coord_label.setText("X: 100   Y: 200")
        self._logger.info("Test: point set to X=100, Y=200")
        self._time_edit.setText("23:59:59")
        self._on_start()

    def closeEvent(self, event) -> None:  # noqa: N802
        if not self._shutting_down:
            self._scheduler.stop()
            self._destroy_overlay()
            self._logger.shutdown()
        event.accept()
