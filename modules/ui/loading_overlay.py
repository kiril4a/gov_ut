from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QFrame, QVBoxLayout, QLabel, QProgressBar


class LoadingOverlay(QWidget):
    """A simple modal-like overlay with a centered rounded panel and an indeterminate spinner."""

    def __init__(self, parent: QWidget, text: str = "Загрузка..."):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setVisible(False)

        # semi-transparent full-screen overlay
        self.setStyleSheet("background-color: rgba(0, 0, 0, 120);")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        panel = QFrame(self)
        panel.setObjectName('panel')
        panel.setFixedWidth(320)
        panel.setStyleSheet(
            "QFrame#panel { background-color: #2b2b2b; border: 1px solid #444; border-radius: 14px; }"
        )

        v = QVBoxLayout(panel)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(12)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel(text, panel)
        self.label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Indeterminate progress bar (acts like spinner/loader)
        self.bar = QProgressBar(panel)
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(10)
        self.bar.setStyleSheet(
            "QProgressBar { background-color: #3a3a3a; border: none; border-radius: 5px; }"
            "QProgressBar::chunk { background-color: #b0b0b0; border-radius: 5px; }"
        )

        v.addWidget(self.label)
        v.addWidget(self.bar)

        layout.addWidget(panel)

    def setText(self, text: str) -> None:
        self.label.setText(text)

    def showOverlay(self, text: str | None = None) -> None:
        if text:
            self.setText(text)
        self._sync_geometry()
        self.setVisible(True)
        self.raise_()

    def hideOverlay(self) -> None:
        self.setVisible(False)

    def _sync_geometry(self) -> None:
        p = self.parentWidget()
        if p is not None:
            self.setGeometry(p.rect())

    def resizeEvent(self, event):
        self._sync_geometry()
        return super().resizeEvent(event)
