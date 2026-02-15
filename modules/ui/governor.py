from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDateEdit, QComboBox, 
                             QDoubleSpinBox, QSpinBox, QMessageBox, QGroupBox, QSizePolicy,
                             QCalendarWidget, QToolButton, QMenu, QAbstractSpinBox, QStyle, QApplication, QStyleOptionComboBox, QStyleOptionSpinBox)
from PyQt6.QtCore import Qt, QDate, QEvent, QLocale, QRect, QPointF, QPoint
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QMouseEvent, QKeyEvent
from modules.core.google_service import GoogleService
from modules.core.utils import get_resource_path

class CustomCalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLocale(QLocale(QLocale.Language.Russian))
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setNavigationBarVisible(True)
        self.setStyleSheet("""
            QCalendarWidget QWidget { 
                alternate-background-color: #2b2b2b; 
                background-color: #2b2b2b; 
                color: white;
            }
            QCalendarWidget QToolButton {
                color: white;
                background-color: transparent;
                border-radius: 4px;
                icon-size: 16px;
                border: none;
                margin: 2px;
                font-weight: bold;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #3a3a3a;
            }
            QCalendarWidget QToolButton#qt_calendar_prevmonth {
                qproperty-icon: none;
                image: url(none); /* We will paint it or use text */
                background-color: transparent;
                width: 20px;
            }
            QCalendarWidget QToolButton#qt_calendar_nextmonth {
                qproperty-icon: none;
                background-color: transparent;
                width: 20px;
            }
            QCalendarWidget QMenu {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #404040;
                border-radius: 6px;
            }
            QCalendarWidget QSpinBox {
                color: white;
                background-color: transparent;
                selection-background-color: #4aa3df;
                border: none;
                font-weight: bold;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: white;
                background-color: #2b2b2b;
                selection-background-color: transparent; /* Disable default box, we draw rounded rect */
                selection-color: white;
                border-radius: 6px;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #555555;
            }
        """)

    def paintCell(self, painter, rect, date):
        # Custom painting for selected date to have rounded rectangle
        if date == self.selectedDate():
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#4aa3df"))
            # Draw rounded rect slightly smaller than cell
            r = QRect(rect.left() + 2, rect.top() + 2, rect.width() - 4, rect.height() - 4)
            painter.drawRoundedRect(r, 6, 6)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(date.day()))
            painter.restore()
        else:
            super().paintCell(painter, rect, date)

class DateEditClickable(QDateEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("dd.MM.yyyy")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Disable manual editing but allow click
        # IMPORTANT: Removing self.setReadOnly(True) restores the arrow functionality implicitly!
        # self.setReadOnly(True) 
        self.lineEdit().setReadOnly(True)
        
        # Set custom calendar
        self.setCalendarWidget(CustomCalendarWidget(self))

        # Center text
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Install event filter to catch clicks everywhere
        self.lineEdit().installEventFilter(self)

    def eventFilter(self, source, event):
        if source == self.lineEdit() and event.type() == QEvent.Type.MouseButtonPress:
            # Send F4 key event to toggle popup
            key_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_F4, Qt.KeyboardModifier.NoModifier)
            QApplication.postEvent(self, key_event)
            return True
        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        # Ignore keys except those that close/navigate popup if open
        if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab):
            super().keyPressEvent(event)
        elif event.text():
             event.ignore()
        else:
             super().keyPressEvent(event)

