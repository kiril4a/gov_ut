from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QRegion, QPainterPath
from PyQt6.QtWidgets import QWidget, QFrame, QVBoxLayout, QLabel, QProgressBar


class RoundedFrame(QFrame):
    """Frame that enforces rounded corners clipping on children."""
    def resizeEvent(self, event):
        path = QPainterPath()
        # Create a rounded rect path for the mask
        path.addRoundedRect(0, 0, self.width(), self.height(), 6, 6)
        
        # Create a region from the path
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)
        super().resizeEvent(event)

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
            "QFrame#panel { background-color: #3a3a3a; border-radius: 14px; }"
        )

        v = QVBoxLayout(panel)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(10)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel(text, panel)
        self.label.setStyleSheet("color: white; font-size: 16px; font-weight: bold; background: transparent;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Container for visual styling (the 'gray track')
        bar_container = QFrame(panel)
        bar_container.setObjectName('bar_container')
        bar_container.setFixedHeight(12)
        bar_container.setFixedWidth(260)  # constrain width
        bar_container.setStyleSheet(
            "QFrame#bar_container { background-color: #252525; border-radius: 6px; }"
        )

        # Create a mask to enforce rounded corners on children (the moving chunk)
        mask_path = QPainterPath()
        mask_path.addRoundedRect(0, 0, 260, 12, 6, 6)
        region = QRegion(mask_path.toFillPolygon().toPolygon())
        bar_container.setMask(region)

        # ProgressBar inside
        self.bar = QProgressBar(bar_container)
        self.bar.setRange(0, 0)  # indeterminate
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(12)
        self.bar.setStyleSheet("""
            QProgressBar {
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background-color: #b0b0b0;
                border-radius: 6px;
            }
        """)

        # Layout for bar container
        bc_layout = QVBoxLayout(bar_container)
        bc_layout.setContentsMargins(0, 0, 0, 0)
        bc_layout.addWidget(self.bar)

        v.addWidget(self.label)
        v.addWidget(bar_container)

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
