from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDateEdit, QComboBox, 
                             QDoubleSpinBox, QSpinBox, QMessageBox, QGroupBox, QSizePolicy,
                             QCalendarWidget, QToolButton, QMenu, QAbstractSpinBox, QStyle, QApplication, QStyleOptionComboBox, QStyleOptionSpinBox, QWidgetAction, QLineEdit, QScrollArea, QListWidget, QListWidgetItem, QCompleter)
from PyQt6.QtCore import Qt, QDate, QEvent, QLocale, QRect, QPointF, QPoint, QSize, QTimer, QThread, pyqtSignal, QMutex, QStringListModel
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QMouseEvent, QKeyEvent
import hashlib
import time
from modules.core.google_service import GoogleService
from modules.core.utils import get_resource_path
from modules.ui.google_sheet_worker import GoogleSheetLoadThread, GoogleSheetSyncThread
from modules.ui.loading_overlay import LoadingOverlay
from modules.ui.scrollbar_styles import get_scrollbar_qss

class CustomCalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLocale(QLocale(QLocale.Language.Russian))
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setNavigationBarVisible(True)
        
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

class RemoteLoadWorker(QThread):
    data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, google_service, spreadsheet_id):
        super().__init__()
        self.google_service = google_service
        self.spreadsheet_id = spreadsheet_id

    def run(self):
        try:
            # Load objects and stats (match apply_imported_data expectations)
            objs = self.google_service.get_sheet_data('objects')
            stats = self.google_service.get_sheet_data('stats')
            payload = {}
            if objs is not None:
                payload['objects'] = objs
            if stats is not None:
                payload['stats'] = stats
            self.data_loaded.emit(payload)
        except Exception as e:
            self.error_occurred.emit(str(e))

def _format_display_amount(value: int) -> str:
    """Format integer amount for display with dot thousand separators and trailing $; include sign for income/expense."""
    sign = '+' if value > 0 else ('-' if value < 0 else '')
    abs_val = abs(int(value))
    s = f"{abs_val:,}".replace(',', '.')
    if sign:
        return f"{sign}{s}$"
    return f"{s}$"


def _parse_display_amount(text: str) -> int:
    """Parse displayed amount (which may contain +, -, dots and $) back to integer value for export/compute."""
    if not text:
        return 0
    t = text.replace('$', '').replace(' ', '').replace('+', '')
    # Keep minus if present, remove dots
    t = t.replace('.', '')
    try:
        return int(t)
    except Exception:
        # fallback: extract digits and optional leading -
        import re
        m = re.search(r"-?\d+", text)
        if m:
            return int(m.group(0))
        return 0

class SyncWorker(QThread):
    finished = pyqtSignal()
    import_ready = pyqtSignal(object)  # Emits dict with sheet data when import detected
    export_done = pyqtSignal()

    def __init__(self, google_service, data_queue):
        super().__init__()
        self.google_service = google_service
        self.data_queue = data_queue
        self.mutex = QMutex()
        self._is_running = True
        self._last_import_hash = { 'stats': None, 'objects': None }
        self._last_export_hash = { 'stats': None, 'objects': None }
        self._skip_next_import = False

    def run(self):
        import time, hashlib
        # Aggregate changes for 3 minutes (180 seconds)
        while self._is_running:
            # Wait 180 seconds to accumulate tasks (collect queue over 3 minutes)
            time.sleep(180)

            # Export if there are queued changes
            self.mutex.lock()
            has_items = bool(self.data_queue)
            if not has_items:
                self.mutex.unlock()
                continue

            current_batch = self.data_queue.copy()
            self.data_queue.clear()
            self.mutex.unlock()

            # Keep only latest update per sheet
            unique_updates = {}
            for item in current_batch:
                sheet_name = item['sheet']
                unique_updates[sheet_name] = item['data']

            for sheet, data in unique_updates.items():
                # attempt with exponential backoff on quota errors
                attempt = 0
                backoff = 1
                success = False
                while attempt < 5 and not success:
                    try:
                        self.google_service.sync_sheet_data(sheet, data)
                        print(f"Synced {sheet} to Google Sheets (Batch export).")
                        try:
                            exported_hash = hashlib.md5(repr(data).encode('utf-8')).hexdigest()
                            self._last_export_hash[sheet] = exported_hash
                            self._last_import_hash[sheet] = exported_hash
                        except Exception:
                            pass
                        success = True
                    except Exception as e:
                        err = str(e)
                        print(f"Sync failed for {sheet} (attempt {attempt+1}): {err}")
                        # detect quota/429 and backoff
                        if '429' in err or 'Quota exceeded' in err or 'quota' in err.lower():
                            time.sleep(backoff)
                            backoff = min(backoff * 2, 60)
                            attempt += 1
                            continue
                        else:
                            break

                if not success:
                    try:
                        self.mutex.lock()
                        self.data_queue.append({'sheet': sheet, 'data': data})
                        self.mutex.unlock()
                    except Exception:
                        try:
                            self.mutex.unlock()
                        except Exception:
                            pass

            try:
                self.export_done.emit()
            except Exception:
                pass

    def perform_import_check(self):
        """Fetch sheets from Google and emit import_ready when new content detected."""
        import hashlib
        sheets = ['stats', 'objects']
        fetched = {}
        changed = False

        for s in sheets:
            rows = self.google_service.get_sheet_data(s)
            if rows is None:
                continue
            fetched[s] = rows
            h = hashlib.md5(repr(rows).encode('utf-8')).hexdigest()
            if self._last_import_hash.get(s) != h:
                self._last_import_hash[s] = h
                changed = True

        if changed and fetched:
            self.import_ready.emit(fetched)

    def stop(self):
        self._is_running = False
        self.wait()

