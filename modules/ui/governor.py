from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDateEdit, QComboBox, 
                             QDoubleSpinBox, QSpinBox, QMessageBox, QGroupBox, QSizePolicy,
                             QCalendarWidget, QToolButton, QMenu, QAbstractSpinBox, QStyle, QApplication, QStyleOptionComboBox, QStyleOptionSpinBox, QWidgetAction, QLineEdit, QScrollArea, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QDate, QEvent, QLocale, QRect, QPointF, QPoint, QSize, QTimer, QThread, pyqtSignal, QMutex
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QMouseEvent, QKeyEvent
import hashlib
import time
from modules.core.google_service import GoogleService
from modules.core.utils import get_resource_path
from modules.core.google_sheet_worker import GoogleSheetLoadThread, GoogleSheetSyncThread
from modules.ui.loading_overlay import LoadingOverlay
from modules.ui.scrollbar_styles import get_scrollbar_qss
from modules.ui.widgets.custom_controls import (CustomCalendarWidget, DateEditClickable, DateRangeEdit, 
                             NoScrollSpinBox, NoScrollDoubleSpinBox, NoScrollComboBox)
from modules.ui.widgets.item_picker_popup import ItemPickerPopup
from modules.ui.widgets.suggestions_popup import SuggestionsPopup
from modules.ui.widgets.simple_suggestions import SimpleSuggestionsPopup
from modules.ui.widgets.table_helpers import (create_centered_spinbox, create_delete_button, 
                             create_date_button, create_plus_button)

class RemoteLoadWorker(QThread):
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

