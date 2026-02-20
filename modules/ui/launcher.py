import sys
import subprocess
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QFrame, QSizePolicy, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from modules.core.utils import get_resource_path
from modules.core.firebase_service import resolve_user_permissions, user_has_permission
from modules.core.firebase_service import can_open_role_settings

class LauncherWindow(QMainWindow):
    launch_main = pyqtSignal(dict)

    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data

        # Resolve permissions for UI decisions
        self.resolved = resolve_user_permissions(self.user_data)
        # Consider admin only if admin.full permission is present (role defs populate this permission).
        # This avoids accidentally granting admin rights if a legacy 'Role' field contains 'Admin'.
        self.is_admin = 'admin.full' in self.resolved.get('permissions', set())

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
        
        # Admin Panel Button removed — admins no longer see a separate admin panel here

        # Role Settings: visible to users allowed by can_open_role_settings
        try:
            from modules.ui.widgets.role_settings_dialog import RoleSettingsDialog
            if can_open_role_settings(self.user_data):
                self.btn_roles = QPushButton("⚙️ Настройка ролей")
                self.btn_roles.setCursor(Qt.CursorShape.PointingHandCursor)
                self.btn_roles.setStyleSheet("""
                    QPushButton { background-color: #2a82da; color: white; border-radius: 10px; padding: 8px; min-width: 140px; }
                    QPushButton:hover { background-color: #3a92ea; }
                """)
                self.btn_roles.clicked.connect(self.open_role_settings)
                top_layout.addWidget(self.btn_roles)
        except Exception:
            # ignore if widget import fails
            pass

        # Display resolved primary role for clarity (human-readable)
        role_label_map = {
            'Admin': 'Администратор', 'Governor': 'Губернатор', 'Minister': 'Министр',
            'Head': 'Начальник', 'Deputy': 'Заместитель', 'Employee': 'Подчиненный',
            'Visitor': 'Посетитель', 'UT_Role': 'УТ'
        }
        primary_role_key = next(iter(self.resolved.get('roles')), None)
        primary_role = role_label_map.get(primary_role_key, self.user_data.get('Role', primary_role_key or 'Visitor'))
        user_info = QPushButton(f"👤 {self.user_data.get('Username', '')} | {primary_role}")
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
        # enable only if explicit view permission (ut.view) or admin/full
        perms = self.resolved.get('permissions', set())
        # Use admin.full (not role string) as override
        has_ut_access = ('ut.view' in perms) or ('admin.full' in perms)
        if not has_ut_access:
            self.btn_labor.setEnabled(False)
            self.btn_labor.setToolTip('Доступ в Управление трудом закрыт')
        self.btn_labor.clicked.connect(self.run_labor_management)
        modules_layout.addWidget(self.btn_labor)
        
        # New Governor Cabinet Button
        self.btn_governor = QPushButton("🏛 Кабинет Губернатора")
        # Governor or Admin only
        if not (('governor.access' in self.resolved.get('permissions', set())) or self.is_admin or ('Governor' in self.resolved.get('roles'))):
            self.btn_governor.setEnabled(False)
            self.btn_governor.setStyleSheet(self.btn_governor.styleSheet() + "background-color: #555; color: #888;")
            self.btn_governor.setToolTip("Доступно только губернатору и администратору")
        
        self.btn_governor.clicked.connect(self.open_governor_cabinet)
        modules_layout.addWidget(self.btn_governor)

        self.btn_gov = QPushButton("🏛 Министерство Финансов")
        self.btn_gov.clicked.connect(self.run_gov_legacy)
        modules_layout.addWidget(self.btn_gov)

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

        version = QLabel("v 1.3.0")
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
            # Show a harmless stub for Министерство Финансов.
            # If a legacy stub script exists (legacy/MINFIN_STUB.py), launch it; otherwise show informational message.
            import os
            python_exec = sys.executable
            script_path = get_resource_path("legacy/MINFIN_STUB.py")
            if os.path.exists(script_path):
                subprocess.Popen([python_exec, script_path])
            else:
                QMessageBox.information(self, "Министерство Финансов", "Министерство Финансов — заглушка")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить Министерство Финансов:\n{e}")

    def open_governor_cabinet(self):
        try:
            from modules.ui.governor import GovernorCabinetWindow
            self.governor_window = GovernorCabinetWindow(self.user_data, self)
            self.governor_window.show()
            self.hide()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть Кабинет Губернатора:\n{e}")

    def run_governor_cabinet(self):
        try:
            if self.user_data.get('Role') != 'Admin':
                QMessageBox.warning(self, "Access Denied", "Available only for Administrators")
                return

            from modules.ui.governor import GovernorCabinetWindow
            self.governor_window = GovernorCabinetWindow(self.user_data, self)
            self.governor_window.show()
            self.hide()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Governor Cabinet:\n{e}")

    def open_role_settings(self):
        try:
            from modules.ui.widgets.role_settings_dialog import RoleSettingsDialog
            # Передаем parent=None, чтобы диалог стал независимым окном
            dlg = RoleSettingsDialog(parent=None, current_user=self.user_data)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть Настройку ролей:\n{e}")

    def change_password(self):
        try:
            from modules.ui.auth import ChangePasswordDialog
            # Normalize username field - Firestore uses 'username' but some places use 'Username' or 'login'
            uname = self.user_data.get('username') or self.user_data.get('Username') or self.user_data.get('login') or ''
            dlg = ChangePasswordDialog(uname, parent=self)
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