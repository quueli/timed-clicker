"""Temporary fullscreen overlay for screen point selection."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PointPickerOverlay(QWidget):
    point_selected = Signal(int, int)
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._hint = QLabel(
            "Click anywhere on the screen to set the point\nEsc - cancel",
            self,
        )
        self._hint.setStyleSheet(
            "color: white; background: rgba(0,0,0,160); padding: 12px; "
            "font-size: 14px; border-radius: 6px;"
        )
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addWidget(self._hint, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(20, 20, 20, 20)

    def show_on_all_screens(self) -> None:
        virtual = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(virtual)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1, Qt.PenStyle.DashLine))
        pos = self.mapFromGlobal(QCursor.pos())
        painter.drawLine(pos.x(), 0, pos.x(), self.height())
        painter.drawLine(0, pos.y(), self.width(), pos.y())

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self._finish(cancel=True)
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            global_pos = event.globalPosition().toPoint()
            self._finish(cancel=False, x=global_pos.x(), y=global_pos.y())
            return
        super().mousePressEvent(event)

    def _finish(self, cancel: bool, x: int = 0, y: int = 0) -> None:
        self.hide()
        if cancel:
            self.cancelled.emit()
        else:
            self.point_selected.emit(x, y)
        self.close()
        self.deleteLater()

    def destroy_overlay(self) -> None:
        self._finish(cancel=True)
