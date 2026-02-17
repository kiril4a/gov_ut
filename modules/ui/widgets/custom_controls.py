from PyQt6.QtWidgets import (QCalendarWidget, QToolButton, QSpinBox, 
                             QAbstractSpinBox, QMenu, QWidget, QDateEdit, 
                             QDoubleSpinBox, QComboBox, QFrame, QListWidget, 
                             QVBoxLayout, QListWidgetItem, QApplication, QAbstractItemView, QHeaderView)
from PyQt6.QtCore import Qt, QLocale, QRect, QPoint, QDate, QEvent, QPointF, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QMouseEvent, QKeyEvent

class CustomCalendarWidget(QCalendarWidget):
    date_selected = pyqtSignal(object)  # Signal containing QDate

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLocale(QLocale(QLocale.Language.Russian))
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setNavigationBarVisible(True)
        self.clicked.connect(self.date_selected.emit)
        self.activated.connect(self.date_selected.emit)
        
        # Add blue buttons with white arrows for prev/next month
        self.findChild(QToolButton, "qt_calendar_prevmonth").setText("◄")
        self.findChild(QToolButton, "qt_calendar_prevmonth").setIcon(QIcon())  # Remove icon
        self.findChild(QToolButton, "qt_calendar_nextmonth").setText("►")
        self.findChild(QToolButton, "qt_calendar_nextmonth").setIcon(QIcon())  # Remove icon

        self.setStyleSheet("""
            QCalendarWidget QWidget { 
                alternate-background-color: #2b2b2b; 
                background-color: #2b2b2b; 
                color: white;
            }
            /* Remove highlight on hover for week days */
            QCalendarWidget QHeaderView {
                background-color: transparent;
            }
            QCalendarWidget QHeaderView::section {
                background-color: transparent;
                color: #b0b0b0;
                padding: 4px;
                border: none;
                font-weight: bold;
            }
            QCalendarWidget QHeaderView::section:hover {
                background-color: transparent; 
                color: #b0b0b0; /* Keep color same */
            }
            QCalendarWidget QHeaderView::section:checked {
                background-color: transparent;
            }
            
            QCalendarWidget QToolButton {
                color: white;
                background-color: transparent;
                border-radius: 4px;
                icon-size: 16px;
                border: none;
                margin: 2px;
                font-weight: bold;
                font-size: 14px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #3a3a3a;
            }
            
            /* Remove triangle near month */
            QCalendarWidget QToolButton::menu-indicator {
                image: none;
                width: 0px;
            }
            
            /* Increase gap between month and year */
            QCalendarWidget QToolButton#qt_calendar_monthbutton {
                margin-right: 10px;
                padding-right: 10px;
                background-color: #2a82da; /* Blue background */
                color: white;              /* White Text */
                border-radius: 4px;        /* Consistent border radius */
                padding: 4px 8px;         /* Padding for pill/button shape */
                height: 25px;              /* Consistent height */
            }
            /* Year SpinBox Styling - Force Background */
            QCalendarWidget QSpinBox {
                margin-left: 10px;
                background-color: #2a82da; 
                background: #2a82da;
                color: white;              
                selection-background-color: #4aa3df;
                selection-color: white; 
                border: none;
                font-weight: bold;
                font-size: 14px;
                border-radius: 4px;        
                padding: 4px 8px;          
                height: 25px;       
                min-width: 60px;       
            }
            QCalendarWidget QSpinBox QAbstractItemView {
                background-color: #2b2b2b;
                color: white;
                selection-background-color: #4aa3df;
            }
            QCalendarWidget QSpinBox::up-button, QCalendarWidget QSpinBox::down-button {
                width: 0px; 
            }

            /* Remove highlight on hover for week days - Aggressive */
            QCalendarWidget QTableView {
                alternate-background-color: #2b2b2b;
            }
            QCalendarWidget QWidget#qt_calendar_week_day_names {
                background-color: transparent;
            } 
            /* If standard header view approach failed, try excluding hover state specifically on the view's header */
            QCalendarWidget QHeaderView::section {
                background-color: transparent;
                color: #b0b0b0;
                padding: 4px;
                border: none;
                font-weight: bold;
            }
            QCalendarWidget QHeaderView::section:hover {
                background-color: transparent;
                color: #b0b0b0; /* Keep color same */
            }
            QCalendarWidget QHeaderView::section:checked {
                 background-color: transparent;
            }

            /* Style Prev/Next buttons (Blue with White text) */
            QCalendarWidget QToolButton#qt_calendar_prevmonth, 
            QCalendarWidget QToolButton#qt_calendar_nextmonth {
                background-color: #2a82da;
                color: white;
                border-radius: 4px;
                width: 30px;
                height: 25px;
                qproperty-icon: none; /* Ensure no default icon interferes */
            }
            QCalendarWidget QToolButton#qt_calendar_prevmonth:hover, 
            QCalendarWidget QToolButton#qt_calendar_nextmonth:hover {
                background-color: #3a92ea;
            }

            /* Month dropdown hover highlight & style */
            QMenu {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #4aa3df;
                color: white;
            }

            QCalendarWidget QAbstractItemView:enabled {
                color: white;
                background-color: #2b2b2b;
                selection-background-color: transparent; 
                selection-color: white;
                border: none;
                outline: none;
            }
            QCalendarWidget QAbstractItemView::item:hover {
                background-color: #3d3d3d; 
                border-radius: 6px;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #555555;
            }
        """)

    def paintCell(self, painter, rect, date):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if date == self.selectedDate():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#4aa3df"))
            r = QRect(rect.left() + 2, rect.top() + 2, rect.width() - 4, rect.height() - 4)
            painter.drawRoundedRect(r, 6, 6)
            painter.setPen(Qt.GlobalColor.white)
        elif date == QDate.currentDate():
            painter.setPen(QColor("#4aa3df")) 
        else:
            if date.month() != self.monthShown():
                painter.setPen(QColor("#555555"))  # Dark grey for other months
            else:
                painter.setPen(Qt.GlobalColor.white)

        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(date.day()))
        painter.restore()

