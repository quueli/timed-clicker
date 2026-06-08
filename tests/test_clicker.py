"""Tests for clicker module."""

import pytest
from PySide6.QtWidgets import QApplication

from app.clicker import Clicker, ClickError

_app = None


@pytest.fixture(scope="session", autouse=True)
def qapp():
    global _app
    if QApplication.instance() is None:
        _app = QApplication([])
    yield QApplication.instance()


def test_click_once_only_one_call(qapp):
    clicker = Clicker(test_mode=True)
    calls = []

    clicker.set_mock_handler(lambda x, y: calls.append((x, y)))
    clicker.click_once(100, 200)
    assert clicker.clicked
    assert calls == [(100, 200)]

    with pytest.raises(ClickError, match="already performed"):
        clicker.click_once(100, 200)


def test_validate_coordinates(qapp):
    clicker = Clicker(test_mode=True)
    screens = qapp.screens()
    if screens:
        geo = screens[0].geometry()
        cx = geo.center().x()
        cy = geo.center().y()
        assert clicker.validate_coordinates(cx, cy)
    assert not clicker.validate_coordinates(-99999, -99999)
