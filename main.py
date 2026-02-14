import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from auth import LoginWindow
from launcher import LauncherWindow
from utils import get_resource_path

def start_launcher(user_data):
    global launcher_window
    launcher_window = LauncherWindow(user_data)
    launcher_window.launch_main.connect(start_main_app)
    launcher_window.show()

def start_main_app(user_data):
    from app_ui import MainWindow
    global main_window
    main_window = MainWindow(user_data)
    main_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(get_resource_path("image.png")))

    login = LoginWindow()
    login.login_success.connect(start_launcher)
    login.show()

    sys.exit(app.exec())