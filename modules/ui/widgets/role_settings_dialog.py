from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QDialogButtonBox, QMenu, 
    QWidget, QSizePolicy, QFrame, QScrollArea, QGroupBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QStringListModel, QPropertyAnimation, QEasingCurve, QEvent
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon
from PyQt6.QtWidgets import QCompleter

from modules.core.firebase_service import get_usernames, get_user, list_users, can_assign_role, save_user_roles, resolve_user_permissions, DEPT_DEFAULT_PERMS, can_manage_user, can_assign_departments, create_user, delete_user

# Reusable style for completer popup dropdowns
COMPLETER_POPUP_STYLE = """
QListView {
    background-color: #2d2d2d; /* darker opaque background */
    color: white;
    border: 1px solid #5a5a5a; /* light border */
    border-radius: 8px;
    padding: 5px;
    outline: none;
}
QListView::item {
    padding: 8px 12px;
    border-radius: 4px;
    margin: 2px 0px;
}
QListView::item:hover {
    background-color: #4a4a4a;
}
QListView::item:selected {
    background-color: #2a82da;
    color: white;
}
QScrollBar:vertical {
    border: none;
    background: #2d2d2d;
    width: 10px;
    border-radius: 5px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #555;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #777;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

# Custom list widget to distinguish clicks on the checkbox indicator vs the row
class ModernListWidget(QListWidget):
    def mousePressEvent(self, event):
        # Toggle the checkbox on single click and consume the event to avoid
        # the default QListWidget behavior which can lead to double-toggling.
        try:
            pos = event.pos()
            item = self.itemAt(pos)
            if item is not None:
                try:
                    cur = item.checkState()
                    new_state = Qt.CheckState.Unchecked if cur == Qt.CheckState.Checked else Qt.CheckState.Checked
                    item.setCheckState(new_state)
                except Exception:
                    pass
                return  # consume the event; do not call base implementation
        except Exception:
            pass
        return super().mousePressEvent(event)

class ModernSelectionPopup(QDialog):
    """Современное всплывающее окно выбора с анимацией и улучшенным дизайном"""
    
    def __init__(self, parent=None, title="", items=None, preselected=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        
        # Настройки окна
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        
        # Основной контейнер с тенью
        main_widget = QWidget(self)
        main_widget.setObjectName("popupContainer")
        main_widget.setStyleSheet("""
            QWidget#popupContainer {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 24px; /* Увеличенный радиус с 16px до 24px */
            }
        """)
        
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(25, 25, 25, 25)  # Увеличенные отступы с 20px до 25px
        layout.setSpacing(18)  # Увеличенный интервал с 15px до 18px
        
        # Заголовок
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 18px; /* Увеличен с 16px до 18px */
                font-weight: 600;
                padding: 12px 16px; /* Увеличены отступы */
                background-color: #363636;
                border-radius: 14px; /* Увеличен радиус */
                border-left: 6px solid #2a82da; /* Утолщена левая граница */
            }
        """)
        layout.addWidget(title_label)
        
        # Список элементов
        self.list_widget = ModernListWidget()
        # Disable whole-row visual selection: only the checkbox will indicate selection
        try:
            self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        except Exception:
            pass
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #363636;
                border: 1px solid #404040;
                border-radius: 18px; /* Увеличен радиус с 12px до 18px */
                padding: 12px; /* Увеличены отступы */
                outline: none;
            }
            QListWidget::item {
                background-color: #404040;
                color: #ffffff;
                padding: 14px 20px; /* Увеличены отступы внутри элементов */
                margin: 6px 0px; /* Увеличены отступы между элементами */
                border-radius: 12px; /* Увеличен радиус элементов */
                font-weight: bold;
                font-size: 15px; /* Увеличен шрифт */
            }
            QListWidget::item:hover {
                background-color: #4a4a4a;
                border-left: 4px solid #2a82da; /* Утолщена левая граница при наведении */
                padding-left: 24px; /* Дополнительный отступ при наведении */
            }
            /* Prevent full-row selection highlight; leave checkbox indicator as the only visual state */
            QListWidget::item:selected {
                background-color: transparent;
                color: #ffffff;
            }
            QListWidget::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #888;
                background-color: white;
            }
            QListWidget::indicator:checked {
                background-color: #2a82da;
                border: 2px solid #2a82da;
                image: url(assets/check.png);
            }
            QListWidget::indicator:unchecked:hover {
                border: 2px solid #2a82da;
            }
        """)
        
        for item_text in (items or []):
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            # mark preselected items as checked
            try:
                if preselected and item_text in (preselected or []):
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
            except Exception:
                try:
                    item.setCheckState(Qt.CheckState.Unchecked)
                except Exception:
                    pass
            self.list_widget.addItem(item)
        
        # Click behavior handled by ModernListWidget.mousePressEvent; no additional connection required
        
        layout.addWidget(self.list_widget)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)  # Увеличен интервал между кнопками
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: #e0e0e0;
                border: 1px solid #505050;
                border-radius: 14px; /* Увеличен радиус с 10px до 14px */
                padding: 12px 28px; /* Увеличены отступы */
                font-weight: 600;
                font-size: 15px; /* Увеличен шрифт */
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #606060;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        ok_btn = QPushButton("Применить")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 14px; /* Увеличен радиус с 10px до 14px */
                padding: 12px 28px; /* Увеличены отступы */
                font-weight: 600;
                font-size: 15px; /* Увеличен шрифт */
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
        """)
        ok_btn.clicked.connect(self.accept)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(ok_btn)
        
        layout.addLayout(buttons_layout)
        
        # Устанавливаем размер окна
        self.resize(450, 500)  # Увеличен размер с 400x450 до 450x500
        
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_widget)
    
    def selected(self):
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count()) 
                if self.list_widget.item(i).checkState() == Qt.CheckState.Checked]


