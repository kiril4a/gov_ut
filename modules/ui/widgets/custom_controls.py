from PyQt6.QtWidgets import (QCalendarWidget, QToolButton, QSpinBox, 
                             QAbstractSpinBox, QMenu, QWidget, QDateEdit, 
                             QDoubleSpinBox, QComboBox, QFrame, QListWidget, 
                             QVBoxLayout, QListWidgetItem, QApplication, QAbstractItemView, QHeaderView, QLineEdit, QHBoxLayout)
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

class RangeCalendarWidget(CustomCalendarWidget):
    """Calendar that supports selecting a date range by two clicks.
    First click sets the range start, second click sets the range end and emits
    range_selected(start_qdate, end_qdate).
    """
    range_selected = pyqtSignal(object, object)  # (QDate start, QDate end)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.range_start = None
        self.range_end = None
        self._awaiting_second = False
        # connect click
        try:
            self.clicked.connect(self._on_clicked)
        except Exception:
            pass

    def _on_clicked(self, qdate):
        try:
            if not self._awaiting_second:
                # start selection
                self.range_start = qdate
                self.range_end = None
                self._awaiting_second = True
                # visually select the start to make it clear
                try:
                    self.setSelectedDate(qdate)
                except Exception:
                    pass
                self.update()
            else:
                # finish selection
                start = self.range_start or qdate
                end = qdate
                if end < start:
                    start, end = end, start
                self.range_start = start
                self.range_end = end
                self._awaiting_second = False
                try:
                    self.setSelectedDate(end)
                except Exception:
                    pass
                self.update()
                # emit signal
                try:
                    self.range_selected.emit(start, end)
                except Exception:
                    pass
        except Exception:
            pass

    def paintCell(self, painter, rect, date):
        # Draw range background first (so numbers/selection are visible on top)
        try:
            if self.range_start and self.range_end:
                if self.range_start <= date <= self.range_end:
                    painter.save()
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(74, 163, 223, 60))  # translucent blue
                    r = QRect(rect.left() + 1, rect.top() + 1, rect.width() - 2, rect.height() - 2)
                    painter.drawRoundedRect(r, 6, 6)
                    painter.restore()
        except Exception:
            pass
        # Call parent to draw text/selection
        try:
            super().paintCell(painter, rect, date)
        except Exception:
            # If parent fails, at least draw the day number
            painter.save()
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

class DateRangeEdit(QWidget):
    """A compact widget that shows a date range and opens a RangeCalendarWidget popup
    to select the interval via two clicks (start and end).
    """
    range_changed = pyqtSignal(object, object)  # start_qdate, end_qdate

    def __init__(self, parent=None):
        super().__init__(parent)
        self._start = None
        self._end = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._edit = QLineEdit(self)
        self._edit.setReadOnly(True)
        self._edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._edit.setMinimumWidth(220)
        layout.addWidget(self._edit)
        # Install event filter so clicks on the read-only line edit open the popup
        try:
            self._edit.installEventFilter(self)
        except Exception:
            pass

        # Popup (created lazily)
        self._popup = None

        # default to current month
        try:
            cur = QDate.currentDate()
            start = QDate(cur.year(), cur.month(), 1)
            end = start.addMonths(1).addDays(-1)
            self.setRange(start, end)
        except Exception:
            pass

        # Install event filter for the inner QLineEdit
        self._edit.installEventFilter(self)

    def mousePressEvent(self, event):
        try:
            self.showPopup()
        except Exception:
            pass
        return super().mousePressEvent(event)

    def showPopup(self, anchor_widget=None):
        """
        Show the range calendar popup. If `anchor_widget` is provided, the popup will
        be anchored to that widget (positioned under it when possible). If not,
        behavior falls back to anchoring to this DateRangeEdit instance.
        """
        try:
            if self._popup and self._popup.isVisible():
                return

            # Create a top-level popup so it can be positioned anywhere on screen
            self._popup = QFrame(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
            self._popup.setStyleSheet("background-color: #2b2b2b; border: 1px solid #404040; border-radius: 8px;")
            v = QVBoxLayout(self._popup)
            v.setContentsMargins(8, 8, 8, 8)
            self._range_cal = RangeCalendarWidget(self._popup)

            try:
                if self._start and self._end:
                    self._range_cal.range_start = self._start
                    self._range_cal.range_end = self._end
                    try:
                        self._range_cal.setSelectedDate(self._end)
                    except Exception:
                        pass
            except Exception:
                pass

            v.addWidget(self._range_cal)

            try:
                self._range_cal.range_selected.connect(self._on_range_selected)
            except Exception:
                pass

            # Positioning: prefer anchor_widget if provided, else this widget
            try:
                anchor = anchor_widget if anchor_widget is not None else self
                try:
                    rect = anchor.rect()
                    global_pt = anchor.mapToGlobal(rect.bottomLeft())
                    x = global_pt.x()
                    y = global_pt.y()
                except Exception:
                    gp = anchor.mapToGlobal(QPoint(0, anchor.height()))
                    x = gp.x(); y = gp.y()

                try:
                    screen = anchor.screen() if hasattr(anchor, 'screen') else QApplication.primaryScreen()
                    if screen is None:
                        screen = QApplication.primaryScreen()
                    geom = screen.availableGeometry()

                    # ensure not off left/top
                    if x < geom.left():
                        x = geom.left()
                    if y < geom.top():
                        y = geom.top()

                    # clamp right edge
                    if x + self._popup.width() > geom.right():
                        x = max(geom.left(), geom.right() - self._popup.width())

                    # if it doesn't fit below, show above
                    if y + self._popup.height() > geom.bottom():
                        try:
                            top_left = anchor.mapToGlobal(anchor.rect().topLeft())
                            y = top_left.y() - self._popup.height()
                        except Exception:
                            y = max(geom.top(), geom.bottom() - self._popup.height())

                        if y < geom.top():
                            y = geom.top()
                except Exception:
                    pass

                self._popup.move(QPoint(int(x), int(y)))
            except Exception:
                try:
                    pos = self.mapToGlobal(QPoint(0, self.height()))
                    self._popup.move(pos)
                except Exception:
                    pass

            self._popup.show()
        except Exception:
            pass

    def _on_range_selected(self, start, end):
        try:
            self.setRange(start, end)
            try:
                if self._popup:
                    self._popup.close()
            except Exception:
                pass
            try:
                self.range_changed.emit(start, end)
            except Exception:
                pass
        except Exception:
            pass

    def setRange(self, start: QDate, end: QDate):
        try:
            if start and end and end < start:
                start, end = end, start
            self._start = start
            self._end = end
            if start and end:
                self._edit.setText(f"{start.toString('dd.MM.yyyy')} — {end.toString('dd.MM.yyyy')}")
            else:
                self._edit.setText("")
        except Exception:
            pass

    def dateRange(self):
        return (self._start, self._end)

    def startDate(self):
        return self._start

    def endDate(self):
        return self._end

    def eventFilter(self, source, event):
        # Open popup when user clicks the read-only line edit
        try:
            if source == self._edit and event.type() == QEvent.Type.MouseButtonPress:
                try:
                    self.showPopup()
                except Exception:
                    pass
                return True
        except Exception:
            pass
        return super().eventFilter(source, event)

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