class DateEditClickable(QDateEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("dd.MM.yyyy")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.lineEdit().setReadOnly(True)
        self.setCalendarWidget(CustomCalendarWidget(self))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lineEdit().installEventFilter(self)

    def eventFilter(self, source, event):
        if source == self.lineEdit() and event.type() == QEvent.Type.MouseButtonPress:
            self.setFocus()
            key_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
            QApplication.postEvent(self, key_event)
            return True
        elif event.type() == QEvent.Type.MouseButtonPress:
            self.setFocus()
            key_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
            QApplication.postEvent(self, key_event)
            return True
        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab):
            super().keyPressEvent(event)
        elif event.text():
             event.ignore()
        else:
             super().keyPressEvent(event)

# Custom widgets that ignore mouse wheel events
class NoScrollSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()

class NoScrollDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event):
        event.ignore()

class NoScrollComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()

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

class SuggestionsPopup(QListWidget):
    """
    Custom popup for suggestions.
    - Shows suggestions below the input.
    - Matches generic dark theme style.
    """
    suggestion_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        # Style matches dark theme requirements
        self.setStyleSheet("""
            QListWidget { 
                background: #232323; 
                color: #f2f2f2; 
                border: 1px solid #3a3a3a; 
                border-radius: 6px; 
                padding: 4px; 
            }
            QListWidget::item { 
                padding: 8px 12px; 
                border-radius: 4px; 
                color: #f2f2f2;
                margin-bottom: 2px;
            }
            QListWidget::item:hover { 
                background: #3a3a3a; 
            }
            QListWidget::item:selected { 
                background: #4aa3df; 
                color: white; 
            }
        """)
        self.itemClicked.connect(self._on_item_clicked)
        # Hide horizontal scrollbar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def show_suggestions(self, suggestions, target_widget):
        self.clear()
        if not suggestions:
            self.hide()
            return

        for s in suggestions:
            # Simple item add
            QListWidgetItem(s, self)

        # Calculate position and size
        # Position below the target widget
        global_pos = target_widget.mapToGlobal(QPoint(0, target_widget.height()))
        
        # Calculate needed height
        row_height = 36 # approx height per item including padding
        content_height = min(len(suggestions) * row_height + 10, 200) # Cap at 200px
        
        self.setGeometry(global_pos.x(), global_pos.y() + 4, target_widget.width(), content_height)
        self.show()
        self.raise_()

    def _on_item_clicked(self, item):
        if item:
            self.suggestion_selected.emit(item.text())
            self.hide()
