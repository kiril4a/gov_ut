import hashlib
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QCheckBox, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from google_service import GoogleService
from utils import get_resource_path

class LoginWindow(QWidget):
    login_success = pyqtSignal(dict) # Signal to pass user data

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Вход в систему")
        self.setWindowIcon(QIcon(get_resource_path("image.png")))
        self.google_service = GoogleService()
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
        
        self.title_label = QLabel("Вход в Employee Data")
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
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self.status_label.setText("Введите логин и пароль")
            return

        self.status_label.setText("Подключение...")
        # Force UI update needed here normally, but single thread blocks anyway.
        # We'll rely on fast auth or just blocking is fine for MVP.
        
        try:
            users = self.google_service.get_users()
            input_hash = hashlib.sha256(password.encode()).hexdigest()
            
            found = False
            for user in users:
                if str(user.get('Username')) == username and str(user.get('PasswordHash')) == input_hash:
                    # Ensure defaults
                    user.setdefault('CanEdit', 0)
                    user.setdefault('CanUpload', 0)
                    user.setdefault('Role', 'User')
                    self.user_data = user
                    found = True
                    break
            
            if found:
                self.login_success.emit(self.user_data)
                self.close()
            else:
                self.status_label.setText("Неверные данные")
                
        except Exception as e:
            self.status_label.setText(f"Ошибка соединения: {e}")

class AdminPanel(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Админ панель")
        self.google_service = GoogleService()
        self.resize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Добавить пользователя")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        self.new_user_entry = QLineEdit()
        self.new_user_entry.setPlaceholderText("Логин")
        layout.addWidget(self.new_user_entry)
        
        self.new_pass_entry = QLineEdit()
        self.new_pass_entry.setPlaceholderText("Пароль")
        self.new_pass_entry.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.new_pass_entry)
        
        self.chk_edit = QCheckBox("Право на редактирование и синхронизацию")
        layout.addWidget(self.chk_edit)
        
        self.chk_upload = QCheckBox("Право на создание новой таблицы")
        layout.addWidget(self.chk_upload)
        
        self.chk_admin = QCheckBox("Право на администрирование")
        layout.addWidget(self.chk_admin)
        
        btn = QPushButton("Создать пользователя")
        btn.clicked.connect(self.create_user)
        layout.addWidget(btn)
        
        layout.addStretch()
        self.setLayout(layout)

    def create_user(self):
        username = self.new_user_entry.text().strip()
        password = self.new_pass_entry.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните логин и пароль")
            return
            
        try:
            role = "Admin" if self.chk_admin.isChecked() else "User"
            can_edit = "1" if self.chk_edit.isChecked() else "0"
            can_upload = "1" if self.chk_upload.isChecked() else "0"
            
            self.google_service.create_user(username, password, role, can_edit, can_upload)
            
            QMessageBox.information(self, "Успех", f"Пользователь {username} создан")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
