import re
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QAbstractItemView, QMessageBox, QFileDialog, 
                             QDialog, QCheckBox, QComboBox, QLineEdit, QScrollArea, QFrame,
                             QInputDialog, QSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, pyqtSlot, QTimer
from PyQt6.QtGui import QAction, QColor, QPalette, QPixmap, QIcon, QCursor
from config import ARTICLES
from auth import AdminPanel
from google_service import GoogleService
from utils import get_resource_path
import csv

# Worker for threaded tasks
class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(Exception)
    result = pyqtSignal(object)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.func(*self.args, **self.kwargs)
            self.result.emit(res)
            self.finished.emit()
        except Exception as e:
            self.error.emit(e)

class ArticlesDialog(QDialog):
    def __init__(self, current_articles, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выберите статьи")
        self.resize(450, 600)
        
        # Parse current articles into count map
        # Expected format in list: ["6.1", "6.1", "7.2"]
        self.article_counts = {}
        for art in current_articles:
            self.article_counts[art] = self.article_counts.get(art, 0) + 1
            
        self.controls = {} # Map code -> (checkbox, spinbox, container_widget)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Style helper for rounded spinbox elements
        # QSpinBox::up-button and ::down-button can be used to style the arrows.
        # But QSpinBox native styling is tricky.
        # Let's apply a general stylesheet for the dialog.
        self.setStyleSheet("""
            QWidget { 
                background-color: #353535; 
                color: white; 
                font-family: "Segoe UI", sans-serif; 
            }
            QCheckBox { 
                spacing: 8px; 
                font-size: 14px; 
            }
            QCheckBox::indicator { 
                width: 18px; 
                height: 18px; 
                border-radius: 4px; 
                background: white; 
                border: 1px solid #ccc; 
            }
            QCheckBox::indicator:unchecked { background-color: white; }
            QCheckBox::indicator:checked { background-color: #2ecc71; border: 1px solid #2ecc71; image: none; }
            
            QSpinBox {
                background-color: #444; 
                color: white; 
                border: 1px solid #555; 
                border-radius: 8px; /* Rounded corners for the field */
                padding: 4px;
                font-weight: bold;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #555;
                /* We can't easily make them perfectly rounded separate buttons via CSS alone on standard QSpinBox without subcontrol-origin hacking, 
                   but we can round the corners that touch the edge or just keep them inside. */
                border-radius: 4px;
                margin: 1px;
                width: 16px; 
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #666;
            }
            QSpinBox:disabled {
                background-color: #333;
                color: #777;
                border: 1px solid #333;
            }
            QPushButton {
                 border-radius: 8px;
            }
            QLineEdit { 
                padding: 8px; 
                border-radius: 15px; 
                border: 1px solid #555; 
                background-color: #252525; 
                color: white; 
            }
        """)

        # Search Filter
        search_layout = QHBoxLayout()
        lbl_search = QLabel("🔍")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск статьи...")
        self.search_input.textChanged.connect(self.filter_articles)
        search_layout.addWidget(lbl_search)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        self.vbox = QVBoxLayout(widget)
        self.vbox.setSpacing(5)
        
        from datetime import datetime, timedelta

        def get_expiration_date(price):
            base_date = datetime.now()
            if price == 25000:
                delta = 7
            elif price == 50000:
                delta = 21
            elif price == 75000:
                delta = 45
            elif price == 100000:
                return "Бессрочно"
            else:
                return "Неизвестно"
                
            expiry_date = base_date - timedelta(days=delta)
            return expiry_date.strftime("%d.%m.%Y")

        for code, label, cost in ARTICLES:
            expiry_str = get_expiration_date(cost)
            text = f"{code} - {label} ({expiry_str})"
            
            # Container for each article row
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            
            # Checkbox
            chk = QCheckBox(text)
            current_count = self.article_counts.get(code, 0)
            if current_count > 0:
                chk.setChecked(True)
            
            # Spinbox logic
            spin = QSpinBox()
            spin.setRange(1, 99)
            spin.setValue(max(1, current_count))
            spin.setFixedWidth(60) # Slightly wider for padding
            # spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus) # Optional style change
            spin.setEnabled(chk.isChecked())
            
            # Toggle spinbox with checkbox
            chk.toggled.connect(spin.setEnabled)
            
            row_layout.addWidget(chk, stretch=1)
            row_layout.addWidget(spin)
            
            self.vbox.addWidget(row_widget)
            
            # Store references for filtering and result gathering
            self.controls[code] = (chk, spin, row_widget, text.lower())
            
        self.vbox.addStretch()
        scroll.setWidget(widget)
        layout.addWidget(scroll)
        
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.accept)
        btn_save.setStyleSheet("background-color: #2e86de; color: white; padding: 8px;")
        layout.addWidget(btn_save)

    def filter_articles(self, text):
        search_text = text.lower()
        for code, (chk, spin, widget, label_text) in self.controls.items():
            visible = search_text in label_text
            widget.setVisible(visible)

    def get_selected(self):
        result = []
        for code, (chk, spin, _, _) in self.controls.items():
            if chk.isChecked():
                # Add duplicate code entries according to spinbox value
                for _ in range(spin.value()):
                    result.append(code)
        return result

