from auth import LoginWindow
from app_ui import App

if __name__ == "__main__":
    login_app = LoginWindow()
    login_app.mainloop()
    
    if login_app.user_data:
        app = App(login_app.user_data)
        app.mainloop()
