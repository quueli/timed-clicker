"""Win32 SendInput click - no background hooks."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Callable

INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]

    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


class ClickError(RuntimeError):
    """Raised when click cannot be performed."""


class Clicker:
    def __init__(self, test_mode: bool = False) -> None:
        self._test_mode = test_mode
        self._clicked = False
        self._mock_handler: Callable[[int, int], None] | None = None

    @property
    def clicked(self) -> bool:
        return self._clicked

    def set_mock_handler(self, handler: Callable[[int, int], None]) -> None:
        self._mock_handler = handler

    def reset_for_test(self) -> None:
        self._clicked = False

    def validate_coordinates(self, x: int, y: int) -> bool:
        return x >= 0 and y >= 0

    def click_once(self, x: int, y: int) -> None:
        if not self.validate_coordinates(x, y):
            raise ClickError(f"Coordinates ({x}, {y}) look invalid")

        if self._test_mode:
            self._clicked = True
            if self._mock_handler:
                self._mock_handler(x, y)
            return

        if sys.platform != "win32":
            raise ClickError("Click is only supported on Windows")

        user32 = ctypes.windll.user32
        if not user32.SetCursorPos(int(x), int(y)):
            raise ClickError(f"SetCursorPos failed for ({x}, {y})")

        extra = ctypes.c_ulong(0)
        inputs = (INPUT * 2)()
        for i, flag in enumerate((MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP)):
            inputs[i].type = INPUT_MOUSE
            inputs[i].mi = MOUSEINPUT(0, 0, 0, flag, 0, ctypes.pointer(extra))

        sent = user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
        if sent != 2:
            raise ClickError(f"SendInput returned {sent}, expected 2")

        self._clicked = True