class StatusPicker(QDialog):
    def __init__(self, parent=None, callback=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.callback = callback
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        container = QFrame()
        container.setObjectName("container")
        container.setStyleSheet("""
            QFrame#container {
                background-color: #353535; 
                border: 1px solid #555; 
                border-radius: 6px;
            }
        """)
        main_layout.addWidget(container)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(5)
        
        def create_btn(text, bg, fg, val):
            btn = QPushButton(text)
            btn.setFixedSize(30, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Override global QPushButton styles
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {fg};
                    border: none;
                    border-radius: 4px;
                    font-size: 16px;
                    font-weight: bold;
                    min-width: 30px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {bg}; 
                    border: 1px solid white;
                }}
            """)
            btn.clicked.connect(lambda: self.on_click(val))
            layout.addWidget(btn)

        # Cross (Red) - 0
        create_btn("✗", "#ffcccc", "#990000", 0)
        # Question (Orange) - 1
        create_btn("?", "#fff4cc", "#cc8800", 1)  
        # Check (Green) - 2
        create_btn("✔", "#ccffcc", "#006600", 2)
        
    def on_click(self, val):
        if self.callback:
            self.callback(val)
        self.close()

class MainWindow(QMainWindow):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.is_admin = user_data.get('Role') == 'Admin'
        self.can_edit = self.is_admin or user_data.get('Role') == 'Editor' # Editors can edit too?
        # Assuming permissions are handled by role check
        
        # State
        self.data = []
        self.filtered_data = []
        self.current_page = 1
        self.items_per_page = 50
        self.is_loading = False
        self.worksheet = None # GSpread worksheet object
        self.sync_mode = False # True if connected to Google Sheet
        self.filter_statuses = [] # Empty means all
        self.filter_articles = []
        
        # Sorting state
        self.current_sort_key = None
        self.current_sort_asc = True
        
        self.google_service = GoogleService()
        
        self.setWindowTitle("МВД Helper v2.0")
        self.resize(1200, 800)
        
        self.current_sort_key = None
        self.current_sort_asc = True

        # Permissions
        if self.is_admin:
            self.can_edit = True
            self.can_upload = True
        else:
            ce_val = str(user_data.get('CanEdit', '0')).lower()
            self.can_edit = ce_val in ('1', 'true', 'yes', 'on')
            
            # Allow upload if permission is set to true
            cu_val = str(user_data.get('CanUpload', '0')).lower()
            self.can_upload = cu_val in ('1', 'true', 'yes', 'on')
            
        # Default view permission is implicit
            
        self.setWindowTitle(f"Employee Data - {user_data.get('Username')} ({user_data.get('Role')})")
        self.setWindowIcon(QIcon(get_resource_path("image.png"))) # Set application icon
        self.resize(1200, 800)
        
        # Initialize Data
        self.data = []
        self.filtered_data = []
        self.filter_statuses = [0, 1, 2]
        self.filter_articles = []
        self.search_text = ""
        self.current_page = 1
        self.items_per_page = 10
        self.article_map = {code: label for code, label, _ in ARTICLES}
        
        self.sync_mode = False 
        self.worksheet = None
        self.is_loading = False
        
        # Thread references
        self.thread = None
        self.worker = None

        self._apply_theme()
        self.init_ui()

    def _apply_theme(self):
        # Dark Theme Palette
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        QApplication.instance().setPalette(dark_palette)
        
        # Additional Stylesheet
        self.setStyleSheet("""
            QWidget { background-color: #353535; color: white; font-family: "Segoe UI", sans-serif; }
            QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }
            QHeaderView::section { background-color: #353535; color: white; padding: 4px; border: none; border-bottom: 2px solid #555; font-weight: bold; font-size: 14px; }
            
            QTableWidget { 
                gridline-color: transparent; 
                border: none; 
                background-color: #353535; 
                font-size: 14px; 
                font-weight: bold;
                selection-background-color: transparent; /* Disable default blue selection */
                outline: none; /* Remove dotted focus line */
            }
            /* Row Styling: Lighter gray background, remove border-radius to fix vertical stripes */
            QTableWidget::item { 
                padding: 10px; 
                border-bottom: 6px solid #353535; 
                background-color: #505050; 
                border-radius: 0px;
                border-left: none;
                border-right: none;
                outline: none;
            }
            
            QTableWidget::item:selected {
                background-color: #505050;
                color: white;
            }
            
            /* Custom Scrollbar */
            QScrollBar:vertical {
                border: none; background: #2d2d2d; width: 10px; margin: 0px; border-radius: 5px;
            }
            
            /* Buttons */
            QPushButton { 
                background-color: #2a82da; color: white; border: none; 
                border-radius: 8px; padding: 10px; min-width: 100px; font-weight: bold; 
                outline: none; /* Remove dotted focus border */
            }
            QPushButton:hover { background-color: #3a92ea; }
            QPushButton:pressed { background-color: #1a72ca; }
            QPushButton:disabled { background-color: #555; color: #aaa; }

            /* Inputs */
            QLineEdit { 
                padding: 5px; border-radius: 8px; border: 1px solid #666; 
                background-color: #252525; color: white; selection-background-color: #2a82da;
            }
            
            /* Checkboxes */
            QCheckBox { spacing: 8px; font-size: 14px; outline: none; }
            QCheckBox:focus { outline: none; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; background: white; border: 1px solid #ccc; }
            QCheckBox::indicator:unchecked { background-color: white; }
            QCheckBox::indicator:checked { background-color: #2ecc71; border: 1px solid #2ecc71; image: none; }
            
            QDialog { background-color: #353535; border-radius: 10px; }
            
            /* Remove dotted focus rectangle */
            QTableWidget:focus { outline: none; }
            QPushButton:focus { outline: none; border: none; }
        """)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # --- Header --- 
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft) 

        # Logo Image
        logo_label = QLabel()
        pixmap = QPixmap(get_resource_path("image.png"))
        if not pixmap.isNull():
            # Increased size even more to match "Logo bigger" + "See photo" request
            pixmap = pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setFixedSize(100, 100)
            header_layout.addWidget(logo_label)
        
        # Title wrapper to center it vertically next to large logo
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container) 
        title_layout.setContentsMargins(0,0,0,0)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title = QLabel("Employee Data")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #4facfe; margin-left: 20px;") # Increased margin-left to separate from logo
        title_layout.addWidget(title)
        
        # Reverted: Search Bar moved back to Controls layout
        
        header_layout.addWidget(title_container)
        
        # --- Stats Blocks ---
        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(10)
        
        def create_stat_block(label_text):
            container = QFrame()
            container.setStyleSheet("background-color: #444; border-radius: 8px; border: 1px solid #555;")
            container.setFixedSize(150, 60)
            
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(10, 5, 10, 5)
            vbox.setSpacing(2)
            
            lbl_title = QLabel(label_text)
            lbl_title.setStyleSheet("color: #aaa; font-size: 12px; font-weight: bold; border: none; background: transparent;")
            lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            lbl_value = QLabel("0")
            lbl_value.setStyleSheet("color: white; font-size: 18px; font-weight: bold; border: none; background: transparent;")
            lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            vbox.addWidget(lbl_title)
            vbox.addWidget(lbl_value)
            
            return container, lbl_value

        self.block_total, self.lbl_total_count = create_stat_block("Всего людей")
        self.block_violators, self.lbl_violators_count = create_stat_block("Нарушителей")
        self.block_sum, self.lbl_total_sum = create_stat_block("Общая сумма")
        
        # Style specific for Sum to look dangerous/important
        self.lbl_total_sum.setStyleSheet("color: #ff6b6b; font-size: 18px; font-weight: bold; border: none; background: transparent;")

        self.stats_layout.addWidget(self.block_total)
        self.stats_layout.addWidget(self.block_violators)
        self.stats_layout.addWidget(self.block_sum)
        
        header_layout.addSpacing(20)
        header_layout.addLayout(self.stats_layout)
        
        header_layout.addStretch()
        
        # Right Side Buttons Container
        right_btn_layout = QVBoxLayout()
        right_btn_layout.setSpacing(5)
        # Changed alignment to ensure they don't jump around
        right_btn_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        # Settings
        settings_btn = QPushButton("⚙ Настройки")
        settings_btn.clicked.connect(self.open_settings)
        # settings_btn.setStyleSheet("margin: 0px;")
        right_btn_layout.addWidget(settings_btn)
        
        # Admin
        if self.is_admin:
            admin_btn = QPushButton("🛡 Админ панель")
            admin_btn.setStyleSheet("background-color: #d63031; color: white; border: none; border-radius: 8px; padding: 10px;")
            admin_btn.clicked.connect(self.open_admin_panel)
            right_btn_layout.addWidget(admin_btn)
            
        # User Info
        user_text = f"{self.user_data.get('Username')} ({self.user_data.get('Role')})"
        self.user_info_label = QLabel(user_text)
        self.user_info_label.setStyleSheet("font-weight: bold; padding: 5px; border: 1px solid #555; border-radius: 8px; background: #444; color: #ddd; font-size: 12px;")
        self.user_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_btn_layout.addWidget(self.user_info_label)

        header_layout.addLayout(right_btn_layout)
        
        # Google Status Label - kept on the far right or below, fixed width if possible to avoid jumping
        # Moved it to a vertical layout with the buttons or keep it separate?
        # User said "прикрепить левее ибо справа появляеться статус гугла и оно скачет туда сюда"
        # So the status label should be to the RIGHT of the buttons, and buttons should be anchored left of it?
        # Currently: header -> [Logo] [Stats] [Stretch] [Buttons] [Status]
        # If [Status] changes text, [Buttons] might move if there is no fixed size.
        # Let's give status label a fixed width or put it in a separate container.
        
        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet("font-style: italic; color: #f1c40f;")
        self.loading_label.setFixedWidth(150) # Fixed width to prevent jumping
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.loading_label)

        main_layout.addLayout(header_layout)

        # --- Controls --- 
        controls_layout = QHBoxLayout()
        
        # Search Bar moved back here as requested
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск (через запятую)...")
        # Kept rounded corners and styling
        self.search_input.setStyleSheet("""
            QLineEdit { 
                padding: 8px; 
                border-radius: 15px; 
                border: 1px solid #555; 
                background-color: #252525; 
                color: white; 
                font-size: 14px;
                min-width: 250px;
            }
            QLineEdit:focus { border: 1px solid #4facfe; }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        controls_layout.addWidget(self.search_input)
        
        controls_layout.addStretch()

        filter_btn = QPushButton("🌪 Фильтр")
        filter_btn.clicked.connect(self.open_filter)
        controls_layout.addWidget(filter_btn)
        
        lbl_sort = QLabel("Сортировка:")
        lbl_sort.setStyleSheet("font-weight: bold; font-size: 16px; margin-left: 10px;")
        controls_layout.addWidget(lbl_sort)

        def create_sort_btn(text, key, asc):
            btn = QPushButton(text)
            btn.clicked.connect(lambda: self.sort_staff(key, asc))
            controls_layout.addWidget(btn)

        create_sort_btn("Имя A-Z", 'name', True)
        create_sort_btn("Имя Z-A", 'name', False)
        create_sort_btn("Ранг ↑", 'rank', True)
        create_sort_btn("Ранг ↓", 'rank', False)
        
        main_layout.addLayout(controls_layout)

        # --- Table --- 
        self.table = QTableWidget()
        self.table.setColumnCount(7) # Added number column back
        self.table.setHorizontalHeaderLabels(["#", "Имя", "Статик", "Ранг", "Статьи", "Сумма", "Статус"])
        self.table.setShowGrid(False)  # Remove grid lines
        self.table.setFrameShape(QFrame.Shape.NoFrame) # Remove frame
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus) # Remove dotted focus line
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 80) # Increased width for numbering
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) # Status
        
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        
        # Connect single click for status toggling
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.cellDoubleClicked.connect(self.on_cell_double_click)
        
        # Enable mouse tracking for hover effects if needed, though stylesheet handles simple hovers
        self.table.setMouseTracking(True)
        
        main_layout.addWidget(self.table)
        
        # --- Pagination ---
        pagination_layout = QHBoxLayout()
        pagination_layout.addStretch()
        
        self.btn_prev = QPushButton("◄ Prev")
        self.btn_prev.setFixedWidth(80)
        self.btn_prev.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.btn_prev)
        
        self.page_input = QLineEdit()
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.setFixedWidth(50)
        self.page_input.returnPressed.connect(self.jump_to_page)
        pagination_layout.addWidget(self.page_input)
        
        self.lbl_total_pages = QLabel("/ 1")
        self.lbl_total_pages.setStyleSheet("font-weight: bold; color: #aaa;")
        pagination_layout.addWidget(self.lbl_total_pages)
        
        self.btn_next = QPushButton("Next ►")
        self.btn_next.setFixedWidth(80)
        self.btn_next.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.btn_next)
        
        pagination_layout.addStretch()
        main_layout.addLayout(pagination_layout)

    def on_search_changed(self, text):
        self.search_text = text
        self.apply_filters()

    def set_loading(self, show, message=""):
        self.is_loading = show
        if show:
            self.loading_label.setText(message)
            self.centralWidget().setEnabled(False) 
        else:
            self.loading_label.setText("")
            self.centralWidget().setEnabled(True)

    def closeEvent(self, event):
        if self.thread is not None:
            try:
                if self.thread.isRunning():
                    self.thread.quit()
                    self.thread.wait()
            except RuntimeError:
                pass
        event.accept()

    def on_cell_clicked(self, row, col):
        # Handle single click for Status column (index 6 now)
        if col == 6:
            name_item = self.table.item(row, 1) # Name is now at col 1
            if name_item:
                data_idx = name_item.data(Qt.ItemDataRole.UserRole)
                # Show popup menu for status
                if not self.can_edit: return
                
                picker = StatusPicker(parent=self, callback=lambda s: self.update_status(data_idx, s))
                # Center popup on mouse cursor
                cursor_pos = QCursor.pos()
                picker.move(cursor_pos.x() - picker.width() // 2, cursor_pos.y() - picker.height() // 2)
                picker.exec()
        
        # Copy Static ID (col 2) on single click as requested
        if col == 2:
            item = self.table.item(row, col)
            if item:
                QApplication.clipboard().setText(item.text())
                # Optional: Show a small tooltip or status message that it was copied
                self.loading_label.setText(f"Copied: {item.text()}")
                QTimer.singleShot(2000, lambda: self.loading_label.setText("Connected" if self.sync_mode else ""))

    def on_cell_double_click(self, row, col):
        # Always try to get index from column 1 (Name)
        name_item = self.table.item(row, 1)
        if not name_item: return
        data_idx = name_item.data(Qt.ItemDataRole.UserRole)
        
        item = self.table.item(row, col)
        
        if col in (1, 2): # Name, Static
            QApplication.clipboard().setText(item.text())
            
        if col == 4: # Articles
            self.open_articles_dialog(data_idx)
            
        # Status double click removed as it's handled by single click now

    def run_threaded(self, func, *args, on_result=None, **kwargs):
        self.thread = QThread(self) 
        self.worker = Worker(func, *args, **kwargs)
        
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        if on_result:
            self.worker.result.connect(on_result)
            
        self.worker.error.connect(lambda e: self.set_loading(False, f"Error: {e}"))
        
        self.thread.start()

    def _on_google_connected(self, ws):
        self.worksheet = ws
        self.sync_mode = True
        self.set_loading(False, "Connected")
        self.refresh_google_data()
        
    def _on_upload_complete(self, ws):
        self._on_google_connected(ws)
    
    def refresh_google_data(self):
        if not self.sync_mode or not self.worksheet: return
        self.set_loading(True, "Updating data...")
        self.run_threaded(self.google_service.fetch_all_values, self.worksheet, on_result=self._on_google_data_fetched)

    def _on_google_data_fetched(self, rows):
        if not rows: 
            self.set_loading(False)
            return

        if len(rows) > 0 and (rows[0][0] == "Name" or "Name" in rows[0]):
            rows = rows[1:]

        new_data = []
        for r in rows:
            while len(r) < 6:
                r.append("")
                
            name = r[0]
            statik = r[1]
            rank = r[2]
            arts_str = r[3]
            s_sum = r[4]
            proc = r[5]
            
            articles = [x.strip() for x in arts_str.split(',') if x.strip()]
            
            new_data.append({
                "name": name,
                "statik": statik,
                "rank": rank,
                "articles": articles,
                "sum": s_sum if s_sum else "0",
                "processed": int(proc) if str(proc).isdigit() else 1
            })
            
        self.data = new_data
        self.apply_filters()
        self.set_loading(False)

    def update_google_row(self, row_data):
        """Worker function: Updates row then fetches fresh data."""
        if not self.worksheet: return []
        
        art_str = ", ".join(row_data['articles'])
        self.google_service.update_row_data(self.worksheet, row_data['name'], art_str, row_data['sum'], row_data['processed'])
        
        # Return fresh data for the UI thread to process
        return self.google_service.fetch_all_values(self.worksheet)

    def update_status(self, idx, new_state):
        if not self.can_edit: return
        
        if idx >= len(self.filtered_data):
            return
        
        row = self.filtered_data[idx]
        current_state = int(row['processed'])
        
        if current_state == new_state:
            return

        row['processed'] = new_state
        self.render_staff() 

        if self.sync_mode:
            # We pass _on_google_data_fetched as the callback to handle the fresh data
            self.run_threaded(self.update_google_row, row, on_result=self._on_google_data_fetched)

    def open_articles_dialog(self, idx):
        if not self.can_edit: return
        if idx >= len(self.filtered_data): return
        
        row = self.filtered_data[idx]
        
        original_sum = float(row.get('sum', 0))
        dlg = ArticlesDialog(row.get('articles', []), self)
        
        if dlg.exec():
            new_selection = dlg.get_selected()
            row['articles'] = new_selection
            
            # Calculate total sum allowing duplicates
            total = 0
            for code in new_selection:
                # Find the article in global ARTICLES list
                article = next((a for a in ARTICLES if a[0] == code), None)
                if article:
                    total += float(article[2])
            
            # Use format to remove .0 if integer
            if total.is_integer():
                row['sum'] = str(int(total))
            else:
                row['sum'] = str(total)

            self.render_staff()
            
            if self.sync_mode:
                 self.run_threaded(self.update_google_row, row, on_result=self._on_google_data_fetched)

    def render_staff(self):
        # Update Stats
        total_people = len(self.filtered_data)
        
        # Count violators (processed != 2 (Checked) OR sum > 0? Let's assume anyone with a sum > 0 is a violator)
        # Or maybe anyone in the list is a violator? Let's assume sum > 0.
        violators = sum(1 for r in self.filtered_data if r.get('sum') != '0' and r.get('sum') != 0)
        
        total_sum_val = 0
        for r in self.filtered_data:
            try:
                s = int(str(r.get('sum', 0)))
                total_sum_val += s
            except: pass
            
        self.lbl_total_count.setText(str(total_people))
        self.lbl_violators_count.setText(str(violators))
        self.lbl_total_sum.setText(f"{total_sum_val:,}".replace(",", " "))

        # Pagination Logic
        total_items = len(self.filtered_data)
        total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        if total_pages < 1: total_pages = 1
        
        if self.current_page > total_pages: self.current_page = total_pages
        if self.current_page < 1: self.current_page = 1
        
        self.page_input.setText(str(self.current_page))
        self.lbl_total_pages.setText(f"/ {total_pages}")
        
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_data = self.filtered_data[start_idx:end_idx]
        
        self.table.setRowCount(0)
        self.table.setRowCount(len(page_data))
        
        # Set row height to be larger for spacing look
        for i in range(len(page_data)):
            self.table.setRowHeight(i, 60) 

        for i, row in enumerate(page_data):
            real_idx = start_idx + i
            
            # --- Column 0: Number ---
            num_item = QTableWidgetItem(str(real_idx + 1))
            self.style_table_item(num_item, is_start=True)
            self.table.setItem(i, 0, num_item)
            
            # --- Column 1: Name ---
            name_item = QTableWidgetItem(str(row['name']))
            name_item.setData(Qt.ItemDataRole.UserRole, real_idx) 
            self.style_table_item(name_item, is_start=True)
            self.table.setItem(i, 1, name_item)
            
            # --- Column 2: Static ---
            statik_item = QTableWidgetItem(str(row['statik']))
            self.style_table_item(statik_item)
            self.table.setItem(i, 2, statik_item)
            
            # --- Column 3: Rank ---
            rank_item = QTableWidgetItem(str(row['rank']))
            self.style_table_item(rank_item)
            self.table.setItem(i, 3, rank_item)
            
            # --- Column 4: Articles (Button) ---
            # Placeholder item for background styling
            dummy_item = QTableWidgetItem("")
            self.style_table_item(dummy_item)
            self.table.setItem(i, 4, dummy_item)
            
            # Create the interactive button
            full_text = ", ".join(row['articles']) if row['articles'] else "-----"
            
            # Truncate text to avoid layout expanding too much
            display_text = full_text
            if len(display_text) > 40:
                display_text = display_text[:37] + "..."
                
            art_btn = QPushButton(display_text)
            art_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            art_btn.setFixedHeight(30) 
            art_btn.setToolTip(full_text)
            
            if self.can_edit:
                art_btn.clicked.connect(lambda _, idx=real_idx: self.open_articles_dialog(idx))
            else:
                art_btn.setEnabled(False)

            art_btn.setStyleSheet("""
                QPushButton {
                    background-color: white; 
                    color: black; 
                    border-radius: 6px; 
                    text-align: center; 
                    padding: 5px;
                    border: 1px solid #ccc;
                    font-weight: normal;
                    font-size: 14px;
                }
                QPushButton:hover { background-color: #f0f0f0; }
                QPushButton:disabled { background-color: #e0e0e0; color: #888; }
            """)
            
            # Container to center vertically and add margins inside cell
            widget_container = QWidget()
            widget_container.setStyleSheet("background-color: transparent;")
            layout = QHBoxLayout(widget_container)
            layout.setContentsMargins(5, 0, 5, 0) # Removed bottom margin to center properly
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center alignment
            layout.addWidget(art_btn)
            self.table.setCellWidget(i, 4, widget_container)
            
            # --- Column 5: Sum ---
            sum_item = QTableWidgetItem(str(row['sum']))
            self.style_table_item(sum_item)
            self.table.setItem(i, 5, sum_item)
            
            # --- Column 6: Status ---
            status_val = int(row.get('processed', 0))
            status_text = "✗"
            color_hex = "#ff4d4d" 
            if status_val == 1:
                status_text = "?"
                color_hex = "#ffa502" 
            elif status_val == 2:
                status_text = "✔"
                color_hex = "#2ecc71" 
                
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(color_hex))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.style_table_item(status_item, is_end=True)
            self.table.setItem(i, 6, status_item)

    def style_table_item(self, item, is_start=False, is_end=False):
        # We simulate rounded rows by setting a specific background on items
        # and using border-radius on the first and last items of the row.
        # However, QTableWidget styling is limited for individual cell borders.
        # The main styling is done in the QTableWidget::item stylesheet in _apply_theme.
        # Here we just ensure alignment and basic properties.
        
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # We rely on the stylesheet for the main look, but to fix the "stripes" (white gaps between cells),
        # we need to ensure the cells touch each other horizontally.
        # The key is padding/border in the stylesheet.
        # Also setting background color to lighter gray for rows as requested.

    def sort_staff(self, key, ascending=True):
        self.current_sort_key = key
        self.current_sort_asc = ascending

        def sort_key(row):
            val = row.get(key, "")
            
            if key == 'rank':
                val = str(val).strip()
                if val.isdigit():
                    return int(val)
                return val.lower()
                
            if key == 'sum':
                 try:
                    return float(val)
                 except ValueError:
                    return 0
            
            return str(val).lower()

        self.filtered_data.sort(key=sort_key, reverse=not ascending)
        self.render_staff()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.render_staff()
            
    def next_page(self):
        total_items = len(self.filtered_data)
        total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        if self.current_page < total_pages:
            self.current_page += 1
            self.render_staff()
            
    def jump_to_page(self):
        try:
            p = int(self.page_input.text())
            self.current_page = p
            self.render_staff()
        except ValueError:
            pass

    def open_settings(self):
        # Settings Dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройки")
        dialog.resize(350, 250) # Increased size
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        btn_local = QPushButton("📂 Импорт из файла (.txt)")
        # Check permissions for import/upload
        if not self.can_upload:
            btn_local.setEnabled(False)
            btn_local.setToolTip("Нет прав на загрузку")
            
        btn_local.clicked.connect(lambda: [dialog.close(), self.load_file()])
        layout.addWidget(btn_local)
        
        btn_google = QPushButton("☁ Синхронизация (Google Sheets)")
        btn_google.clicked.connect(lambda: [dialog.close(), self.connect_google_dialog()])
        layout.addWidget(btn_google)
        
        # Export Button
        btn_export = QPushButton("💾 Экспорт данных")
        btn_export.clicked.connect(lambda: [dialog.close(), self.open_export_dialog()])
        layout.addWidget(btn_export)
        
        dialog.exec()
        
    def open_export_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Экспорт")
        dialog.resize(400, 400)
        
        layout = QVBoxLayout(dialog)
        
        # --- Export Options Filter ---
        group = QFrame()
        group.setStyleSheet("background-color: #404040; border-radius: 5px; padding: 10px;")
        g_layout = QVBoxLayout(group)
        g_layout.addWidget(QLabel("<b>Настройки экспорта (что включить):</b>"))
        
        chk_header = QCheckBox("Заголовки столбцов")
        chk_header.setChecked(True)
        g_layout.addWidget(chk_header)
        
        chk_export_all = QCheckBox("Экспортировать ВСЕ (игнорировать фильтр)")
        chk_export_all.setChecked(False)
        g_layout.addWidget(chk_export_all)
        
        layout.addWidget(group)
        # -----------------------------

        lbl = QLabel("Выберите формат экспорта:")
        layout.addWidget(lbl)
        
        # Helper to safely retrieve values before closing
        def do_export(method):
            inc_h = chk_header.isChecked()
            exp_all = chk_export_all.isChecked()
            
            dialog.close()
            # Defer execution to let dialog close properly and event loop settle
            QTimer.singleShot(100, lambda: method(inc_h, exp_all))

        # Options
        btn_xls = QPushButton("Excel / CSV (.csv)")
        btn_xls.clicked.connect(lambda: do_export(self.export_to_csv))
        layout.addWidget(btn_xls)
        
        btn_txt = QPushButton("Текстовый файл (.txt)")
        btn_txt.clicked.connect(lambda: do_export(self.export_to_txt))
        layout.addWidget(btn_txt)
        
        btn_gsheet = QPushButton("Новая Google Таблица")
        # Check permission for creating new sheet
        if not self.can_upload:
             btn_gsheet.setEnabled(False)
             btn_gsheet.setText("Новая Google Таблица (Нет прав)")
             
        btn_gsheet.clicked.connect(lambda: do_export(self.export_to_google))
        layout.addWidget(btn_gsheet)
        
        dialog.exec()

    def export_to_csv(self, include_header, export_all):
        fname, _ = QFileDialog.getSaveFileName(self, "Сохранить как CSV", "", "CSV Files (*.csv)")
        if not fname: return
        
        data_source = self.data if export_all else self.filtered_data
        
        try:
            with open(fname, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';') 
                if include_header:
                    writer.writerow(["Имя", "Статик", "Ранг", "Статьи", "Сумма", "Статус"])
                
                for row in data_source:
                    status_str = "Не обработан"
                    if row['processed'] == 1: status_str = "Вопрос"
                    elif row['processed'] == 2: status_str = "Обработан"
                    
                    writer.writerow([
                        row['name'],
                        row['statik'],
                        row['rank'],
                        ",".join(row['articles']),
                        row['sum'],
                        status_str
                    ])
            QMessageBox.information(self, "Успех", "Данные успешно экспортированы в CSV!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def export_to_txt(self, include_header, export_all):
        fname, _ = QFileDialog.getSaveFileName(self, "Сохранить как TXT", "", "Text Files (*.txt)")
        if not fname: return
        
        data_source = self.data if export_all else self.filtered_data
        
        try:
            with open(fname, 'w', encoding='utf-8') as f:
                if include_header:
                    f.write(f"{'Имя':<30} | {'Статик':<10} | {'Ранг':<15} | {'Сумма':<10} | {'Статьи'}\n")
                    f.write("-" * 100 + "\n")
                
                for row in data_source:
                    articles = ",".join(row['articles'])
                    f.write(f"{row['name']:<30} | {str(row['statik']):<10} | {str(row['rank']):<15} | {str(row['sum']):<10} | {articles}\n")
            QMessageBox.information(self, "Успех", "Данные успешно экспортированы в TXT!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            
    def export_to_google(self, include_header, export_all):
        text, ok = QInputDialog.getText(self, "Новая таблица", "Введите название нового листа:")
        if not ok or not text: return
        
        data_source = self.data if export_all else self.filtered_data
        self.set_loading(True, "Экспорт в Google...")
        self.run_threaded(self.google_service.upload_sheet_data, text, data_source, include_header=include_header, on_result=self._on_upload_complete)
    
    def connect_google_dialog(self):
        text, ok = QInputDialog.getText(self, "Название листа", "Введите название листа для синхронизации:")
        if ok and text:
            self.load_from_google(text)

    def open_admin_panel(self):
        AdminPanel(self).exec()
        
    def open_filter(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Фильтр")
        dialog.resize(300, 450)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        
        layout.addWidget(QLabel("Статусы:"))
        status_checks = {}
        for code, text in [(0, "Не обработан"), (1, "Вопрос"), (2, "Обработан")]:
            chk = QCheckBox(text)
            chk.setChecked(code in self.filter_statuses)
            layout.addWidget(chk)
            status_checks[code] = chk
            
        layout.addWidget(QLabel("Статьи:"))
        scroll = QScrollArea()
        scroll.setStyleSheet("background-color: #404040; border-radius: 5px; border: none;")
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background-color: #404040;")
        scroll_layout = QVBoxLayout(scroll_widget)
        article_checks = {}
        
        # Sort articles using natural sort order (so 6.1 comes before 10.1)
        def natural_sort_key(item):
            # item is (code, label, cost)
            # Split code by dot and convert parts to integers
            try:
                parts = [int(p) for p in item[0].split('.')]
                return parts
            except ValueError:
                return [0]

        sorted_articles = sorted(ARTICLES, key=natural_sort_key)
        
        for code, label, _ in sorted_articles:
            chk = QCheckBox(f"{code} ({label})")
            chk.setChecked(code in self.filter_articles)
            scroll_layout.addWidget(chk)
            article_checks[code] = chk
            
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        btns_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Сбросить")
        reset_btn.setStyleSheet("background-color: #7f8c8d;")
        def reset():
            for chk in status_checks.values(): chk.setChecked(True)
            for chk in article_checks.values(): chk.setChecked(False)
        reset_btn.clicked.connect(reset)
        btns_layout.addWidget(reset_btn)
        
        apply_btn = QPushButton("Применить")
        def apply():
            self.filter_statuses = [c for c, chk in status_checks.items() if chk.isChecked()]
            self.filter_articles = [c for c, chk in article_checks.items() if chk.isChecked()]
            self.apply_filters()
            dialog.accept()
            
        apply_btn.clicked.connect(apply)
        btns_layout.addWidget(apply_btn)
        
        layout.addLayout(btns_layout)
        dialog.exec()

    def apply_filters(self):
        text = self.search_text.lower()
        res = []
        
        for r in self.data:
            # Check search text
            match_search = (text in str(r['name']).lower() or 
                            text in str(r['statik']).lower() or 
                            text in str(r['rank']).lower())
            
            # Check status filter
            match_status = True
            if self.filter_statuses:
                match_status = r['processed'] in self.filter_statuses
                
            # Check article filter 
            match_articles = True
            if self.filter_articles:
                # If any of the row's articles match any of the filter articles
                # Or must match ALL? Usually "any".
                has_any = any(art in self.filter_articles for art in r['articles'])
                if not has_any:
                    match_articles = False
            
            if match_search and match_status and match_articles:
                res.append(r)
                
        self.filtered_data = res
        self.current_page = 1
        
        if self.current_sort_key:
            self.sort_staff(self.current_sort_key, self.current_sort_asc)
        else:
            self.render_staff()

    def load_file(self):
        if not self.can_upload:
            QMessageBox.warning(self, "Доступ запрещен", "Нет прав")
            return
            
        fname, _ = QFileDialog.getOpenFileName(self, "Открыть", "", "Text files (*.txt)")
        if not fname: return

        text, ok = QInputDialog.getText(self, "Название листа", "Введите название нового листа:")
        if not ok or not text: return
        sheet_name = text

        try:
            new_data = []
            with open(fname, encoding="utf-8") as f:
                 for line in f:
                    if not line.strip(): continue
                    parts = line.strip().split("\t")
                    if len(parts) < 2: continue
                    
                    name_part = parts[0].strip()
                    rank = parts[1].strip()
                    statik_match = re.search(r'\[(\d+)\]', name_part)
                    statik = statik_match.group(1) if statik_match else ""
                    name = re.sub(r'\s*\[\d+\]', '', name_part).strip()
                    
                    new_data.append({
                        "name": name,
                        "statik": statik,
                        "rank": rank,
                        "articles": [],
                        "sum": 0,
                        "processed": 1 
                    })
            self.data = new_data
            self.filtered_data = list(self.data)
            self.render_staff()
            
            self.set_loading(True, "Загрузка в Google...")
            self.run_threaded(self.google_service.upload_sheet_data, sheet_name, self.data, on_result=self._on_upload_complete)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.set_loading(False)
    
    def load_from_google(self, sheet_title):
        self.set_loading(True, "Connecting...")
        
        self.run_threaded(self.google_service.connect_worksheet, sheet_title, on_result=self._on_google_connected)

    def closeEvent(self, event):
        if self.thread:
            try:
                if self.thread.isRunning():
                    self.thread.quit()
                    self.thread.wait()
            except RuntimeError:
                pass
        event.accept()

    def set_loading(self, show, message=""):
        self.is_loading = show
        self.loading_label.setText(message if show else "")
        self.loading_label.setVisible(show)

    def on_search_changed(self, text):
        self.search_text = text.lower()
        self.apply_filters()
