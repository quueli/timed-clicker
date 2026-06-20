"""Smoke tests with offscreen Qt platform."""

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.clicker import Clicker
from app.main_window import MainWindow
from app.scheduler import Scheduler
from app.time_logic import get_timezone, now_in_tz

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UTC = get_timezone("UTC")


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_scheduler_fires_once(qapp, qtbot):
    fired = []

    def on_click():
        fired.append(True)

    scheduler = Scheduler(click_fn=on_click)
    target = now_in_tz(UTC).replace(microsecond=0)
    from datetime import timedelta

    target = target + timedelta(seconds=1)

    with qtbot.waitSignal(scheduler.finished, timeout=5000):
        scheduler.start(target)
    assert len(fired) == 1
    scheduler.stop()


def test_main_window_test_mode_auto_exit(qapp, qtbot, tmp_path, monkeypatch):
    from app import logging_service

    log_path = tmp_path / "test.log"
    monkeypatch.setattr(logging_service, "_default_log_path", lambda: log_path)
    monkeypatch.setattr(sys, "exit", lambda code=0: None)

    window = MainWindow(timezone=UTC, test_mode=True, auto_start_seconds=1)
    window.show()

    with qtbot.waitSignal(window._scheduler.finished, timeout=10000):
        pass

    qtbot.wait(2000)
    assert window._clicker.clicked
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "Application started" in content
    assert "Click performed successfully" in content
