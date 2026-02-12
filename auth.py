import customtkinter as ctk
import hashlib
import gspread
from tkinter import messagebox
from config import FILES_PATH # Assuming user wants to keep paths configurable later or use defaults

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Вход в систему")
        self.geometry("400x350")
        self.user_data = None
        
        # UI элементы
        ctk.CTkLabel(self, text="Вход в Employee Data", font=("Arial", 20, "bold")).pack(pady=(30, 20))
        
        self.username_entry = ctk.CTkEntry(self, placeholder_text="Имя пользователя", width=250)
        self.username_entry.pack(pady=10)
        
        self.password_entry = ctk.CTkEntry(self, placeholder_text="Пароль", width=250, show="*")
        self.password_entry.pack(pady=10)
        
        ctk.CTkButton(self, text="Войти", command=self.login, width=250, height=40).pack(pady=20)
        
        # Лейбл статуса
        self.status_label = ctk.CTkLabel(self, text="", text_color="red")
        self.status_label.pack(pady=5)

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            self.status_label.configure(text="Введите логин и пароль")
            return

        try:
            gc = gspread.service_account(filename='service_account.json')
            
            try:
                sh = gc.open("Gov UT")
            except gspread.SpreadsheetNotFound:
                sh = gc.create("Gov UT")

            try:
                ws = sh.worksheet("Users")
            except gspread.WorksheetNotFound:
                ws = sh.add_worksheet(title="Users", rows=100, cols=5)
                ws.append_row(["Username", "PasswordHash", "Role", "CanEdit", "CanUpload"])
                default_hash = hashlib.sha256("admin".encode()).hexdigest()
                ws.append_row(["admin", default_hash, "Admin", "1", "1"])
            
            users = ws.get_all_records()
            input_hash = hashlib.sha256(password.encode()).hexdigest()
            
            found = False
            for user in users:
                # Add default dict for missing keys to avoid key errors later
                if str(user.get('Username')) == username and str(user.get('PasswordHash')) == input_hash:
                    # Ensure defaults for boolean flags
                    user.setdefault('CanEdit', 0)
                    user.setdefault('CanUpload', 0)
                    user.setdefault('Role', 'User')
                    self.user_data = user
                    found = True
                    break
            
            if found:
                self.destroy()
            else:
                self.status_label.configure(text="Неверные данные")
                
        except Exception as e:
            self.status_label.configure(text=f"Ошибка соединения: {e}")

class AdminPanel(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Админ панель")
        self.geometry("500x400")
        
        ctk.CTkLabel(self, text="Добавить пользователя", font=("Arial", 16, "bold")).pack(pady=10)
        
        self.new_user_entry = ctk.CTkEntry(self, placeholder_text="Логин")
        self.new_user_entry.pack(pady=5)
        
        self.new_pass_entry = ctk.CTkEntry(self, placeholder_text="Пароль", show="*")
        self.new_pass_entry.pack(pady=5)
        
        # Чекбоксы прав
        self.chk_edit_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self, text="Может редактировать (CanEdit)", variable=self.chk_edit_var).pack(pady=5)
        
        self.chk_upload_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self, text="Может загружать/синхронизировать (CanUpload)", variable=self.chk_upload_var).pack(pady=5)
        
        self.chk_admin_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self, text="Администратор (Admin)", variable=self.chk_admin_var).pack(pady=5)
        
        ctk.CTkButton(self, text="Создать пользователя", command=self.create_user).pack(pady=15)
        
    def create_user(self):
        login = self.new_user_entry.get()
        pwd = self.new_pass_entry.get()
        
        if not login or not pwd:
            return

        try:
            gc = gspread.service_account(filename='service_account.json')
            sh = gc.open("Gov UT")
            ws = sh.worksheet("Users")
            
            pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
            role = "Admin" if self.chk_admin_var.get() else "User"
            can_edit = 1 if self.chk_edit_var.get() else 0
            can_upload = 1 if self.chk_upload_var.get() else 0
            
            ws.append_row([login, pwd_hash, role, can_edit, can_upload])
            messagebox.showinfo("Успех", f"Пользователь {login} создан")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
