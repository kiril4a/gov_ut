from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QListWidget, QListWidgetItem, QApplication)
from PyQt6.QtCore import Qt, QEvent, QPoint

class ItemPickerPopup(QFrame):
    """Lightweight suggestion popup implemented with QListWidget.
    Styled dark, rounded, larger and closes when focus/window deactivates.
    """
    def __init__(self, items, parent=None, on_select=None):
        # Create as top-level popup (no parent) so it floats above main window reliably
        super().__init__(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._owner = parent
        self.on_select = on_select
        self._items = list(items)

        # Dark, rounded, larger styling
        self.setStyleSheet('''
            QFrame { background-color: #232323; border: 1px solid #3a3a3a; border-radius: 12px; }
            QListWidget { background: transparent; border: none; padding: 10px; }
            QListWidget::item { color: #f2f2f2; padding: 8px 12px; font-size: 14px; border-radius: 8px; }
            QListWidget::item:hover { background-color: #3a3a3a; color: #ffffff; }
            QListWidget::item:selected { background-color: #3a3a3a; }
        ''')

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(0)

        self.list = QListWidget(self)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setSelectionMode(self.list.SingleSelection)
        self.list.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.list.itemClicked.connect(self._on_item_clicked)
        self.layout.addWidget(self.list)

        self.rebuild(items)

    def focusOutEvent(self, event):
        # close when popup loses focus (e.g., user switches to browser)
        try:
            self.close()
        except Exception:
            pass
        return super().focusOutEvent(event)

    def event(self, e):
        # Close on window deactivation (alt-tab, switch app)
        try:
            if e.type() == QEvent.Type.WindowDeactivate:
                try:
                    self.close()
                except Exception:
                    pass
        except Exception:
            pass
        return super().event(e)

    def rebuild(self, items):
        self._items = list(items)
        self.list.clear()
        for it in self._items:
            li = QListWidgetItem(it)
            self.list.addItem(li)
        # increase width for larger appearance
        self.setFixedWidth(380)
        self._clamp_height()

    def _clamp_height(self):
        count = self.list.count()
        max_visible = 9
        item_h = 28
        h = min(count, max_visible) * item_h + 20
        self.setFixedHeight(h)

    def filter(self, text):
        txt = (text or '').lower().strip()
        self.list.clear()
        for it in self._items:
            if not txt or txt in it.lower():
                self.list.addItem(QListWidgetItem(it))
        self._clamp_height()

    def show_at_widget(self, widget):
        # Compute global position from widget and clamp to screen so popup is visible
        try:
            local_point = widget.rect().bottomLeft()
            # larger vertical offset for clear separation
            p = widget.mapToGlobal(local_point + QPoint(0, 10))
            try:
                screen = QApplication.primaryScreen()
                avail = screen.availableGeometry()
                x = p.x()
                y = p.y()
                if x + self.width() > avail.x() + avail.width():
                    x = max(avail.x(), avail.x() + avail.width() - self.width() - 8)
                if y + self.height() > avail.y() + avail.height():
                    y_alt = widget.mapToGlobal(widget.rect().topLeft()).y() - self.height() - 10
                    if y_alt > avail.y():
                        y = y_alt
                    else:
                        y = max(avail.y(), avail.y() + avail.height() - self.height() - 8)
                self.move(QPoint(x, y))
            except Exception:
                self.move(p)
        except Exception:
            if getattr(self, '_owner', None):
                try:
                    p = self._owner.mapToGlobal(widget.rect().bottomLeft() + QPoint(0, 10))
                    self.move(p)
                except Exception:
                    pass
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.show()
        try:
            if self.list.count() > 0:
                self.list.setCurrentRow(0)
            self.list.setFocus()
        except Exception:
            pass

    def _on_item_clicked(self, item):
        if callable(self.on_select):
            self.on_select(item.text())
        self.close()

    def closeEvent(self, event):
        # ensure no dangling reference
        try:
            if getattr(self, '_owner', None):
                pass
        except Exception:
            pass
        return super().closeEvent(event)
