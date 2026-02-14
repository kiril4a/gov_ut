import sys
import subprocess
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QFrame, QSizePolicy, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from modules.core.utils import get_resource_path

class LauncherWindow(QMainWindow):
    launch_main = pyqtSignal(dict)

    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        
        # Check if user is admin based on data
        self.is_admin = self.user_data.get('Role') == 'Admin'

        self.setWindowTitle("GIH - Government Industrial Helper")
        self.setWindowIcon(QIcon(get_resource_path("assets/image.png")))
        self.setMinimumSize(900, 600)
        self.resize(900, 600)

        # Стиль окна
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QFrame {
                background-color: #2d2d2d;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 8px; /* Changed from 6px to match app_ui */
                font-weight: bold;
                font-size: 16px;
                padding: 15px 20px;
                text-align: center; /* Changed from left to center */
                height: 50px; /* Enforce uniform height */
                outline: none; /* Remove focus outline */
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #888;
            }
        """)

        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Верхняя панель
        top_frame = QFrame()
        top_frame.setFixedHeight(70)
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(15, 10, 15, 10)

        title = QLabel("GIH - Government Industrial Helper")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #4facfe;")
        top_layout.addWidget(title)

        top_layout.addStretch()
        
        # Admin Panel Button (Visible only to admins) - MOVED TO HEADER
        if self.is_admin:
            self.btn_admin = QPushButton("🛡 Админ панель")
            self.btn_admin.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_admin.clicked.connect(self.open_admin_panel)
            self.btn_admin.setStyleSheet("""
                QPushButton {
                    background-color: #d63031; 
                    color: white; 
                    border: none; 
                    border-radius: 12px; 
                    font-weight: bold; 
                    font-size: 13px; 
                    min-width: 130px;
                    padding: 8px; 
                    outline: none;
                }
                QPushButton:hover { background-color: #e74c3c; }
            """)
            top_layout.addWidget(self.btn_admin)

        user_info = QPushButton(f"👤 {self.user_data.get('Username', 'admin')} | {self.user_data.get('Role', 'Admin')}")
        user_info.setStyleSheet("""
            QPushButton {
                padding: 8px; 
                background-color: #3d3d3d; 
                border-radius: 12px;
                border: 1px solid #555;
                font-weight: bold; 
                font-size: 13px;
                min-width: 130px;
                color: white;
                outline: none;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
                border: 1px solid #2a82da;
            }
        """)
        user_info.setCursor(Qt.CursorShape.PointingHandCursor)
        user_info.clicked.connect(self.change_password)
        top_layout.addWidget(user_info)

        layout.addWidget(top_frame)

        # Центральная область с модулями
        modules_frame = QFrame()
        modules_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        modules_layout = QVBoxLayout(modules_frame)
        modules_layout.setContentsMargins(30, 30, 30, 30)
        modules_layout.setSpacing(15)

        section_title = QLabel("Доступные модули")
        section_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #aaa;")
        modules_layout.addWidget(section_title)

        # Кнопки модулей
        self.btn_labor = QPushButton("👥 Управление трудом")
        self.btn_labor.clicked.connect(self.run_labor_management)
        modules_layout.addWidget(self.btn_labor)

        self.btn_gov = QPushButton("⚡ GovYPT (старая версия)")
        self.btn_gov.clicked.connect(self.run_gov_legacy)
        modules_layout.addWidget(self.btn_gov)
        
        # REMOVED Admin Panel Button from here
            
        self.btn_order = QPushButton("📄 Шаблон постановлений")
        self.btn_order.clicked.connect(self.run_order_template)
        modules_layout.addWidget(self.btn_order)

        self.btn_economy = QPushButton("📊 Экономика и отчёты")
        self.btn_economy.clicked.connect(self.run_economy)
        self.btn_economy.setEnabled(False)
        modules_layout.addWidget(self.btn_economy)

        modules_layout.addStretch()
        layout.addWidget(modules_frame)

        # Нижняя панель
        bottom_frame = QFrame()
        bottom_frame.setFixedHeight(60)
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(15, 5, 15, 5)

        version = QLabel("v1.2.5")
        version.setStyleSheet("color: #888;")
        bottom_layout.addWidget(version)

        bottom_layout.addStretch()

        logout_btn = QPushButton("Выйти из системы")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #d63031; 
                padding: 8px 25px;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 16px;
                outline: none;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
                color: white;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        bottom_layout.addWidget(logout_btn)

        layout.addWidget(bottom_frame)

    def run_labor_management(self):
        self.launch_main.emit(self.user_data)
        self.close()

    def run_gov_legacy(self):
        try:
            python_exec = sys.executable
            # GOV.py is now in legacy folder
            script_path = get_resource_path("legacy/GOV.py")
            subprocess.Popen([python_exec, script_path])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить GOV.py:\n{e}")

    def open_admin_panel(self):
        try:
            from modules.ui.auth import AdminPanel
            # Pass a flag or adjust init to center on screen if parent is passed but we want absolute center
            # Actually, per request "center of application", passing self (window) usually centers on window.
            # But the user specifically asked "fix in center of application". 
            # The current implementation in AdminPanel tries to position under the button if parent has btn_admin.
            # We will modify AdminPanel to ignore button position and center on parent window.
            AdminPanel(self, center_on_parent=True).exec()
        except Exception as e:
             QMessageBox.critical(self, "Ошибка", f"Не удалось открыть админ панель:\n{e}")

    def change_password(self):
        try:
            from modules.ui.auth import ChangePasswordDialog
            dlg = ChangePasswordDialog(self.user_data.get('Username'), parent=self)
            if dlg.exec():
                QMessageBox.information(self, "Успех", "Пароль успешно изменен!")
        except Exception as e:
             QMessageBox.critical(self, "Ошибка", f"Ошибка смены пароля: {e}")

    def run_order_template(self):
        try:
            from modules.ui.order_editor import OrderEditorWindow
            self.order_window = OrderEditorWindow()
            self.order_window.show()
        except ImportError:
            QMessageBox.warning(
                self,
                "Модуль не найден",
                "Файл order_editor.py не найден.\n"
                "Создайте его в папке проекта и скопируйте код редактора."
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть редактор:\n{e}")

    def run_economy(self):
        QMessageBox.information(self, "Информация", "Модуль 'Экономика и отчёты' находится в разработке.")

    def logout(self):
        from modules.ui.auth import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.login_success.connect(self.restart)
        self.login_window.show()
        self.close()

    def restart(self, user_data):
        self.close() 
        self.new_launcher = LauncherWindow(user_data)
        self.new_launcher.launch_main.connect(self.run_labor_management_from_signal)
        self.new_launcher.show()

    def run_labor_management_from_signal(self, user_data):
        from modules.ui.app_ui import MainWindow
        self.main_window = MainWindow(user_data)
        self.main_window.show()