class RoleSettingsDialog(QDialog):
    def __init__(self, parent=None, current_user=None):
        self.current_user = current_user if current_user is not None else getattr(parent, 'user_data', None)
        super().__init__(parent)
        
        # Настройки окна
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle("Настройка ролей пользователя")
        self.setModal(True)
        self.resize(700, 600)  # Увеличен размер с 650x550 до 700x600
        
        # Основной контейнер
        main_widget = QWidget(self)
        main_widget.setObjectName("mainContainer")
        
        # Основной layout
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(30, 30, 30, 30)  # Увеличены отступы с 25px до 30px
        layout.setSpacing(22)  # Увеличен интервал с 20px до 22px
        
        # Заголовок с кнопкой закрытия
        title_layout = QHBoxLayout()
        
        title_label = QLabel("⚙️ Настройка ролей пользователя")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px; /* Увеличен с 20px до 24px */
                font-weight: 700;
                padding: 10px 0;
            }
        """)
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 36)  # Увеличен размер кнопки
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: #e0e0e0;
                border: none;
                border-radius: 18px; /* Увеличен радиус */
                font-size: 18px; /* Увеличен шрифт */
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d63031;
                color: white;
            }
        """)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)
        
        layout.addLayout(title_layout)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #404040; max-height: 2px;")  # Утолщена линия
        layout.addWidget(separator)
        
        # Панель выбора режима
        mode_panel = QFrame()
        mode_panel.setStyleSheet("""
            QFrame {
                background-color: #363636;
                border-radius: 16px; /* Увеличен радиус с 12px до 16px */
                padding: 8px;
            }
        """)
        mode_layout = QHBoxLayout(mode_panel)
        mode_layout.setContentsMargins(15, 8, 15, 8)  # Увеличены отступы
        
        # Кнопки режимов
        self.mode_roles_btn = QPushButton("📋 Настройка ролей")
        self.mode_roles_btn.setCheckable(True)
        self.mode_roles_btn.setChecked(True)
        self.mode_roles_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.mode_add_btn = QPushButton("➕ Добавить пользователя")
        self.mode_add_btn.setCheckable(True)
        self.mode_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.mode_delete_btn = QPushButton("🗑️ Удалить пользователя")
        self.mode_delete_btn.setCheckable(True)
        self.mode_delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Проверка прав
        try:
            res = resolve_user_permissions(self.current_user) if self.current_user else {}
            roles = set(res.get('roles', []))
            is_global = bool(roles & {'Admin', 'Governor'})
        except Exception:
            is_global = False
        
        self.mode_add_btn.setVisible(is_global)
        self.mode_delete_btn.setVisible(is_global)
        
        # Стиль для кнопок режимов
        mode_button_style = """
            QPushButton {
                background-color: transparent;
                color: #a0a0a0;
                border: none;
                border-radius: 12px; /* Увеличен радиус с 8px до 12px */
                padding: 12px 24px; /* Увеличены отступы */
                font-weight: 600;
                font-size: 15px; /* Увеличен шрифт */
            }
            QPushButton:hover {
                background-color: #404040;
                color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #2a82da;
                color: white;
            }
        """
        
        self.mode_roles_btn.setStyleSheet(mode_button_style)
        self.mode_add_btn.setStyleSheet(mode_button_style)
        self.mode_delete_btn.setStyleSheet(mode_button_style)
        
        self.mode_roles_btn.clicked.connect(lambda: self.set_mode('roles'))
        self.mode_add_btn.clicked.connect(lambda: self.set_mode('add'))
        self.mode_delete_btn.clicked.connect(lambda: self.set_mode('delete'))
        
        mode_layout.addWidget(self.mode_roles_btn)
        mode_layout.addWidget(self.mode_add_btn)
        mode_layout.addWidget(self.mode_delete_btn)
        mode_layout.addStretch()
        
        layout.addWidget(mode_panel)
        
        # Контентная область
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(18)  # Увеличен интервал
        
        # Панель ввода для режима ролей
        self.roles_input_widget = QWidget()
        roles_input_layout = QHBoxLayout(self.roles_input_widget)
        roles_input_layout.setContentsMargins(0, 0, 0, 0)
        roles_input_layout.setSpacing(15)  # Добавлен интервал между элементами
        
        username_label = QLabel("👤 Логин пользователя:")
        username_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-weight: 600;
                padding: 12px 20px; /* Увеличены отступы */
                background-color: #363636;
                border-radius: 14px; /* Увеличен радиус */
                min-width: 160px; /* Увеличена минимальная ширина */
                font-size: 15px; /* Увеличен шрифт */
            }
        """)
        roles_input_layout.addWidget(username_label)
        
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Введите логин для поиска...")
        self.input_username.setStyleSheet("""
            QLineEdit {
                background-color: #363636;
                color: white;
                border: 2px solid #404040;
                border-radius: 14px; /* Увеличен радиус с 10px до 14px */
                padding: 12px 20px; /* Увеличены отступы */
                font-size: 15px; /* Увеличен шрифт */
                font-weight: 500;
                min-width: 280px; /* Увеличена минимальная ширина */
            }
            QLineEdit:focus {
                border-color: #2a82da;
            }
        """)
        # Only focus on click (prevents automatic focus when dialog opens)
        try:
            self.input_username.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        except Exception:
            pass
        
        # Комплектор
        self.completer_model = QStringListModel(self)
        self.completer = QCompleter(self.completer_model, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setWidget(self.input_username)

        # Настройка выпадающего списка комплектора
        popup = self.completer.popup()
        popup.setStyleSheet(COMPLETER_POPUP_STYLE)
        # Убрано переопределение windowFlags для popup, так как это вызывает баг с появлением пустого окна
        # Но мы можем добавить NoDropShadowWindowHint чтобы избежать артефактов
        try:
            popup.setWindowFlags(popup.windowFlags() | Qt.WindowType.NoDropShadowWindowHint)
        except Exception:
            pass
        
        # Ensure single-click on the popup selects the user
        try:
            popup.clicked.connect(lambda idx: self._on_completer_popup_clicked(idx))
        except Exception:
            pass
        
        roles_input_layout.addWidget(self.input_username)
        roles_input_layout.addStretch()
        
        content_layout.addWidget(self.roles_input_widget)
        
        # Панели для добавления/удаления
        self.add_panel = self.create_add_panel()
        self.delete_panel = self.create_delete_panel()
        
        content_layout.addWidget(self.add_panel)
        content_layout.addWidget(self.delete_panel)
        
        # Информационная панель
        self.info_group = QGroupBox("Информация о пользователе")
        self.info_group.setStyleSheet("""
            QGroupBox {
                color: #e0e0e0;
                font-weight: 600;
                font-size: 16px; /* Увеличен шрифт */
                border: 2px solid #404040;
                border-radius: 16px; /* Увеличен радиус */
                margin-top: 18px; /* Увеличен отступ */
                padding-top: 18px; /* Увеличен отступ */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 18px; /* Увеличен отступ */
                padding: 0 12px 0 12px; /* Увеличены отступы */
                background-color: #2d2d2d;
            }
        """)
        info_layout = QVBoxLayout(self.info_group)
        info_layout.setContentsMargins(18, 18, 18, 18)  # Увеличены отступы
        
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("""
            QLabel {
                color: #b0b0b0;
                background-color: #363636;
                border-radius: 14px; /* Увеличен радиус */
                padding: 18px; /* Увеличены отступы */
                font-size: 14px; /* Увеличен шрифт */
                line-height: 1.8; /* Увеличена высота строки */
            }
        """)
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        
        content_layout.addWidget(self.info_group)
        
        # Панель действий
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 15, 0, 0)  # Увеличен отступ сверху
        actions_layout.setSpacing(15)  # Увеличен интервал между кнопками
        
        # Кнопки выбора
        self.btn_roles = self.create_action_button("🎭 Выбрать роли", "#2a82da")
        self.btn_depts = self.create_action_button("🏢 Выбрать отделы", "#27ae60")
        self.btn_perms = self.create_action_button("🔑 Выбрать разрешения", "#e67e22")
        
        self.btn_roles.clicked.connect(self.open_roles_popup)
        self.btn_depts.clicked.connect(self.open_depts_popup)
        self.btn_perms.clicked.connect(self.open_perms_popup)
        
        actions_layout.addWidget(self.btn_roles)
        actions_layout.addWidget(self.btn_depts)
        actions_layout.addWidget(self.btn_perms)
        actions_layout.addStretch()
        
        content_layout.addWidget(actions_widget)
        
        # Кнопки сохранения/отмены
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 15, 0, 0)  # Увеличен отступ сверху
        
        self.btn_save = QPushButton("💾 Сохранить изменения")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 14px; /* Увеличен радиус */
                padding: 14px 35px; /* Увеличены отступы */
                font-weight: 700;
                font-size: 15px; /* Увеличен шрифт */
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.btn_save.clicked.connect(self.on_save)
        
        self.btn_cancel = QPushButton("✕ Отмена")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: #e0e0e0;
                border: none;
                border-radius: 14px; /* Увеличен радиус */
                padding: 14px 35px; /* Увеличены отступы */
                font-weight: 700;
                font-size: 15px; /* Увеличен шрифт */
            }
            QPushButton:hover {
                background-color: #d63031;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_save)
        buttons_layout.addWidget(self.btn_cancel)
        
        content_layout.addWidget(buttons_widget)
        content_layout.addStretch()
        
        layout.addWidget(content_widget)
        
        # Устанавливаем основной стиль
        main_widget.setStyleSheet("""
            QWidget#mainContainer {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 24px; /* Увеличен радиус с 20px до 24px */
            }
        """)
        
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_widget)
        
        # Внутренние переменные
        self.role_hierarchy = [
            'Администратор',
            'Губернатор',
            'Министр',
            'Начальник',
            'Заместитель',
            'Подчиненный',
            'Посетитель'
        ]
        
        self.role_to_depts = {
            'Администратор': ['УТ', 'ЭУ', 'УК'],
            'Губернатор': ['УТ', 'ЭУ', 'УК'],
            'Министр': ['ЭУ', 'УК'],
            'Начальник': ['УТ', 'ЭУ', 'УК'],
            'Заместитель': ['УТ', 'ЭУ', 'УК'],
            'Подчиненный': ['УТ', 'ЭУ', 'УК'],
        }
        
        self.label_to_key = {
            'Администратор': 'Admin',
            'Губернатор': 'Governor',
            'Министр': 'Minister',
            'Начальник': 'Head',
            'Заместитель': 'Deputy',
            'Подчиненный': 'Employee',
            'Посетитель': 'Visitor',
        }
        
        # Состояние
        self.mode = 'roles'
        self.loaded_user = None
        self.selected_roles = []
        self.selected_depts = []
        self.selected_perms = []
        self._all_user_docs = None
        
        # Подключение сигналов
        self.input_username.textChanged.connect(self.on_username_typed)
        
        # Обработка фокуса для показа всех пользователей
        self.input_username.installEventFilter(self)
        
        try:
            self.completer.activated.connect(self.on_username_selected)
        except Exception:
            pass
        
        # Инициализация видимости
        self.set_mode('roles')
    
    def showEvent(self, event):
        super().showEvent(event)
        # Анимация появления
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(200)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()

    def eventFilter(self, obj, event):
        # On focus show full suggestions list for the relevant field
        if (obj == self.input_username and event.type() == QEvent.Type.FocusIn):
            # refresh suggestions and show popup only if not already visible
            self._refresh_user_suggestions()
            try:
                popup = self.completer.popup()
                if not popup.isVisible():
                    self.completer.complete()
            except Exception:
                try:
                    self.completer.complete()
                except Exception:
                    pass
        elif (hasattr(self, 'del_login') and obj == self.del_login and event.type() == QEvent.Type.FocusIn):
            self._refresh_user_suggestions()
            try:
                if hasattr(self, 'del_completer'):
                    del_popup = self.del_completer.popup()
                    if not del_popup.isVisible():
                        self.del_completer.complete()
            except Exception:
                try:
                    if hasattr(self, 'del_completer'):
                        self.del_completer.complete()
                except Exception:
                    pass
        return super().eventFilter(obj, event)

    def _is_widget_or_child(self, widget, candidate):
        # Returns True if candidate is widget or a descendant of widget
        try:
            w = candidate
            while w is not None:
                if w == widget:
                    return True
                w = w.parentWidget()
        except Exception:
            pass
        return False

    def mousePressEvent(self, event):
        # If user clicks outside the input fields, clear their focus and hide completer popups
        try:
            clicked = self.childAt(event.pos())
            inside_input = False
            if clicked is not None:
                if self._is_widget_or_child(self.input_username, clicked):
                    inside_input = True
                if hasattr(self, 'del_login') and self._is_widget_or_child(self.del_login, clicked):
                    inside_input = True
            if not inside_input:
                try:
                    self.input_username.clearFocus()
                except Exception:
                    pass
                try:
                    popup = self.completer.popup()
                    if popup.isVisible():
                        popup.hide()
                except Exception:
                    pass
                try:
                    if hasattr(self, 'del_login'):
                        self.del_login.clearFocus()
                except Exception:
                    pass
                try:
                    if hasattr(self, 'del_completer'):
                        dpopup = self.del_completer.popup()
                        if dpopup.isVisible():
                            dpopup.hide()
                except Exception:
                    pass
        except Exception:
            pass
        super().mousePressEvent(event)

    def _is_doc_manageable(self, d):
        """Return True if the current_user may manage the user document d.
        Updated rule: for users with restricted roles (Minister/Head/Deputy) the
        assigner may manage the target only when they share at least one
        department. Targets without departments are NOT manageable by these
        restricted assigners. Global roles (Admin/Governor) keep backend ACL.
        """
        try:
            # Basic backend ACL first
            if not can_manage_user(self.current_user, d):
                return False
        except Exception:
            return False

        try:
            assigner_res = resolve_user_permissions(self.current_user) if self.current_user else {}
            assigner_roles = set(assigner_res.get('roles', []))
            assigner_depts = set(assigner_res.get('departments', []))
            # Roles that are limited to managing only same-department users
            restricted_roles = {'Minister', 'Head', 'Deputy'}

            # If assigner has a restricted role, enforce department intersection
            if assigner_roles & restricted_roles:
                target_depts = set(d.get('departments') or [])
                # Require target to have departments and share at least one
                if not target_depts:
                    return False
                if not (assigner_depts & target_depts):
                    return False
        except Exception:
            # On error resolving permissions, deny management
            return False

        return True

    def _can_manage_doc(self, d):
        # Delegate to the stricter _is_doc_manageable implementation to keep
        # listing and editing checks consistent (restrict Heads/Ministers/Deputies
        # to same-department targets).
        try:
            return self._is_doc_manageable(d)
        except Exception:
            return False

    def _refresh_user_suggestions(self):
        # Load all manageable users and update completer models
        if self._all_user_docs is None:
            try:
                self._all_user_docs = list_users() or []
            except Exception:
                self._all_user_docs = []
        suggestions = []
        for d in self._all_user_docs:
            try:
                name = d.get('username') or d.get('login') or ''
                if not name:
                    continue
                try:
                    # Use unified manageability check that includes department rules
                    if not self._can_manage_doc(d):
                        continue
                except Exception:
                    continue
                suggestions.append(name)
            except Exception:
                continue
        suggestions = sorted(suggestions)
        try:
            self.completer_model.setStringList(suggestions)
        except Exception:
            pass
        try:
            if hasattr(self, 'del_completer_model'):
                self.del_completer_model.setStringList(suggestions)
        except Exception:
            pass

    def create_add_panel(self):
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #363636;
                border-radius: 16px; /* Увеличен радиус */
                padding: 18px; /* Увеличены отступы */
            }
        """)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)  # Увеличены отступы
        layout.setSpacing(15)  # Увеличен интервал
        
        icon_label = QLabel("➕")
        icon_label.setStyleSheet("font-size: 28px; background: none;")  # Увеличен размер иконки
        layout.addWidget(icon_label)
        
        self.add_login = QLineEdit()
        self.add_login.setPlaceholderText("Логин нового пользователя")
        self.add_login.setStyleSheet("""
            QLineEdit {
                background-color: #404040;
                color: white;
                border: 1px solid #505050;
                border-radius: 12px; /* Увеличен радиус */
                padding: 12px 16px; /* Увеличены отступы */
                font-size: 15px; /* Увеличен шрифт */
            }
            QLineEdit:focus {
                border-color: #2a82da;
            }
        """)
        layout.addWidget(self.add_login)
        
        self.add_password = QLineEdit()
        self.add_password.setPlaceholderText("Пароль")
        self.add_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_password.setStyleSheet("""
            QLineEdit {
                background-color: #404040;
                color: white;
                border: 1px solid #505050;
                border-radius: 12px; /* Увеличен радиус */
                padding: 12px 16px; /* Увеличены отступы */
                font-size: 15px; /* Увеличен шрифт */
            }
            QLineEdit:focus {
                border-color: #2a82da;
            }
        """)
        layout.addWidget(self.add_password)
        
        self.add_create_btn = QPushButton("Создать")
        self.add_create_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 12px; /* Увеличен радиус */
                padding: 12px 25px; /* Увеличены отступы */
                font-weight: 600;
                font-size: 15px; /* Увеличен шрифт */
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.add_create_btn.clicked.connect(self._on_create_user)
        layout.addWidget(self.add_create_btn)
        
        return panel
    
    def create_delete_panel(self):
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #363636;
                border-radius: 16px; /* Увеличен радиус */
                padding: 18px; /* Увеличены отступы */
            }
        """)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)  # Увеличены отступы
        layout.setSpacing(15)  # Увеличен интервал
        
        icon_label = QLabel("🗑️")
        icon_label.setStyleSheet("font-size: 28px; background: none;")  # Увеличен размер иконки
        layout.addWidget(icon_label)
        
        self.del_login = QLineEdit()
        self.del_login.setPlaceholderText("Логин пользователя для удаления")
        self.del_login.setStyleSheet("""
            QLineEdit {
                background-color: #404040;
                color: white;
                border: 1px solid #505050;
                border-radius: 12px; /* Увеличен радиус */
                padding: 12px 16px; /* Увеличены отступы */
                font-size: 15px; /* Увеличен шрифт */
            }
            QLineEdit:focus {
                border-color: #2a82da;
            }
        """)
        # Only focus on click
        try:
            self.del_login.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        except Exception:
            pass
        layout.addWidget(self.del_login)
        
        # Completer for delete field (same style/behaviour as main input)
        self.del_completer_model = QStringListModel(self)
        self.del_completer = QCompleter(self.del_completer_model, self)
        self.del_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.del_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.del_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.del_completer.setWidget(self.del_login)
        del_popup = self.del_completer.popup()
        del_popup.setStyleSheet(COMPLETER_POPUP_STYLE)
        # Убрано переопределение windowFlags для del_popup
        try:
            del_popup.setWindowFlags(del_popup.windowFlags() | Qt.WindowType.NoDropShadowWindowHint)
        except Exception:
            pass
        try:
            del_popup.clicked.connect(lambda idx: self._on_del_completer_popup_clicked(idx))
        except Exception:
            pass
        # del_completer attached via setWidget; avoid calling setCompleter twice to prevent duplicate popups
        # ensure del_login also responds to focus to show full suggestions
        self.del_login.installEventFilter(self)
        # connect single-click activation
        try:
            self.del_completer.activated.connect(self.on_delete_username_selected)
        except Exception:
            pass
        
        self.del_delete_btn = QPushButton("Удалить")
        self.del_delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d63031;
                color: white;
                border: none;
                border-radius: 12px; /* Увеличен радиус */
                padding: 12px 25px; /* Увеличены отступы */
                font-weight: 600;
                font-size: 15px; /* Увеличен шрифт */
            }
            QPushButton:hover {
                background-color: #ff6b6b;
            }
        """)
        self.del_delete_btn.clicked.connect(self._on_delete_user)
        layout.addWidget(self.del_delete_btn)
        
        return panel

    def on_delete_username_selected(self, name):
        # Single-click selection handler for delete field
        self.del_login.setText(name)
        # remove focus so popup hides immediately
        try:
            self.del_login.clearFocus()
        except Exception:
            pass

    def create_action_button(self, text, color):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 12px; /* Увеличен радиус с 8px до 12px */
                padding: 12px 20px; /* Увеличены отступы */
                font-weight: 600;
                font-size: 14px; /* Увеличен шрифт */
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(color)};
            }}
            QPushButton:disabled {{
                background-color: #404040;
                color: #888;
            }}
        """)
        return btn
    
    def lighten_color(self, color):
        # Простое осветление цвета для hover эффекта
        colors = {
            "#2a82da": "#3a92ea",
            "#27ae60": "#2ecc71",
            "#e67e22": "#f39c12",
        }
        return colors.get(color, color)
    
    def set_mode(self, mode):
        self.mode = mode
        
        # Обновление состояния кнопок
        self.mode_roles_btn.setChecked(mode == 'roles')
        self.mode_add_btn.setChecked(mode == 'add')
        self.mode_delete_btn.setChecked(mode == 'delete')
        
        # Видимость панелей
        self.roles_input_widget.setVisible(mode == 'roles')
        self.add_panel.setVisible(mode == 'add')
        self.delete_panel.setVisible(mode == 'delete')
        
        # Видимость элементов управления ролями
        is_roles = (mode == 'roles')
        self.info_group.setVisible(is_roles and self.loaded_user is not None)
        
        if is_roles:
            # Use unified document manageability that includes department rules
            try:
                manageable = (self.loaded_user is not None and self._is_doc_manageable(self.loaded_user))
            except Exception:
                manageable = False
            self.btn_roles.setVisible(manageable)
            self.btn_depts.setVisible(manageable)
            self.btn_perms.setVisible(manageable)
            self.btn_save.setVisible(True)
        else:
            self.btn_roles.setVisible(False)
            self.btn_depts.setVisible(False)
            self.btn_perms.setVisible(False)
            # Clear search and loaded user state so no stale info remains
            try:
                self.input_username.clear()
            except Exception:
                pass
            self.loaded_user = None
            # Clear selected state and hide info panel
            self.selected_roles = []
            self.selected_depts = []
            self.selected_perms = []
            try:
                self.info_label.setText('')
            except Exception:
                pass
            try:
                self.info_group.setVisible(False)
            except Exception:
                pass
            # Also clear add/delete inputs if present
            try:
                if hasattr(self, 'add_login'):
                    self.add_login.clear()
                if hasattr(self, 'add_password'):
                    self.add_password.clear()
                if hasattr(self, 'del_login'):
                    self.del_login.clear()
            except Exception:
                pass
        
        if mode == 'roles':
            # Do not autofocus; require user click to activate input to avoid immediate focus when dialog opens
            pass
    
    def on_username_typed(self, text):
        # ... (сохраняем логику из оригинального кода)
        txt = text.strip()
        if not txt:
            if self._all_user_docs is None:
                try:
                    self._all_user_docs = list_users() or []
                except Exception:
                    self._all_user_docs = []
            suggestions = []
            for d in self._all_user_docs:
                try:
                    name = d.get('username') or d.get('login') or ''
                    if not name:
                        continue
                    try:
                        if not self._can_manage_doc(d):
                            continue
                    except Exception:
                        continue
                    suggestions.append(name)
                except Exception:
                    continue
            self.completer_model.setStringList(sorted(suggestions))
            self.loaded_user = None
            self.btn_roles.setVisible(False)
            self.btn_depts.setVisible(False)
            self.btn_perms.setVisible(False)
            self.info_group.setVisible(False)
            return
        
        if self._all_user_docs is None:
            try:
                self._all_user_docs = list_users() or []
            except Exception:
                self._all_user_docs = []
        
        suggestions = []
        ltxt = txt.lower()
        for d in self._all_user_docs:
            try:
                name = d.get('username') or d.get('login') or ''
                if not name:
                    continue
                if ltxt not in name.lower():
                    continue
                try:
                    if not self._can_manage_doc(d):
                        continue
                except Exception:
                    continue
                suggestions.append(name)
                if len(suggestions) >= 200:
                    break
            except Exception:
                continue
        
        self.completer_model.setStringList(sorted(suggestions))
        
    def on_username_selected(self, name):
        self.input_username.setText(name)
        doc = None
        if self._all_user_docs is not None:
            for d in self._all_user_docs:
                if (d.get('username') or d.get('login')) == name:
                    doc = d
                    break
        
        if not self._can_manage_doc(doc or name):
            QMessageBox.warning(self, "Доступ запрещен", 
                               "Вы не можете редактировать этого пользователя.",
                               QMessageBox.StandardButton.Ok)
            return
        self.load_user(name)
        
        # Убираем фокус с поля ввода, чтобы скрыть выпадающий список
        try:
            self.input_username.clearFocus()
        except Exception:
            pass

    def _on_completer_popup_clicked(self, index):
        # index is a QModelIndex from the popup; extract display text and select
        try:
            text = index.data(Qt.ItemDataRole.DisplayRole)
        except Exception:
            try:
                text = self.completer.model().data(index, Qt.ItemDataRole.DisplayRole)
            except Exception:
                text = None
        if text:
            self.on_username_selected(text)

    def _on_del_completer_popup_clicked(self, index):
        try:
            text = index.data(Qt.ItemDataRole.DisplayRole)
        except Exception:
            try:
                text = self.del_completer.model().data(index, Qt.ItemDataRole.DisplayRole)
            except Exception:
                text = None
        if text:
            self.on_delete_username_selected(text)
    
    def load_user(self, username):
        try:
            u = get_user(username)
        except Exception:
            u = None
        
        self.loaded_user = u
        
        if u:
            # Unified check (backend ACL + department rules)
            try:
                manageable = self._is_doc_manageable(u)
            except Exception:
                manageable = False
            self.btn_roles.setVisible(manageable)
            self.btn_depts.setVisible(manageable)
            self.btn_perms.setVisible(manageable)
            
            if not manageable:
                QMessageBox.information(self, "Ограничение", 
                                      "Вы видите этого пользователя, но не можете изменять его роли/отделы.")
            
            db_roles = set(u.get('roles') or [])
            valid_keys = set(self.label_to_key.values())
            self.selected_roles = [r for r in db_roles if r in valid_keys]
            self.selected_depts = list(u.get('departments') or [])
            self.selected_perms = list(u.get('permissions') or [])
            
            self.update_info_label()
        else:
            self.btn_roles.setVisible(False)
            self.btn_depts.setVisible(False)
            self.btn_perms.setVisible(False)
            self.info_group.setVisible(False)
            self.selected_roles = []
            self.selected_depts = []
            self.selected_perms = []
    
    def open_roles_popup(self):
        allowed = []
        for lbl, key in self.label_to_key.items():
            try:
                if can_assign_role(self.current_user, key):
                    allowed.append(lbl)
            except Exception:
                continue
        
        if not allowed:
            QMessageBox.information(self, "Нет доступных ролей", 
                                  "У вас нет прав назначать какие-либо роли.")
            return
        
        pre = [lbl for lbl, key in self.label_to_key.items() 
               if key in self.selected_roles and lbl in allowed]
        
        popup = ModernSelectionPopup(self, title="Выберите роли", items=allowed, preselected=pre)
        
        # Центрирование
        center = self.mapToGlobal(self.rect().center())
        popup.move(int(center.x() - popup.width()/2), int(center.y() - popup.height()/2))
        
        if popup.exec() == QDialog.DialogCode.Accepted:
            selected = popup.selected()
            self.selected_roles = [self.label_to_key.get(s) for s in selected if self.label_to_key.get(s)]
            
            # Обновление доступных отделов
            allowed = set()
            for lbl, key in self.label_to_key.items():
                if key in self.selected_roles:
                    allowed.update(self.role_to_depts.get(lbl, []))
            if not allowed:
                allowed = set(['УТ', 'ЭУ', 'УК'])
            
            self.selected_depts = [d for d in self.selected_depts if d in allowed]
            self.update_info_label()
    
    def open_depts_popup(self):
        allowed = set()
        for lbl, key in self.label_to_key.items():
            if key in self.selected_roles:
                allowed.update(self.role_to_depts.get(lbl, []))
        
        if not allowed:
            allowed = set(['УТ', 'ЭУ', 'УК'])
        
        # Проверка прав на назначение отделов
        try:
            assigner_res = resolve_user_permissions(self.current_user) if self.current_user else {}
        except Exception:
            assigner_res = {}
        
        assigner_roles = set(assigner_res.get('roles', []))
        global_assign_roles = {'Admin', 'Governor', 'Minister'}
        
        if not (assigner_roles & global_assign_roles):
            assigner_depts = set(assigner_res.get('departments', []))
            if assigner_depts:
                allowed = allowed & assigner_depts
            else:
                allowed = set()
        
        if not allowed:
            QMessageBox.information(self, "Нет доступных отделов", 
                                  "У вас нет прав назначать отделы для этого пользователя.")
            return
        
        popup = ModernSelectionPopup(self, title="Выберите отделы", 
                                    items=list(allowed), preselected=self.selected_depts)
        
        center = self.mapToGlobal(self.rect().center())
        popup.move(int(center.x() - popup.width()/2), int(center.y() - popup.height()/2))
        
        if popup.exec() == QDialog.DialogCode.Accepted:
            self.selected_depts = popup.selected()
            self.update_info_label()
    
    def open_perms_popup(self):
        synth = {
            'roles': self.selected_roles,
            'departments': self.selected_depts,
            'permissions': self.selected_perms or []
        }
        try:
            resolved = resolve_user_permissions(synth)
            perms_set = set()
            for d in self.selected_depts:
                perms_set.update(DEPT_DEFAULT_PERMS.get(d, []))
            perms_set.update([p for p in resolved.get('permissions', []) 
                            if p not in ('ut.sync', 'ut.access')])
            perms_list = sorted(perms_set)
        except Exception:
            perms_list = []
            
        # Словарь для перевода разрешений на человеческий язык
        perm_translations = {
            'admin.full': 'Полный доступ (Админ)',
            'governor.access': 'Доступ губернатора',
            'ut.view': 'Просмотр УТ',
            'ut.edit': 'Редактирование УТ',
            'ut.upload': 'Загрузка УТ',
            'ut.sync': 'Синхронизация УТ',
            'ut.access': 'Доступ к УТ'
        }
        
        # Переводим список разрешений для отображения
        display_items = [perm_translations.get(p, p) for p in perms_list]
        
        # Переводим предвыбранные разрешения для отображения
        display_preselected = [perm_translations.get(p, p) for p in self.selected_perms]
        
        popup = ModernSelectionPopup(self, title="Выберите разрешения", 
                                    items=display_items, preselected=display_preselected)
        
        center = self.mapToGlobal(self.rect().center())
        popup.move(int(center.x() - popup.width()/2), int(center.y() - popup.height()/2))
        
        if popup.exec() == QDialog.DialogCode.Accepted:
            # Обратный перевод из человеческого языка в ключи разрешений
            reverse_translations = {v: k for k, v in perm_translations.items()}
            
            selected_display = popup.selected()
            self.selected_perms = [reverse_translations.get(p, p) for p in selected_display 
                                 if reverse_translations.get(p, p) not in ('ut.sync', 'ut.access')]
            self.update_info_label()
    
    def update_info_label(self):
        username = self.input_username.text().strip() or '-'
        
        key_to_label = {v: k for k, v in self.label_to_key.items()}
        role_labels = [key_to_label.get(k, k) for k in self.selected_roles]
        
        perms = self.selected_perms if self.selected_perms else (self.loaded_user.get('permissions') if self.loaded_user else [])
        
        # Словарь для перевода разрешений на человеческий язык
        perm_translations = {
            'admin.full': 'Полный доступ (Админ)',
            'governor.access': 'Доступ губернатора',
            'ut.view': 'Просмотр УТ',
            'ut.edit': 'Редактирование УТ',
            'ut.upload': 'Загрузка УТ',
            'ut.sync': 'Синхронизация УТ',
            'ut.access': 'Доступ к УТ'
        }
        
        translated_perms = [perm_translations.get(p, p) for p in perms]
        
        info_text = f"""👤 Пользователь: {username}