def _format_display_amount(value: int, show_sign: bool = True) -> str:
    """Format integer amount for display with dot thousand separators and trailing $; include sign for income/expense when requested.
    If show_sign is False, positive values will not receive a leading '+', negative values still show '-'.
    """
    sign = ('+' if value > 0 and show_sign else ('-' if value < 0 else ''))
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
            # Use smaller sleep chunks to detect stop signal faster
            for _ in range(180): 
                if not self._is_running:
                    return
                time.sleep(1)

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
        # Do not wait for thread to finish if it is sleeping
        # instead, self.wait() can cause hang if we don't break the loop
        # The loop modification above ensures quick exit.
        if self.isRunning():
            self.wait(2000) # Wait at most 2 seconds
            if self.isRunning():
                self.terminate() # Force terminate if stuck

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
        
        # Avoid horizontal scrollbar and allow table to expand horizontally within the layout
        try:
            self.items_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.items_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        except Exception:
            pass

        # Init items table with plus row
        self.init_items_table()

        # Create minimal suggestions popup early so any callbacks during import/worker
        # that call _show_suggestions_for_editor find the popup initialized.
        try:
            # During initialization we still want to suppress showing suggestions until
            # imports/initialization finish, but create the popup instance early so
            # any code paths that reference it won't trigger lazy display at (0,0).
            self._suspend_suggestions = True
            self._suggestions_popup = SimpleSuggestionsPopup(self)
            try:
                self._suggestions_popup.suggestion_selected.connect(self._on_suggestion_selected)
            except Exception:
                pass
            try:
                self._suggestions_popup.suggestion_closed.connect(self._on_suggestions_closed)
            except Exception:
                pass
            # timestamp until which reopening is suppressed
            self._suppress_reopen_until = 0
        except Exception as e:
            try:
                print(f"[Governor] Failed to create suggestions popup during init: {e}")
            except Exception:
                pass
            self._suggestions_popup = None

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

        # suggestions popup was created earlier; log current state
        try:
            print("[Governor] suggestions_popup state after init:", getattr(self, '_suggestions_popup', None))
        except Exception:
            pass

        # Track which row editor triggered the popup
        self._popup_active_editor = None

    def closeEvent(self, event):
        if self.sync_worker:
            self.sync_worker.stop()
        super().closeEvent(event)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)        
        header_layout = QHBoxLayout()
        title_label = QLabel("GOVERNOR\nCABINET")
        title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #4aa3df;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Create three individual rounded metric frames and add them directly to header
        def _make_small_metric(text):
            f = QFrame()
            f.setStyleSheet("background-color: #333333; border: 1px solid #404040; border-radius: 8px; padding: 10px;")
            f.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
            lb = QLabel(text)
            # Ensure label has no background/border so only the outer frame is visible
            lb.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background: transparent; border: none;")
            lb.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            ly = QVBoxLayout(f)
            ly.setContentsMargins(10, 6, 10, 6)
            ly.addWidget(lb)
            return f, lb

        inc_frame, self.lbl_income = _make_small_metric("Доходы: 0")
        exp_frame, self.lbl_expense = _make_small_metric("Расходы: 0")
        bal_frame, self.lbl_balance = _make_small_metric("Баланс: 0")

        # Add them to header directly (no outer rounded box)
        header_layout.addWidget(inc_frame)
        header_layout.addWidget(exp_frame)
        header_layout.addWidget(bal_frame)

        header_layout.addStretch()

        # Period control: single styled button ("Фильтр по дате") which opens DateRangeEdit popup
        self.period_range = DateRangeEdit()
        # Default to current month range
        try:
            cur = QDate.currentDate()
            start = QDate(cur.year(), cur.month(), 1)
            end = start.addMonths(1).addDays(-1)
            self.period_range.setRange(start, end)
        except Exception:
            pass

        # Create a primary-style push button for filtering (same style as import)
        try:
            btn_text = self.period_range._edit.text() if hasattr(self.period_range, '_edit') else 'Фильтр по дате'
        except Exception:
            btn_text = 'Фильтр по дате'
        self.period_button = QPushButton(btn_text)
        # Apply same style as import/launcher buttons
        try:
            self.period_button.setStyleSheet("""
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
        except Exception:
            pass
        self.period_button.setCursor(Qt.CursorShape.PointingHandCursor)
        try:
            # Anchor the period_range popup to the header button so it opens next to it
            self.period_button.clicked.connect(lambda: self.period_range.showPopup(anchor_widget=self.period_button))
        except Exception:
            pass

        # Update button text when range changes and refresh stats/hiding; also trigger sort
        try:
            def _on_range_changed(s, e):
                try:
                    txt = self.period_range._edit.text() if hasattr(self.period_range, '_edit') else ''
                    # keep button label fixed to 'Фильтр по дате' but show selected range in tooltip
                    self.period_button.setToolTip(txt or '')
                except Exception:
                    pass
                try:
                    # Update the stats table and re-run transactions sorting/filtering
                    self.update_stats_table()
                    try:
                        self._sort_transactions_by_date()
                    except Exception:
                        pass
                except Exception:
                    pass
            self.period_range.range_changed.connect(_on_range_changed)
        except Exception:
            pass

        period_layout = QHBoxLayout()
        period_layout.addWidget(self.period_button)
        # The menu provides sort action, no separate sort button needed now

        header_layout.addLayout(period_layout)
        header_layout.addSpacing(20)

        # Buttons container
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(5)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        btn_back = QPushButton("В лаунчер")
        # Apply same style as Import button
        btn_back.setStyleSheet("""
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

        # Export button: same style as Import/launcher buttons, placed under Import
        btn_export = QPushButton("Экспорт")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setStyleSheet("""
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
        btn_export.clicked.connect(lambda: self.export_transactions())

        buttons_layout.addWidget(btn_export)

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

        # Column 3 (Предмет) should never be truncated too small: give it a minimum
        # width of 150 px and allow it to take remaining space (Stretch). Price and
        # Sum columns are reduced so the name column can expand when needed.
        self.trans_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        # Ensure an initial/minimum width so short windows don't truncate the name
        try:
            self.trans_table.setColumnWidth(3, 150)
        except Exception:
            pass
 
        self.trans_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        # Qty column slightly narrower
        self.trans_table.setColumnWidth(4, 80)
        
        # Price and Sum columns: make narrower so they yield space to the item name
        self.trans_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(5, 120)
        
        self.trans_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(6, 120)

        self.trans_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(7, 50)
        
        self.trans_table.setShowGrid(False) 
        self.trans_table.verticalHeader().setVisible(False)
        self.trans_table.verticalHeader().setDefaultSectionSize(45)
        self.trans_table.horizontalHeader().setDefaultSectionSize(40)
        self.trans_table.horizontalHeader().setMinimumSectionSize(40) 
        # Avoid horizontal scrollbar on transactions table; let columns resize instead
        try:
            self.trans_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.trans_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        except Exception:
            pass
         
        grp_trans_layout.addWidget(self.trans_table)
        
        self.init_trans_table()

        left_layout.addWidget(grp_trans)
        
        content_layout.addLayout(left_layout, stretch=3)

        right_layout = QVBoxLayout()
        
        right_layout.setStretch(0, 3)
        right_layout.setContentsMargins(0, 0, 0, 0)

        grp_items = QGroupBox("Управление предметами")
        grp_items_layout = QVBoxLayout(grp_items)
        
        grp_items_layout.addWidget(self.items_table)
        
        right_layout.addWidget(grp_items, stretch=1)
        
        grp_stats = QGroupBox("Общая статистика по предметам")
        grp_stats_layout = QVBoxLayout(grp_stats)

        # Search input above the stats table
        self.stats_search = QLineEdit()
        self.stats_search.setPlaceholderText("Поиск по предмету")
        self.stats_search.setStyleSheet("""
            QLineEdit { background-color: white; color: black; border: 1px solid #555555; border-radius: 4px; padding: 4px; }
        """)
        self.stats_search.setMaximumHeight(30)
        self.stats_search.textChanged.connect(lambda txt: self.update_stats_table(txt))
        grp_stats_layout.addWidget(self.stats_search)

        # Stats table: columns - Item, Qty, Avg price per unit, Total sum
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(4)
        self.stats_table.setHorizontalHeaderLabels(["Предмет", "Кол-во", "За шт.", "Сумма"]) 
        # Use Stretch resize mode so columns expand to fill available width and
        # do not cause horizontal scroll. Set sensible minimum widths so small
        # windows don't make columns too narrow.
        for ci in range(4):
            try:
                self.stats_table.horizontalHeader().setSectionResizeMode(ci, QHeaderView.ResizeMode.Stretch)
            except Exception:
                pass
        # Minimum widths (smaller to avoid overflow on narrow windows)
        try:
            self.stats_table.setColumnWidth(0, 100)  # Предмет
            self.stats_table.setColumnWidth(1, 60)   # Кол-во
            self.stats_table.setColumnWidth(2, 90)   # За шт.
            self.stats_table.setColumnWidth(3, 90)   # Сумма
        except Exception:
            pass

        self.stats_table.setShowGrid(False)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.verticalHeader().setDefaultSectionSize(40)
        self.stats_table.horizontalHeader().setDefaultSectionSize(40)
        self.stats_table.horizontalHeader().setMinimumSectionSize(40)
        # Avoid horizontal scrollbar and allow table to expand horizontally within the layout
        try:
            self.stats_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.stats_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            # also ensure items table doesn't force extra width
            self.items_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.items_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        except Exception:
            pass

        grp_stats_layout.addWidget(self.stats_table)

        # Adjust stats table columns to fill available space proportionally
        try:
            self._adjust_stats_table_column_widths()
        except Exception:
            pass

        right_layout.addWidget(grp_stats, stretch=1)
        
        # Right pane ~40% (use 2 in the 3:2 stretch ratio)
        content_layout.addLayout(right_layout, stretch=2)
        
        main_layout.addLayout(content_layout)

        # Schedule a deferred adjustment after the UI is shown to ensure
        # table viewports have valid sizes — this prevents initial overflow
        # where columns are sized before layout completes.
        try:
            QTimer.singleShot(0, lambda: self._adjust_stats_table_column_widths())
        except Exception:
            pass

    def return_to_launcher(self):
        if self.sync_worker:
            self.sync_worker.stop()
        self.close()
        if self.parent_launcher:
            self.parent_launcher.show()
        else:
            from modules.ui.launcher import LauncherWindow
            self.launcher = LauncherWindow(self.user_data)
            self.launcher.show()

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
        
        btn_add = create_plus_button(self.add_new_transaction_row)
        
        self.trans_table.setSpan(row_idx, 0, 1, 8)
        self.trans_table.setCellWidget(row_idx, 0, btn_add)

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

        # Use helper for date button
        container_date = create_date_button(QDate.currentDate().toString("dd.MM.yyyy"), self.show_calendar_popup)
        self.trans_table.setCellWidget(row, 1, container_date)

        # Type button (starts as Expense '-')
        type_btn = QPushButton("-")
        type_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        type_btn.setProperty("is_income", False)
        # slightly larger to comfortably show +/-, with bold font
        type_btn.setFixedSize(28, 28)
        type_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        # Default style for Expense
        type_btn.setStyleSheet("""
            QPushButton { 
                background-color: #ff5555; 
                color: #ffffff; 
                border-radius: 4px; 
                font-weight: bold; 
                font-size: 16px; 
                border: none; 
                padding: 0px; 
            }
        """)
        
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
        
        container_item = QWidget()
        layout_item = QHBoxLayout(container_item)
        # Reduce vertical margins to avoid pushing the edit below its cell area
        layout_item.setContentsMargins(4, 0, 4, 0)
        layout_item.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        name_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_item.addWidget(name_edit)
        self.trans_table.setCellWidget(row, 3, container_item)

        # Track active editor and ensure popup shows on request
        try:
            name_edit.setProperty('trans_row', int(row))
            self._active_item_editor = name_edit
        except Exception:
            pass

        # Use event filter or signal to trigger popup
        try:
            name_edit.textEdited.connect(lambda txt, r=row, le=name_edit: self._on_item_editor_interaction(r, le))
        except Exception:
            pass
        
        # Override focusInEvent on instance
        try:
            old_focus = name_edit.focusInEvent
        except Exception:
            old_focus = None
            
        def _focus_in_mk2(ev, le=name_edit, r=row):
            try:
                if callable(old_focus): old_focus(ev)
                self._on_item_editor_interaction(r, le)
            except Exception:
                pass
        name_edit.focusInEvent = _focus_in_mk2

        # Removing installation of the Governor as an event filter on the line edit.
        # The global popup installs its own app-level filter; installing the window
        # as an event filter on each editor caused focus/key handling oddities
        # (prevented paste/focus-out in some configurations). Do not install here.
        # name_edit.installEventFilter(self)
        name_edit.textChanged.connect(lambda txt, r=row: self.on_item_text_changed(r, txt))
        # Adjust name column width when user types longer names so the name column
        # grows (at expense of price/sum) but keeps a sensible minimum.
        try:
            name_edit.textChanged.connect(lambda txt, le=name_edit: self._adjust_name_column_for_editor(le))
        except Exception:
            pass
        
        # Use helpers for Qty and Price spinboxes
        qty_block = create_centered_spinbox(value=0, min_val=-999999, max_val=999999, on_change=lambda: self.recalc_row(row))
        self.trans_table.setCellWidget(row, 4, qty_block)

        container_price = create_centered_spinbox(value=0, min_val=-1000000000, max_val=1000000000, on_change=lambda: self.recalc_row(row))
        self.trans_table.setCellWidget(row, 5, container_price)

        sum_item = QTableWidgetItem("0")
        sum_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        sum_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        sum_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.trans_table.setItem(row, 6, sum_item)

        type_btn.clicked.connect(lambda checked, r=row, btn=type_btn: self.toggle_type(r, btn))

        # Use helper for delete button
        container_del = create_delete_button(lambda btn: self.delete_row_by_widget(btn))
        
        # Ensure button takes up full space and passes clicks if needed, 
        # but typically button handles click. We want hover on container.
        # So we make button transparent and layout stretch.
        # Delete button container
        self.trans_table.setCellWidget(row, 7, container_del)

        # Apply initial type state to ensure correct qty visibility
        self._apply_type_state(row, False)

        self.update_row_numbers()
        self.recalc_row(row)
        # Trigger sync on change
        self.sync_all_data()
        self.update_stats_table()

        # Re-enable updates
        try:
            self.trans_table.setUpdatesEnabled(True)
            self.trans_table.viewport().update()
        except Exception:
            pass

    def _on_item_editor_interaction(self, row, le):
        """Called on focus/click/typing to show suggestions immediately (minimal).
        Uses a short debounce so rapid focus/text events don't cause flicker
        when the popup is repeatedly shown/hidden.
        """
        try:
            # Check suppression window to avoid immediate reopen after close
            if time.time() < getattr(self, '_suppress_reopen_until', 0):
                try:
                    print("[Governor] Suppression active, skipping popup show")
                except Exception:
                    pass
                return

            # If popup already visible for this editor and query unchanged, skip
            try:
                popup_obj = getattr(self, '_suggestions_popup', None)
                if popup_obj is not None:
                    try:
                        if popup_obj.isVisible() and getattr(popup_obj, '_target_widget', None) == le:
                            # If text hasn't changed from last shown query, don't reshow
                            last_q = getattr(self, '_last_suggestions_query', None)
                            cur_q = (le.text() or '').strip().lower()
                            if last_q == cur_q:
                                try:
                                    print('[Governor] popup already visible for editor with same query -> skip scheduling')
                                except Exception:
                                    pass
                                return
                    except Exception:
                        pass
            except Exception:
                pass

            # Remember active editor so selection callback can reference it
            self._popup_active_editor = le

            # Store pending parameters for debounced processing
            try:
                self._pending_suggestion_le = le
                self._pending_suggestion_text = le.text()
            except Exception:
                self._pending_suggestion_le = le
                self._pending_suggestion_text = ''

            # Lazily create debounce timer
            try:
                if not hasattr(self, '_suggestions_debounce_timer') or self._suggestions_debounce_timer is None:
                    self._suggestions_debounce_timer = QTimer(self)
                    self._suggestions_debounce_timer.setSingleShot(True)
                    self._suggestions_debounce_timer.timeout.connect(self._process_pending_suggestions)
            except Exception:
                self._suggestions_debounce_timer = None

            # Start/Restart debounce (short delay to avoid flicker)
            try:
                if getattr(self, '_suggestions_debounce_timer', None):
                    self._suggestions_debounce_timer.start(80)  # 80 ms debounce
                else:
                    # Fallback to immediate call
                    self._process_pending_suggestions()
            except Exception:
                pass
        except Exception:
            pass

    def _process_pending_suggestions(self):
        """Called by debounce timer to show suggestions for the latest pending editor/text."""
        try:
            # Check suppression window to avoid immediate reopen after close
            if time.time() < getattr(self, '_suppress_reopen_until', 0):
                try:
                    print("[Governor] Suppression active, skipping popup show")
                except Exception:
                    pass
                return

            le = getattr(self, '_pending_suggestion_le', None)
            text = getattr(self, '_pending_suggestion_text', '')
            if le is not None:
                try:
                    self._show_suggestions_for_editor(le, text)
                except Exception as e:
                    print(f"[Governor] _process_pending_suggestions error: {e}")
        except Exception as e:
            print(f"[Governor] _process_pending_suggestions outer error: {e}")
        
    def _show_suggestions_for_editor(self, le, text):
        """Minimal: get items from right table, filter by text and show popup.
        Closes popup when there are no suggestions or editor is None.
        Added readiness checks and deferred-show to avoid popup appearing at (0,0).
        """
        try:
            # Do not show suggestions while suspended (during init/import)
            if getattr(self, '_suspend_suggestions', False):
                try:
                    print('[Governor][PopupFix] suggestions suspended, skip show')
                except Exception:
                    pass
                return

            # Also avoid showing while performing a full import/apply
            if getattr(self, '_importing', False):
                try:
                    print('[Governor][PopupFix] importing in progress, skip show')
                except Exception:
                    pass
                return

            try:
                print(f"[Governor] _show_suggestions_for_editor called. editor={le} text='{text}'")
            except Exception:
                pass

            # Throttle repeated calls per-editor to avoid tight-loop show/hide which
            # can prevent the editor from receiving key events.
            try:
                if not hasattr(self, '_suggestions_last_called'):
                    self._suggestions_last_called = {}
                eid = id(le) if le is not None else None
                last = self._suggestions_last_called.get(eid)
                now = time.time()
                if last is not None and (now - last) < 0.05:
                    try:
                        print(f"[Governor] Throttling _show_suggestions_for_editor for editor={le}")
                    except Exception:
                        pass
                    return
                try:
                    self._suggestions_last_called[eid] = now
                except Exception:
                    pass
            except Exception:
                pass

            # Acquire (or lazily create) the popup instance
            popup_obj = getattr(self, '_suggestions_popup', None)
            try:
                print(f"[Governor] popup_obj repr={repr(popup_obj)} type={type(popup_obj)} id={(id(popup_obj) if popup_obj is not None else None)}")
            except Exception:
                pass

            # If popup not yet created, abort (do not attempt lazy creation here)
            if popup_obj is None:
                try:
                    print('[Governor] suggestions popup not initialized -> abort show')
                except Exception:
                    pass
                return

            if le is None or popup_obj is None:
                try:
                    print("[Governor] No editor or suggestions_popup not initialized -> hide and return")
                except Exception:
                    pass
                except Exception as e:
                    try:
                        print(f"[Governor] Failed lazy create popup: {e}")
                    except Exception:
                        pass
                    return

            if le is None or popup_obj is None:
                try:
                    print("[Governor] No editor or suggestions_popup not initialized -> hide and return")
                except Exception:
                    pass
                if popup_obj is not None:
                    try:
                        popup_obj.hide()
                    except Exception:
                        pass
                return

            # If editor or its top-level window are not yet visible/ready, defer show
            try:
                widget_ready = False
                if hasattr(le, 'isVisible') and le.isVisible():
                    wnd = le.window()
                    if wnd is not None and hasattr(wnd, 'isVisible') and wnd.isVisible():
                        widget_ready = True
                if not widget_ready:
                    # Defer and allow layout/window to finish so mapToGlobal returns sane coords
                    try:
                        print('[Governor][PopupFix] editor/window not ready - deferring popup show')
                    except Exception:
                        pass
                    QTimer.singleShot(120, lambda: self._process_pending_suggestions())
                    return
            except Exception:
                pass

            # Source suggestions from items_table (right-hand table)
            try:
                items_map = self._items_map()
                items = list(items_map.keys())
                print(f"[Governor] items_map read, total items={len(items)}")
            except Exception as e:
                print(f"[Governor] Failed to read items_map: {e}")
                items = []

            if not items:
                try:
                    print("[Governor] No items available -> hiding popup")
                except Exception:
                    pass
                try:
                    popup_obj.hide()
                except Exception:
                    pass
                return

            query = (text or '').strip().lower()
            if not query:
                filtered = items.copy()
            else:
                filtered = [it for it in items if query in it.lower()]

            try:
                print(f"[Governor] filter query='{query}' -> {len(filtered)} matches")
            except Exception:
                pass

            if filtered:
                try:
                    # Avoid re-showing repeatedly for same editor/query which can cause flicker
                    last_q = getattr(self, '_last_suggestions_query', None)
                    last_editor_id = getattr(self, '_last_suggestions_editor_id', None)
                    cur_editor_id = id(le)
                    is_vis = False
                    try:
                        is_vis = popup_obj.isVisible()
                    except Exception:
                        is_vis = False

                    if is_vis and last_q == query and last_editor_id == cur_editor_id:
                        try:
                            print('[Governor] Popup already visible for same editor/query -> skip show')
                        except Exception:
                            pass
                    else:
                        # Record state before showing to prevent races that cause immediate re-show
                        try:
                            self._last_suggestions_query = query
                            self._last_suggestions_editor_id = cur_editor_id
                            self._last_suggestions_shown_at = time.time()
                        except Exception:
                            pass

                        # Try to position popup near editor BEFORE showing to avoid (0,0) fallback
                        try:
                            global_pos = le.mapToGlobal(QPoint(0, le.height()))
                            # If mapToGlobal returns 0,0 it's likely not ready - but we checked earlier
                            try:
                                popup_obj.move(global_pos)
                            except Exception:
                                pass
                        except Exception:
                            pass

                        # Finally show popup; the popup itself will handle focus flags
                        try:
                            popup_obj.show_suggestions(filtered, le)
                            print('[Governor][PopupFix] called show_suggestions')
                        except Exception as e:
                            print(f"[Governor] Error showing suggestions popup: {e}")

                        # Ensure editor keeps keyboard focus: suppress reopen briefly to avoid focus-in triggering another show.
                        try:
                            self._suppress_reopen_until = time.time() + 0.2
                        except Exception:
                            pass
                except Exception as e:
                    print(f"[Governor] Error showing suggestions popup: {e}")
            else:
                try:
                    print("[Governor] No filtered suggestions -> hide popup")
                except Exception:
                    pass
                try:
                    popup_obj.hide()
                except Exception:
                    pass
        except Exception as e:
            print(f"[Governor] Exception in _show_suggestions_for_editor: {e}")

    def _on_suggestion_selected(self, text):
        """Minimal handler when suggestion clicked: set text and apply selection logic."""
        try:
            try:
                print(f"[Governor] _on_suggestion_selected called with text='{text}'")
            except Exception:
                pass

            le = getattr(self, '_popup_active_editor', None)
            try:
                print(f"[Governor] popup_active_editor={le}")
            except Exception:
                pass

            if isinstance(le, QLineEdit):
                try:
                    le.setText(text)
                    print("[Governor] Set editor text from suggestion")
                except Exception as e:
                    print(f"[Governor] Failed to set editor text: {e}")
                try:
                    row_prop = le.property('trans_row')
                    row = int(row_prop) if row_prop is not None else None
                    print(f"[Governor] Editor trans_row property={row}")
                except Exception as e:
                    print(f"[Governor] Failed to get trans_row: {e}")
                    row = None

                if row is not None:
                    try:
                        self.on_item_selected(row, text)
                        print("[Governor] on_item_selected called after suggestion pick")
                    except Exception as e:
                        print(f"[Governor] on_item_selected raised: {e}")
            else:
                try:
                    print("[Governor] Active editor is not a QLineEdit - cannot apply suggestion")
                except Exception:
                    pass
        except Exception as e:
            print(f"[Governor] Exception in _on_suggestion_selected: {e}")

        try:
            if getattr(self, '_suggestions_popup', None):
                try:
                    self._suggestions_popup.hide()
                    print("[Governor] suggestions_popup hidden after selection")
                except Exception:
                    pass
        except Exception:
            pass

    def _on_suggestions_closed(self, widget=None):
        """Called when suggestions popup hides — set a short suppression so clicks/focus
        that caused the close don't immediately reopen it.
        If `widget` is provided, it is the widget that was clicked; set focus to it after a short delay.
        """
        try:
            # Clear last shown query so reopen logic resets
            try:
                self._last_suggestions_query = None
                self._last_suggestions_editor_id = None
            except Exception:
                pass

            # Clear pending debounce so we don't show immediately
            try:
                self._pending_suggestion_le = None
                self._pending_suggestion_text = ''
            except Exception:
                pass

            # Set suppression window
            try:
                self._suppress_reopen_until = time.time() + 0.25  # suppress reopen for 250ms
                try:
                    print(f"[Governor] suggestions closed, suppress until {self._suppress_reopen_until}")
                except Exception:
                    pass
            except Exception:
                pass

            # If a widget was provided (user clicked it), do not force focus here.
            # For consistency across platforms we avoid calling setFocus() which
            # previously caused the popup to steal keyboard input. The natural
            # focus handling of the application will assign focus on click.
            # If callers require explicit focus, they can handle it via the
            # suggestion_closed signal.
            pass
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
        self.update_stats_table()

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
        try:
            # Re-number visible transaction rows (exclude the trailing add-row)
            for r in range(self.trans_table.rowCount() - 1):
                try:
                    it = self.trans_table.item(r, 0)
                    txt = str(r + 1)
                    if it is None:
                        it = QTableWidgetItem(txt)
                        it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.trans_table.setItem(r, 0, it)
                    else:
                        it.setText(txt)

                    # Re-apply type state to ensure correct qty visibility for income rows
                    # IMPORTANT: do NOT force recreation here — forcing would recreate
                    # the qty widget and reset its value to 0. Use a non-forcing
                    # update so existing Qty values are preserved.
                    cont_type = self.trans_table.cellWidget(r, 2)
                    is_income = False
                    if cont_type:
                        btn = cont_type.findChild(QPushButton)
                        if btn:
                            is_income = bool(btn.property('is_income'))
                    try:
                        self._apply_type_state(r, is_income, force_update=False)
                    except Exception:
                        pass
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
            self.update_stats_table()

            try:
                self.trans_table.setUpdatesEnabled(True)
                self.trans_table.viewport().update()
            except Exception:
                pass

    def recalc_row(self, row):
        try:
            if not hasattr(self, 'trans_table'):
                return

            # If called by signal, find the row - use object sender to be safe
            target_row = row
            sender = self.sender()
            
            # If recalculating from signal
            if sender and isinstance(sender, QAbstractSpinBox):
                 # Find which row this sender belongs to robustly
                found_sender = False
                for r in range(self.trans_table.rowCount()):
                    # Check columns 4 (Qty) and 5 (Price)
                    # The cell widget is a container, look inside it
                    container_qty = self.trans_table.cellWidget(r, 4)
                    container_price = self.trans_table.cellWidget(r, 5)
                    
                    if container_qty and sender in container_qty.findChildren(QAbstractSpinBox):
                        target_row = r
                        found_sender = True
                        break
                    if container_price and sender in container_price.findChildren(QAbstractSpinBox):
                        target_row = r
                        found_sender = True
                        break
                
                if found_sender:
                     target_row = r 
            
            # Check logic based on Type
            container_type = self.trans_table.cellWidget(target_row, 2)
            is_income = False
            if container_type:
                 btn = container_type.findChild(QPushButton)
                 if btn:
                     try:
                        is_income = bool(btn.property("is_income"))
                     except Exception:
                        pass

            container_qty = self.trans_table.cellWidget(target_row, 4)
            container_price = self.trans_table.cellWidget(target_row, 5)
            sum_item = self.trans_table.item(target_row, 6) 
            
            price = 0
            if container_price:
                price_widgets = container_price.findChildren(QAbstractSpinBox)
                # Look for spinning box inside container
                if price_widgets:
                    price = price_widgets[0].value()

            if is_income:
                # Income: Sum = Price (Quantity ignored/hidden); show plus sign
                total = int(price)
            else:
                # Expense: Sum = Price * Qty and should be negative
                qty = 0
                if container_qty:
                    qty_widgets = container_qty.findChildren(QAbstractSpinBox)
                    if qty_widgets:
                        qty = qty_widgets[0].value()
                total = int(qty * price) * -1

            if sum_item:
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
        self.update_stats_table()

    def delete_transaction(self):
        pass

    def init_items_table(self):
        self.items_table.setRowCount(0)
        self.add_item_plus_row()

    def add_item_plus_row(self):
        row_idx = self.items_table.rowCount()
        self.items_table.insertRow(row_idx)
        self.items_table.setRowHeight(row_idx, 50) 
        
        btn_add = create_plus_button(self.add_new_item_row)
        
        self.items_table.setSpan(row_idx, 0, 1, 3) # Span all 3 columns
        self.items_table.setCellWidget(row_idx, 0, btn_add)

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
        # Use helper for centered spinbox
        container_price = create_centered_spinbox(value=0, prefix="$", min_val=0, max_val=1000000000, 
                                                  on_change=lambda: (self.sync_all_data(), self.update_stats_table()))
        self.items_table.setCellWidget(row, 1, container_price)

        # 2. Delete Button
        # Use helper for delete button
        container_del = create_delete_button(lambda btn: self.delete_item_row_by_widget(btn))
        
        self.items_table.setCellWidget(row, 2, container_del)
        
        # Connect signals for immediate sync and stats refresh
        name_edit.textChanged.connect(lambda txt: (self.sync_all_data(), self.update_stats_table()))
        
        self.sync_all_data() # Sync on adding new item row
        # Also ensure stats reflect the new empty row
        try:
            self.update_stats_table()
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
                self.update_stats_table()
            except Exception:
                pass
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
            
            # Disable updates to prevent flickering and improve performance
            try:
                self.trans_table.setUpdatesEnabled(False)
                self.items_table.setUpdatesEnabled(False)
            except Exception:
                pass

            # Apply objects sheet to items_table (replace content)
            objs = fetched.get('objects')
            if objs:
                # First row may be headers
                rows = objs[1:] if len(objs) > 1 else []
                # Clear items_table and ensure '+' row exists
                self.items_table.setRowCount(0)
                self.add_item_plus_row()
                # Recreate rows (each add_new_item_row inserts before the + row)
                for r in rows:
                    if not r: continue # Skip empty rows
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
                # Use a looser check or just log to debug why it's skipping
                try:
                     print(f"DEBUG: Processing stats with {len(rows)} rows from import.")
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

                    # Qty/Price - delegation to _apply_type_state handles visibility
                    c_qty = self.trans_table.cellWidget(idx, 4)
                    if c_qty:
                        try:
                            sp = c_qty.findChild(QAbstractSpinBox)
                            if sp:
                                sp.setValue(qty_val)
                        except Exception:
                            pass

                    c_price = self.trans_table.cellWidget(idx, 5)
                    if c_price:
                        try:
                            sp = c_price.findChild(QAbstractSpinBox)
                            if sp:
                                sp.setValue(price_val)
                        except Exception:
                            pass

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
                    # Re-apply state to ensure correct visibility
                    c_type = self.trans_table.cellWidget(r, 2)
                    is_inc = False
                    if c_type:
                        btn = c_type.findChild(QPushButton)
                        if btn:
                            is_inc = bool(btn.property("is_income"))
                    # Do NOT force recreation here; preserve existing qty/spinbox values
                    self._apply_type_state(r, is_inc, force_update=False)

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
            # Re-enable updates
            try:
                self.trans_table.setUpdatesEnabled(True)
                self.items_table.setUpdatesEnabled(True)
                self.trans_table.viewport().update()
                self.items_table.viewport().update()
                self.trans_table.setEnabled(True)
                self.items_table.setEnabled(True)
            except Exception:
                pass
            self._importing = False
            self.update_stats_table()

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
        """Ensure the visual state for the given row's Type and Qty cells.
        For expense rows (is_income=False) ensure a Qty spinbox exists and is visible.
        For income rows (is_income=True) ensure the Qty cell is removed (or hidden).
        Reconnects the type button handler so it always toggles the correct row.
        """
        try:
            # Basic validation
            if not hasattr(self, 'trans_table'):
                return
            if row is None:
                return
            if row < 0 or row >= self.trans_table.rowCount():
                return

            # Get/create type button container
            try:
                container = self.trans_table.cellWidget(row, 2)
                if container is None:
                    # Nothing to do if there's no type container (row not initialized)
                    return
                btn = container.findChild(QPushButton)
            except Exception:
                btn = None

            # Update button property/text/style and ensure click handler references this row
            try:
                if btn:
                    try:
                        btn.setProperty('is_income', bool(is_income))
                    except Exception:
                        pass
                    btn.setText('+' if is_income else '-')
                    if is_income:
                        btn.setStyleSheet("""
                            QPushButton { background-color: #55aa55; color: white; border-radius: 4px; font-weight: bold; font-size: 16px; border: none; padding: 0px; }
                        """)
                    else:
                        btn.setStyleSheet("""
                            QPushButton { background-color: #ff5555; color: #ffffff; border-radius: 4px; font-weight: bold; font-size: 16px; border: none; padding: 0px; }
                        """)
                    # Reconnect clicked handler so it toggles this specific row
                    try:
                        btn.clicked.disconnect()
                    except Exception:
                        pass
                    try:
                        btn.clicked.connect(lambda checked=False, r=row, b=btn: self.toggle_type(r, b))
                    except Exception:
                        pass
            except Exception:
                pass

            # Manage Qty cell (column 4)
            try:
                w_qty = self.trans_table.cellWidget(row, 4)
                if is_income:
                    # For income rows remove the qty widget so it cannot be used
                    if w_qty is not None:
                        try:
                            # Remove widget from cell. Keep the widget object for GC by detaching.
                            self.trans_table.setCellWidget(row, 4, None)
                        except Exception:
                            try:
                                w_qty.setVisible(False)
                            except Exception:
                                pass
                else:
                    # For expense rows ensure a qty widget exists and is visible
                    if w_qty is None or force_update:
                        try:
                            qty_widget = create_centered_spinbox(value=0, min_val=-999999, max_val=999999,
                                                                 on_change=lambda r=row: self.recalc_row(r))
                            self.trans_table.setCellWidget(row, 4, qty_widget)
                            try:
                                qty_widget.setVisible(True)
                            except Exception:
                                pass
                        except Exception as e:
                            try:
                                print(f"[Governor] _apply_type_state: failed to create qty widget: {e}")
                            except Exception:
                                pass
                    else:
                        try:
                            w_qty.setVisible(True)
                        except Exception:
                            pass

            except Exception:
                pass

            # Refresh viewport so changes reflect immediately
            try:
                self.trans_table.viewport().update()
            except Exception:
                pass
        except Exception as e:
            try:
                print(f"[Governor] _apply_type_state error: {e}")
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
            self.trans_table.setUpdatesEnabled(False)
            self.items_table.setUpdatesEnabled(False)
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
            self.trans_table.setUpdatesEnabled(True)
            self.items_table.setUpdatesEnabled(True)
            self.trans_table.viewport().update()
            self.items_table.viewport().update()
            self.trans_table.setEnabled(True)
            self.items_table.setEnabled(True)
        except Exception:
            pass
        try:
            self._loading_overlay.hideOverlay()
        except Exception:
            pass
        self.setCursor(Qt.CursorShape.ArrowCursor)
        # End of import/update - re-enable suggestions
        try:
            self._suspend_suggestions = False
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
        try:
             # Use the same debounced interaction path so rapid text changes
             # don't trigger immediate show/hide flicker. Respect suppression window
             if time.time() < getattr(self, '_suppress_reopen_until', 0):
                 try:
                     print("[Governor] Suppression active in on_item_text_changed, skipping popup")
                 except Exception:
                     pass
             else:
                 try:
                     if getattr(self, '_active_item_editor', None) and self._active_item_editor.hasFocus():
                         # Reuse interaction path which starts/refreshes debounce
                         try:
                             self._on_item_editor_interaction(row, self._active_item_editor)
                             self._popup_active_editor = self._active_item_editor
                         except Exception:
                             pass
                 except Exception:
                     pass
        except Exception:
             pass

        self.sync_all_data()

    def _on_popup_pick(self, row, widget_container, text):
        le = widget_container.findChild(QLineEdit)
        if le:
            le.setText(text)
            self.on_item_selected(row, text)
            # Remove focus from editor to prevent immediate popup reopen
            try:
                # Clear focus from the line edit but DO NOT force focus elsewhere.
                # Forcing focus to another widget caused focus grab issues on some platforms.
                le.clearFocus()
            except Exception:
                pass
        if getattr(self, "_item_popup", None):
            try:
                self._item_popup.close()
            except Exception:
                pass
            self._item_popup = None

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

        # Create delete button container using helper
        container_del = create_delete_button(lambda btn: self.delete_row_by_widget(btn))
        
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
        # Ensure stats table columns expand to fill available width when window resizes
        try:
            if getattr(self, 'stats_table', None):
                self._adjust_stats_table_column_widths()
        except Exception:
            pass
        return super().resizeEvent(event)

    def _auto_import_on_open(self):
        if self._auto_loaded_once:
            return
        self._auto_loaded_once = True
        # Set importing flag before starting import to prevent suggestion popups
        try:
            self._importing = True
        except Exception:
            pass
        self._start_import_with_overlay()

    def show_calendar_popup(self, sender_widget):
        """Standard calendar popup for the date button. Position under the button and clamp to screen.
        """
        # Diagnostic log to help debug positioning issues
        try:
            print(f"[Governor] show_calendar_popup called. sender={repr(sender_widget)}, sender.rect={getattr(sender_widget, 'rect', None)}")
        except Exception:
            pass
        cal_widget = CustomCalendarWidget(parent=None)
        cal_widget.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)

        # Try to parse current date from button or default to current
        try:
            current_date_str = sender_widget.text()
            current_date = QDate.fromString(current_date_str, "dd.MM.yyyy")
            if current_date.isValid():
                cal_widget.setSelectedDate(current_date)
            else:
                cal_widget.setSelectedDate(QDate.currentDate())
        except Exception:
            cal_widget.setSelectedDate(QDate.currentDate())

        def on_date_selected(qdate):
            sender_widget.setText(qdate.toString("dd.MM.yyyy"))
            cal_widget.close()
            # Trigger sync if needed
            self.sync_all_data()

        cal_widget.date_selected.connect(on_date_selected)

        # Position: compute global bottom-left of the sender and clamp to screen
        try:
            cal_widget.adjustSize()
            btn_rect = sender_widget.rect()
            bottom_left = sender_widget.mapToGlobal(btn_rect.bottomLeft())
            x = bottom_left.x()
            y = bottom_left.y()

            try:
                screen = sender_widget.screen()
                if screen is None:
                    screen = QApplication.primaryScreen()
                geom = screen.availableGeometry()
                try:
                    print(f"[Governor] computed bottom_left=({x},{y}), popup_size=({cal_widget.width()},{cal_widget.height()}), screen_geom=({geom.left()},{geom.top()},{geom.right()},{geom.bottom()})")
                except Exception:
                    pass
                # clamp right edge
                if x + cal_widget.width() > geom.right():
                    x = max(geom.left(), geom.right() - cal_widget.width())
                # if it doesn't fit below, show above
                if y + cal_widget.height() > geom.bottom():
                    top_left = sender_widget.mapToGlobal(btn_rect.topLeft())
                    y = top_left.y() - cal_widget.height()
                    if y < geom.top():
                        y = geom.top()
                # ensure not off left/top
                if x < geom.left():
                    x = geom.left()
                if y < geom.top():
                    y = geom.top()
            except Exception:
                pass

            cal_widget.move(QPoint(x, y))
        except Exception:
            try:
                # fallback: position at sender global pos
                pos = sender_widget.mapToGlobal(QPoint(0, sender_widget.height()))
                try:
                    print(f"[Governor] fallback position used: {pos}")
                except Exception:
                    pass
                cal_widget.move(pos)
            except Exception:
                pass

        cal_widget.show()

    def _sort_transactions_by_date(self, descending=False):
        """Sort visible transactions by date without removing rows.
        Rows outside the selected range are hidden (not deleted). Visible rows
        are sorted in-place by updating values/widgets rather than reparenting
        widgets/items to avoid losing data that is later exported.
        """
        try:
            # Read selected range (if any)
            start = None
            end = None
            try:
                if getattr(self, 'period_range', None):
                    start, end = self.period_range.dateRange()
            except Exception:
                start = None
                end = None

            total_rows = self.trans_table.rowCount()
            data_rows = max(0, total_rows - 1)  # exclude trailing plus row

            # Hide rows outside the selected period (do not delete)
            for r in range(data_rows):
                try:
                    visible = True
                    if start or end:
                        c_date = self.trans_table.cellWidget(r, 1)
                        date_text = ''
                        if c_date:
                            btns = c_date.findChildren(QPushButton)
                            date_text = btns[0].text() if btns else ''
                        qd = QDate.fromString(date_text, 'dd.MM.yyyy') if date_text else None
                        if qd:
                            if start and qd < start:
                                visible = False
                            if end and qd > end:
                                visible = False
                    try:
                        self.trans_table.setRowHidden(r, not visible)
                    except Exception:
                        pass
                except Exception:
                    pass

            # Collect primitives for visible rows
            rows = []
            visible_positions = []
            for r in range(data_rows):
                try:
                    if self.trans_table.isRowHidden(r):
                        continue
                    visible_positions.append(r)
                    # Read primitives
                    # Date
                    date_text = ''
                    qd = None
                    c_date = self.trans_table.cellWidget(r, 1)
                    if c_date:
                        btns = c_date.findChildren(QPushButton)
                        if btns:
                            date_text = btns[0].text()
                        else:
                            try:
                                de = c_date.findChild(DateEditClickable)
                                if de:
                                    qd = de.date()
                                    date_text = qd.toString('dd.MM.yyyy')
                            except Exception:
                                pass
                        if date_text and not qd:
                            try:
                                qd = QDate.fromString(date_text, 'dd.MM.yyyy')
                            except Exception:
                                qd = None

                    # Type
                    is_income = False
                    c_type = self.trans_table.cellWidget(r, 2)
                    if c_type:
                        btn = c_type.findChild(QPushButton)
                        if btn:
                            try:
                                is_income = bool(btn.property('is_income'))
                            except Exception:
                                is_income = False

                    # Item
                    item_name = ''
                    c_item = self.trans_table.cellWidget(r, 3)
                    if c_item:
                        le = c_item.findChild(QLineEdit)
                        if le:
                            item_name = le.text().strip()

                    # Qty
                    qty = 0
                    w_qty = self.trans_table.cellWidget(r, 4)
                    if w_qty:
                        try:
                            sp = w_qty.findChild((NoScrollSpinBox, QSpinBox, QDoubleSpinBox))
                            if sp:
                                qty = int(sp.value())
                        except Exception:
                            qty = 0

                    # Price
                    price = 0
                    w_price = self.trans_table.cellWidget(r, 5)
                    if w_price:
                        try:
                            sp = w_price.findChild((QSpinBox, QDoubleSpinBox, NoScrollSpinBox))
                            if sp:
                                price = int(sp.value())
                        except Exception:
                            price = 0

                    # Sum
                    sum_val = 0
                    w_sum = self.trans_table.item(r, 6)
                    if w_sum:
                        try:
                            sum_val = _parse_display_amount(w_sum.text())
                        except Exception:
                            sum_val = 0

                    rows.append({'date_text': date_text, 'qdate': qd, 'is_income': is_income,
                                 'item': item_name, 'qty': qty, 'price': price, 'sum': sum_val,
                                 'height': self.trans_table.rowHeight(r)})
                except Exception:
                    pass

            if not rows:
                return

            # Sort by qdate (None as very old)
            def _sort_key(x):
                return (x['qdate'].toJulianDay() if x.get('qdate') else -999999)

            rows.sort(key=_sort_key, reverse=descending)

            # Write sorted values back into the visible positions (preserve widgets)
            for pos, rowdata in zip(visible_positions, rows):
                try:
                    # Date
                    c_date = self.trans_table.cellWidget(pos, 1)
                    if c_date:
                        btns = c_date.findChildren(QPushButton)
                        if btns and rowdata.get('date_text') is not None:
                            try:
                                btns[0].setText(rowdata.get('date_text') or "")
                            except Exception:
                                pass
                        else:
                            try:
                                de = c_date.findChild(DateEditClickable)
                                if de and rowdata.get('qdate'):
                                    de.setDate(rowdata.get('qdate'))
                            except Exception:
                                pass

                    # Type and qty visibility
                    try:
                        self._ensure_type_button(pos, rowdata.get('is_income', False))
                        self._apply_type_state(pos, rowdata.get('is_income', False), force_update=False)
                    except Exception:
                        pass

                    # Item
                    c_item = self.trans_table.cellWidget(pos, 3)
                    if c_item:
                        le = c_item.findChild(QLineEdit)
                        if le:
                            le.setText(rowdata.get('item', ''))

                    # Qty
                    c_qty = self.trans_table.cellWidget(pos, 4)
                    if c_qty:
                        try:
                            sp = c_qty.findChild((NoScrollSpinBox, QSpinBox, QDoubleSpinBox))
                            if sp:
                                sp.setValue(rowdata.get('qty', 0))
                        except Exception:
                            pass

                    # Price
                    c_price = self.trans_table.cellWidget(pos, 5)
                    if c_price:
                        try:
                            sp = c_price.findChild((QSpinBox, QDoubleSpinBox, NoScrollSpinBox))
                            if sp:
                                sp.setValue(rowdata.get('price', 0))
                        except Exception:
                            pass

                    # Sum
                    item_sum = self.trans_table.item(pos, 6)
                    if item_sum:
                        try:
                            item_sum.setText(_format_display_amount(rowdata.get('sum', 0)))
                        except Exception:
                            pass

                    # Ensure delete button exists
                    try:
                        self._ensure_delete_widget_for_row(pos)
                    except Exception:
                        pass

                    try:
                        self.trans_table.setRowHeight(pos, rowdata.get('height', 45))
                    except Exception:
                        pass
                except Exception:
                    pass

            # Update numbering and recalc visible rows
            try:
                self.update_row_numbers()
            except Exception:
                pass
            try:
                for r in visible_positions:
                    try:
                        self.recalc_row(r)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                self.refresh_item_combos()
            except Exception:
                pass

        except Exception as e:
            try:
                print(f"[Governor] _sort_transactions_by_date error: {e}")
            except Exception:
                pass

    def update_stats_table(self, filter_text: str = ''):
        """Aggregate expense rows from trans_table into stats_table.
        Case-insensitive aggregation. Respects selected period in `period_range`.
        """
        try:
            f = (filter_text or '').strip().lower()
            stats = {}
            # read period from single DateRangeEdit (period_range)
            start = None
            end = None
            try:
                if getattr(self, 'period_range', None):
                    start, end = self.period_range.dateRange()
            except Exception:
                start = None
                end = None

            for r in range(self.trans_table.rowCount() - 1):
                # read type
                c_type = self.trans_table.cellWidget(r, 2)
                is_inc = False
                if c_type:
                    btn = c_type.findChild(QPushButton)
                    if btn:
                        is_inc = bool(btn.property('is_income'))
                # ignore income rows
                if is_inc:
                    continue

                # read date and check period
                c_date = self.trans_table.cellWidget(r, 1)
                date_ok = True
                if c_date and (start is not None or end is not None):
                    btns = c_date.findChildren(QPushButton)
                    date_text = btns[0].text() if btns else ''
                    qd = QDate.fromString(date_text, 'dd.MM.yyyy') if date_text else None
                    if qd:
                        if start and qd < start:
                            date_ok = False
                        if end and qd > end:
                            date_ok = False
                if not date_ok:
                    continue

                # item name
                c_item = self.trans_table.cellWidget(r, 3)
                name = ''
                if c_item:
                    le = c_item.findChild(QLineEdit)
                    if le:
                        name = le.text().strip()
                if not name:
                    continue
                if f and f not in name.lower():
                    continue

                # qty and sum
                qty = 0
                w_qty = self.trans_table.cellWidget(r, 4)
                if w_qty:
                    sp = w_qty.findChild((NoScrollSpinBox, QSpinBox, QDoubleSpinBox))
                    if sp:
                        try:
                            qty = int(sp.value())
                        except Exception:
                            qty = 0
                # sum
                w_sum = self.trans_table.item(r, 6)
                total = 0
                if w_sum:
                    try:
                        total = _parse_display_amount(w_sum.text())
                    except Exception:
                        total = 0

                key = name.lower()
                if key not in stats:
                    stats[key] = {'display': name, 'qty': 0, 'total': 0}
                stats[key]['qty'] += abs(int(qty))
                stats[key]['total'] += abs(int(total))

            # Populate stats_table
            self.stats_table.setRowCount(0)
            for k, v in stats.items():
                row_idx = self.stats_table.rowCount()
                self.stats_table.insertRow(row_idx)
                # Name (make bold)
                it_name = QTableWidgetItem(v['display'])
                it_name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.stats_table.setItem(row_idx, 0, it_name)
                # Qty (make bold)
                it_qty = QTableWidgetItem(str(v['qty']))
                it_qty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_qty.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.stats_table.setItem(row_idx, 1, it_qty)
                # avg per unit
                avg = 0
                try:
                    avg = int(v['total'] / v['qty']) if v['qty'] else 0
                except Exception:
                    avg = 0
                it_avg = QTableWidgetItem(_format_display_amount(avg, show_sign=False))
                it_avg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_avg.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.stats_table.setItem(row_idx, 2, it_avg)
                it_sum = QTableWidgetItem(_format_display_amount(v['total'], show_sign=False))
                it_sum.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_sum.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.stats_table.setItem(row_idx, 3, it_sum)

        except Exception as e:
            try:
                print(f"[Governor] update_stats_table error: {e}")
            except Exception:
                pass

    def _adjust_name_column_for_editor(self, le: QLineEdit):
        """Ensure the 'Предмет' column (index 3) is at least 150px and expand it
        when the editor content requires more space, reducing Price(5)/Sum(6)
        columns if possible. This keeps the name visible and only shrinks numeric
        columns within sensible minima.
        """
        try:
            if le is None:
                return
            text = le.text() or ""
            fm = le.fontMetrics()
            # desired width including some padding
            desired = fm.horizontalAdvance(text) + 30
            # minimum for name column
            min_name = 150
            desired = max(desired, min_name)

            col_name = 3
            col_price = 5
            col_sum = 6

            cur_name_w = self.trans_table.columnWidth(col_name)
            if desired <= cur_name_w:
                return

            delta = desired - cur_name_w
            # minima for numeric columns
            min_price = 80
            min_sum = 80

            avail_price = max(0, self.trans_table.columnWidth(col_price) - min_price)
            avail_sum = max(0, self.trans_table.columnWidth(col_sum) - min_sum)
            total_avail = avail_price + avail_sum
            if total_avail <= 0:
                # nothing to take from; just set name to desired but don't change others
                try:
                    self.trans_table.setColumnWidth(col_name, desired)
                except Exception:
                    pass
                return

            take = min(delta, total_avail)
            # Prefer taking from Price first, then Sum
            take_from_price = min(avail_price, take)
            take_from_sum = take - take_from_price

            new_price = max(min_price, self.trans_table.columnWidth(col_price) - take_from_price)
            new_sum = max(min_sum, self.trans_table.columnWidth(col_sum) - take_from_sum)

            try:
                # Apply new widths
                self.trans_table.setColumnWidth(col_price, int(new_price))
                self.trans_table.setColumnWidth(col_sum, int(new_sum))
                self.trans_table.setColumnWidth(col_name, int(cur_name_w + take))
            except Exception:
                pass
        except Exception:
            pass

    def _adjust_stats_table_column_widths(self):
        """Distribute available width of stats_table across columns proportionally
        while respecting minimum column widths configured earlier.
        """
        try:
            tbl = getattr(self, 'stats_table', None)
            if tbl is None:
                return

            # Ensure header is in Stretch mode so columns fill available space
            try:
                for ci in range(tbl.columnCount()):
                    tbl.horizontalHeader().setSectionResizeMode(ci, QHeaderView.ResizeMode.Stretch)
                tbl.horizontalHeader().setStretchLastSection(True)
            except Exception:
                pass

            # base minimal widths (reduced to avoid forcing overflow)
            mins = [80, 50, 70, 70]
            total_min = sum(mins)

            # available content width in the viewport (reduce a bit for paddings)
            avail = max(0, (tbl.viewport().width() or tbl.width()) - 10)
            if avail <= 0:
                return

            # If there's extra space beyond total_min, distribute proportionally
            extra = max(0, avail - total_min)
            props = [m / total_min for m in mins]

            # If no extra, just set each column to at least its minimum
            for i, m in enumerate(mins):
                w = m + int(extra * props[i]) if extra > 0 else m
                try:
                    # In Stretch mode setColumnWidth is advisory; still set minimal via resize
                    tbl.setColumnWidth(i, max(40, int(w)))
                except Exception:
                    pass
        except Exception:
            pass

    def showEvent(self, event):
        """Ensure stats table columns are adjusted once the window is shown."""
        try:
            QTimer.singleShot(0, lambda: self._adjust_stats_table_column_widths())
        except Exception:
            pass
        try:
            return super().showEvent(event)
        except Exception:
            return

    def export_transactions(self):
        """Export visible transaction rows to a .txt file with totals appended.
        Writes a human-friendly aligned table where each column starts at the same position.
        """
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import os

        sep = ' | '

        # Gather visible rows first so we can compute column widths
        rows = []
        headers = ["№", "Дата", "Тип", "Предмет|Услуга", "Кол-во", "Цена", "Сумма"]

        # Build rows array
        for r in range(self.trans_table.rowCount() - 1):
            if self.trans_table.isRowHidden(r):
                continue

            row_cells = []
            for c in range(7):
                text_val = ''
                item = self.trans_table.item(r, c)
                if item and item.text():
                    text_val = item.text()
                else:
                    widget = self.trans_table.cellWidget(r, c)
                    if widget:
                        try:
                            btn = widget.findChild(QPushButton)
                            if btn and btn.text():
                                text_val = btn.text()
                            else:
                                le = widget.findChild(QLineEdit)
                                if le and le.text():
                                    text_val = le.text()
                                else:
                                    sp = widget.findChild(QAbstractSpinBox)
                                    if sp is not None:
                                        try:
                                            text_val = str(sp.value())
                                        except Exception:
                                            text_val = ''
                                    else:
                                        combo = widget.findChild(QComboBox)
                                        if combo and combo.currentText():
                                            text_val = combo.currentText()
                                        else:
                                            date_w = widget.findChild(QDateEdit)
                                            if date_w:
                                                try:
                                                    text_val = date_w.date().toString("dd.MM.yyyy")
                                                except Exception:
                                                    text_val = ''
                                            else:
                                                text_val = ''
                        except Exception:
                            text_val = ''
                    else:
                        text_val = ''

                # Clean unwanted whitespace characters
                if isinstance(text_val, str):
                    text_val = text_val.replace('\t', ' ').replace('\n', ' ').strip()
                else:
                    text_val = str(text_val)

                row_cells.append(text_val)

            rows.append(row_cells)

        # Compute column widths based on headers and data
        col_count = len(headers)
        widths = [0] * col_count
        for ci in range(col_count):
            maxw = len(headers[ci])
            for r in rows:
                try:
                    maxw = max(maxw, len(r[ci]))
                except Exception:
                    pass
            widths[ci] = maxw

        # Use alignment per column: right for numeric-ish, center for type, left for text
        aligns = ['>' , '<', '^', '<', '>', '>', '>']

        # Open Save As dialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить транзакции", "", "Text Files (*.txt);;All Files (*)")
        if not file_path:
            return
        if not file_path.lower().endswith('.txt'):
            file_path += '.txt'

        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                # Write header line with padding
                hdr_parts = []
                for i, h in enumerate(headers):
                    align = aligns[i] if i < len(aligns) else '<'
                    fmt = f"{{:{align}{widths[i]}}}"
                    hdr_parts.append(fmt.format(h))
                file.write(sep.join(hdr_parts) + '\n')

                # Underline header
                underline = []
                for w in widths:
                    underline.append('-' * w)
                file.write(sep.join(underline) + '\n')

                # Write rows with same padding
                for rdata in rows:
                    parts = []
                    for i, cell in enumerate(rdata):
                        align = aligns[i] if i < len(aligns) else '<'
                        fmt = f"{{:{align}{widths[i]}}}"
                        parts.append(fmt.format(cell))
                    file.write(sep.join(parts) + '\n')

                # Totals (strip duplicate prefixes if any)
                def _strip_label_prefix(lbl_text, prefix):
                    if not lbl_text:
                        return ''
                    t = lbl_text
                    if t.lower().startswith(prefix.lower()):
                        return t.split(':', 1)[1].strip()
                    return t

                try:
                    income_label = getattr(self, 'lbl_income', None)
                    expense_label = getattr(self, 'lbl_expense', None)
                    balance_label = getattr(self, 'lbl_balance', None)

                    income_text = _strip_label_prefix(income_label.text() if income_label else '', 'Доходы:')
                    expense_text = _strip_label_prefix(expense_label.text() if expense_label else '', 'Расходы:')
                    balance_text = _strip_label_prefix(balance_label.text() if balance_label else '', 'Баланс:')

                    file.write('\n')
                    file.write(f"Доходы: {income_text}\n")
                    file.write(f"Расходы: {expense_text}\n")
                    file.write(f"Баланс: {balance_text}\n")
                except Exception:
                    try:
                        self.update_totals()
                        file.write('\n')
                        file.write(f"Доходы: {getattr(self, 'lbl_income', QTableWidgetItem()).text()}\n")
                        file.write(f"Расходы: {getattr(self, 'lbl_expense', QTableWidgetItem()).text()}\n")
                        file.write(f"Баланс: {getattr(self, 'lbl_balance', QTableWidgetItem()).text()}\n")
                    except Exception:
                        pass

            # Styled success message
            try:
                msg = QMessageBox(self)
                msg.setWindowTitle("Экспорт завершен")
                msg.setText(f"Транзакции успешно экспортированы в файл:\n{os.path.basename(file_path)}")
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setStyleSheet("QMessageBox { background-color: #1f1f1f; color: #ffffff; } QPushButton { background-color: #2a82da; color: white; padding: 6px 12px; border-radius: 4px; }")
                msg.exec()
            except Exception:
                try:
                    QMessageBox.information(self, "Экспорт завершен", f"Транзакции успешно экспортированы в файл:\n{os.path.basename(file_path)}")
                except Exception:
                    pass
        except Exception as e:
            try:
                err = QMessageBox(self)
                err.setWindowTitle("Ошибка экспорта")
                err.setText(f"Не удалось экспортировать транзакции:\n{str(e)}")
                err.setIcon(QMessageBox.Icon.Critical)
                err.setStyleSheet("QMessageBox { background-color: #1f1f1f; color: #ffffff; } QPushButton { background-color: #2a82da; color: white; padding: 6px 12px; border-radius: 4px; }")
                err.exec()
            except Exception:
                try:
                    QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось экспортировать транзакции:\n{str(e)}")
                except Exception:
                    pass
