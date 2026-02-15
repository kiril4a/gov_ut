from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDateEdit, QComboBox, 
                             QDoubleSpinBox, QSpinBox, QMessageBox, QGroupBox, QSizePolicy,
                             QCalendarWidget, QToolButton, QMenu, QAbstractSpinBox, QStyle, QApplication, QStyleOptionComboBox, QStyleOptionSpinBox, QWidgetAction, QLineEdit)
from PyQt6.QtCore import Qt, QDate, QEvent, QLocale, QRect, QPointF, QPoint, QSize
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QMouseEvent, QKeyEvent
from modules.core.google_service import GoogleService
from modules.core.utils import get_resource_path

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

class GovernorCabinetWindow(QMainWindow):
    def __init__(self, user_data, parent_launcher=None):
        super().__init__()
        self.user_data = user_data
        self.parent_launcher = parent_launcher
        self.google_service = GoogleService()
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

        btn_back = QPushButton("В лаунчер")
        btn_back.setStyleSheet("background-color: #555; border: 1px solid #777;")
        btn_back.clicked.connect(self.return_to_launcher)
        header_layout.addWidget(btn_back)
        
        main_layout.addLayout(header_layout)

        content_layout = QHBoxLayout()
        
        left_layout = QVBoxLayout()
        
        grp_trans = QGroupBox("Операции (Доход/Расход)")
        grp_trans_layout = QVBoxLayout(grp_trans)
        grp_trans_layout.setContentsMargins(5, 20, 5, 5)
        
        self.trans_table = QTableWidget()
        self.trans_table.setColumnCount(8)
        self.trans_table.setHorizontalHeaderLabels(["№", "Дата", "Тип", "Предмет", "Кол-во", "Цена", "Сумма", "x"])
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

        type_btn = QPushButton("-")
        type_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        type_btn.setProperty("is_income", False)
        type_btn.setFixedSize(24, 24)
        
        type_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5555; 
                color: white; 
                border-radius: 4px; 
                font-weight: bold;
                font-size: 18px; 
                border: none;
                padding: 0px; 
                margin: 0px;
                qproperty-text: "-";
            }
        """)
        
        container_type = QFrame()
        layout_type = QVBoxLayout(container_type)
        layout_type.setContentsMargins(0,0,0,0)
        layout_type.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_type.addWidget(type_btn)
        
        self.trans_table.setCellWidget(row, 2, container_type)

        item_combo = NoScrollComboBox()
        item_combo.setEditable(True)
        item_combo.setCurrentIndex(-1)
        item_combo.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        container_item = QWidget()
        layout_item = QHBoxLayout(container_item)
        layout_item.setContentsMargins(0,0,0,0)
        layout_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
        item_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_item.addWidget(item_combo)
        self.trans_table.setCellWidget(row, 3, container_item)

        qty_block = QFrame()
        qty_block_layout = QVBoxLayout(qty_block)
        qty_block_layout.setContentsMargins(0,0,0,0)
        qty_block_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qty_spin = NoScrollSpinBox()
        qty_spin.setRange(-999999, 999999)
        qty_spin.setValue(0) 
        qty_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qty_spin.valueChanged.connect(lambda: self.recalc_row(row))
        
        qty_block_layout.addWidget(qty_spin)
        self.trans_table.setCellWidget(row, 4, qty_block)

        price_spin = NoScrollSpinBox()
        price_spin.setRange(-1000000000, 1000000000)
        price_spin.setValue(0)
        price_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price_spin.valueChanged.connect(lambda: self.recalc_row(row))
        
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

        self.update_row_numbers()
        self.recalc_row(row)

    def toggle_type(self, row, btn):
        is_income = btn.property("is_income")
        new_state = not is_income
        btn.setProperty("is_income", new_state)
        
        # 8. If Income selected: Quantity section abolished effectively (Hidden).
        # Item name (service name) gets more focus.
        # 9. If Income (Profit) selected: Cannot change Sum.
        
        # Recalculate context for the row
        w_qty = self.trans_table.cellWidget(row, 4)
        w_price = self.trans_table.cellWidget(row, 5)
        
        if new_state: # Became Income
            # Style: Green +
            btn.setText("+")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4caf50; 
                    color: white; 
                    border-radius: 4px; 
                    font-weight: bold;
                    font-size: 18px;
                    border: none;
                    padding: 0px;
                    margin: 0px;
                }
            """)
            
            # Hide Qty (4)
            if w_qty: w_qty.setVisible(False)
            
            # If quantity was pre-selected or whatever, we logically treat it as 1
            # But visually we hide it.
            
            # Show Price (5) - This acts as the "Amount" input for Income
            if w_price: w_price.setVisible(True)
            
            # Sum (6) - Read Only (We revert specific editable widget if it was there)
            # Remove direct cell widget if exists (from previous logic check) and restore Item
            if self.trans_table.cellWidget(row, 6):
                self.trans_table.removeCellWidget(row, 6)
                
            sum_item = QTableWidgetItem("0")
            sum_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            sum_item.setFlags(Qt.ItemFlag.ItemIsEnabled) # Read only
            sum_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.trans_table.setItem(row, 6, sum_item)

            # Update Item column placeholder
            w_item = self.trans_table.cellWidget(row, 3)
            if w_item:
                combo = w_item.findChild(NoScrollComboBox)
                if combo:
                    combo.setPlaceholderText("Наименование услуги") # Service Name
            
        else: # Became Expense
            # Style: Red -
            btn.setText("-")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff5555; 
                    color: white; 
                    border-radius: 4px; 
                    font-weight: bold;
                    font-size: 18px;
                    border: none;
                    padding: 0px;
                    margin: 0px;
                }
            """)
            
            # Show Qty (4) and Price (5)
            if w_qty: w_qty.setVisible(True)
            if w_price: w_price.setVisible(True)
            
            # Ensure Sum (6) is Read Only (Standard)
            if self.trans_table.cellWidget(row, 6):
                self.trans_table.removeCellWidget(row, 6)
                
            sum_item = QTableWidgetItem("0")
            sum_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            sum_item.setFlags(Qt.ItemFlag.ItemIsEnabled) 
            sum_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.trans_table.setItem(row, 6, sum_item)
            
            w_item = self.trans_table.cellWidget(row, 3)
            if w_item:
                combo = w_item.findChild(NoScrollComboBox)
                if combo:
                    combo.setPlaceholderText("") # Default

        self.recalc_row(row)

    def show_calendar_popup(self, button):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                border: 1px solid #404040;
                border-radius: 8px; /* Rounded corners for the menu itself */
                padding: 5px;       /* Padding inside the menu */
            }
        """)
        
        calendar = CustomCalendarWidget(menu)
        calendar.setGridVisible(True)
        
        # Set selection to currently displayed date on the button
        text_date = button.text()
        if text_date:
            try:
                date_val = QDate.fromString(text_date, "dd.MM.yyyy")
                if date_val.isValid():
                    calendar.setSelectedDate(date_val)
            except:
                pass

        # Handle date selection
        def on_date_selected(date):
            button.setText(date.toString("dd.MM.yyyy"))
            menu.close()
            
        calendar.clicked.connect(on_date_selected)
        
        action =  QWidgetAction(menu)
        action.setDefaultWidget(calendar)
        menu.addAction(action)
        
        menu.exec(button.mapToGlobal(QPoint(0, button.height())))

    def update_row_numbers(self):
        for r in range(self.trans_table.rowCount() - 1):
             item = self.trans_table.item(r, 0)
             if item:
                 item.setText(str(r + 1))

    def delete_row_by_widget(self, sender_widget):
        row_to_delete = -1
        for r in range(self.trans_table.rowCount()):
            container = self.trans_table.cellWidget(r, 7)
            if container:
                if sender_widget in container.findChildren(QPushButton):
                    row_to_delete = r
                    break

        if row_to_delete != -1:
            self.trans_table.removeRow(row_to_delete)
            self.update_row_numbers()
            
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
                 btn_type = container_type.findChild(QPushButton)
                 if btn_type:
                     is_income = btn_type.property("is_income")

            container_qty = self.trans_table.cellWidget(target_row, 4)
            container_price = self.trans_table.cellWidget(target_row, 5)
            sum_item = self.trans_table.item(target_row, 6) 
            
            if container_price and sum_item:
                price_widgets = container_price.findChildren((QSpinBox, QDoubleSpinBox))
                price = price_widgets[0].value() if price_widgets else 0

                if is_income:
                    # Income: Sum = Price (Quantity ignored/hidden)
                    total = price
                    sum_item.setText(f"{total}")
                else:
                    # Expense: Sum = Price * Qty
                    qty_widgets = container_qty.findChildren((QSpinBox, QDoubleSpinBox)) if container_qty else []
                    qty = qty_widgets[0].value() if qty_widgets else 0
                    total = int(qty * price)
                    sum_item.setText(f"{total}")
        except Exception:
            pass

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
        self.items_table.insertRow(plus_row_index)
        row = plus_row_index 
        
        self.items_table.setRowHeight(row, 45)
        
        # 0. Item Name (Styled QLineEdit)
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Название")
        name_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 10px;
                color: #ffffff;
                padding: 4px;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #4aa3df;
                background-color: #2b2b2b;
            }
        """)
        
        container_name = QWidget()
        layout_name = QHBoxLayout(container_name)
        layout_name.setContentsMargins(5, 0, 5, 0)
        layout_name.addWidget(name_edit)
        self.items_table.setCellWidget(row, 0, container_name)

        # 1. Base Price (Double SpinBox)
        # Using a container for centering exactly like left table used for prices
        price_spin = NoScrollDoubleSpinBox()
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

    def delete_item_row_by_widget(self, sender_widget):
        row_to_delete = -1
        for r in range(self.items_table.rowCount()):
            container = self.items_table.cellWidget(r, 2)
            if container:
                if sender_widget in container.findChildren(QPushButton):
                    row_to_delete = r
                    break
        if row_to_delete != -1:
            self.items_table.removeRow(row_to_delete)