🎭 Роли: {', '.join(role_labels) if role_labels else '—'}

🏢 Отделы: {', '.join(self.selected_depts) if self.selected_depts else '—'}

🔑 Разрешения: {', '.join(translated_perms) if translated_perms else '—'}"""
        
        self.info_label.setText(info_text)
        self.info_group.setVisible(True)
    
    def on_save(self):
        username = self.input_username.text().strip()
        if not username:
            QMessageBox.warning(self, "Ошибка", "Введите логин пользователя.")
            return
        
        if self.current_user:
            for rk in self.selected_roles:
                if not can_assign_role(self.current_user, rk):
                    QMessageBox.warning(self, "Доступ запрещен", 
                                       f"Вы не можете назначать роль {rk}.")
                    return
            
            if self.selected_depts:
                try:
                    if not can_assign_departments(self.current_user, self.selected_depts):
                        QMessageBox.warning(self, "Доступ запрещен", 
                                          "Вы не можете назначать выбранные отделы.")
                        return
                except Exception:
                    QMessageBox.warning(self, "Ошибка проверки", 
                                      "Не удалось проверить права на назначение отделов.")
                    return
        
        try:
            save_user_roles(username, self.selected_roles, self.selected_depts, permissions=self.selected_perms)
            
            # Анимированное закрытие
            self.animation = QPropertyAnimation(self, b"windowOpacity")
            self.animation.setDuration(150)
            self.animation.setStartValue(1)
            self.animation.setEndValue(0)
            self.animation.finished.connect(self.accept)
            self.animation.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка при сохранении", str(e))
    
    def _on_create_user(self):
        login = self.add_login.text().strip()
        pwd = self.add_password.text()
        
        if not login or not pwd:
            QMessageBox.warning(self, 'Ошибка', 'Укажите логин и пароль для нового пользователя.')
            return
        
        try:
            create_user(login, pwd)
            QMessageBox.information(self, 'Готово', f'Пользователь {login} создан.')
            
            # Очистка полей
            self.add_login.clear()
            self.add_password.clear()
            self._all_user_docs = None
            
            # Переключение в режим ролей
            self.set_mode('roles')
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))
    
    def _on_delete_user(self):
        login = self.del_login.text().strip()
        
        if not login:
            QMessageBox.warning(self, 'Ошибка', 'Укажите логин для удаления.')
            return
        
        # Стилизованное подтверждение
        msg = QMessageBox(self)
        msg.setWindowTitle("Подтверждение")
        msg.setText(f"Вы действительно хотите удалить пользователя {login}?")
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        
        # Стилизация
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2d2d2d;
            }
            QLabel {
                color: white;
                font-size: 15px; /* Увеличен шрифт */
                padding: 25px; /* Увеличены отступы */
            }
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                border-radius: 10px; /* Увеличен радиус */
                padding: 10px 25px; /* Увеличены отступы */
                font-weight: bold;
                min-width: 90px; /* Увеличена ширина */
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return
        
        try:
            if delete_user(login):
                QMessageBox.information(self, 'Готово', f'Пользователь {login} удалён.')
                self.del_login.clear()
                self._all_user_docs = None
                self.set_mode('roles')
            else:
                QMessageBox.information(self, 'Инфо', 'Пользователь не найден.')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))