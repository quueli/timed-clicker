"""Countdown scheduler with precise final-phase worker thread."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

MAX_WAIT_SECONDS = 25 * 3600
FINAL_BUSY_WAIT_SECONDS = 0.5
THREAD_JOIN_TIMEOUT = 2.0


class Scheduler(QObject):
    tick = Signal(float)
    triggered = Signal()
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        click_fn: Callable[[], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._click_fn = click_fn
        self._target: datetime | None = None
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(1000)
        self._ui_timer.timeout.connect(self._on_ui_tick)

    @property
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def start(self, target: datetime) -> None:
        self.stop()
        self._target = target
        self._stop_event.clear()

        remaining = (target - datetime.now(target.tzinfo)).total_seconds()
        if remaining > MAX_WAIT_SECONDS:
            self.error.emit("Wait interval is too long")
            return
        if remaining < 0:
            self.error.emit("Target time has already passed")
            return

        self._ui_timer.start()
        self._on_ui_tick()

        self._worker = threading.Thread(
            target=self._worker_run,
            name="scheduler-worker",
            daemon=True,
        )
        self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._ui_timer.stop()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=THREAD_JOIN_TIMEOUT)
        self._worker = None

    def remaining_seconds(self) -> float:
        if self._target is None:
            return 0.0
        return max(0.0, (self._target - datetime.now(self._target.tzinfo)).total_seconds())

    def _on_ui_tick(self) -> None:
        if self._target is None:
            return
        self.tick.emit(self.remaining_seconds())

    def _worker_run(self) -> None:
        assert self._target is not None
        tz = self._target.tzinfo

        try:
            while not self._stop_event.is_set():
                remaining = (self._target - datetime.now(tz)).total_seconds()
                if remaining <= FINAL_BUSY_WAIT_SECONDS:
                    break
                if remaining > 1.0:
                    if self._stop_event.wait(timeout=min(remaining - FINAL_BUSY_WAIT_SECONDS, 1.0)):
                        return
                else:
                    if self._stop_event.wait(timeout=remaining - FINAL_BUSY_WAIT_SECONDS):
                        return

            deadline = time.perf_counter() + FINAL_BUSY_WAIT_SECONDS
            while not self._stop_event.is_set():
                if datetime.now(tz) >= self._target:
                    break
                if time.perf_counter() >= deadline:
                    break
                time.sleep(0.001)

            if self._stop_event.is_set():
                return

            while datetime.now(tz) < self._target and not self._stop_event.is_set():
                time.sleep(0.0005)

            if self._stop_event.is_set():
                return

            self.triggered.emit()
            self._click_fn()
            self.finished.emit()
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
