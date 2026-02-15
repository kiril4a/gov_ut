import sys
import os

# Add the project root to sys.path so that modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from modules.ui.auth import LoginWindow
from modules.ui.launcher import LauncherWindow
from modules.core.utils import get_resource_path

def start_launcher(user_data):
    global launcher_window
    launcher_window = LauncherWindow(user_data)
    launcher_window.launch_main.connect(start_main_app)
    launcher_window.show()

def start_main_app(user_data):
    from modules.ui.app_ui import MainWindow
    global main_window
    main_window = MainWindow(user_data)
    main_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Needs to handle asset path correctly based on moved assets
    # In utils.py get_resource_path likely defaults to '.'
    # We moved image.png to assets/image.png
    # Let's check get_resource_path behavior or just pass 'assets/image.png'
    
    app.setWindowIcon(QIcon(get_resource_path("assets/image.png")))

    login = LoginWindow()
    login.login_success.connect(start_launcher)
    login.show()

    sys.exit(app.exec())