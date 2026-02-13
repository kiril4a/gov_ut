import sys
from PyQt6.QtWidgets import QApplication
from auth import LoginWindow
from app_ui import MainWindow

def start_main_app(user_data):
    # This function runs after successful login
    global main_window
    main_window = MainWindow(user_data)
    main_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    login = LoginWindow()
    # Connect the signal from LoginWindow to our start function
    login.login_success.connect(start_main_app)
    login.show()
    
    sys.exit(app.exec())