class GovernorCabinetWindow(QMainWindow):
    def __init__(self, user_data, parent_launcher=None):
        super().__init__()
        self.user_data = user_data
        self.parent_launcher = parent_launcher
        self.google_service = GoogleService(target_spreadsheet_id="1E1dzanmyjcGUur8sp4uFsc7cADDhvNp4UEley6VIS6Y")
        self.spreadsheet_id = "1E1dzanmyjcGUur8sp4uFsc7cADDhvNp4UEley6VIS6Y"
        
        self.setWindowTitle("Governor Cabinet")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QGroupBox {
                border: 1px solid #404040;
                border-radius: 6px;
                margin-top: 10px;
                font-weight: bold;
                color: #ccc;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QTableWidget {
                background-color: #1e1e1e;
                gridline-color: transparent;
                color: #ddd;
                border: none;
                font-size: 13px;
                selection-background-color: transparent;
                outline: none;
            }
            QTableWidget::item {
                background-color: #333333;
                margin-top: 0px; 
                margin-bottom: 8px;
                margin-left: 2px;
                margin-right: 4px;
                padding-left: 0px; 
                border-radius: 6px; 
                border: 1px solid #404040;
            }
            QHeaderView {
                background-color: transparent;
                border: none;
            }
            QHeaderView::section {
                background-color: #333333;
                color: white;
                padding: 6px;
                border: 1px solid #404040;
                font-weight: bold;
                border-radius: 6px;
                margin-right: 4px;
                margin-left: 2px;
                margin-bottom: 8px;
                margin-top: 6px; 
            }
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
            QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox {
                background-color: white; 
                color: black;
                border: none;
                padding: 0px; 
                border-radius: 4px; 
                font-weight: bold;
                min-height: 25px;
                max-height: 25px;
                margin: 5px;
                selection-background-color: #4aa3df;
                selection-color: white;
            }
            QComboBox:hover, QDateEdit:hover, QDoubleSpinBox:hover, QSpinBox:hover,
            QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
                background-color: #f0f0f0;
                border-radius: 4px;
            }
        """ + get_scrollbar_qss())

        self.transaction_data = [] # Left table
        self.item_definitions = [] # Right top table

        # Initialize items_table before accessing it
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(3) # Changed to 3 columns: Name, Price, Delete
        self.items_table.setHorizontalHeaderLabels(["Название предмета", "Базовая цена", "x"])
        
        # Configure columns to match trans_table style
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.items_table.setColumnWidth(1, 120)
        
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.items_table.setColumnWidth(2, 50)
        
        self.items_table.horizontalHeader().setStretchLastSection(False)

        # Header "x" centered
        item_del = QTableWidgetItem("x")
        item_del.setToolTip("Удалить")
        item_del.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.items_table.setHorizontalHeaderItem(2, item_del)

        # Visual styles matching left table
        self.items_table.setShowGrid(False) 
        self.items_table.verticalHeader().setVisible(False) # Hide line numbers
        self.items_table.verticalHeader().setDefaultSectionSize(45)
        self.items_table.horizontalHeader().setDefaultSectionSize(40)
        self.items_table.horizontalHeader().setMinimumSectionSize(40)

        self.items_table.setMinimumWidth(200)  # Set a smaller minimum width for the right table
        
        # Init items table with plus row
        self.init_items_table()

        # Ensure init_ui is called to initialize all UI components, including trans_table
        self.init_ui()
        self.setup_auto_sync()

        # No automatic import on open. Provide manual import button in header.
        # The button is created in init_ui; connect it here if needed.
        # Ensure importing flag starts as False
        self._importing = False

        # Sync Queue and Thread
        self.sync_queue = []
        # Local dirty flag - set when the user/app makes local changes
        self._local_dirty = False
        # Track last exported hash per sheet to avoid re-exporting identical data
        self._last_export_hash = { 'stats': None, 'objects': None }
        # Flag to avoid enqueuing syncs while applying imported changes
        self._importing = False
        self.sync_worker = SyncWorker(self.google_service, self.sync_queue)
        self.sync_worker.import_ready.connect(self.apply_imported_data)
        self.sync_worker.export_done.connect(lambda: setattr(self, '_local_dirty', False))
        self.sync_worker.start()

        self._auto_loaded_once = False
        self._load_thread = None
        self._sync_thread = None
        self._loading_overlay = LoadingOverlay(self, text="Загрузка...")

        # Auto-import on first open
        QTimer.singleShot(0, self._auto_import_on_open)

        # Shared completer model for item suggestions (robust alternative to custom popup)
        try:
            self._items_completer_model = QStringListModel()
            self._items_completer = QCompleter(self._items_completer_model, self)
            self._items_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            try:
                self._items_completer.setFilterMode(Qt.MatchFlag.MatchContains)
            except Exception:
                pass
            self._items_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            # Style the completer popup to match dark theme
            try:
                popup = self._items_completer.popup()
                popup.setStyleSheet('''
                    QListView { background: #232323; color: #f2f2f2; border: 1px solid #3a3a3a; border-radius: 10px; padding: 6px; }
                    QListView::item { padding: 8px 12px; border-radius: 6px; }
                    QListView::item:hover { background: #3a3a3a; }
                    QListView::item:selected { background: #4aa3df; color: white; }
                ''')
            except Exception:
                pass

            # Ensure completer selection applies and closes popup
            try:
                self._items_completer.activated.connect(lambda text: self._on_completer_activated(text))
            except Exception:
                pass
        except Exception:
            self._items_completer = None
            self._items_completer_model = None

        # Install global event filter to close popups/completers on outside click
        try:
            app = QApplication.instance()
            if app:
                app.installEventFilter(self)
                self._global_eventfilter_installed = True
        except Exception:
            self._global_eventfilter_installed = False

        # suppression flag to avoid immediate reopen after selection
        self._suppress_popup = False

    def closeEvent(self, event):
        self.sync_worker.stop()
        super().closeEvent(event)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        title_label = QLabel("GOVERNOR CABINET")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #4aa3df;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        stats_frame = QFrame()
        stats_frame.setStyleSheet("border: 2px solid #555; border-radius: 8px; padding: 5px;")
        stats_layout = QHBoxLayout(stats_frame)
        
        self.lbl_income = QLabel("Доходы: 0")
        self.lbl_expense = QLabel("Расходы: 0")
        self.lbl_balance = QLabel("Баланс: 0")
        for lbl in [self.lbl_income, self.lbl_expense, self.lbl_balance]:
            lbl.setStyleSheet("font-size: 16px; font-weight: bold; padding: 0 10px; border: none;")
            stats_layout.addWidget(lbl)
            
        header_layout.addWidget(stats_frame)
        
        header_layout.addStretch()
        
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Период:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Текущий месяц", "Прошлый месяц", "Все время"])
        period_layout.addWidget(self.period_combo)
        header_layout.addLayout(period_layout)
        
        header_layout.addSpacing(20)

        # Buttons container
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(5)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        btn_back = QPushButton("В лаунчер")
        btn_back.setStyleSheet("background-color: #555; border: 1px solid #777;")
        btn_back.clicked.connect(self.return_to_launcher)
        
        btn_import = QPushButton("Импорт")
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
        """)
        btn_import.clicked.connect(self.on_manual_import_click)

        buttons_layout.addWidget(btn_back)
        buttons_layout.addWidget(btn_import)
        
        header_layout.addLayout(buttons_layout)
        
        main_layout.addLayout(header_layout)

        content_layout = QHBoxLayout()
        
        left_layout = QVBoxLayout()
        
        grp_trans = QGroupBox("Операции (Доход/Расход)")
        grp_trans_layout = QVBoxLayout(grp_trans)
        grp_trans_layout.setContentsMargins(5, 20, 5, 5)
        
        self.trans_table = QTableWidget()
        self.trans_table.setColumnCount(8)
        self.trans_table.setHorizontalHeaderLabels(["№", "Дата", "Тип", "Предмет|Услуга", "Кол-во", "Цена", "Сумма", "x"])
        self.trans_table.horizontalHeader().setStretchLastSection(False)
        
        item_del = QTableWidgetItem("x")
        item_del.setToolTip("Удалить")
        item_del.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trans_table.setHorizontalHeaderItem(7, item_del)
        
        self.trans_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(0, 50)
        
        self.trans_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(1, 120)

        self.trans_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(2, 40)

        self.trans_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.trans_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(4, 80) 
        
        self.trans_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(5, 150)
        
        self.trans_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(6, 150)

        self.trans_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(7, 50)
        
        self.trans_table.setShowGrid(False) 
        self.trans_table.verticalHeader().setVisible(False)
        self.trans_table.verticalHeader().setDefaultSectionSize(45)
        self.trans_table.horizontalHeader().setDefaultSectionSize(40)
        self.trans_table.horizontalHeader().setMinimumSectionSize(40) 
        
        grp_trans_layout.addWidget(self.trans_table)
        
        self.init_trans_table()

        left_layout.addWidget(grp_trans)
        
        grp_filter = QGroupBox("Фильтр по предметам")
        filter_layout = QHBoxLayout(grp_filter)
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Все предметы")
        filter_layout.addWidget(self.filter_combo)
        
        self.lbl_filter_qty = QLabel("Кол-во: 0")
        self.lbl_filter_sum = QLabel("Сумма: 0")
        filter_layout.addWidget(self.lbl_filter_qty)
        filter_layout.addWidget(self.lbl_filter_sum)
        
        left_layout.addWidget(grp_filter)
        
        content_layout.addLayout(left_layout, stretch=7)

        right_layout = QVBoxLayout()
        
        right_layout.setStretch(0, 3)
        right_layout.setContentsMargins(0, 0, 0, 0)

        grp_items = QGroupBox("Управление предметами")
        grp_items_layout = QVBoxLayout(grp_items)
        
        grp_items_layout.addWidget(self.items_table)
        
        right_layout.addWidget(grp_items, stretch=1)
        
        grp_stats = QGroupBox("Общая статистика по предметам")
        grp_stats_layout = QVBoxLayout(grp_stats)
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(3)
        self.stats_table.setHorizontalHeaderLabels(["Предмет", "Количество", "Сумма"])
        self.stats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        grp_stats_layout.addWidget(self.stats_table)
        
        right_layout.addWidget(grp_stats, stretch=1)
        
        content_layout.addLayout(right_layout, stretch=3)
        
        main_layout.addLayout(content_layout)

    def return_to_launcher(self):
        if self.parent_launcher:
            self.parent_launcher.show()
        else:
            from modules.ui.launcher import LauncherWindow
            self.launcher = LauncherWindow(self.user_data)
            self.launcher.show()
        self.close()

    def add_transaction(self):
        pass
        
    def add_item_definition(self):
        pass

    def load_data(self):
        pass

    def init_trans_table(self):
        self.trans_table.setRowCount(0)
        self.add_plus_row()

    def add_plus_row(self):
        row_idx = self.trans_table.rowCount()
        self.trans_table.insertRow(row_idx)
        self.trans_table.setRowHeight(row_idx, 50) 
        
        btn_add = QPushButton("+")
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                font-size: 24px; 
                font-weight: bold; 
                color: #4aa3df; 
                border: 1px dashed #404040; 
                border-radius: 8px;
                margin: 0px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #252525;
            }
        """)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trans_table.setSpan(row_idx, 0, 1, 8)
        self.trans_table.setCellWidget(row_idx, 0, btn_add)
        
        btn_add.clicked.connect(self.add_new_transaction_row)

    def add_new_transaction_row(self):
        # Prevent intermediate repaints to avoid flicker of qty column when widgets are added
        try:
            self.trans_table.setUpdatesEnabled(False)
        except Exception:
            pass

        plus_row_index = self.trans_table.rowCount() - 1
        self.trans_table.insertRow(plus_row_index)
        row = plus_row_index
        
        self.trans_table.setRowHeight(row, 45)
        
        num_item = QTableWidgetItem(str(row + 1))
        num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        num_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        num_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.trans_table.setItem(row, 0, num_item)

        date_btn = QPushButton(QDate.currentDate().toString("dd.MM.yyyy"))
        date_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        date_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-weight: bold;
                color: #dddddd;
            }
            QPushButton:hover {
                color: #4aa3df;
            }
        """)
        
        date_btn.clicked.connect(lambda checked, btn=date_btn: self.show_calendar_popup(btn))

        container_date = QWidget()
        layout_date = QHBoxLayout(container_date)
        layout_date.setContentsMargins(0,0,0,0)
        layout_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_date.addWidget(date_btn)
        self.trans_table.setCellWidget(row, 1, container_date)

        # Type button (starts as Expense '-')
        type_btn = QPushButton("-")
        type_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        type_btn.setProperty("is_income", False)
        # slightly larger to comfortably show +/-, with bold font
        type_btn.setFixedSize(28, 28)
        type_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        # Use minimal base style; visuals applied in _apply_type_state
        type_btn.setStyleSheet("border: none; padding: 0px; margin: 0px;")
        
        container_type = QFrame()
        layout_type = QVBoxLayout(container_type)
        layout_type.setContentsMargins(0,0,0,0)
        layout_type.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_type.addWidget(type_btn)
        
        self.trans_table.setCellWidget(row, 2, container_type)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Название предмета")
        name_edit.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        # Make text bold and ensure proper height so it doesn't overflow the cell
        name_edit.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        name_edit.setStyleSheet("""
            QLineEdit { background-color: white; color: black; border-radius: 6px; padding: 4px 8px; border: 1px solid #555; }
            QLineEdit:focus { border: 2px solid #4aa3df; }
        """)
        name_edit.setMinimumHeight(30)

        # Attach shared completer if available
        try:
            if getattr(self, '_items_completer', None):
                name_edit.setCompleter(self._items_completer)

                # Show suggestions while typing (supports IME/Cyrillic): use textEdited and schedule complete
                def _on_name_text_edited(txt, r=row, le=name_edit):
                    try:
                        comp = self._items_completer
                        if comp is None:
                            return
                        comp.setCompletionPrefix(txt or "")
                        # suppress global auto-close for the short time until popup shows
                        try:
                            self._suppress_global_close_until = time.time() + 0.25
                        except Exception:
                            pass
                        QTimer.singleShot(0, comp.complete)
                    except Exception:
                        pass

                name_edit.textEdited.connect(_on_name_text_edited)

                # Show all suggestions when the field is focused and when empty
                try:
                    orig_focus = name_edit.focusInEvent
                except Exception:
                    orig_focus = None

                def _focus_in(ev, r=row, le=name_edit):
                    try:
                        if callable(orig_focus):
                            try:
                                orig_focus(ev)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        comp = self._items_completer
                        if comp is None:
                            return
                        comp.setCompletionPrefix("")
                        try:
                            self._suppress_global_close_until = time.time() + 0.25
                        except Exception:
                            pass
                        QTimer.singleShot(0, comp.complete)
                    except Exception:
                        pass

                try:
                    name_edit.focusInEvent = _focus_in
                except Exception:
                    pass
        except Exception:
            pass

        container_item = QWidget()
        layout_item = QHBoxLayout(container_item)
        # Reduce vertical margins to avoid pushing the edit below its cell area
        layout_item.setContentsMargins(4, 0, 4, 0)
        layout_item.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        name_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_item.addWidget(name_edit)
        self.trans_table.setCellWidget(row, 3, container_item)

        # Track active editor and ensure popup shows on first interaction
        try:
            name_edit.setProperty('trans_row', int(row))
            self._active_item_editor = name_edit
        except Exception:
            pass

        # show popup as soon as user focuses/clicks into the field
        try:
            name_edit.selectionChanged.connect(lambda r=row, le=name_edit: self._on_item_editor_interaction(r, le))
        except Exception:
            pass
        try:
            name_edit.cursorPositionChanged.connect(lambda _o, _n, r=row, le=name_edit: self._on_item_editor_interaction(r, le))
        except Exception:
            pass

        name_edit.installEventFilter(self)
        name_edit.textChanged.connect(lambda txt, r=row: self.on_item_text_changed(r, txt))
        # Do not use QCompleter here; suggestions handled by custom popup
        
        qty_block = QFrame()
        qty_block_layout = QVBoxLayout(qty_block)
        qty_block_layout.setContentsMargins(0,0,0,0)
        qty_block_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qty_spin = NoScrollSpinBox()
        qty_spin.setRange(-999999, 999999)
        qty_spin.setValue(0) 
        qty_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qty_spin.valueChanged.connect(lambda: self.recalc_row(row))
        # remove physical up/down buttons
        try:
            qty_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        except Exception:
            pass
        
        qty_block_layout.addWidget(qty_spin)
        self.trans_table.setCellWidget(row, 4, qty_block)

        price_spin = NoScrollSpinBox()
        price_spin.setRange(-1000000000, 1000000000)
        price_spin.setValue(0)
        price_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price_spin.valueChanged.connect(lambda: self.recalc_row(row))
        try:
            price_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        except Exception:
            pass
        
        container_price = QWidget()
        layout_price = QHBoxLayout(container_price)
        layout_price.setContentsMargins(0,0,0,0)
        layout_price.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_price.addWidget(price_spin)
        self.trans_table.setCellWidget(row, 5, container_price)

        sum_item = QTableWidgetItem("0")
        sum_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        sum_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        sum_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.trans_table.setItem(row, 6, sum_item)

        type_btn.clicked.connect(lambda checked, r=row, btn=type_btn: self.toggle_type(r, btn))

        del_btn = QPushButton()
        # Use simple unicode trash can as requested: 🗑️
        del_btn.setText("🧹")
             
        del_btn.setIcon(QIcon()) # Remove icon property if any
        # Adjust size for text instead of icon
        del_btn.setFixedSize(30, 30) 
        
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("background: transparent; border: none; font-size: 16px; color: white;")
        del_btn.clicked.connect(lambda: self.delete_row_by_widget(del_btn))

        container_del = QFrame()
        container_del.setFrameShape(QFrame.Shape.Box)
        # Move styling to the container to handle hover effect for the whole block
        # Make the button inside transparent and fill the container
        container_del.setStyleSheet("""
            QFrame {
                border: 2px solid #ff5555; 
                border-radius: 4px;
                background-color: #ff5555;
            }
            QFrame:hover {
                background-color: #ff7777; /* Lighter red on hover */
                border: 2px solid #ff7777;
            }
        """)
        container_del.setLayout(QVBoxLayout())
        container_del.layout().setContentsMargins(0, 0, 0, 0)
        container_del.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Ensure button takes up full space and passes clicks if needed, 
        # but typically button handles click. We want hover on container.
        # So we make button transparent and layout stretch.
        del_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        del_btn.setStyleSheet("background: transparent; border: none; font-size: 16px; color: white;")
        
        container_del.layout().addWidget(del_btn)
        
        self.trans_table.setCellWidget(row, 7, container_del)

        # Apply initial type state to ensure correct qty visibility
        self._apply_type_state(row, False)

        self.update_row_numbers()
        self.recalc_row(row)
        # Trigger sync on change
        self.sync_all_data()

        # Re-enable updates
        try:
            self.trans_table.setUpdatesEnabled(True)
            self.trans_table.viewport().update()
        except Exception:
            pass

    def _on_item_editor_interaction(self, row: int, le: QLineEdit):
        """Called on focus/click/typing to force suggestions popup."""
        try:
            self._active_item_editor = le
        except Exception:
            pass
        try:
            self.on_item_text_changed(row, le.text())
        except Exception:
            pass

    def toggle_type(self, row, btn):
        # Toggle type state and reuse _apply_type_state to keep visuals consistent
        try:
            is_income = bool(btn.property("is_income"))
        except Exception:
            is_income = False

        new_state = not is_income
        try:
            btn.setProperty("is_income", bool(new_state))
        except Exception:
            pass

        self._apply_type_state(row, new_state, force_update=True)
        self.recalc_row(row)
        self.sync_all_data()

    def _ensure_type_button(self, row, is_income=False):
        """Ensure the type QPushButton exists for given row. Create and wire toggle handler if missing."""
        try:
            container = self.trans_table.cellWidget(row, 2)
            if container:
                btn = container.findChild(QPushButton)
                if btn:
                    btn.setProperty('is_income', bool(is_income))
                    # rewire click handler to guarantee toggling works after import
                    try:
                        btn.clicked.disconnect()
                    except Exception:
                        pass
                    btn.clicked.connect(lambda checked=False, r=row, b=btn: self.toggle_type(r, b))
                    self._apply_type_state(row, bool(is_income), force_update=True)
                    return
        except Exception:
            pass

        type_btn = QPushButton('+' if is_income else '-')
        type_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        type_btn.setProperty('is_income', bool(is_income))
        type_btn.setFixedSize(30, 30)
        type_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        type_btn.clicked.connect(lambda checked=False, r=row, b=type_btn: self.toggle_type(r, b))

        container_type = QFrame()
        layout_type = QVBoxLayout(container_type)
        layout_type.setContentsMargins(0,0,0,0)
        layout_type.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_type.addWidget(type_btn)

        self.trans_table.setCellWidget(row, 2, container_type)
        self._apply_type_state(row, bool(is_income), force_update=True)

    def update_row_numbers(self):
        for r in range(self.trans_table.rowCount() - 1):
             item = self.trans_table.item(r, 0)
             if item:
                 item.setText(str(r + 1))
        # Reapply type state for all rows to ensure qty visibility maintained after row moves
        try:
            for r in range(self.trans_table.rowCount() - 1):
                container = self.trans_table.cellWidget(r, 2)
                if container:
                    btn = container.findChild(QPushButton)
                    if btn:
                        is_income = bool(btn.property('is_income'))
                        try:
                            self._apply_type_state(r, is_income)
                        except Exception:
                            pass
        except Exception:
            pass

    def delete_row_by_widget(self, sender_widget):
        row_to_delete = -1
        for r in range(self.trans_table.rowCount()):
            container = self.trans_table.cellWidget(r, 7)
            if container:
                if sender_widget in container.findChildren(QPushButton):
                    row_to_delete = r
                    break

        if row_to_delete != -1:
            try:
                self.trans_table.setUpdatesEnabled(False)
            except Exception:
                pass

            self.trans_table.removeRow(row_to_delete)
            self.update_row_numbers()
            self.sync_all_data() # Sync on delete transaction

            try:
                self.trans_table.setUpdatesEnabled(True)
                self.trans_table.viewport().update()
            except Exception:
                pass

    def recalc_row(self, row):
        try:
            if not hasattr(self, 'trans_table'):
                return

            # If called by signal, find the row
            target_row = row
            sender = self.sender()
            
            # If recalculating from signal
            if sender and isinstance(sender, (QSpinBox, QDoubleSpinBox)):
                 # Find which row this sender belongs to
                found_sender = False
                for r in range(self.trans_table.rowCount()):
                    # Check columns 4 (Qty) and 5 (Price)
                    # The cell widget is a container, look inside it
                    container_qty = self.trans_table.cellWidget(r, 4)
                    container_price = self.trans_table.cellWidget(r, 5)
                    
                    if container_qty and sender in container_qty.findChildren((QSpinBox, QDoubleSpinBox)):
                        target_row = r
                        found_sender = True
                        break
                    if container_price and sender in container_price.findChildren((QSpinBox, QDoubleSpinBox)):
                        target_row = r
                        found_sender = True
                        break
                
                if found_sender:
                     target_row = r # Correctly capture the row
            
            # Check logic based on Type
            container_type = self.trans_table.cellWidget(target_row, 2)
            is_income = False
            if container_type:
                 btn = container_type.findChild(QPushButton)
                 if btn:
                     is_income = btn.property("is_income")

            container_qty = self.trans_table.cellWidget(target_row, 4)
            container_price = self.trans_table.cellWidget(target_row, 5)
            sum_item = self.trans_table.item(target_row, 6) 
            
            if container_price and sum_item:
                price_widgets = container_price.findChildren((QSpinBox, QDoubleSpinBox))
                price = price_widgets[0].value() if price_widgets else 0

                if is_income:
                    # Income: Sum = Price (Quantity ignored/hidden); show plus sign
                    total = int(price)
                else:
                    # Expense: Sum = Price * Qty and should be negative
                    qty_widgets = container_qty.findChildren((QSpinBox, QDoubleSpinBox)) if container_qty else []
                    qty = qty_widgets[0].value() if qty_widgets else 0
                    total = int(qty * price) * -1

                # Set display with formatting (dots, $ and sign for income/expense)
                sum_item.setText(_format_display_amount(total))
        except Exception:
            pass

        # Update header totals
        try:
            self.update_totals()
        except Exception:
            pass

        # Trigger sync on change
        self.sync_all_data()

    def delete_transaction(self):
        pass

    def init_items_table(self):
        self.items_table.setRowCount(0)
        self.add_item_plus_row()

    def add_item_plus_row(self):
        row_idx = self.items_table.rowCount()
        self.items_table.insertRow(row_idx)
        self.items_table.setRowHeight(row_idx, 50) 
        
        btn_add = QPushButton("+")
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                font-size: 24px; 
                font-weight: bold; 
                color: #4aa3df; 
                border: 1px dashed #404040; 
                border-radius: 8px;
                margin: 0px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #252525;
            }
        """)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.items_table.setSpan(row_idx, 0, 1, 3) # Span all 3 columns
        self.items_table.setCellWidget(row_idx, 0, btn_add)
        
        btn_add.clicked.connect(self.add_new_item_row)

    def add_new_item_row(self):
        plus_row_index = self.items_table.rowCount() - 1 
        try:
            self.items_table.setUpdatesEnabled(False)
        except Exception:
            pass
        self.items_table.insertRow(plus_row_index)
        row = plus_row_index 
        
        self.items_table.setRowHeight(row, 45)
        
        # 0. Item Name (Styled QLineEdit)
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Название")
        name_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Apply style to match QSpinBox (dark background, white text, etc.)
        name_edit.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: black;
                border: 1px solid #555555;
                border-radius: 4px; /* Common QSpinBox radius */
                font-weight: bold; /* Often spinboxes are bold in this theme */
                padding: 2px;
            }
        """)
        
        container_name = QWidget()
        layout_name = QHBoxLayout(container_name)
        layout_name.setContentsMargins(5, 5, 5, 5)
        layout_name.addWidget(name_edit)
        self.items_table.setCellWidget(row, 0, container_name)

        # 1. Base Price (Integer SpinBox)
        # Using a container for centering exactly like left table used for prices
        price_spin = NoScrollSpinBox()
        price_spin.setRange(0, 1000000000)
        price_spin.setPrefix("$")
        price_spin.setValue(0)
        price_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons) # Cleaner look? Or keep default
        
        container_price = QWidget()
        layout_price = QHBoxLayout(container_price)
        layout_price.setContentsMargins(0,0,0,0)
        layout_price.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_price.addWidget(price_spin)
        self.items_table.setCellWidget(row, 1, container_price)

        # 2. Delete Button
        del_btn = QPushButton("🧹")
        del_btn.setFixedSize(30, 30) 
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("background: transparent; border: none; font-size: 16px; color: white;")
        del_btn.clicked.connect(lambda: self.delete_item_row_by_widget(del_btn))

        container_del = QFrame()
        container_del.setFrameShape(QFrame.Shape.Box)
        container_del.setStyleSheet("""
            QFrame {
                border: 2px solid #ff5555; 
                border-radius: 4px;
                background-color: #ff5555;
            }
            QFrame:hover {
                background-color: #ff7777;
                border: 2px solid #ff7777;
            }
        """)
        container_del.setLayout(QVBoxLayout())
        container_del.layout().setContentsMargins(0, 0, 0, 0)
        container_del.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        del_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        container_del.layout().addWidget(del_btn)
        
        self.items_table.setCellWidget(row, 2, container_del)
        
        # Connect signals for immediate sync
        name_edit.textChanged.connect(self.sync_all_data)
        price_spin.valueChanged.connect(self.sync_all_data)
        
        self.sync_all_data() # Sync on adding new item row

        try:
            self.items_table.setUpdatesEnabled(True)
            self.items_table.viewport().update()
        except Exception:
            pass

    def delete_item_row_by_widget(self, widget):
        # find parent row
        pos = widget.mapToGlobal(QPoint(0,0))
        index = self.items_table.indexAt(self.items_table.viewport().mapFromGlobal(pos))
        if index.isValid():
            try:
                self.items_table.setUpdatesEnabled(False)
            except Exception:
                pass
            self.items_table.removeRow(index.row())
            self.sync_all_data() # Sync on delete item row
            try:
                self.items_table.setUpdatesEnabled(True)
                self.items_table.viewport().update()
            except Exception:
                pass

    def setup_auto_sync(self):
        """Previously this enqueued a full sync every 10 seconds.
        Change: do NOT auto-enqueue. The SyncWorker will wait 3 seconds and
        either export accumulated local changes or import when queue is empty.
        """
        # Disabled automatic periodic enqueue to avoid exporting when no local changes.
        # If a periodic import-only check is desired, the SyncWorker already performs import when queue is empty.
        return

    def sync_all_data(self):
        """Called on local changes. Enqueue export using a background thread."""
        # Do not export while applying/importing remote data
        if getattr(self, '_importing', False):
            return

        try:
            stats_data = self.collect_stats_data()
            objects_data = self.collect_objects_data()

            payload = {'stats': stats_data, 'objects': objects_data}
            # Enqueue payload to be flushed in a single batched request to reduce API calls
            self._enqueue_sync_payload(payload)
        except Exception as e:
            print(f"Failed to enqueue export: {e}")

    def _enqueue_sync_payload(self, payload: dict):
        """Merge/queue payload and (re)start a short timer to batch multiple rapid changes.
        Uses self._sync_interval_ms (ms) default 3000ms. On quota errors the payload
        will be retried with exponential backoff.
        """
        try:
            # store latest payload (overwrite to avoid excessive history)
            self._pending_payload = payload

            # init timer if needed
            if not hasattr(self, '_sync_timer') or self._sync_timer is None:
                self._sync_timer = QTimer(self)
                self._sync_timer.setSingleShot(True)
                self._sync_timer.timeout.connect(self._flush_sync_queue)

            interval = getattr(self, '_sync_interval_ms', None) or 3000
            self._sync_timer.start(interval)
        except Exception as e:
            print(f"Failed to schedule batched sync: {e}")

    def _flush_sync_queue(self):
        """Send the accumulated payload in one background thread."""
        try:
            payload = getattr(self, '_pending_payload', None)
            if not payload:
                return
            # clear pending to allow new enqueues
            self._pending_payload = None

            # Start sync thread for the combined payload
            th = GoogleSheetSyncThread(self.google_service, self.spreadsheet_id, payload, parent=self)
            # handle errors: detect 429/quota and requeue with backoff
            th.error.connect(lambda m, p=payload: self._on_sync_error(m, p))
            # on success clear backoff counter
            th.finished.connect(lambda: setattr(self, '_sync_backoff_seconds', 0))
            th.start()
            self._last_sync_thread = th
        except Exception as e:
            print(f"Failed to flush sync queue: {e}")

    def _on_sync_error(self, msg, payload):
        """Handle sync errors from the background thread. Retries on quota errors with exponential backoff."""
        try:
            text = str(msg)
            # simple detection for quota/read/write limits
            is_quota = ('429' in text) or ('quota' in text.lower()) or ('Too Many Requests' in text)
            # exponential backoff state
            backoff = getattr(self, '_sync_backoff_seconds', 0) or 0
            if is_quota:
                # increase backoff (min 3s, double each time, cap at 10 minutes)
                backoff = backoff * 2 if backoff else 3
                backoff = min(backoff, 600)
                self._sync_backoff_seconds = backoff
                print(f"Quota hit: retrying in {backoff}s")
                QTimer.singleShot(int(backoff * 1000), lambda p=payload: self._enqueue_sync_payload(p))
            else:
                # non-quota error: try short retry once
                print(f"Sync error, retrying in 3s: {text}")
                QTimer.singleShot(3000, lambda p=payload: self._enqueue_sync_payload(p))
        except Exception as e:
            print(f"Error handling sync error: {e}")

    def collect_stats_data(self):
        """Scrapes data from trans_table (stats)."""
        data = []
        # Headers (matches your column structure roughly or define new)
        headers = ["#", "Date", "Type", "Item", "Qty", "Price", "Sum"]
        data.append(headers)
        
        for r in range(self.trans_table.rowCount() - 1): # Last row is + button
            row_data = [] 

            # 0. Num
            num_item = self.trans_table.item(r, 0)
            row_data.append(num_item.text() if num_item else str(r + 1))
            
            # 1. Date
            w_date_container = self.trans_table.cellWidget(r, 1)
            date_text = ""
            if w_date_container:
                # Look for any QPushButton (date button) inside the container
                btns = w_date_container.findChildren(QPushButton)
                if btns:
                    date_text = btns[0].text()
                else:
                    # Maybe a DateEditClickable exists
                    de = w_date_container.findChild(DateEditClickable)
                    if de:
                        date_text = de.date().toString("dd.MM.yyyy")
            row_data.append(date_text)

            # 2. Type (Income/Expense)
            container_type = self.trans_table.cellWidget(r, 2)
            type_text = ""
            is_income = False
            if container_type:
                btn = container_type.findChild(QPushButton)
                if btn:
                    is_income = bool(btn.property("is_income"))
                    # Export standardized values to avoid locale mismatch
                    type_text = "Income" if is_income else "Expense"
            row_data.append(type_text)

            # 3. Item Name (Service/Good) - be robust: look for combo, editable lineedit inside combo, or a plain QLineEdit
            w_item_container = self.trans_table.cellWidget(r, 3)
            item_text = ""
            if w_item_container:
                # Prefer any QLineEdit found first (editable combos expose lineEdit)
                le = w_item_container.findChild(QLineEdit)
                if le and le.text():
                    item_text = le.text()
                else:
                    # Look for any combo box and use currentText
                    combo = w_item_container.findChild(QComboBox)
                    if combo:
                        # If editable, prefer its lineEdit
                        try:
                            if combo.isEditable():
                                cle = combo.lineEdit()
                                if cle and cle.text():
                                    item_text = cle.text()
                                else:
                                    item_text = combo.currentText()
                            else:
                                item_text = combo.currentText()
                        except Exception:
                            item_text = combo.currentText()
            row_data.append(item_text)

            # 4. Qty
            w_qty = self.trans_table.cellWidget(r, 4)
            # If QTY widget is hidden (Income), we treat it as 1 for export stats
            
            qty = 0
            if is_income:
                qty = 1
            else:
                if isinstance(w_qty, QWidget): 
                    spin = w_qty.findChild(QSpinBox) or w_qty.findChild(QDoubleSpinBox) or w_qty.findChild(NoScrollSpinBox)
                    if spin: qty = spin.value()
                
            w_sum = self.trans_table.item(r, 6)
            # Parse displayed sum to plain number for export
            sum_val = 0
            if w_sum:
                sum_val = _parse_display_amount(w_sum.text())

            row_data.append(qty)

            # 5. Price
            w_price_container = self.trans_table.cellWidget(r, 5)
            price_val = 0
            if w_price_container:
                 spin = w_price_container.findChild(QSpinBox)
                 if spin:
                     price_val = spin.value()
            row_data.append(price_val)

            # 6. Sum
            row_data.append(str(sum_val))
            
            data.append(row_data)
        return data

    def collect_objects_data(self):
        """Scrapes data from items_table (objects)."""
        data = []
        # Headers should match sheet expectation
        headers = ["Item Name", "Base Price"]
        data.append(headers)
        
        # Iterating up to rowCount() - 1 because the last row is the "+" button
        for r in range(self.items_table.rowCount() - 1): 
            row_data = [] 
            
            # 0. Name
            w_name_container = self.items_table.cellWidget(r, 0)
            name_text = ""
            if w_name_container:
                # Prefer direct QLineEdit
                le = w_name_container.findChild(QLineEdit)
                if le:
                    name_text = le.text()
                else:
                    # Fallback: any widget with text() like QPushButton
                    btns = w_name_container.findChildren(QPushButton)
                    if btns:
                        name_text = btns[0].text()
            row_data.append(name_text)
                
            # 1. Price
            w_price_container = self.items_table.cellWidget(r, 1)
            price_val = 0
            if w_price_container:
                # Prefer NoScrollSpinBox or any QSpinBox/QDoubleSpinBox
                spin = w_price_container.findChild(NoScrollSpinBox)
                if not spin:
                    spin = w_price_container.findChild(QSpinBox)
                if not spin:
                    spin = w_price_container.findChild(QDoubleSpinBox)
                if not spin:
                    spin = w_price_container.findChild(NoScrollDoubleSpinBox)
                if spin:
                    try:
                        price_val = spin.value()
                    except Exception:
                        price_val = 0
                else:
                    # Fallback: check any child with value() or text()
                    for child in w_price_container.findChildren(QWidget):
                        try:
                            val_fn = getattr(child, 'value', None)
                            if callable(val_fn):
                                v = val_fn()
                                try:
                                    price_val = int(v)
                                    break
                                except Exception:
                                    continue
                            txt_fn = getattr(child, 'text', None)
                            if callable(txt_fn):
                                s = txt_fn()
                                if isinstance(s, str):
                                    s = s.replace('$', '').strip()
                                    if s:
                                        price_val = int(float(s))
                                        break
                        except Exception:
                            continue
                 
            row_data.append(price_val)
            data.append(row_data)
        return data

    def handle_imported_data(self, fetched):
        """Handle imported data from SyncWorker."""
        try:
            self._importing = True  # Set flag to avoid re-exporting during import

            # Apply objects sheet to items_table
            if 'objects' in fetched:
                self.items_table.setRowCount(0)  # Clear existing rows
                for row in fetched['objects'][1:]:  # Skip header row
                    self.add_new_item_row()
                    last_row = self.items_table.rowCount() - 2  # Last data row (before + row)
                    w_name_container = self.items_table.cellWidget(last_row, 0)
                    w_price_container = self.items_table.cellWidget(last_row, 1)
                    if w_name_container:
                        le = w_name_container.findChild(QLineEdit)
                        if le:
                            le.setText(row[0])
                    if w_price_container:
                        spin = w_price_container.findChild(QSpinBox)
                        if spin:
                            spin.setValue(int(row[1]))

            # Apply stats sheet to trans_table (if needed)
            # Example: self.apply_stats_data(fetched['stats'])

        except Exception as e:
            print(f"Failed to handle imported data: {e}")
        finally:
            self._importing = False

    def apply_imported_data(self, fetched):
        """Apply imported sheets to UI. fetched is a dict with sheet titles mapping to rows.
        We set _importing flag to avoid re-export while applying.
        """
        try:
            self._importing = True
            # Apply objects sheet to items_table (replace content)
            objs = fetched.get('objects')
            if objs:
                # First row may be headers
                rows = objs[1:] if len(objs) > 1 else []
                # If objects payload equals last exported objects, skip applying to avoid echo
                try:
                    objs_payload = objs
                    h_objs = hashlib.md5(repr(objs_payload).encode('utf-8')).hexdigest()
                    if h_objs == self._last_export_hash.get('objects'):
                        rows = []
                except Exception:
                    pass
                # Clear items_table and ensure '+' row exists
                self.items_table.setRowCount(0)
                self.add_item_plus_row()
                # Recreate rows (each add_new_item_row inserts before the + row)
                for r in rows:
                    # Expecting [Item Name, Base Price]
                    name = r[0] if len(r) > 0 else ""
                    price = 0
                    if len(r) > 1:
                        try:
                            price = int(float(r[1]))
                        except Exception:
                            price = 0
                    # Add a new item row and populate
                    self.add_new_item_row()
                    # The newly added row is before the + row
                    idx = self.items_table.rowCount() - 2
                    c_name = self.items_table.cellWidget(idx, 0)
                    if c_name:
                        le = c_name.findChild(QLineEdit)
                        if le:
                            le.setText(name)
                    c_price = self.items_table.cellWidget(idx, 1)
                    if c_price:
                        sp = c_price.findChild(QSpinBox)
                        if sp:
                            sp.setValue(price)

            stats = fetched.get('stats')
            if stats:
                # Rows after header
                rows = stats[1:] if len(stats) > 1 else []
                # If stats payload equals last exported stats, skip applying to avoid echo
                try:
                    stats_payload_full = stats
                    h_stats = hashlib.md5(repr(stats_payload_full).encode('utf-8')).hexdigest()
                    if h_stats == self._last_export_hash.get('stats'):
                        rows = []
                except Exception:
                    pass
                # Clear transactions and add + row
                self.trans_table.setRowCount(0)
                self.add_plus_row()

                def _normalize_type_to_income_flag(type_value: str, sum_value: str) -> bool:
                    """Return True for income(+), False for expense(-), handling messy imports."""
                    try:
                        t = str(type_value or "").strip().lower()
                        # common variants
                        if t in ("+", "плюс", "plus", "income", "in", "i", "доход", "приход"):
                            return True
                        if t in ("-", "минус", "minus", "expense", "out", "o", "расход"):
                            return False
                        # if type is empty/unknown, infer from sum sign
                        s = str(sum_value or "").strip()
                        if s.startswith('+'):
                            return True
                        if s.startswith('-'):
                            return False
                        # if still unknown, default to expense (matches UI default)
                        return False
                    except Exception:
                        return False

                for r in rows:
                    # Expecting header: [#, Date, Type, Item, Qty, Price, Sum]
                    date_txt = r[1] if len(r) > 1 else ""
                    type_txt = r[2] if len(r) > 2 else ""
                    item_txt = r[3] if len(r) > 3 else ""
                    try:
                        qty_val = int(float(r[4])) if len(r) > 4 and r[4] != "" else 0
                    except Exception:
                        qty_val = 0
                    try:
                        price_val = int(float(r[5])) if len(r) > 5 and r[5] != "" else 0
                    except Exception:
                        price_val = 0
                    sum_txt = r[6] if len(r) > 6 else "0"

                    # Robust income detection
                    is_income_flag = _normalize_type_to_income_flag(type_txt, sum_txt)

                    self.add_new_transaction_row()
                    idx = self.trans_table.rowCount() - 2

                    # Ensure type button exists and is styled (fix missing +/-)
                    self._ensure_type_button(idx, is_income_flag)
                    self._apply_type_state(idx, is_income_flag, force_update=True)

                    # Date button
                    c_date = self.trans_table.cellWidget(idx, 1)
                    if c_date:
                        btns = c_date.findChildren(QPushButton)
                        if btns:
                            btns[0].setText(date_txt)

                    # Item
                    c_item = self.trans_table.cellWidget(idx, 3)
                    if c_item:
                        le = c_item.findChild(QLineEdit)
                        if le:
                            le.setText(item_txt)

                    # Qty/Price
                    c_qty = self.trans_table.cellWidget(idx, 4)
                    if c_qty:
                        sp_list = c_qty.findChildren(QSpinBox)
                        sp = sp_list[0] if sp_list else None
                        if is_income_flag:
                            c_qty.setVisible(False)
                            if sp:
                                sp.setEnabled(False)
                        else:
                            c_qty.setVisible(True)
                            if sp:
                                sp.setEnabled(True)
                                sp.setValue(qty_val)

                    c_price = self.trans_table.cellWidget(idx, 5)
                    if c_price:
                        sp = c_price.findChild(QSpinBox)
                        if sp:
                            sp.setValue(price_val)

                    # Sum
                    item_sum = self.trans_table.item(idx, 6)
                    if item_sum:
                        try:
                            parsed = _parse_display_amount(str(sum_txt))
                        except Exception:
                            parsed = 0
                        if parsed == 0:
                            parsed = int(price_val) if is_income_flag else (-int(qty_val) * int(price_val))
                        item_sum.setText(_format_display_amount(parsed))
                        item_sum.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                        item_sum.setFlags(Qt.ItemFlag.ItemIsEnabled)

                    self._ensure_delete_widget_for_row(idx)

                # Force update all row type states to be safe
                for r in range(self.trans_table.rowCount() - 1):
                    c_type = self.trans_table.cellWidget(r, 2)
                    is_inc = False
                    if c_type:
                        btn = c_type.findChild(QPushButton)
                        if btn:
                            is_inc = bool(btn.property("is_income"))
                    self._apply_type_state(r, is_inc, force_update=True)

                # Recalculate sums and refresh combos after import
                try:
                    for r in range(self.trans_table.rowCount() - 1):
                        try:
                            self.recalc_row(r)
                        except Exception:
                            pass
                    self.update_row_numbers()
                    self.refresh_item_combos()
                except Exception:
                    pass

        except Exception as e:
            print(f"Failed to apply imported data: {e}")
        finally:
            self._importing = False

    def load_remote_sheets(self):
        """Fetch 'objects' and 'stats' sheets once and apply them to the UI on open.
        Uses apply_imported_data to reuse import-application logic.
        """
        fetched = {}
        try:
            objs = self.google_service.get_sheet_data('objects')
            stats = self.google_service.get_sheet_data('stats')
            if objs is not None:
                fetched['objects'] = objs
            if stats is not None:
                fetched['stats'] = stats

            if fetched:
                # Reuse existing UI-apply logic (runs in main thread)
                self.apply_imported_data(fetched)
        except Exception as e:
            print(f"Error loading remote sheets: {e}")

        return

    def _apply_type_state(self, row, is_income, force_update=False):
        """Applies the visual state for Income/Expense."""
        btn_type_container = self.trans_table.cellWidget(row, 2)
        if not btn_type_container:
            return
        btn = btn_type_container.findChild(QPushButton)
        if not btn:
            return

        # keep property synced
        try:
            btn.setProperty('is_income', bool(is_income))
        except Exception:
            pass

        # Hard reset style that might hide text after import/polish
        try:
            btn.setStyleSheet("")
        except Exception:
            pass

        btn.setFixedSize(30, 30)
        btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        if is_income:
            btn.setText("+")
            btn.setStyleSheet(
                "QPushButton { background-color: #4caf50; color: #ffffff; border-radius: 4px; font-weight: bold; font-size: 16px; border: none; padding: 0px; }"
            )
        else:
            btn.setText("-")
            btn.setStyleSheet(
                "QPushButton { background-color: #ff5555; color: #ffffff; border-radius: 4px; font-weight: bold; font-size: 16px; border: none; padding: 0px; }"
            )

        # Force immediate redraw (import case: widget exists but text not painted until interaction)
        try:
            btn.show()
            btn.setVisible(True)
            btn.repaint()
            btn.update()
        except Exception:
            pass

        # Handle visibility of Quantity depending on type
        w_qty = self.trans_table.cellWidget(row, 4)
        if w_qty:
            try:
                # show/hide whole widget cell
                if is_income:
                    w_qty.setVisible(False)
                    # reset qty to 0
                    spin = w_qty.findChild((QSpinBox, QDoubleSpinBox, NoScrollSpinBox))
                    if spin:
                        try:
                            spin.setValue(0)
                        except Exception:
                            pass
                else:
                    w_qty.setVisible(True)
            except Exception:
                pass

        # 5. Hide any popup if Income
        if is_income:
            try:
                if getattr(self, '_item_popup', None):
                    try:
                        self._item_popup.close()
                    except Exception:
                        pass
            except Exception:
                pass

        # Force repaint to ensure button text is shown correctly
        try:
            btn.update()
            btn.repaint()
        except Exception:
            pass

    def on_manual_import_click(self):
        """Handle manual import button click with queue check and delay."""
        btn = self.sender()
        if btn:
            btn.setEnabled(False)
            btn.setText("Ждите...")

        # Function to proceed with import after waiting
        def proceed_import():
            QTimer.singleShot(1500, self.start_import_process)
            if btn:
                btn.setEnabled(True)
                btn.setText("Импорт")

        # Check sync queue
        if not self.sync_queue:
            proceed_import()
        else:
            # If queue not empty, we need to wait. 
            self._wait_timer = QTimer(self)
            self._wait_timer.setInterval(100)
            
            def check_queue():
                if not self.sync_queue:
                    self._wait_timer.stop()
                    proceed_import()
            
            self._wait_timer.timeout.connect(check_queue)
            self._wait_timer.start()

    def start_import_process(self):
        """Starts the actual import worker."""
        if getattr(self, '_importing', False):
            return
        self._importing = True
        self.setCursor(Qt.CursorShape.WaitCursor)
        self._start_import_with_overlay()
        # reset flags when overlay finishes (apply_imported_data sets _importing False)

    def _start_import_with_overlay(self):
        # show overlay and disable interactions
        try:
            self._loading_overlay.showOverlay("Загрузка...")
        except Exception:
            pass
        try:
            self.trans_table.setEnabled(False)
            self.items_table.setEnabled(False)
        except Exception:
            pass

        self._load_thread = GoogleSheetLoadThread(self.google_service, self.spreadsheet_id, parent=self)
        self._load_thread.loaded.connect(self._on_initial_loaded)
        self._load_thread.error.connect(self._on_initial_load_error)
        self._load_thread.start()

    def _on_initial_loaded(self, fetched: dict):
        try:
            self.apply_imported_data(fetched)
        finally:
            self._finish_overlay()

    def _on_initial_load_error(self, msg: str):
        try:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить таблицы: {msg}")
        except Exception:
            pass
        self._finish_overlay()

    def _finish_overlay(self):
        try:
            self.trans_table.setEnabled(True)
            self.items_table.setEnabled(True)
        except Exception:
            pass
        try:
            self._loading_overlay.hideOverlay()
        except Exception:
            pass

    def update_totals(self):
        """Recompute totals for header labels: income, expense, balance."""
        income_total = 0
        expense_total = 0
        for r in range(self.trans_table.rowCount() - 1):
            cont_type = self.trans_table.cellWidget(r, 2)
            is_inc = False
            if cont_type:
                btn = cont_type.findChild(QPushButton)
                if btn:
                    is_inc = bool(btn.property("is_income"))
            sum_item = self.trans_table.item(r, 6)
            if not sum_item:
                continue
            val = _parse_display_amount(sum_item.text())
            if is_inc:
                income_total += val
            else:
                expense_total += val  # expense values are negative by design

        # expense_total is negative; for display we keep negative
        balance = income_total + expense_total

        # Set labels with formatted display (income should show '+' prefix)
        self.lbl_income.setText(f"Доходы: {_format_display_amount(income_total)}")
        self.lbl_expense.setText(f"Расходы: {_format_display_amount(expense_total)}")
        self.lbl_balance.setText(f"Баланс: {_format_display_amount(balance)}")

    def _items_map(self):
        """Return ordered dict of item name -> base price from items_table."""
        from collections import OrderedDict
        m = OrderedDict()
        for r in range(self.items_table.rowCount() - 1):
            c_name = self.items_table.cellWidget(r, 0)
            name = ""
            if c_name:
                le = c_name.findChild(QLineEdit)
                if le:
                    name = le.text().strip()
            if not name:
                continue
            c_price = self.items_table.cellWidget(r, 1)
            price_val = 0
            if c_price:
                spin = c_price.findChild((NoScrollSpinBox, QSpinBox, QDoubleSpinBox))
                if spin:
                    try:
                        price_val = int(spin.value())
                    except Exception:
                        price_val = 0
            m[name] = price_val
        return m

    def refresh_item_combos(self):
        """Refresh all item combo lists in transactions to reflect current items_table.
        Also update the shared completer model so QLineEdit suggestions work.
        """
        items = list(self._items_map().keys())
        # update completer model
        try:
            if getattr(self, '_items_completer_model', None):
                self._items_completer_model.setStringList(items)
        except Exception:
            pass

        for r in range(self.trans_table.rowCount() - 1):
            w_item = self.trans_table.cellWidget(r, 3)
            if not w_item:
                continue
            combo = w_item.findChild(QComboBox)
            if not combo:
                # If there is a plain QLineEdit, ensure its completer reflects items
                le = w_item.findChild(QLineEdit)
                if le and getattr(self, '_items_completer', None):
                    try:
                        le.setCompleter(self._items_completer)
                    except Exception:
                        pass
                continue
            cur = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(items)
            combo.setCurrentText(cur)
            combo.blockSignals(False)

    def on_item_selected(self, row, text):
        """Handle selection from item list: set base price into price field."""
        # ensure row exists
        try:
            # If this row is income, ignore
            cont_type = self.trans_table.cellWidget(row, 2)
            if cont_type:
                btn = cont_type.findChild(QPushButton)
                if btn and btn.property("is_income"):
                    return

            items = self._items_map()
            if text in items:
                price = items[text]
                c_price = self.trans_table.cellWidget(row, 5)
                if c_price:
                    spin = c_price.findChild((QSpinBox, NoScrollSpinBox, QDoubleSpinBox))
                    if spin:
                        spin.setValue(int(price))
                # recalc row after setting price
                self.recalc_row(row)
        except Exception:
            pass

    def on_item_text_changed(self, row, text):
        """If text matches an item name, auto-fill price. Show custom popup."""
        try:
            cont_type = self.trans_table.cellWidget(row, 2)
            if cont_type:
                btn = cont_type.findChild(QPushButton)
                if btn and btn.property("is_income"):
                    return

            # refresh items each time
            items = list(self._items_map().keys())
            w_item = self.trans_table.cellWidget(row, 3)
            if not w_item:
                return
            le = w_item.findChild(QLineEdit)
            if not le:
                return

            # exact match
            if text in items:
                self.on_item_selected(row, text)
                if getattr(self, "_item_popup", None):
                    try:
                        self._item_popup.close()
                    except Exception:
                        pass
                    self._item_popup = None
                return

            # close stale popup
            try:
                if getattr(self, "_item_popup", None):
                    try:
                        self._item_popup.close()
                    except Exception:
                        pass
                    self._item_popup = None
            except Exception:
                pass

            if not items:
                return

            # show popup immediately (even for empty text)
            self._item_popup = ItemPickerPopup(items, parent=self, on_select=lambda t, r=row: self._on_popup_pick(r, w_item, t))
            self._item_popup.filter(text or "")
            # suppress global auto-close while popup is being shown
            try:
                self._suppress_global_close_until = time.time() + 0.25
            except Exception:
                pass
            self._item_popup.show_at_widget(le)
        except Exception:
            pass

    def _on_popup_pick(self, row, widget_container, text):
        le = widget_container.findChild(QLineEdit)
        if le:
            le.setText(text)
            self.on_item_selected(row, text)
            # Remove focus from editor to prevent immediate popup reopen
            try:
                le.clearFocus()
                # Move focus to the table so keyboard focus isn't in the editor
                try:
                    self.trans_table.setFocus()
                except Exception:
                    self.setFocus()
            except Exception:
                pass
        if getattr(self, "_item_popup", None):
            try:
                self._item_popup.close()
            except Exception:
                pass
            self._item_popup = None
        # Suppress immediate reopen for a short moment
        try:
            self._suppress_popup = True
            QTimer.singleShot(250, lambda: setattr(self, '_suppress_popup', False))
            # also prevent global filter from thinking this was an outside click
            try:
                self._suppress_global_close_until = time.time() + 0.25
            except Exception:
                pass
        except Exception:
            pass

    def _on_completer_activated(self, text: str):
        """Handle completer activation: set active editor text, apply price if matches, and hide popup."""
        try:
            le = getattr(self, '_active_item_editor', None)
            if isinstance(le, QLineEdit):
                # Temporarily suppress popup reopening
                try:
                    self._suppress_popup = True
                    QTimer.singleShot(250, lambda: setattr(self, '_suppress_popup', False))
                except Exception:
                    pass

                # Apply text to editor
                try:
                    le.setText(text)
                    # Trigger item selected logic: use its trans_row property
                    row_prop = le.property('trans_row')
                    row = int(row_prop) if row_prop is not None else None
                    if row is not None:
                        try:
                            self.on_item_selected(row, text)
                        except Exception:
                            pass
                except Exception:
                    pass

                # Hide completer popup
                try:
                    comp = getattr(self, '_items_completer', None)
                    if comp:
                        comp.popup().hide()
                except Exception:
                    pass

                # Ensure editor loses focus so eventFilter doesn't re-show popup
                try:
                    le.clearFocus()
                    try:
                        self.trans_table.setFocus()
                    except Exception:
                        self.setFocus()
                except Exception:
                    pass

                # also suppress global close detection for the immediate mouse event
                try:
                    self._suppress_global_close_until = time.time() + 0.25
                except Exception:
                    pass
        except Exception:
            pass

    def eventFilter(self, source, event):
        # First, existing eventFilter logic used for QLineEdit interactions
        try:
            # Do not trigger popup when suppressed (prevent immediate reopen after selection)
            if getattr(self, '_suppress_popup', False):
                return super().eventFilter(source, event)

            if isinstance(source, QLineEdit):
                row_prop = source.property('trans_row')
                row = int(row_prop) if row_prop is not None else None
                if row is not None:
                    if event.type() in (QEvent.Type.FocusIn, QEvent.Type.MouseButtonPress):
                        QTimer.singleShot(0, lambda r=row, le=source: self._on_item_editor_interaction(r, le))
                    elif event.type() == QEvent.Type.KeyPress:
                        QTimer.singleShot(0, lambda r=row, le=source: self._on_item_editor_interaction(r, le))
        except Exception:
            pass

        # Global filter: close completer popup or custom popup when clicking outside
        try:
            if event.type() == QEvent.Type.MouseButtonPress:
                # If recent popup show action requests suppression, skip closing here
                try:
                    if getattr(self, '_suppress_global_close_until', 0) > time.time():
                        return super().eventFilter(source, event)
                except Exception:
                    pass

                # If there's a completer popup shown, and click is outside it and not on an editor, close it
                try:
                    comp = getattr(self, '_items_completer', None)
                    if comp:
                        popup = comp.popup()
                        if popup and popup.isVisible():
                            gw = QApplication.widgetAt(event.globalPosition().toPoint()) if hasattr(QApplication, 'widgetAt') else None
                            if gw is not None and (popup.isAncestorOf(gw) or gw is popup):
                                pass
                            else:
                                try:
                                    popup.hide()
                                except Exception:
                                    try:
                                        popup.close()
                                    except Exception:
                                        pass
                except Exception:
                    pass

                # Close custom item popup if click outside
                try:
                    ip = getattr(self, '_item_popup', None)
                    if ip and isinstance(ip, QFrame) and ip.isVisible():
                        gw = QApplication.widgetAt(event.globalPosition().toPoint()) if hasattr(QApplication, 'widgetAt') else None
                        if gw is not None and (ip.isAncestorOf(gw) or gw is ip):
                            pass
                        else:
                            try:
                                ip.close()
                            except Exception:
                                pass
                except Exception:
                    pass

            # Additional: if window deactivates or focus is lost, close popups to handle Alt+Tab cases
            if event.type() in (QEvent.Type.WindowDeactivate, QEvent.Type.FocusOut):
                try:
                    comp = getattr(self, '_items_completer', None)
                    if comp:
                        try:
                            comp.popup().hide()
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    ip = getattr(self, '_item_popup', None)
                    if ip and isinstance(ip, QFrame):
                        try:
                            ip.close()
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        return super().eventFilter(source, event)

    def _ensure_delete_widget_for_row(self, row):
        """Ensure the delete (red square) widget exists for transaction row `row`.
        This is used after import to recreate any missing delete controls.
        """
        try:
            cont = self.trans_table.cellWidget(row, 7)
            if cont is not None:
                return
        except Exception:
            cont = None

        # Create delete button container similar to add_new_transaction_row
        del_btn = QPushButton()
        del_btn.setText("\ud83e\uddf9")
        del_btn.setFixedSize(30, 30)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("background: transparent; border: none; font-size: 16px; color: white;")
        del_btn.clicked.connect(lambda: self.delete_row_by_widget(del_btn))

        container_del = QFrame()
        container_del.setFrameShape(QFrame.Shape.Box)
        container_del.setStyleSheet("""
            QFrame {
                border: 2px solid #ff5555; 
                border-radius: 4px;
                background-color: #ff5555;
            }
            QFrame:hover {
                background-color: #ff7777; /* Lighter red on hover */
                border: 2px solid #ff7777;
            }
        """)
        container_del.setLayout(QVBoxLayout())
        container_del.layout().setContentsMargins(0, 0, 0, 0)
        container_del.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
        del_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        container_del.layout().addWidget(del_btn)
        try:
            self.trans_table.setCellWidget(row, 7, container_del)
        except Exception:
            pass

    def resizeEvent(self, event):
        try:
            if getattr(self, '_loading_overlay', None):
                self._loading_overlay._sync_geometry()
        except Exception:
            pass
        return super().resizeEvent(event)

    def _auto_import_on_open(self):
        if self._auto_loaded_once:
            return
        self._auto_loaded_once = True
        self._start_import_with_overlay()