class GovernorCabinetWindow(QMainWindow):
    def __init__(self, user_data, parent_launcher=None):
        super().__init__()
        self.user_data = user_data
        self.parent_launcher = parent_launcher
        self.google_service = GoogleService()
        self.spreadsheet_id = "1E1dzanmyjcGUur8sp4uFsc7cADDhvNp4UEley6VIS6Y" # User provided link
        
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
                font-weight: bold; /* Make labels bolder */
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
                background-color: #1e1e1e; /* Match the frame around the table */
                gridline-color: transparent;
                color: #ddd;
                border: none;
                font-size: 13px;
                selection-background-color: transparent;
                outline: none;
            }
            QTableWidget::item {
                background-color: #333333;
                /* Vertical spacing - reset to minimal to see if that helps */
                margin-top: 0px; 
                margin-bottom: 8px; /* Push next row down */
                /* Horizontal spacing between columns */
                margin-left: 0px; 
                margin-right: 4px; /* Same as header margin-right */
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
                border-radius: 6px; /* Rounded headers */
                margin-right: 4px; /* Space between headers */
                margin-bottom: 8px; /* Space from table */
                margin-top: 6px; 
            }
            QHeaderView::section:last {
                background-color: rgba(128, 128, 128, 0.2); 
                color: #808080; 
                border: 2px solid #808080;
                margin-right: 0px; 
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
                margin: 5px; /* Add margin to center vertically roughly if item is taller */
                selection-background-color: #4aa3df;
                selection-color: white;
            }
            /* Add hover/focus effects to show it's editable */
            QComboBox:hover, QDateEdit:hover, QDoubleSpinBox:hover, QSpinBox:hover,
            QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
                background-color: #f0f0f0;
                border-radius: 4px;
            }
            /* Restore drop-down arrows and spin box arrows */
            QComboBox::drop-down, QDateEdit::drop-down {
                border: none;
                width: 15px; 
            }
            QComboBox::down-arrow, QDateEdit::down-arrow {
                border: none;
            }
            QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
                width: 0px;
                height: 0px;
                border: none;
                background: transparent;
            }
        """)

        # Data placeholders
        self.transaction_data = [] # Left table
        self.item_definitions = [] # Right top table
        
        self.init_ui()
        # TODO: Load data from Google Sheets

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # --- Top Header --- 
        header_layout = QHBoxLayout()
        title_label = QLabel("GOVERNOR CABINET")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #4aa3df;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Stats Summary
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
        
        # Period Selection
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Период:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Текущий месяц", "Прошлый месяц", "Все время"])
        period_layout.addWidget(self.period_combo)
        header_layout.addLayout(period_layout)
        
        header_layout.addSpacing(20)

        # Back to Launcher
        btn_back = QPushButton("В лаунчер")
        btn_back.setStyleSheet("background-color: #555; border: 1px solid #777;")
        btn_back.clicked.connect(self.return_to_launcher)
        header_layout.addWidget(btn_back)
        
        main_layout.addLayout(header_layout)

        # --- Main Content Area (Split Left/Right) ---
        content_layout = QHBoxLayout()
        
        # === LEFT COLUMN: Transactions ===
        left_layout = QVBoxLayout()
        
        # Group: Add Transaction (Using a custom widget to look like table header row?)
        grp_trans = QGroupBox("Операции (Доход/Расход)")
        grp_trans_layout = QVBoxLayout(grp_trans)
        grp_trans_layout.setContentsMargins(5, 20, 5, 5) # Increased top to 20 to clear title, others 5 for small gap
        
        # Transaction Table
        self.trans_table = QTableWidget()
        self.trans_table.setColumnCount(7) # Increase column for number (0) and delete button (6)
        self.trans_table.setHorizontalHeaderLabels(["№", "Дата", "Предмет", "Кол-во", "Цена", "Сумма", "x"])
        self.trans_table.horizontalHeader().setStretchLastSection(False) # Don't stretch last section automatically
        
        # Last header item custom widget or just unicode
        item_del = QTableWidgetItem("x")
        item_del.setToolTip("Удалить")
        # Ensure header text is visible (not empty string) and styled appropriately
        item_del.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trans_table.setHorizontalHeaderItem(6, item_del)
        
        # Adjust column widths
        self.trans_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(0, 50)
        
        self.trans_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(1, 120)  # Date

        # Item (2) matches Price (4) and Sum (5) = 150px fixed
        self.trans_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self.trans_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(3, 80) 
        
        self.trans_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(4, 150) 
        
        self.trans_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(5, 150)

        self.trans_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.trans_table.setColumnWidth(6, 50) # Increased to 50 to prevent button cropping
        
        # Make the item column (2) stretch to fill available space
        self.trans_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # Enable styling for transparent table background to show spacing
        self.trans_table.setShowGrid(False) 
        self.trans_table.verticalHeader().setVisible(False) # Hide default vertical header numbers since we have col 0
        self.trans_table.verticalHeader().setDefaultSectionSize(45) # Make rows slightly more compact to match header height maybe? Headers are auto.
        self.trans_table.horizontalHeader().setDefaultSectionSize(40) # Reset header height
        self.trans_table.horizontalHeader().setMinimumSectionSize(40) 
        
        grp_trans_layout.addWidget(self.trans_table)
        
        self.init_trans_table()

        left_layout.addWidget(grp_trans)
        
        # Filter (Bottom Left)
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
        
        content_layout.addLayout(left_layout, stretch=70) # Increase width of left table (70%)

        # === RIGHT COLUMN: Items & Stats ===
        right_layout = QVBoxLayout()
        
        # Top Right: Item Definitions
        grp_items = QGroupBox("Управление предметами")
        grp_items_layout = QVBoxLayout(grp_items)
        
        item_input_container = QFrame()
        item_input_container.setStyleSheet("background-color: #2b2b2b; border: 1px solid #404040; border-radius: 6px; padding: 5px;")
        item_input_row = QHBoxLayout(item_input_container)
        item_input_row.setContentsMargins(5, 5, 5, 5)

        self.new_item_name = QComboBox() 
        self.new_item_name.setEditable(True)
        self.new_item_name.setPlaceholderText("Название")
        self.new_item_name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.new_item_price = QDoubleSpinBox()
        self.new_item_price.setRange(0, 1000000000)
        self.new_item_price.setPrefix("$")
        self.new_item_price.setFixedWidth(100)
        
        btn_add_item = QPushButton("+")
        btn_add_item.setFixedSize(30, 30)
        btn_add_item.setStyleSheet("""
            QPushButton { background-color: #2a82da; border-radius: 15px; font-weight: bold; font-size: 18px; }
            QPushButton:hover { background-color: #3a92ea; }
        """)
        btn_add_item.clicked.connect(self.add_item_definition)
        
        item_input_row.addWidget(QLabel("Предмет:"))
        item_input_row.addWidget(self.new_item_name)
        item_input_row.addWidget(QLabel("Базовая цена:"))
        item_input_row.addWidget(self.new_item_price)
        item_input_row.addWidget(btn_add_item)
        
        grp_items_layout.addWidget(item_input_container)
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(2)
        self.items_table.setHorizontalHeaderLabels(["Название предмета", "Базовая цена"])
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.items_table.setShowGrid(False) 
        self.items_table.verticalHeader().setDefaultSectionSize(50)
        self.items_table.setStyleSheet(self.trans_table.styleSheet()) # Copy style if possible or rely on global QTableWidget style
        
        grp_items_layout.addWidget(self.items_table)
        
        right_layout.addWidget(grp_items, stretch=1)
        
        # Bottom Right: Item Statistics
        grp_stats = QGroupBox("Общая статистика по предметам")
        grp_stats_layout = QVBoxLayout(grp_stats)
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(3)
        self.stats_table.setHorizontalHeaderLabels(["Предмет", "Количество", "Сумма"])
        self.stats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        grp_stats_layout.addWidget(self.stats_table)
        
        right_layout.addWidget(grp_stats, stretch=1)
        
        content_layout.addLayout(right_layout, stretch=30) # Decrease width of right tables (30%)
        
        main_layout.addLayout(content_layout)

        # Footer
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        self.lbl_global_sum = QLabel("Общая сумма: 0")
        self.lbl_global_sum.setStyleSheet("font-size: 18px; font-weight: bold; color: #4aa3df; border: 2px solid #4aa3df; padding: 10px; border-radius: 5px;")
        footer_layout.addWidget(self.lbl_global_sum)
        main_layout.addLayout(footer_layout)

    def return_to_launcher(self):
        if self.parent_launcher:
            self.parent_launcher.show()
        else:
            # Re-create launcher if reference lost
            from modules.ui.launcher import LauncherWindow
            self.launcher = LauncherWindow(self.user_data)
            self.launcher.show()
        self.close()

    def add_transaction(self):
        # Placeholder
        pass
        
    def add_item_definition(self):
        # Placeholder
        pass

    def load_data(self):
        # Placeholder for loading from GSheets
        pass

    def init_trans_table(self):
        # Initial setup of table with one "Add" row
        self.trans_table.setRowCount(0) # Clear
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
                margin: 0px; /* REMOVE ALL MARGINS to center */
                padding-bottom: 5px; /* Adjust padding if font baseline is off */
            }
            QPushButton:hover {
                background-color: #252525;
            }
        """)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trans_table.setSpan(row_idx, 0, 1, 7) 
        self.trans_table.setCellWidget(row_idx, 0, btn_add)
        
        # Connect signal
        btn_add.clicked.connect(self.add_new_transaction_row)

    def add_new_transaction_row(self):
        # Insert a new editable row BEFORE the "Plus" row
        # Find the last row index, which is the plus button
        plus_row_index = self.trans_table.rowCount() - 1 
        
        # If the table is somehow empty or doesn't have the plus row at the end, handling might be tricky
        # But assuming logic holds:
        self.trans_table.insertRow(plus_row_index)
        row = plus_row_index 
        
        self.trans_table.setRowHeight(row, 45) # Match row height
        
        # 0. Number 
        num_item = QTableWidgetItem(str(row + 1))
        # Center alignment
        num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        num_item.setFlags(Qt.ItemFlag.ItemIsEnabled) # Read only
        num_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold)) # Bold
        self.trans_table.setItem(row, 0, num_item)

        # 1. Date - Using Custom DateEditClickable
        date_edit = DateEditClickable()
        date_edit.setDate(QDate.currentDate())
        # The keyPressEvent override handles "read only" behavior for typing
        
        # Use container for centering
        container_date = QWidget()
        layout_date = QHBoxLayout(container_date)
        layout_date.setContentsMargins(0,0,0,0)
        layout_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_date.addWidget(date_edit)
        self.trans_table.setCellWidget(row, 1, container_date)

        # 2. Item (ComboBox) - Empty by default
        item_combo = QComboBox()
        item_combo.setEditable(True)
        item_combo.setCurrentIndex(-1) # No selection
        item_combo.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter) # Center text in line edit
        
        # Use container for centering
        container_item = QWidget()
        layout_item = QHBoxLayout(container_item)
        layout_item.setContentsMargins(0,0,0,0)
        layout_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
        item_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed) # Expand horizontally
        layout_item.addWidget(item_combo)
        self.trans_table.setCellWidget(row, 2, container_item)

        # 3. Qty - Default to empty or 0 visually? 
        # Spinbox always has a number. Let's start with 0.
        qty_spin = QSpinBox()
        qty_spin.setRange(-999999, 999999)
        qty_spin.setValue(0) 
        qty_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qty_spin.valueChanged.connect(lambda: self.recalc_row(row))
        
        # Use container for centering
        container_qty = QWidget()
        layout_qty = QHBoxLayout(container_qty)
        layout_qty.setContentsMargins(0,0,0,0)
        layout_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_qty.addWidget(qty_spin)
        self.trans_table.setCellWidget(row, 3, container_qty)

        # 4. Price - Integer as requested
        price_spin = QSpinBox() # Changed from QDoubleSpinBox
        price_spin.setRange(-1000000000, 1000000000)
        price_spin.setValue(0)
        price_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price_spin.valueChanged.connect(lambda: self.recalc_row(row))
        
        # Use container for centering
        container_price = QWidget()
        layout_price = QHBoxLayout(container_price)
        layout_price.setContentsMargins(0,0,0,0)
        layout_price.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_price.addWidget(price_spin)
        self.trans_table.setCellWidget(row, 4, container_price)

        # 5. Sum (Calculated, Read Only Item)
        sum_item = QTableWidgetItem("0") # Integer 0
        sum_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        sum_item.setFlags(Qt.ItemFlag.ItemIsEnabled) # Read only
        sum_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold)) # Bold
        self.trans_table.setItem(row, 5, sum_item)

        # 6. Delete Action - REMOVED BUTTON as per request
        # Just create a cell widget that mimics the red square style
        
        del_label = QLabel()
        del_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: 2px solid #ff5555; 
                border-radius: 4px;
            }
        """)
        # Using a label as a widget to get borders
        # We wrap it in a container to respect cell size/alignment/margins
        
        container_del = QWidget()
        layout_del = QHBoxLayout(container_del)
        # Mimic QTableWidget::item margins: margin-bottom: 8px; margin-right: 4px;
        # But wait, QTableWidget styling is weird.
        # "margin-bottom: 8px" on item means 8px gap between rows?
        # If we remove margins here, the widget touches the cell boundaries.
        # The cell boundaries are defined by row height.
        # The user wants "окантовку как в наименовании".
        # Let's try to match the visual block size.
        layout_del.setContentsMargins(0, 0, 4, 8) 
        
        # del_label.setFixedHeight(30) # Let it expand
        layout_del.addWidget(del_label)
        
        self.trans_table.setCellWidget(row, 6, container_del)

        # Recalculate row numbers for all rows just in case
        self.update_row_numbers()
        
        # Initial calculation
        self.recalc_row(row)

    def update_row_numbers(self):
        # Iterate all rows except the last one (which is the + button)
        for r in range(self.trans_table.rowCount() - 1):
             item = self.trans_table.item(r, 0)
             if item:
                 item.setText(str(r + 1))

    def delete_row_by_widget(self, sender_widget):
        # Find the row that contains this widget
        row_to_delete = -1
        # Loop through rows to find the widget
        for r in range(self.trans_table.rowCount()):
             # The button is inside a container, which is the cell widget
            container = self.trans_table.cellWidget(r, 6)
            if container:
                # Our button is a child of this container
                if sender_widget in container.findChildren(QPushButton):
                    row_to_delete = r
                    break

        if row_to_delete != -1:
            self.trans_table.removeRow(row_to_delete)
            # Re-number rows
            self.update_row_numbers()
            
    def recalc_row(self, row):
        try:
            # If called by signal, find the row
            target_row = row
            sender = self.sender()
            
            # If recalculating from signal
            if sender and isinstance(sender, (QSpinBox, QDoubleSpinBox)):
                 # Find which row this sender belongs to
                found_sender = False
                for r in range(self.trans_table.rowCount()):
                    # Check columns 3 (Qty) and 4 (Price)
                    # The cell widget is a container, look inside it
                    container_qty = self.trans_table.cellWidget(r, 3)
                    container_price = self.trans_table.cellWidget(r, 4)
                    
                    if container_qty and sender in container_qty.findChildren((QSpinBox, QDoubleSpinBox)):
                        target_row = r
                        found_sender = True
                        break
                    if container_price and sender in container_price.findChildren((QSpinBox, QDoubleSpinBox)):
                        target_row = r
                        found_sender = True
                        break
                
                if not found_sender:
                     # Fallback if somehow not found or direct call with row
                     pass
            
            # Now calculate for target_row
            container_qty = self.trans_table.cellWidget(target_row, 3)
            container_price = self.trans_table.cellWidget(target_row, 4)
            sum_item = self.trans_table.item(target_row, 5)
            
            if container_qty and container_price and sum_item:
                # Extract spinboxes from containers
                # Assuming there is only one spinbox in each container
                qty_widgets = container_qty.findChildren((QSpinBox, QDoubleSpinBox))
                price_widgets = container_price.findChildren((QSpinBox, QDoubleSpinBox))
                
                if qty_widgets and price_widgets:
                    qty = qty_widgets[0].value()
                    price = price_widgets[0].value()
                    total = int(qty * price) # Integer sum
                    sum_item.setText(f"{total}")
        except Exception:
            pass

    def delete_transaction(self):
        # Old method, kept for compatibility if needed or removed
        pass
