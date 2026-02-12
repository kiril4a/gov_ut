import customtkinter as ctk
import tkinter as tk  # Needed for some constants or specific dialogs
from tkinter import filedialog, messagebox
import re

# Set the theme and color appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

ARTICLES = [
    ("1.2", "Статья 1.2", 5000),
    ("1.3", "Статья 1.3", 5000),
    # Можно добавить больше статей
]

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Employee Data")
        self.geometry("1100x800")
        self.data = []
        self.filtered_data = []
        self.filter_statuses = [0, 1, 2]  # Default: all statuses selected
        self.filter_articles = []         # Default: empty list means "all articles" (no filter)
        self.row_widgets = {}
        
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

        # Settings Button (replaces Menu)
        self.settings_btn = ctk.CTkButton(self.header_frame, text="Settings", width=100, command=self.open_settings)
        self.settings_btn.grid(row=0, column=1, sticky="e")

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
        # Functions as the 'Load File' menu item did
        self.load_file()

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

    def load_file(self):
        file_path = filedialog.askopenfilename(parent=self, filetypes=[("Text files", "*.txt")])
        if not file_path:
            return
        self.data.clear()
        try:
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
                    
                    self.data.append({
                        "name": name,
                        "statik": statik,
                        "rank": rank,
                        "articles": [],
                        "sum": 0,
                        "processed": 0 # 0: No (Red), 1: Question (Yellow), 2: Yes (Green)
                    })
            self.filtered_data = list(self.data) # Initialize filtered_data
            self.current_page = 0
            self.render_staff()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

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
        total_pages = (len(self.filtered_data) + self.page_size - 1) // self.page_size
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.render_staff()
            # Scroll to top
            self.staff_scroll._parent_canvas.yview_moveto(0)

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
        
        if processed_state == 2:
            status_color = "green"
            status_text = "✔"
            hover_color = "darkgreen"
        elif processed_state == 1:
            status_color = "orange" # Yellow/Orange
            status_text = "?"
            hover_color = "darkorange"
        else: # 0
            status_color = "red"
            status_text = "✗"
            hover_color = "darkred"
        
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

    def toggle_processed(self, idx):
        row = self.filtered_data[idx]
        current_state = int(row['processed'])
        new_state = (current_state + 1) % 3
        row['processed'] = new_state
        
        widgets = self.row_widgets.get(idx)
        if widgets:
            btn = widgets["status_btn"]
            
            if new_state == 2:
                btn.configure(text="✔", fg_color="green", hover_color="darkgreen")
            elif new_state == 1:
                btn.configure(text="?", fg_color="orange", hover_color="darkorange")
            else:
                btn.configure(text="✗", fg_color="red", hover_color="darkred")

    def copy_to_clipboard(self, value):
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update()
        # Optional: visual feedback?

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
            
            new_filtered = []
            for row in self.data:
                # 1. Check Status (Must match one of selected)
                if int(row['processed']) not in self.filter_statuses:
                    continue
                
                # 2. Check Articles (If any selected, row must have at least one)
                if self.filter_articles:
                    has_match = any(art in row['articles'] for art in self.filter_articles)
                    if not has_match:
                        continue
                
                new_filtered.append(row)
            
            self.filtered_data = new_filtered
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
            selected_articles = []
            total_sum = 0
            for code, var, price in vars:
                if var.get():
                    selected_articles.append(code)
                    total_sum += price
            
            row["articles"] = selected_articles
            row["sum"] = total_sum
            
            widgets = self.row_widgets.get(idx)
            if widgets:
                new_text = ", ".join(row['articles']) if row['articles'] else "Выбрать..."
                # Handle text overflow if too many articles
                if len(new_text) > 30: new_text = new_text[:27] + "..."

                widgets["articles_btn"].configure(text=new_text)
                widgets["sum_label"].configure(text=f"{row['sum']} RUB")
            
            popup.destroy()
        
        apply_btn = ctk.CTkButton(container, text="Сохранить", command=apply_changes, fg_color="green", hover_color="darkgreen")
        apply_btn.pack(pady=(10, 5), fill="x", padx=20)

if __name__ == "__main__":
    app = App()
    app.mainloop()
