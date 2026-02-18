import hashlib
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QCheckBox, QDialog, QFrame, QHBoxLayout, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QIcon, QPainter, QColor
from modules.core.utils import get_resource_path
from modules.core.firebase_service import list_users, get_user, create_user, update_user_password, save_user_roles, resolve_user_permissions

class LoginWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password

    def run(self):
        try:
            # Use Firestore users collection exclusively for authentication
            fb_user = None
            try:
                fb_user = get_user(self.username)
            except Exception as e:
                fb_user = None

            if not fb_user:
                # No such user in Firestore
                self.finished.emit({})
                return

            # authenticate against Firestore
            input_hash = hashlib.sha256(self.password.encode()).hexdigest()
            if str(fb_user.get('hashpassword', '')) == input_hash:
                perms = resolve_user_permissions(fb_user)
                fb_user['resolved_permissions'] = perms
                self.finished.emit(fb_user)
                return

            # Wrong password
            self.finished.emit({})

        except Exception as e:
            self.error.emit(str(e))

class SuccessOverlay(QDialog):
    def __init__(self, parent=None, message=""):
        super().__init__(parent)
        # Use Popup style like other menus to close on outside click, but no full screen overlay
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Calculate size based on content, but keep it reasonable
        # We'll set a fixed width for the container inside
        self.setFixedWidth(340)

        # Center on parent
        if parent:
            qr = self.frameGeometry()
            cp = parent.frameGeometry().center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Container for the dialog box
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 12px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                background: transparent;
                border: none;
            }
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                padding: 8px 30px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setSpacing(20)
        container_layout.setContentsMargins(25, 25, 25, 25)
        
        # Content Row (Icon + Text)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        # Icon ("i" symbol)
        self.icon_label = QLabel("i")
        self.icon_label.setFixedSize(30, 30)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("""
            background-color: #2a82da;
            color: white;
            border-radius: 15px;
            font-weight: bold;
            font-size: 18px;
            font-family: serif;
        """)
        
        # Message
        self.msg_label = QLabel(message)
        self.msg_label.setWordWrap(True)
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        content_layout.addWidget(self.icon_label)
        content_layout.addWidget(self.msg_label, 1) 
        container_layout.addLayout(content_layout)
        
        # OK Button centered
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addStretch()
        
        container_layout.addLayout(btn_layout)
        
        self.main_layout.addWidget(self.container)
        
    # Paint event removed to delete the "shadow" (dimmed background)
    # create_user and change_password dialogs already use this or similar styling via separate classes. 
    # This edits SuccessOverlay which is used by them for the success message.

class LoginWindow(QWidget):
    login_success = pyqtSignal(dict) # Signal to pass user data

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Вход в систему")
        self.setWindowIcon(QIcon(get_resource_path("assets/image.png")))
        self.resize(400, 350)
        self.user_data = None
        
        # Apple Dark Theme Stylesheet
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit {
                background-color: #353535;
                color: white;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                selection-background-color: #2a82da;
            }
            QLineEdit:focus {
                border: 1px solid #2a82da;
                background-color: #404040;
            }
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
            QPushButton:pressed {
                background-color: #1a72ca;
            }
            QLabel#TitleLabel {
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 20px;
            }
            QLabel#StatusLabel {
                font-size: 12px;
                margin-top: 10px;
            }
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)
        
        self.title_label = QLabel("Вход в Government Industrial Helper")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Имя пользователя")
        self.username_input.setMinimumHeight(45)
        layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(45)
        layout.addWidget(self.password_input)
        
        self.login_btn = QPushButton("Войти")
        self.login_btn.setMinimumHeight(45)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self.login)
        layout.addWidget(self.login_btn)
        
        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setStyleSheet("color: #ff6b6b;") # Override color for status
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)

    def login(self):
        from modules.ui.loading_overlay import LoadingOverlay
        
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self.status_label.setText("Введите логин и пароль")
            return

        self.status_label.setText("Подключение...")
        self.loading_overlay = LoadingOverlay(self, "Вход...")
        self.loading_overlay.showOverlay()
        
        # Disable inputs
        self.login_btn.setEnabled(False)
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)

        self.worker = LoginWorker(username, password)
        self.worker.finished.connect(self.on_login_finished)
        self.worker.error.connect(self.on_login_error)
        self.worker.start()

    def on_login_finished(self, user_data):
        self._cleanup_login_ui()
        if user_data:
            self.user_data = user_data
            self.login_success.emit(self.user_data)
            self.close()
        else:
            self.status_label.setText("Неверные данные")

    def on_login_error(self, error_msg):
        self._cleanup_login_ui()
        self.status_label.setText(f"Ошибка соединения: {error_msg}")

    def _cleanup_login_ui(self):
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.hideOverlay()
        
        self.login_btn.setEnabled(True)
        self.username_input.setEnabled(True)
        self.password_input.setEnabled(True)

