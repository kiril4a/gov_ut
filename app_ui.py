import customtkinter as ctk
import re
import gspread
import threading
from tkinter import filedialog, messagebox
from config import ARTICLES
from auth import AdminPanel

class App(ctk.CTk):
    def __init__(self, user_data):
        super().__init__()
        
        self.user_data = user_data
        self.is_admin = user_data.get('Role') == 'Admin'
        
        # Permissions: Admin gets everything, otherwise check flags
        if self.is_admin:
            self.can_edit = True
            self.can_upload = True
        else:
            # Handle various truthy values just in case
            ce_val = str(user_data.get('CanEdit', '0')).lower()
            self.can_edit = ce_val in ('1', 'true', 'yes', 'on')
            
            cu_val = str(user_data.get('CanUpload', '0')).lower()
            self.can_upload = cu_val in ('1', 'true', 'yes', 'on')

        self.title(f"Employee Data - {user_data.get('Username')} ({user_data.get('Role')})")
        self.geometry("1100x800")
        self.data = []
        self.filtered_data = []
        self.filter_statuses = [0, 1, 2]  # Default: all statuses selected
        self.filter_articles = []         # Default: empty list means "all articles" (no filter)
        self.row_widgets = {}
        
        # Sync state
        self.sync_mode = False 
        self.worksheet = None
        self.auto_refresh_job = None
        self.is_loading = False
        
        # Pagination state
        self.current_page = 0
        self.page_size = 13  # Reduced to fit on screen without scrolling

        # Configure grid layout structure
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Scrollable frame for staff

        # --- Header ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self.header_frame, text="Employee Data", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w")
        
        # User info label
        self.user_info_label = ctk.CTkLabel(self.header_frame, text=f"User: {self.user_data.get('Username')} | Role: {self.user_data.get('Role')}", font=ctk.CTkFont(size=12))
        self.user_info_label.grid(row=0, column=3, sticky="e", padx=(10, 0))

        # Status Indicator (New)
        self.loading_label = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(size=12, slant="italic"))
        self.loading_label.grid(row=0, column=4, sticky="e", padx=(10, 0))

        # Settings Button (replaces Menu)
        self.settings_btn = ctk.CTkButton(self.header_frame, text="Settings", width=100, command=self.open_settings)
        self.settings_btn.grid(row=0, column=1, sticky="e")
        
        if self.is_admin:
            self.admin_btn = ctk.CTkButton(self.header_frame, text="Admin Panel", width=100, fg_color="darkred", hover_color="red", command=self.open_admin_panel)
            self.admin_btn.grid(row=0, column=2, sticky="e", padx=(10, 0))

        # --- Sort Controls ---
        self.sort_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.sort_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        
        self.sort_label = ctk.CTkLabel(self.sort_frame, text="Сортировка:", text_color="gray")
        self.sort_label.pack(side="left", padx=(0, 10))

        # Filter Button
        self.filter_btn = ctk.CTkButton(self.sort_frame, text="Фильтр", width=80, height=24, font=ctk.CTkFont(size=12), command=self.open_filter)
        self.filter_btn.pack(side="left", padx=5)

        # Helper to create small sort buttons
        def create_sort_btn(text, command):
            btn = ctk.CTkButton(self.sort_frame, text=text, command=command, width=80, height=24, font=ctk.CTkFont(size=12))
            btn.pack(side="left", padx=5)
            return btn

        create_sort_btn("Имя A-Z", lambda: self.sort_staff('name', True))
        create_sort_btn("Имя Z-A", lambda: self.sort_staff('name', False))
        create_sort_btn("Ранг ↑", lambda: self.sort_staff('rank', True))
        create_sort_btn("Ранг ↓", lambda: self.sort_staff('rank', False))

        # --- Pagination Controls ---
        self.pages_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.pages_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        
        self.prev_btn = ctk.CTkButton(self.pages_frame, text="< Назад", command=self.prev_page, width=100)
        self.prev_btn.pack(side="left")
        
        self.page_label = ctk.CTkLabel(self.pages_frame, text="Страница 1", font=("Arial", 14))
        self.page_label.pack(side="left", expand=True)

        self.next_btn = ctk.CTkButton(self.pages_frame, text="Вперед >", command=self.next_page, width=100)
        self.next_btn.pack(side="right")

        # --- Staff List (Scrollable) ---
        self.staff_scroll = ctk.CTkScrollableFrame(self, label_text="Список сотрудников")
        self.staff_scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=(10, 0)) # Adjusted padding
        self.staff_scroll.grid_columnconfigure(0, weight=1)

    def open_settings(self):
        # Create a settings popup
        popup = ctk.CTkToplevel(self)
        popup.title("Настройки")
        popup.geometry("300x200")
        popup.grab_set()
        
        ctk.CTkLabel(popup, text="Источник данных:", font=("Arial", 16, "bold")).pack(pady=10)
        
        def load_local():
            popup.destroy()
            self.stop_auto_refresh()
            self.load_file()
            
        def connect_google():
            popup.destroy()
            input_dialog = ctk.CTkInputDialog(text="Введите название листа для синхронизации:", title="Название листа")
            sheet_title = input_dialog.get_input()
            if sheet_title:
                self.load_from_google(sheet_title)

        ctk.CTkButton(popup, text="📂 Создать из файла (.txt)", command=load_local).pack(pady=10, fill="x", padx=20)
        ctk.CTkButton(popup, text="☁ Синхронизация (Google Sheets)", command=connect_google, fg_color="purple", hover_color="darkviolet").pack(pady=10, fill="x", padx=20)

    def open_admin_panel(self):
        AdminPanel(self)

    def set_loading(self, is_loading, text=""):
        self.is_loading = is_loading
        if is_loading:
            self.loading_label.configure(text=text if text else "Загрузка...")
        else:
            self.loading_label.configure(text="")

    def load_from_google(self, sheet_title):
        if not self.can_upload:
            messagebox.showwarning("Доступ запрещен", "У вас нет прав на синхронизацию.")
            return
        
        self.set_loading(True, "Подключение к Google...")
        
        def worker():
            try:
                gc = gspread.service_account(filename='service_account.json')
                
                # Open spreadsheet named "Gov UT" 
                spreadsheet_name = "Gov UT" 
                try:
                    sh = gc.open(spreadsheet_name)
                except gspread.SpreadsheetNotFound:
                    sh = gc.create(spreadsheet_name)
                    # If creating, maybe share?
                    # sh.share('me@gmail.com', perm_type='user', role='writer')
                
                try:
                    ws = sh.worksheet(sheet_title)
                except gspread.WorksheetNotFound:
                    # If loading from google and sheet is missing, maybe create it?
                    ws = sh.add_worksheet(title=sheet_title, rows=100, cols=20)
                    ws.append_row(["Name", "Static ID", "Rank", "Articles", "Sum", "Processed"])

                # Update UI thread
                self.after(0, lambda: self._on_google_connected(ws))
                
            except Exception as e:
                self.after(0, lambda: self._on_google_error(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_google_connected(self, ws):
        self.worksheet = ws
        self.sync_mode = True
        self.set_loading(False)
        self.refresh_google_data()
        self.start_auto_refresh()

    def _on_google_error(self, error):
        self.sync_mode = False
        self.set_loading(False)
        messagebox.showerror("Google Error", f"Ошибка подключения: {error}\nПроверьте service_account.json")

    def load_file(self):
        if not self.can_upload:
            messagebox.showwarning("Доступ запрещен", "У вас нет прав на загрузку файлов.")
            return

        file_path = filedialog.askopenfilename(parent=self, filetypes=[("Text files", "*.txt")])
        if not file_path:
            return
            
        # Ask for new sheet name
        input_dialog = ctk.CTkInputDialog(text="Введите название нового листа для экспорта:", title="Название листа")
        sheet_name = input_dialog.get_input()
        if not sheet_name:
            return

        try:
            new_data = [] # Temporary list
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    parts = line.strip().split("\t")
                    if len(parts) < 2:
                        continue
                    
                    name_part = parts[0].strip()
                    rank = parts[1].strip()
                    statik_match = re.search(r'\[(\d+)\]', name_part)
                    statik = statik_match.group(1) if statik_match else ""
                    name = re.sub(r'\s*\[\d+\]', '', name_part).strip()
                    
                    new_data.append({
                        "name": name,
                        "statik": statik,
                        "rank": rank,
                        "articles": [],
                        "sum": 0,
                        "processed": 0 
                    })
            self.data = new_data
            
            self.set_loading(True, "Загрузка в Google...")
            
            # Switch to sync mode with new sheet upload in background
            def worker():
                try:
                    gc = gspread.service_account(filename='service_account.json')
                    
                    try:
                        sh = gc.open("Gov UT")
                    except gspread.SpreadsheetNotFound:
                        sh = gc.create("Gov UT")

                    # Check if exists, maybe delete or define usage
                    try:
                        ws = sh.worksheet(sheet_name)
                        ws.clear()
                    except:
                        ws = sh.add_worksheet(title=sheet_name, rows=len(self.data)+10, cols=20)
                    
                    # Prepare data for upload
                    headers = ["Name", "Static ID", "Rank", "Articles", "Sum", "Processed"]
                    values = [headers]
                    for item in self.data:
                         # Correct structure for upload: Name, Static, Rank, Articles (empty), Sum (0), Status (0)
                         values.append([
                             item['name'],
                             item['statik'], 
                             item['rank'],
                             "", 
                             0,
                             0
                         ])
                    
                    ws.update(range_name="A1", values=values)
                    
                    self.after(0, lambda: self._on_file_loaded(ws))
                    
                except Exception as e:
                    self.after(0, lambda: self._on_file_load_error(e))

            threading.Thread(target=worker, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

    def _on_file_loaded(self, ws):
        self.worksheet = ws
        self.sync_mode = True
        self.set_loading(False)
        self.filtered_data = list(self.data)
        self.current_page = 0
        self.render_staff()
        self.refresh_google_data() 
        self.start_auto_refresh()

    def _on_file_load_error(self, e):
        self.set_loading(False)
        messagebox.showerror("Sync Error", f"Не удалось создать лист в Google: {e}")
        self.sync_mode = False 
        # Fallback to local only render if upload failed?
        self.filtered_data = list(self.data) 
        self.current_page = 0
        self.render_staff()

    def toggle_processed(self, idx):
        if not self.can_edit:
             return

        row = self.filtered_data[idx]
        current_state = int(row['processed'])
        new_state = (current_state + 1) % 3
        row['processed'] = new_state
        
        # Immediate UI Update
        self.filtered_data[idx] = row
        widgets = self.row_widgets.get(idx)
        if widgets:
            btn = widgets["status_btn"]
            if new_state == 2:
                btn.configure(text="✔", fg_color="green", hover_color="darkgreen")
            elif new_state == 1:
                btn.configure(text="?", fg_color="orange", hover_color="darkorange")
            else:
                btn.configure(text="✗", fg_color="red", hover_color="darkred")

        if self.sync_mode:
            # Send update in background
            threading.Thread(target=self.update_google_row, args=(row,), daemon=True).start()

    def render_staff(self):
        # Clear existing widgets in scrollable frame
        for widget in self.staff_scroll.winfo_children():
            widget.destroy()
        self.row_widgets.clear()
        
        # Use filtered_data for rendering
        current_data = self.filtered_data

        # Headers for the list
        headers_frame = ctk.CTkFrame(self.staff_scroll, fg_color="transparent")
        headers_frame.pack(fill="x", pady=(0, 5), padx=5)
        
        headers = ["№", "Name", "Static ID", "Rank", "Articles", "Payment", "Status"]
        
        # Configure Grid Layout for Headers using uniform to enforce strict proportional width
        # Weights: No(1), Name(4), Static(2), Rank(2), Articles(4), Payment(2), Status(1)
        headers_frame.grid_columnconfigure(0, weight=1, uniform="group1") 
        headers_frame.grid_columnconfigure(1, weight=4, uniform="group1") 
        headers_frame.grid_columnconfigure(2, weight=2, uniform="group1") 
        headers_frame.grid_columnconfigure(3, weight=2, uniform="group1") 
        headers_frame.grid_columnconfigure(4, weight=4, uniform="group1") 
        headers_frame.grid_columnconfigure(5, weight=2, uniform="group1") 
        headers_frame.grid_columnconfigure(6, weight=1, uniform="group1") 

        for i, h in enumerate(headers):
            lbl = ctk.CTkLabel(headers_frame, text=h, font=ctk.CTkFont(size=12, weight="bold"), text_color="gray", anchor="w")
            lbl.grid(row=0, column=i, sticky="ew", padx=5)

        # Calculate slice
        total_pages = (len(current_data) + self.page_size - 1) // self.page_size
        if total_pages == 0: total_pages = 1
        
        if self.current_page >= total_pages: self.current_page = total_pages - 1
        if self.current_page < 0: self.current_page = 0

        start = self.current_page * self.page_size
        end = min(start + self.page_size, len(current_data))

        # Update controls
        self.page_label.configure(text=f"Страница {self.current_page + 1} из {total_pages}")
        self.prev_btn.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.current_page < total_pages - 1 else "disabled")

        for idx in range(start, end):
            self.create_staff_card(idx, current_data[idx])

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_staff()

    def next_page(self):
        total_items = len(self.filtered_data)
        total_pages = (total_items + self.page_size - 1) // self.page_size
        if total_pages == 0: total_pages = 1
        
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.render_staff()

    def create_staff_card(self, idx, row):
        card = ctk.CTkFrame(self.staff_scroll, corner_radius=10, fg_color=("gray85", "gray17")) 
        card.pack(fill="x", pady=4, padx=5)

        # Grid layout for the card content with MATCHING weights and uniform group
        card.grid_columnconfigure(0, weight=1, uniform="group1") # No
        card.grid_columnconfigure(1, weight=4, uniform="group1") # Name
        card.grid_columnconfigure(2, weight=2, uniform="group1") # Static
        card.grid_columnconfigure(3, weight=2, uniform="group1") # Rank
        card.grid_columnconfigure(4, weight=4, uniform="group1") # Articles
        card.grid_columnconfigure(5, weight=2, uniform="group1") # Payment
        card.grid_columnconfigure(6, weight=1, uniform="group1") # Status

        # Number
        num_label = ctk.CTkLabel(card, text=str(idx + 1), text_color="gray", anchor="w")
        num_label.grid(row=0, column=0, pady=10, padx=5, sticky="ew")

        # Name
        name_label = ctk.CTkLabel(card, text=str(row['name']), font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
        name_label.grid(row=0, column=1, pady=10, padx=5, sticky="ew")
        name_label.bind('<Button-1>', lambda e, v=row['name']: self.copy_to_clipboard(v))
        
        # Static ID
        statik_val = str(row['statik'])
        statik_label = ctk.CTkLabel(card, text=statik_val, text_color="gray", anchor="w")
        statik_label.grid(row=0, column=2, pady=10, padx=5, sticky="ew")
        statik_label.bind('<Button-1>', lambda e, v=statik_val: self.copy_to_clipboard(v))

        # Rank
        rank_label = ctk.CTkLabel(card, text=str(row['rank']), anchor="w")
        rank_label.grid(row=0, column=3, pady=10, padx=5, sticky="ew")

        # Articles
        articles_display = ", ".join(row['articles']) if row['articles'] else "Выбрать..."
        # Text truncation to prevent breaking grid layout
        if len(articles_display) > 25: 
             articles_display = articles_display[:22] + "..."
             
        articles_btn = ctk.CTkButton(card, text=articles_display, 
                                     fg_color="transparent", border_width=1, 
                                     text_color=("gray10", "gray90"),
                                     anchor="w",
                                     height=28,
                                     command=lambda: self.open_articles_dropdown(idx))
        articles_btn.grid(row=0, column=4, pady=5, padx=5, sticky="ew")

        # Payment
        sum_label = ctk.CTkLabel(card, text=f"{row['sum']} RUB", anchor="w")
        sum_label.grid(row=0, column=5, pady=10, padx=5, sticky="ew")

        # Status
        # processed is now int: 0, 1, 2
        processed_state = int(row.get('processed', 0))
        
        status_color = "red"
        status_text = "✗"
        hover_color = "darkred"

        if processed_state == 2:
            status_color = "green"
            status_text = "✔"
            hover_color = "darkgreen"
        elif processed_state == 1:
            status_color = "orange" # Yellow/Orange
            status_text = "?"
            hover_color = "darkorange"
        
        status_frame = ctk.CTkFrame(card, fg_color="transparent")
        status_frame.grid(row=0, column=6, padx=5, sticky="w")
        
        status_btn = ctk.CTkButton(
            status_frame, text=status_text, width=40, height=32,
            fg_color=status_color, 
            border_width=2,
            border_color="gray",
            hover_color=hover_color,
            command=lambda: self.toggle_processed(idx)
        )
        status_btn.pack(anchor="w")
        
        self.row_widgets[idx] = {
            "articles_btn": articles_btn,
            "sum_label": sum_label,
            "status_btn": status_btn
        }

    def copy_to_clipboard(self, value):
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update()

    def open_filter(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Фильтр")
        popup.geometry("300x600")
        popup.grab_set()

        # --- Status Filter ---
        ctk.CTkLabel(popup, text="Статусы:", font=("Arial", 14, "bold")).pack(pady=(10, 5))
        
        status_vars = {}
        status_frame = ctk.CTkFrame(popup, fg_color="transparent")
        status_frame.pack(fill="x", padx=20)

        statuses = [
            (0, "Не обработан (✗)", "red", "darkred"),
            (1, "Вопрос (?)", "orange", "darkorange"),
            (2, "Обработан (✔)", "green", "darkgreen")
        ]

        for code, text, color, hover in statuses:
            is_checked = code in self.filter_statuses
            var = ctk.BooleanVar(value=is_checked)
            status_vars[code] = var
            chk = ctk.CTkCheckBox(status_frame, text=text, variable=var, 
                                  fg_color=color, hover_color=hover)
            chk.pack(anchor="w", pady=2)

        # --- Article Filter ---
        ctk.CTkLabel(popup, text="Статьи (OR):", font=("Arial", 14, "bold")).pack(pady=(15, 5))
        
        article_vars = {}
        scroll = ctk.CTkScrollableFrame(popup, height=200)
        scroll.pack(fill="both", padx=10, pady=5, expand=True)

        for code, label, _ in ARTICLES:
            # If filter_articles is empty, everything is effectively "shown", 
            # but for UI we default to unchecked to imply "Add to filter"
            is_checked = code in self.filter_articles
            var = ctk.BooleanVar(value=is_checked)
            article_vars[code] = var
            chk = ctk.CTkCheckBox(scroll, text=f"{code} ({label})", variable=var)
            chk.pack(anchor="w", pady=2)

        # --- Actions ---
        def apply_filters():
            # Update state
            self.filter_statuses = [code for code, var in status_vars.items() if var.get()]
            self.filter_articles = [code for code, var in article_vars.items() if var.get()]
            
            self.apply_filters_internal()
            self.current_page = 0
            self.render_staff()
            popup.destroy()

        def reset_filters():
            # Reset UI vars
            for code, var in status_vars.items():
                var.set(True)
            for code, var in article_vars.items():
                var.set(False)

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10, padx=20)
        
        ctk.CTkButton(btn_frame, text="Применить", command=apply_filters, fg_color="green", hover_color="darkgreen").pack(side="left", expand=True, fill="x", padx=(0, 5))
        ctk.CTkButton(btn_frame, text="Все", command=reset_filters, width=80).pack(side="right", padx=(5, 0))

    def apply_filters_internal(self):
        new_filtered = []
        for row in self.data:
            if int(row.get('processed', 0)) not in self.filter_statuses:
                continue
            if self.filter_articles:
                has_match = any(art in row['articles'] for art in self.filter_articles)
                if not has_match:
                    continue
            new_filtered.append(row)
        self.filtered_data = new_filtered

    def sort_staff(self, key, ascending):
        def sort_key_wrapper(item):
            val = item.get(key, "")
            # Try to convert to number for numeric sorting, else string
            try:
                if key == 'rank':
                    return float(val)
                elif key == 'statik':
                    return int(val) if val else 0
                return val
            except (ValueError, TypeError):
                return str(val).lower()

        # Sort both lists so the order is maintained even if filter changes
        self.data.sort(key=sort_key_wrapper, reverse=not ascending)
        self.filtered_data.sort(key=sort_key_wrapper, reverse=not ascending)
        
        self.current_page = 0 # Reset to first page on sort
        self.render_staff()

    def update_google_row(self, row_dict):
        # Allow thread to call this
        if not self.sync_mode or not self.worksheet:
            return
            
        r = row_dict.get('gs_row_index')
        if not r: return
        
        try:
            articles_str = ", ".join(row_dict['articles'])
            # Update range D:F (Articles, Sum, Status)
            # D = 4, E = 5, F = 6
            # We are updating D, E, F columns for row r
            self.worksheet.update(range_name=f"D{r}:F{r}", values=[[articles_str, row_dict['sum'], row_dict['processed']]])
        except Exception as e:
            print(f"Update Row Error: {e}")

    def refresh_google_data(self):
        if not self.sync_mode or not self.worksheet:
            return
            
        if self.is_loading:
            return

        def worker():
            try:
                raw_data = self.worksheet.get_all_values()
                self.after(0, lambda: self._on_data_refreshed(raw_data))
            except Exception as e:
                print(f"Sync Refresh Error: {e}")

        # Start thread
        threading.Thread(target=worker, daemon=True).start()

    def _on_data_refreshed(self, raw_data):
        if not raw_data:
            self.data.clear()
        else:
            new_data = []
            # Headers: Name (0), Static (1), Rank (2), Articles (3), Sum (4), Status (5)
            rows = raw_data[1:] # Skip header
            for i, row in enumerate(rows):
                while len(row) < 6: row.append("")
                
                name = row[0]
                statik = row[1]
                rank = row[2]
                
                articles_str = row[3]
                articles = [a.strip() for a in articles_str.split(',') if a.strip()]
                
                try: payment = int(row[4])
                except: payment = 0
                
                try: processed = int(row[5])
                except: processed = 0
                
                new_data.append({
                    "name": name,
                    "statik": statik,
                    "rank": rank,
                    "articles": articles,
                    "sum": payment,
                    "processed": processed,
                    "gs_row_index": i + 2 
                })
            
            self.data = new_data
            
        self.apply_filters_internal()
        self.render_staff()

    def start_auto_refresh(self):
        self.stop_auto_refresh()
        if self.sync_mode:
            # First call immediately? Or just schedule
            self.refresh_google_data()
            # Refresh every 10000ms (10 seconds) - Increased as it is heavy
            self.auto_refresh_job = self.after(10000, self.start_auto_refresh)

    def stop_auto_refresh(self):
        if self.auto_refresh_job:
            self.after_cancel(self.auto_refresh_job)
            self.auto_refresh_job = None

    def open_articles_dropdown(self, idx):
        # Update to use filtered_data instead of data
        row = self.filtered_data[idx]
        button = self.row_widgets[idx]["articles_btn"]

        # Use Toplevel as a modal dialog
        popup = ctk.CTkToplevel(self)
        popup.title("Выбор статей")
        
        # Calculate position
        x = button.winfo_rootx()
        y = button.winfo_rooty() + button.winfo_height()
        popup.geometry(f"250x300+{x}+{y}")
        
        popup.grab_set() 
        popup.attributes("-topmost", True)
        
        container = ctk.CTkFrame(popup)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(container, text="Выберите статьи:", font=("Arial", 14, "bold")).pack(pady=5)
        
        scroll = ctk.CTkScrollableFrame(container)
        scroll.pack(fill="both", expand=True, padx=2, pady=2)

        vars = []
        for code, label, price in ARTICLES:
            is_checked = code in row["articles"]
            var = ctk.BooleanVar(value=is_checked)
            chk = ctk.CTkCheckBox(scroll, text=f"{code} - {price} RUB", variable=var)
            chk.pack(anchor="w", pady=5, padx=5)
            vars.append((code, var, price))

        def apply_changes():
            if not self.can_edit:
                messagebox.showwarning("Доступ запрещен", "Редактирование запрещено.")
                return

            selected_articles = []
            total_sum = 0
            for code, var, price in vars:
                if var.get():
                    selected_articles.append(code)
                    total_sum += price
            
            row["articles"] = selected_articles
            row["sum"] = total_sum
            
            # Update UI immediately before sync
            self.filtered_data[idx] = row
            widgets = self.row_widgets.get(idx)
            if widgets:
                new_text = ", ".join(row['articles']) if row['articles'] else "Выбрать..."
                # Handle text overflow if too many articles
                if len(new_text) > 30: new_text = new_text[:27] + "..."

                widgets["articles_btn"].configure(text=new_text)
                widgets["sum_label"].configure(text=f"{row['sum']} RUB")

            if self.sync_mode:
                 threading.Thread(target=self.update_google_row, args=(row,), daemon=True).start()
            
            popup.destroy()
        
        apply_btn = ctk.CTkButton(container, text="Сохранить", command=apply_changes, fg_color="green", hover_color="darkgreen")
        apply_btn.pack(pady=(10, 5), fill="x", padx=20)