class AdminPanel(QDialog):
    def __init__(self, parent=None, center_on_parent=False):
        super().__init__(parent)
        self.setWindowTitle("Админ панель")
        self.setFixedSize(400, 500)
        
        # Window flags to make it popup and frameless
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Center logic
        if parent:
            if center_on_parent:
                # Strictly center on parent window
                qr = self.frameGeometry()
                cp = parent.frameGeometry().center()
                qr.moveCenter(cp)
                self.move(qr.topLeft())
            elif hasattr(parent, 'btn_admin'):
                # Position below button (MENU STYLE - CURRENT BEHAVIOR for some, but user requested center)
                # But we are keeping this logic if center_on_parent is FALSE
                btn_pos = parent.btn_admin.mapToGlobal(parent.btn_admin.rect().bottomLeft())
                self.move(btn_pos.x(), btn_pos.y() + 5)
            else:
                 # Default center
                qr = self.frameGeometry()
                cp = parent.frameGeometry().center()
                qr.moveCenter(cp)
                self.move(qr.topLeft())
            
        self.init_ui()

    def init_ui(self):
        # Container frame for consistent styling
        container_layout = QVBoxLayout(self)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QFrame()
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            QFrame#container {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 12px;
            }
            QLabel {
                color: white;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QLineEdit {
                border: 1px solid #555;
                border-radius: 12px;
                padding: 10px;
                background-color: white;
                color: black;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #2a82da;
            }
            QCheckBox {
                color: white;
                font-size: 14px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #555;
                background: #353535;
            }
            QCheckBox::indicator:checked {
                background: #2a82da;
                border: 1px solid #2a82da;
            }
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
        """)
        container_layout.addWidget(self.container)

        layout = QVBoxLayout(self.container)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        title = QLabel("Добавить пользователя")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4facfe;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        self.new_user_entry = QLineEdit()
        self.new_user_entry.setPlaceholderText("Логин")
        self.new_user_entry.setMinimumHeight(40)
        layout.addWidget(self.new_user_entry)
        
        self.new_pass_entry = QLineEdit()
        self.new_pass_entry.setPlaceholderText("Пароль")
        self.new_pass_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pass_entry.setMinimumHeight(40)
        layout.addWidget(self.new_pass_entry)
        
        chk_layout = QVBoxLayout()
        chk_layout.setSpacing(10)
        
        self.chk_edit = QCheckBox("Редактирование")
        chk_layout.addWidget(self.chk_edit)
        
        self.chk_upload = QCheckBox("Создание таблиц")
        chk_layout.addWidget(self.chk_upload)
        
        self.chk_admin = QCheckBox("Администратор")
        chk_layout.addWidget(self.chk_admin)
        
        layout.addLayout(chk_layout)
        
        layout.addStretch()
        
        btn = QPushButton("Создать пользователя")
        btn.clicked.connect(self.create_user)
        btn.setMinimumHeight(45)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(btn)

    def create_user(self):
        username = self.new_user_entry.text().strip()
        password = self.new_pass_entry.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните логин и пароль")
            return
            
        try:
            role = "Admin" if self.chk_admin.isChecked() else None
            can_edit = True if self.chk_edit.isChecked() else False
            # Create user in Firestore only; Google Sheets no longer used for users
            try:
                perms = ['ut.access'] if can_edit else []
                create_user(username, password, role=role, departments=[], permissions=perms)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать пользователя в БД: {e}")
                return

            success_dialog = SuccessOverlay(self, f"Пользователь {username} создан")
            success_dialog.exec()
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать пользователя: {e}")

class ChangePasswordDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle("Смена пароля")
        self.setFixedSize(350, 300)
        
        # Consistent Menu Style
        if parent:
            qr = self.frameGeometry()
            cp = parent.frameGeometry().center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())

        # Removed overlay style, just popup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            QFrame#container {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 12px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit {
                background-color: #353535;
                color: white;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #2a82da;
            }
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
        """)
        layout.addWidget(self.container)

        container_layout = QVBoxLayout(self.container)
        container_layout.setSpacing(15)
        container_layout.setContentsMargins(30, 30, 30, 30)
        
        title_lbl = QLabel(f"Смена пароля для:\n{self.username}")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #4facfe;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setWordWrap(True) 
        container_layout.addWidget(title_lbl)
        
        self.old_pass = QLineEdit()
        self.old_pass.setPlaceholderText("Старый пароль")
        self.old_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.old_pass.setMinimumHeight(40)
        container_layout.addWidget(self.old_pass)
        
        self.new_pass = QLineEdit()
        self.new_pass.setPlaceholderText("Новый пароль")
        self.new_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pass.setMinimumHeight(40)
        container_layout.addWidget(self.new_pass)
        
        btn = QPushButton("Сменить пароль")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.change_password)
        btn.setMinimumHeight(40)
        container_layout.addWidget(btn)

    def change_password(self):
        old_p = self.old_pass.text().strip()
        new_p = self.new_pass.text().strip()
        
        if not old_p or not new_p:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return
            
        try:
            # Update password in Firestore only
            fb = get_user(self.username)
            if not fb:
                QMessageBox.critical(self, "Ошибка", "Пользователь не найден в БД")
                return

            old_hash = hashlib.sha256(old_p.encode()).hexdigest()
            if str(fb.get('hashpassword', '')) != old_hash:
                QMessageBox.warning(self, "Ошибка", "Старый пароль неверен")
                return

            update_user_password(self.username, new_p)

            # Close the password dialog FIRST
            self.close()

            success_dialog = SuccessOverlay(self.parent(), "Пароль успешно изменен")
            success_dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сменить пароль: {e}")

class CreateUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать пользователя")
        self.setFixedSize(350, 450)
        
        # User requested style: Menu-like, centered on application, closes on outside click
        if parent:
             # Center on parent window
            qr = self.frameGeometry()
            cp = parent.frameGeometry().center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())
            
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup) 
        # Qt.Popup handles "close on outside click" automatically for the most part, 
        # but combined with FramelessWindowHint acts more like a menu.
        
        self.setStyleSheet("""
            QDialog {
                background-color: transparent;
            }
            QFrame#mainFrame {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 12px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #353535;
                color: white;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #2a82da;
            }
            QCheckBox {
                color: white;
                font-size: 14px;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                background-color: #353535;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #2a82da;
                border: 1px solid #2a82da;
                 /* Checkmark icon could be added here if needed, or rely on defautt */
            }
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main Frame
        self.main_frame = QFrame()
        self.main_frame.setObjectName("mainFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setSpacing(15)
        frame_layout.setContentsMargins(25, 25, 25, 25)

        # Header
        header = QLabel("Новый сотрудник")
        header.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_layout.addWidget(header)
        
        frame_layout.addSpacing(10)

        # Inputs
        self.new_user_entry = QLineEdit()
        self.new_user_entry.setPlaceholderText("Логин")
        frame_layout.addWidget(self.new_user_entry)
        
        self.new_pass_entry = QLineEdit()
        self.new_pass_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pass_entry.setPlaceholderText("Пароль")
        frame_layout.addWidget(self.new_pass_entry)
        
        # Checkboxes
        self.chk_admin = QCheckBox("Администратор")
        self.chk_edit = QCheckBox("Редактирование")
        self.chk_upload = QCheckBox("Создание таблиц")
        
        frame_layout.addWidget(self.chk_admin)
        frame_layout.addWidget(self.chk_edit)
        frame_layout.addWidget(self.chk_upload)
        
        frame_layout.addSpacing(10)
        
        # Create Button
        self.btn_create = QPushButton("Создать")
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create.clicked.connect(self.create_user)
        frame_layout.addWidget(self.btn_create)
        
        layout.addWidget(self.main_frame)

    def create_user(self):
        username = self.new_user_entry.text().strip()
        password = self.new_pass_entry.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните логин и пароль")
            return
            
        try:
            role = "Admin" if self.chk_admin.isChecked() else None
            can_edit = True if self.chk_edit.isChecked() else False
            # Create user in Firestore only; Google Sheets no longer used for users
            try:
                perms = ['ut.access'] if can_edit else []
                create_user(username, password, role=role, departments=[], permissions=perms)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать пользователя в БД: {e}")
                return

            # Close the input dialog first
            self.close()
            
            success_dialog = SuccessOverlay(self.parent(), f"Пользователь {username} создан")
            success_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать пользователя: {e}")
            self.google_service.delete_user(username)
            self.load_users()
            success_dialog = SuccessOverlay(self, f"Пользователь {username} удален")
            success_dialog.exec()

