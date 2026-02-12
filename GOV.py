import customtkinter as ctk
from tkinter import filedialog, messagebox
import re
import pyperclip
import os
from datetime import datetime
import json

# Настройка темы
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class PeopleApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # === НАСТРОЙКИ ОКНА ===
        self.title("⚡ GovYPT PRO v3.1 — Статусы и аналитика")
        self.geometry("1600x900")
        self.minsize(1200, 700)
        
        # === ЦВЕТОВАЯ СХЕМА ===
        self.colors = {
            'bg_dark': '#050608',
            'bg_medium': '#0c0e10',
            'bg_light': '#14171c',
            'accent': '#3a8cff',
            'accent_hover': '#5a9cff',
            'accent_green': '#3aa876',
            'accent_red': '#ff4f4f',
            'accent_orange': '#ffa64f',
            'accent_purple': '#aa80ff',
            'text_primary': '#e8eaed',
            'text_secondary': '#9aa0a8',
            'border': '#202428',
            'status_red': '#ff4f4f',
            'status_green': '#3aa876', 
            'status_yellow': '#ffd966',
            'status_red_bg': '#2c1a1a',
            'status_green_bg': '#1a2c24',
            'status_yellow_bg': '#2c2c1a'
        }
        
        self.root = self
        
        # === ШРИФТЫ ===
        self.fonts = {
            'h1': ctk.CTkFont(size=24, weight="bold"),
            'h2': ctk.CTkFont(size=18, weight="bold"),
            'h3': ctk.CTkFont(size=14, weight="bold"),
            'body': ctk.CTkFont(size=12),
            'body_bold': ctk.CTkFont(size=12, weight="bold"),
            'small': ctk.CTkFont(size=11),
            'small_bold': ctk.CTkFont(size=11, weight="bold")
        }
        
        # === ЗАГРУЗКА ДАННЫХ ===
        self.load_articles()
        
        # === ПЕРЕМЕННЫЕ СОСТОЯНИЯ ===
        self.data = []
        self.filtered_data = []
        self.current_page = 0
        self.page_size = 20
        self.current_filter = 'all'  # all, filled, empty, favorites
        self.current_sort = {'key': 'rank', 'ascending': False}
        self.search_text = ""
        self.favorites = []
        self.load_favorites()
        
        self.stats = {
            'total_records': 0,
            'total_sum': 0,
            'total_files': 0,
            'duplicates': 0,
            'loaded_files': []
        }
        
        # === СОЗДАНИЕ ИНТЕРФЕЙСА ===
        self.create_widgets()
        self.setup_hotkeys()
        
    def load_articles(self):
        """Загрузка статей и сумм"""
        raw_articles = {
            '6.1': '25', '6.2': '50', '6.3': '75',
            '7.1': '100', '7.2': '25',
            '8.1': '75', '8.2': '25', '8.3': '25',
            '9.3': '25', '9.7': '75',
            '10.1': '25', '10.2': '25', '10.4': '25',
            '10.5': '50', '10.5.2': '50', '10.6': '50',
            '10.7': '25', '10.8': '50', '10.9': '25',
            '11.1': '25', '11.2': '25', '11.3': '25',
            '11.4': '50', '11.5': '25', '11.6': '75',
            '11.6.1': '75', '11.7': '25',
            '12.1': '100', '12.2': '100', '12.3': '100',
            '12.4': '25', '12.5': '75', '12.6': '25',
            '12.7': '25', '12.7.1': '25', '12.8': '25',
            '12.8.1': '25', '12.9': '75', '12.9.1': '25',
            '12.10': '50', '12.11': '25', '12.12': '100',
            '12.13': '100', '12.14': '100',
            '13.1': '50',
            '14.1': '100', '14.2': '100', '14.3': '100',
            '14.4': '100', '14.5': '100',
            '15.1': '50', '15.2': '25', '15.3': '25',
            '15.4': '50', '15.4.1': '50', '15.4.2': '25',
            '15.4.3': '50', '15.5': '50', '15.6': '25',
            '15.7': '50',
            '16.1': '75', '16.2': '100', '16.4': '50',
            '16.5': '75', '16.6': '25', '16.7': '75',
            '16.8': '75', '16.9': '25', '16.10': '50',
            '16.11': '50', '16.12': '50', '16.13': '50',
            '16.14': '75',
            '17.1': '100', '17.2': '25', '17.4': '50',
            '17.5': '50', '17.6': '25', '17.6.1': '50',
            '17.7': '25', '17.7.1': '50', '17.8': '50',
            '17.9': '25',
            '18.2': '50', '18.3': '50', '18.4': '25',
            '18.5': '50', '18.6': '25', '18.8': '25'
        }
        
        self.articles_data = []
        for code, amount in raw_articles.items():
            thousands = int(amount) * 1000
            self.articles_data.append({
                'code': code,
                'name': f'Статья {code}',
                'price': thousands
            })
        
        # Сортируем по коду
        self.articles_data.sort(key=lambda x: x['code'])
    
    def create_widgets(self):
        """Создание интерфейса"""
        
        # === ВЕРХНЯЯ ПАНЕЛЬ ===
        self.header_frame = ctk.CTkFrame(self, fg_color=self.colors['bg_medium'], height=80)
        self.header_frame.pack(fill="x", padx=0, pady=(0, 10))
        self.header_frame.pack_propagate(False)
        
        # Логотип
        self.logo_label = ctk.CTkLabel(
            self.header_frame, 
            text="⚡", 
            font=ctk.CTkFont(size=40, weight="bold"),
            text_color=self.colors['accent']
        )
        self.logo_label.pack(side="left", padx=(20, 10))
        
        # Заголовок
        self.title_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.title_frame.pack(side="left", fill="y", pady=10)
        
        self.title_label = ctk.CTkLabel(
            self.title_frame, 
            text="GovYPT PRO", 
            font=self.fonts['h1'],
            text_color=self.colors['text_primary']
        )
        self.title_label.pack(anchor="w")
        
        self.subtitle_label = ctk.CTkLabel(
            self.title_frame, 
            text="Статусы, фильтры и аналитика",
            font=self.fonts['body'],
            text_color=self.colors['text_secondary']
        )
        self.subtitle_label.pack(anchor="w")
        
        # Время
        self.time_label = ctk.CTkLabel(
            self.header_frame,
            text=datetime.now().strftime("%H:%M"),
            font=self.fonts['h2'],
            text_color=self.colors['text_secondary']
        )
        self.time_label.pack(side="right", padx=20)
        self.update_time()
        
        # === ПАНЕЛЬ УПРАВЛЕНИЯ ===
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.pack(fill="x", padx=20, pady=10)
        
        # Группа 1: Загрузка
        self.group1 = ctk.CTkFrame(self.control_frame, fg_color=self.colors['bg_light'])
        self.group1.pack(side="left", padx=5)
        
        self.load_btn = ctk.CTkButton(
            self.group1,
            text="📂 ЗАГРУЗИТЬ ФАЙЛЫ",
            command=self.load_multiple_files,
            fg_color=self.colors['accent'],
            hover_color=self.lighten_color(self.colors['accent']),
            font=self.fonts['small_bold'],
            width=140,
            height=40
        )
        self.load_btn.pack(side="left", padx=2, pady=2)
        
        # ИСПРАВЛЕНО: Кнопка избранного с выходом
        self.fav_btn = ctk.CTkButton(
            self.group1,
            text="⭐ ИЗБРАННОЕ",
            command=self.toggle_favorites_filter,
            fg_color=self.colors['accent_purple'],
            hover_color=self.lighten_color(self.colors['accent_purple']),
            font=self.fonts['small_bold'],
            width=120,
            height=40
        )
        self.fav_btn.pack(side="left", padx=2, pady=2)
        
        # Группа 2: Сохранение
        self.group2 = ctk.CTkFrame(self.control_frame, fg_color=self.colors['bg_light'])
        self.group2.pack(side="left", padx=5)
        
        self.save_btn = ctk.CTkButton(
            self.group2,
            text="💾 СОХРАНИТЬ",
            command=self.save_results,
            fg_color=self.colors['accent_green'],
            hover_color=self.lighten_color(self.colors['accent_green']),
            font=self.fonts['small_bold'],
            width=120,
            height=40
        )
        self.save_btn.pack(side="left", padx=2, pady=2)
        
        self.export_btn = ctk.CTkButton(
            self.group2,
            text="📊 ЭКСПОРТ JSON",
            command=self.export_json,
            fg_color=self.colors['accent_orange'],
            hover_color=self.lighten_color(self.colors['accent_orange']),
            font=self.fonts['small_bold'],
            width=120,
            height=40
        )
        self.export_btn.pack(side="left", padx=2, pady=2)
        
        # Группа 3: Управление
        self.group3 = ctk.CTkFrame(self.control_frame, fg_color=self.colors['bg_light'])
        self.group3.pack(side="left", padx=5)
        
        self.clear_btn = ctk.CTkButton(
            self.group3,
            text="🗑 ОЧИСТИТЬ",
            command=self.clear_all,
            fg_color=self.colors['accent_red'],
            hover_color=self.lighten_color(self.colors['accent_red']),
            font=self.fonts['small_bold'],
            width=100,
            height=40
        )
        self.clear_btn.pack(side="left", padx=2, pady=2)
        
        self.articles_btn = ctk.CTkButton(
            self.group3,
            text="📚 СТАТЬИ",
            command=self.show_articles,
            fg_color=self.colors['accent_purple'],
            hover_color=self.lighten_color(self.colors['accent_purple']),
            font=self.fonts['small_bold'],
            width=100,
            height=40
        )
        self.articles_btn.pack(side="left", padx=2, pady=2)
        
        # === ПАНЕЛЬ СТАТИСТИКИ ===
        self.stats_panel = ctk.CTkFrame(self, fg_color=self.colors['bg_medium'])
        self.stats_panel.pack(fill="x", padx=20, pady=10)
        
        # Карточки статистики
        self.create_stat_cards()
        
        # === ПАНЕЛЬ ФАЙЛОВ ===
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.pack(fill="x", padx=20, pady=5)
        
        self.files_label = ctk.CTkLabel(
            self.info_frame,
            text="📎 Загруженные файлы: —",
            font=self.fonts['small_bold'],
            text_color=self.colors['text_secondary']
        )
        self.files_label.pack(side="left", padx=5)
        
        # === ПОИСК И СОРТИРОВКА ===
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.pack(fill="x", padx=20, pady=10)
        
        # Поиск
        self.search_var = ctk.StringVar()
        self.search_var.trace('w', self.filter_data)
        
        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            textvariable=self.search_var,
            placeholder_text="🔍 Поиск по имени, ID или статье...",
            font=self.fonts['body'],
            width=400,
            height=40
        )
        self.search_entry.pack(side="left", padx=(0, 20))
        
        # Сортировка
        self.sort_frame = ctk.CTkFrame(self.search_frame, fg_color="transparent")
        self.sort_frame.pack(side="left")
        
        self.sort_label = ctk.CTkLabel(
            self.sort_frame,
            text="Сортировка:",
            font=self.fonts['small'],
            text_color=self.colors['text_secondary']
        )
        self.sort_label.pack(side="left", padx=(0, 10))
        
        # Кнопки сортировки
        self.create_sort_buttons()
        
        # Фильтры - ИСПРАВЛЕНО: Добавлена подсветка активного фильтра
        self.filter_frame = ctk.CTkFrame(self.search_frame, fg_color="transparent")
        self.filter_frame.pack(side="right")
        
        self.create_filter_buttons()
        
        # === ЛЕГЕНДА СТАТУСОВ ===
        self.legend_frame = ctk.CTkFrame(self, fg_color=self.colors['bg_light'], height=50)
        self.legend_frame.pack(fill="x", padx=20, pady=5)
        
        legend_label = ctk.CTkLabel(
            self.legend_frame,
            text="Статусы:",
            font=self.fonts['small_bold'],
            text_color=self.colors['text_secondary']
        )
        legend_label.pack(side="left", padx=10)
        
        # 🔴 Не проверен
        status_red_frame = ctk.CTkFrame(self.legend_frame, fg_color="transparent")
        status_red_frame.pack(side="left", padx=15)
        ctk.CTkLabel(status_red_frame, text="🔴", font=ctk.CTkFont(size=14)).pack(side="left")
        ctk.CTkLabel(status_red_frame, text="Не проверен", font=self.fonts['small'], text_color=self.colors['text_secondary']).pack(side="left", padx=5)
        
        # 🟢 Проверен
        status_green_frame = ctk.CTkFrame(self.legend_frame, fg_color="transparent")
        status_green_frame.pack(side="left", padx=15)
        ctk.CTkLabel(status_green_frame, text="🟢", font=ctk.CTkFont(size=14)).pack(side="left")
        ctk.CTkLabel(status_green_frame, text="Проверен", font=self.fonts['small'], text_color=self.colors['text_secondary']).pack(side="left", padx=5)
        
        # 🟡 Проверен частично
        status_yellow_frame = ctk.CTkFrame(self.legend_frame, fg_color="transparent")
        status_yellow_frame.pack(side="left", padx=15)
        ctk.CTkLabel(status_yellow_frame, text="🟡", font=ctk.CTkFont(size=14)).pack(side="left")
        ctk.CTkLabel(status_yellow_frame, text="Частично", font=self.fonts['small'], text_color=self.colors['text_secondary']).pack(side="left", padx=5)
        
        # === СПИСОК СОТРУДНИКОВ (СКРОЛЛ) ===
        self.staff_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=self.colors['bg_dark']
        )
        self.staff_scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        # === ПАГИНАЦИЯ ===
        self.pages_frame = ctk.CTkFrame(self, fg_color="transparent", height=50)
        self.pages_frame.pack(fill="x", padx=20, pady=10)
        
        self.prev_btn = ctk.CTkButton(
            self.pages_frame,
            text="◀ Назад",
            command=self.prev_page,
            width=100,
            height=35,
            fg_color=self.colors['bg_light'],
            hover_color=self.colors['border']
        )
        self.prev_btn.pack(side="left")
        
        self.page_label = ctk.CTkLabel(
            self.pages_frame,
            text="Страница 1 из 1",
            font=self.fonts['h3'],
            text_color=self.colors['text_primary']
        )
        self.page_label.pack(side="left", expand=True)
        
        self.next_btn = ctk.CTkButton(
            self.pages_frame,
            text="Вперед ▶",
            command=self.next_page,
            width=100,
            height=35,
            fg_color=self.colors['bg_light'],
            hover_color=self.colors['border']
        )
        self.next_btn.pack(side="right")
        
        # === НИЖНЯЯ ПАНЕЛЬ ===
        self.bottom_frame = ctk.CTkFrame(self, fg_color=self.colors['bg_medium'], height=30)
        self.bottom_frame.pack(fill="x", side="bottom")
        self.bottom_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            self.bottom_frame,
            text="✓ Готов к работе | Ctrl+O - загрузить | Ctrl+S - сохранить | Ctrl+F - поиск | ⭐ - повторный клик сброс фильтра",
            font=self.fonts['small'],
            text_color=self.colors['text_secondary']
        )
        self.status_label.pack(side="left", padx=10)
        
        self.version_label = ctk.CTkLabel(
            self.bottom_frame,
            text="v3.1 STATUS",
            font=self.fonts['small_bold'],
            text_color=self.colors['accent']
        )
        self.version_label.pack(side="right", padx=10)
    
    def toggle_favorites_filter(self):
        """Переключение фильтра избранного - ИСПРАВЛЕНО: теперь можно выйти"""
        if self.current_filter == 'favorites':
            # Если уже в избранном - выходим
            self.current_filter = 'all'
            self.fav_btn.configure(fg_color=self.colors['accent_purple'])
            self.show_tooltip("✓ Фильтр избранного отключен")
        else:
            # Включаем фильтр избранного
            self.current_filter = 'favorites'
            self.fav_btn.configure(fg_color=self.colors['accent_green'])
            self.show_tooltip("⭐ Показаны избранные записи")
        
        self.filter_data()
    
    def create_stat_cards(self):
        """Создание карточек статистики"""
        self.stats_panel.grid_columnconfigure((0,1,2,3), weight=1, uniform="stats")
        
        # Карточка 1: Записи
        self.counter_card = ctk.CTkFrame(self.stats_panel, fg_color=self.colors['bg_light'])
        self.counter_card.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(
            self.counter_card,
            text="👥 ЗАПИСЕЙ",
            font=self.fonts['small'],
            text_color=self.colors['text_secondary']
        ).pack(pady=(10, 5))
        
        self.counter_value = ctk.CTkLabel(
            self.counter_card,
            text="0",
            font=self.fonts['h2'],
            text_color=self.colors['text_primary']
        )
        self.counter_value.pack(pady=(0, 10))
        
        # Карточка 2: Файлы
        self.files_card = ctk.CTkFrame(self.stats_panel, fg_color=self.colors['bg_light'])
        self.files_card.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(
            self.files_card,
            text="📄 ФАЙЛОВ",
            font=self.fonts['small'],
            text_color=self.colors['text_secondary']
        ).pack(pady=(10, 5))
        
        self.files_value = ctk.CTkLabel(
            self.files_card,
            text="0",
            font=self.fonts['h2'],
            text_color=self.colors['text_primary']
        )
        self.files_value.pack(pady=(0, 10))
        
        # Карточка 3: Сумма
        self.sum_card = ctk.CTkFrame(self.stats_panel, fg_color=self.colors['bg_light'])
        self.sum_card.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(
            self.sum_card,
            text="💰 ОБЩАЯ СУММА",
            font=self.fonts['small'],
            text_color=self.colors['text_secondary']
        ).pack(pady=(10, 5))
        
        self.sum_value = ctk.CTkLabel(
            self.sum_card,
            text="$0",
            font=self.fonts['h2'],
            text_color=self.colors['text_primary']
        )
        self.sum_value.pack(pady=(0, 10))
        
        # Карточка 4: Дубликаты
        self.duplicate_card = ctk.CTkFrame(self.stats_panel, fg_color=self.colors['bg_light'])
        self.duplicate_card.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(
            self.duplicate_card,
            text="⚠ ДУБЛИКАТЫ",
            font=self.fonts['small'],
            text_color=self.colors['text_secondary']
        ).pack(pady=(10, 5))
        
        self.duplicate_value = ctk.CTkLabel(
            self.duplicate_card,
            text="0",
            font=self.fonts['h2'],
            text_color=self.colors['text_primary']
        )
        self.duplicate_value.pack(pady=(0, 10))
    
    def create_sort_buttons(self):
        """Создание кнопок сортировки"""
        sort_buttons = [
            ("Имя ↑", lambda: self.sort_data('name', True)),
            ("Имя ↓", lambda: self.sort_data('name', False)),
            ("Ранг ↑", lambda: self.sort_data('rank', True)),
            ("Ранг ↓", lambda: self.sort_data('rank', False)),
            ("Сумма ↑", lambda: self.sort_data('sum', True)),
            ("Сумма ↓", lambda: self.sort_data('sum', False)),
            ("Статус", lambda: self.sort_data('status', True))
        ]
        
        for text, command in sort_buttons:
            btn = ctk.CTkButton(
                self.sort_frame,
                text=text,
                command=command,
                width=80,
                height=30,
                font=self.fonts['small'],
                fg_color=self.colors['bg_light'],
                hover_color=self.colors['border'],
                text_color=self.colors['text_secondary']
            )
            btn.pack(side="left", padx=2)
    
    def create_filter_buttons(self):
        """Создание кнопок фильтрации - ИСПРАВЛЕНО: теперь с подсветкой"""
        self.filter_buttons = {}
        
        filter_configs = [
            ("ВСЕ", 'all'),
            ("📋 ЗАПОЛН.", 'filled'),
            ("📭 ПУСТЫЕ", 'empty'),
            ("🔴 НЕ ПРОВ.", 'status_red'),
            ("🟡 ЧАСТ.", 'status_yellow'),
            ("🟢 ПРОВ.", 'status_green')
        ]
        
        for text, filter_type in filter_configs:
            btn = ctk.CTkButton(
                self.filter_frame,
                text=text,
                command=lambda ft=filter_type: self.set_filter(ft),
                width=90,
                height=30,
                font=self.fonts['small'],
                fg_color=self.colors['bg_light'],
                hover_color=self.colors['border'],
                text_color=self.colors['text_secondary']
            )
            btn.pack(side="left", padx=2)
            self.filter_buttons[filter_type] = btn
    
    def set_filter(self, filter_type):
        """Установка фильтра - ИСПРАВЛЕНО: подсветка активной кнопки"""
        self.current_filter = filter_type
        
        # Сбрасываем цвет всех кнопок
        for btn in self.filter_buttons.values():
            btn.configure(fg_color=self.colors['bg_light'], text_color=self.colors['text_secondary'])
        
        # Подсвечиваем активную кнопку
        if filter_type in self.filter_buttons:
            self.filter_buttons[filter_type].configure(fg_color=self.colors['accent'], text_color='white')
        
        # Сбрасываем цвет кнопки избранного если не в режиме избранного
        if filter_type != 'favorites':
            self.fav_btn.configure(fg_color=self.colors['accent_purple'])
        
        self.filter_data()
    
    def lighten_color(self, color):
        """Осветление цвета"""
        if color == self.colors['accent']:
            return self.colors['accent_hover']
        elif color == self.colors['accent_green']:
            return '#5ab886'
        elif color == self.colors['accent_red']:
            return '#ff6f6f'
        elif color == self.colors['accent_orange']:
            return '#ffb66f'
        elif color == self.colors['accent_purple']:
            return '#bb99ff'
        return color
    
    def update_time(self):
        """Обновление времени"""
        current_time = datetime.now().strftime("%H:%M")
        self.time_label.configure(text=current_time)
        self.after(1000, self.update_time)
    
    def parse_line(self, line):
        """Парсинг строки с эмодзи"""
        line = line.strip()
        if not line:
            return None, None, None
        
        line = re.sub(r'^[🔴🟢🔵🟡🟣]\s*', '', line)
        
        match = re.match(r'([A-Za-zА-Яа-я]+_[A-Za-zА-Яа-я]+)\s*\[(\d+)\].*?(\d+)$', line)
        if match:
            return match.group(1), match.group(2), match.group(3)
        
        match = re.match(r'([A-Za-zА-Яа-я]+_[A-Za-zА-Яа-я]+)\s*\[(\d+)\]', line)
        if match:
            full_name = match.group(1)
            user_id = match.group(2)
            rank_match = re.search(r'(\d+)$', line)
            rank = rank_match.group(1) if rank_match else "0"
            return full_name, user_id, rank
            
        return None, None, None
    
    def load_multiple_files(self):
        """Загрузка нескольких файлов"""
        files = filedialog.askopenfilenames(
            title="Выберите файлы для объединения",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not files:
            return
        
        existing_ids = {item['id'] for item in self.data if 'id' in item}
        duplicate_count = 0
        new_count = 0
        loaded_files = set(self.stats.get('loaded_files', []))
        
        for file_path in files:
            filename = os.path.basename(file_path)
            loaded_files.add(filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line in lines:
                    full_name, user_id, rank = self.parse_line(line)
                    if full_name and user_id and rank:
                        if user_id not in existing_ids:
                            self.data.append({
                                'name': full_name,
                                'id': user_id,
                                'rank': rank,
                                'articles': [],
                                'sum': 0,
                                'source': filename,
                                'favorite': f"{user_id}_{full_name}" in self.favorites,
                                'status': 'red'  # 🔴 По умолчанию не проверен
                            })
                            existing_ids.add(user_id)
                            new_count += 1
                        else:
                            duplicate_count += 1
                            
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить {filename}:\n{str(e)}")
        
        self.stats['loaded_files'] = list(loaded_files)
        self.stats['total_files'] = len(loaded_files)
        self.stats['duplicates'] = self.stats.get('duplicates', 0) + duplicate_count
        
        self.filter_data()
        self.update_stats(new_records=new_count, duplicates=duplicate_count)
        
        messagebox.showinfo(
            "Успешно",
            f"✅ Загружено: {new_count} записей\n"
            f"⚠ Пропущено дубликатов: {duplicate_count}\n"
            f"📁 Всего записей: {len(self.data)}"
        )
    
    def filter_data(self, *args):
        """Фильтрация данных - ИСПРАВЛЕНО: добавлены фильтры по статусам"""
        self.search_text = self.search_var.get().lower()
        self.filtered_data = []
        
        for item in self.data:
            show = True
            
            # Фильтр по типу
            if self.current_filter == 'filled':
                show = show and bool(item.get('articles', []))
            elif self.current_filter == 'empty':
                show = show and not bool(item.get('articles', []))
            elif self.current_filter == 'favorites':
                show = show and item.get('favorite', False)
            elif self.current_filter == 'status_red':
                show = show and item.get('status', 'red') == 'red'
            elif self.current_filter == 'status_green':
                show = show and item.get('status', 'red') == 'green'
            elif self.current_filter == 'status_yellow':
                show = show and item.get('status', 'red') == 'yellow'
            
            # Поиск по тексту
            if show and self.search_text and self.search_text != "поиск по имени, id или статье...":
                searchable = f"{item.get('name', '')} {item.get('id', '')} {', '.join(item.get('articles', []))}".lower()
                show = self.search_text in searchable
            
            if show:
                self.filtered_data.append(item)
        
        # Применяем сортировку
        self.apply_sort()
        self.current_page = 0
        self.render_staff()
    
    def sort_data(self, key, ascending):
        """Сортировка данных - ИСПРАВЛЕНО: добавлена сортировка по статусу"""
        self.current_sort = {'key': key, 'ascending': ascending}
        self.apply_sort()
        self.render_staff()
    
    def apply_sort(self):
        """Применение сортировки - ИСПРАВЛЕНО: сортировка статусов"""
        key = self.current_sort['key']
        ascending = self.current_sort['ascending']
        
        status_order = {'green': 0, 'yellow': 1, 'red': 2}
        
        def sort_key(item):
            if key == 'status':
                val = status_order.get(item.get('status', 'red'), 2)
                return val
            elif key == 'rank' or key == 'sum':
                val = item.get(key, 0)
                try:
                    return float(val) if val else 0
                except:
                    return 0
            else:
                return str(item.get(key, '')).lower()
        
        self.filtered_data.sort(key=sort_key, reverse=not ascending)
    
    def show_favorites(self):
        """Показать избранное"""
        self.set_filter('favorites')
    
    def render_staff(self):
        """Отрисовка списка сотрудников - ИСПРАВЛЕНО: ровные столбцы и статусы"""
        # Очищаем скролл
        for widget in self.staff_scroll.winfo_children():
            widget.destroy()
        
        if not self.filtered_data:
            # Показываем пустое состояние
            empty_frame = ctk.CTkFrame(self.staff_scroll, fg_color="transparent")
            empty_frame.pack(expand=True, fill="both", pady=50)
            
            ctk.CTkLabel(
                empty_frame,
                text="📭 Нет данных",
                font=self.fonts['h2'],
                text_color=self.colors['text_secondary']
            ).pack(pady=10)
            
            ctk.CTkLabel(
                empty_frame,
                text="Загрузите файлы с помощью кнопки 'ЗАГРУЗИТЬ ФАЙЛЫ'",
                font=self.fonts['body'],
                text_color=self.colors['text_secondary']
            ).pack()
            
            self.page_label.configure(text="Страница 0 из 0")
            self.prev_btn.configure(state="disabled")
            self.next_btn.configure(state="disabled")
            return
        
        # Пагинация
        total_pages = (len(self.filtered_data) + self.page_size - 1) // self.page_size
        if total_pages == 0:
            total_pages = 1
        
        if self.current_page >= total_pages:
            self.current_page = total_pages - 1
        if self.current_page < 0:
            self.current_page = 0
        
        start = self.current_page * self.page_size
        end = min(start + self.page_size, len(self.filtered_data))
        
        # Обновляем кнопки пагинации
        self.page_label.configure(text=f"Страница {self.current_page + 1} из {total_pages}")
        self.prev_btn.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.current_page < total_pages - 1 else "disabled")
        
        # Заголовки таблицы - ИСПРАВЛЕНО: ровные столбцы
        headers_frame = ctk.CTkFrame(self.staff_scroll, fg_color="transparent")
        headers_frame.pack(fill="x", pady=(0, 5))
        
        # Настройка весов колонок с uniform для ровных столбцов
        weights = [1, 4, 2, 1, 4, 2, 1, 1]  # №, Имя, ID, Ранг, Статьи, Сумма, Статус, Избр.
        
        for i, weight in enumerate(weights):
            headers_frame.grid_columnconfigure(i, weight=weight, uniform="staff_columns")
        
        headers = ["№", "ИМЯ_ФАМИЛИЯ", "ID", "РАНГ", "СТАТЬИ", "СУММА", "СТАТУС", "ИЗБР."]
        
        for i, header in enumerate(headers):
            ctk.CTkLabel(
                headers_frame,
                text=header,
                font=self.fonts['small_bold'],
                text_color=self.colors['text_secondary']
            ).grid(row=0, column=i, padx=5, pady=5, sticky="w")
        
        # Карточки сотрудников
        for i in range(start, end):
            self.create_staff_card(i, self.filtered_data[i])
    
    def create_staff_card(self, idx, item):
        """Создание карточки сотрудника - ИСПРАВЛЕНО: ровные столбцы и статусы"""
        card = ctk.CTkFrame(
            self.staff_scroll,
            fg_color=self.colors['bg_light'],
            corner_radius=8
        )
        card.pack(fill="x", pady=2, padx=2)
        
        # Настройка весов колонок - ТОЧНО ТАКИЕ ЖЕ КАК В ЗАГОЛОВКЕ!
        weights = [1, 4, 2, 1, 4, 2, 1, 1]
        for i, weight in enumerate(weights):
            card.grid_columnconfigure(i, weight=weight, uniform="staff_columns")
        
        # №
        ctk.CTkLabel(
            card,
            text=str(idx + 1),
            font=self.fonts['body'],
            text_color=self.colors['text_secondary']
        ).grid(row=0, column=0, padx=5, pady=10, sticky="w")
        
        # Имя (кликабельно)
        name_label = ctk.CTkLabel(
            card,
            text=item['name'],
            font=self.fonts['body_bold'],
            text_color=self.colors['text_primary'],
            cursor="hand2"
        )
        name_label.grid(row=0, column=1, padx=5, pady=10, sticky="w")
        name_label.bind('<Button-1>', lambda e, v=item['name']: self.copy_to_clipboard(v))
        
        # ID (кликабельно)
        id_label = ctk.CTkLabel(
            card,
            text=item['id'],
            font=self.fonts['body'],
            text_color=self.colors['accent'],
            cursor="hand2"
        )
        id_label.grid(row=0, column=2, padx=5, pady=10, sticky="w")
        id_label.bind('<Button-1>', lambda e, v=item['id']: self.copy_to_clipboard(v))
        
        # Ранг
        rank_label = ctk.CTkLabel(
            card,
            text=item['rank'],
            font=self.fonts['body_bold'],
            text_color=self.colors['text_primary']
        )
        rank_label.grid(row=0, column=3, padx=5, pady=10, sticky="w")
        
        # Статьи (кнопка выбора)
        articles_text = ", ".join(item['articles']) if item['articles'] else "Выбрать..."
        if len(articles_text) > 25:
            articles_text = articles_text[:22] + "..."
        
        articles_btn = ctk.CTkButton(
            card,
            text=articles_text,
            command=lambda: self.open_articles_dropdown(idx, item),
            fg_color="transparent",
            hover_color=self.colors['border'],
            border_width=1,
            border_color=self.colors['border'],
            text_color=self.colors['text_primary'],
            font=self.fonts['small'],
            height=30,
            anchor="w"
        )
        articles_btn.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
        
        # Сумма
        sum_value = item.get('sum', 0)
        sum_formatted = f"${sum_value:,}".replace(",", " ") if sum_value else "$0"
        
        sum_label = ctk.CTkLabel(
            card,
            text=sum_formatted,
            font=self.fonts['body_bold'],
            text_color=self.colors['accent_green'] if sum_value else self.colors['text_secondary']
        )
        sum_label.grid(row=0, column=5, padx=5, pady=10, sticky="w")
        
        # === СТАТУС: 🔴 🟡 🟢 ===
        status = item.get('status', 'red')
        status_colors = {
            'red': self.colors['status_red'],
            'green': self.colors['status_green'],
            'yellow': self.colors['status_yellow']
        }
        status_texts = {
            'red': '🔴',
            'green': '🟢',
            'yellow': '🟡'
        }
        
        status_btn = ctk.CTkButton(
            card,
            text=status_texts.get(status, '🔴'),
            command=lambda: self.cycle_status(idx, item),
            width=40,
            height=30,
            fg_color=status_colors.get(status, self.colors['status_red']),
            hover_color=self.lighten_color(status_colors.get(status, self.colors['status_red'])),
            text_color='white',
            font=ctk.CTkFont(size=14)
        )
        status_btn.grid(row=0, column=6, padx=5, pady=8)
        
        # Избранное
        favorite_btn = ctk.CTkButton(
            card,
            text="⭐" if item.get('favorite', False) else "☆",
            command=lambda: self.toggle_favorite(idx, item),
            width=40,
            height=30,
            fg_color=self.colors['bg_light'],
            hover_color=self.colors['border'],
            text_color="#ffd700" if item.get('favorite', False) else self.colors['text_secondary'],
            font=ctk.CTkFont(size=14)
        )
        favorite_btn.grid(row=0, column=7, padx=5, pady=8)
    
    def cycle_status(self, data_idx, item):
        """Циклическое переключение статуса: 🔴 -> 🟡 -> 🟢 -> 🔴"""
        status_order = ['red', 'yellow', 'green']
        current = item.get('status', 'red')
        
        try:
            next_index = (status_order.index(current) + 1) % len(status_order)
            next_status = status_order[next_index]
        except:
            next_status = 'red'
        
        item['status'] = next_status
        
        # Показываем подсказку
        status_names = {'red': '🔴 Не проверен', 'yellow': '🟡 Частично', 'green': '🟢 Проверен'}
        self.show_tooltip(status_names.get(next_status, '🔴 Не проверен'))
        
        # Перерисовываем
        self.render_staff()
    
    def open_articles_dropdown(self, data_idx, item):
        """Открыть окно выбора статей"""
        popup = ctk.CTkToplevel(self)
        popup.title("Выбор статей")
        popup.geometry("400x500")
        popup.configure(fg_color=self.colors['bg_dark'])
        
        # Делаем модальным
        popup.transient(self)
        popup.grab_set()
        
        # Заголовок
        ctk.CTkLabel(
            popup,
            text=f"📋 Выбор статей для {item['name']}",
            font=self.fonts['h3'],
            text_color=self.colors['text_primary']
        ).pack(pady=15)
        
        # Скролл с чекбоксами
        scroll_frame = ctk.CTkScrollableFrame(
            popup,
            fg_color=self.colors['bg_light'],
            height=300
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        checkboxes = []
        vars_list = []
        
        for article in self.articles_data:
            is_checked = article['code'] in item.get('articles', [])
            var = ctk.BooleanVar(value=is_checked)
            
            frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            
            checkbox = ctk.CTkCheckBox(
                frame,
                text=f"{article['code']} — ${article['price']:,}".replace(",", " "),
                variable=var,
                font=self.fonts['body'],
                text_color=self.colors['text_primary']
            )
            checkbox.pack(side="left", padx=10, pady=5)
            
            checkboxes.append((article['code'], var, article['price']))
            vars_list.append(var)
        
        def apply_changes():
            selected = []
            total = 0
            
            for code, var, price in checkboxes:
                if var.get():
                    selected.append(code)
                    total += price
            
            # Обновляем данные
            data_item = self.filtered_data[data_idx]
            data_item['articles'] = selected
            data_item['sum'] = total
            
            # Обновляем статистику
            self.update_total_sum()
            
            # Перерисовываем
            self.render_staff()
            popup.destroy()
            self.show_tooltip(f"✅ Выбрано статей: {len(selected)}")
        
        def select_all():
            for var in vars_list:
                var.set(True)
        
        def clear_all():
            for var in vars_list:
                var.set(False)
        
        # Кнопки управления
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text="✓ Выбрать все",
            command=select_all,
            fg_color=self.colors['bg_light'],
            hover_color=self.colors['border'],
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="✗ Очистить все",
            command=clear_all,
            fg_color=self.colors['bg_light'],
            hover_color=self.colors['border'],
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="💾 Сохранить",
            command=apply_changes,
            fg_color=self.colors['accent_green'],
            hover_color=self.lighten_color(self.colors['accent_green']),
            width=120
        ).pack(side="right", padx=5)
    
    def toggle_favorite(self, data_idx, item):
        """Переключение избранного"""
        key = f"{item['id']}_{item['name']}"
        
        if key in self.favorites:
            self.favorites.remove(key)
            item['favorite'] = False
            self.show_tooltip("☆ Удалено из избранного")
        else:
            self.favorites.append(key)
            item['favorite'] = True
            self.show_tooltip("⭐ Добавлено в избранное")
        
        self.save_favorites()
        self.render_staff()
    
    def load_favorites(self):
        """Загрузка избранного"""
        try:
            if os.path.exists('favorites.json'):
                with open('favorites.json', 'r', encoding='utf-8') as f:
                    self.favorites = json.load(f)
        except:
            self.favorites = []
    
    def save_favorites(self):
        """Сохранение избранного"""
        try:
            with open('favorites.json', 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def copy_to_clipboard(self, value):
        """Копирование в буфер обмена"""
        self.clipboard_clear()
        self.clipboard_append(str(value))
        self.show_tooltip(f"📋 Скопировано: {value[:30]}...")
    
    def show_tooltip(self, message):
        """Показать всплывающую подсказку"""
        tooltip = ctk.CTkToplevel(self)
        tooltip.wm_overrideredirect(True)
        
        x = self.winfo_pointerx()
        y = self.winfo_pointery() - 30
        tooltip.geometry(f"+{x}+{y}")
        
        label = ctk.CTkLabel(
            tooltip,
            text=message,
            font=self.fonts['small'],
            text_color=self.colors['text_primary'],
            fg_color=self.colors['bg_medium'],
            corner_radius=5,
            padx=10,
            pady=5
        )
        label.pack()
        
        tooltip.after(1500, tooltip.destroy)
    
    def prev_page(self):
        """Предыдущая страница"""
        if self.current_page > 0:
            self.current_page -= 1
            self.render_staff()
    
    def next_page(self):
        """Следующая страница"""
        total_pages = (len(self.filtered_data) + self.page_size - 1) // self.page_size
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.render_staff()
            # Скролл вверх
            self.staff_scroll._parent_canvas.yview_moveto(0)
    
    def update_stats(self, new_records=0, duplicates=0):
        """Обновление статистики"""
        total_items = len(self.data)
        self.stats['total_records'] = total_items
        self.stats['total_files'] = len(self.stats.get('loaded_files', []))
        
        self.counter_value.configure(text=str(total_items))
        self.files_value.configure(text=str(self.stats['total_files']))
        self.duplicate_value.configure(text=str(self.stats.get('duplicates', 0)))
        
        files_text = "📎 Загруженные файлы: " + ", ".join(self.stats.get('loaded_files', [])) if self.stats.get('loaded_files') else "📎 Загруженные файлы: —"
        self.files_label.configure(text=files_text)
        
        self.update_total_sum()
    
    def update_total_sum(self):
        """Обновление общей суммы"""
        total = sum(item.get('sum', 0) for item in self.data)
        self.stats['total_sum'] = total
        formatted_total = f"${total:,}".replace(",", " ")
        self.sum_value.configure(text=formatted_total)
    
    def clear_all(self):
        """Очистка всего"""
        if messagebox.askyesno("Очистка", "Удалить все данные?"):
            self.data = []
            self.filtered_data = []
            self.stats = {
                'total_records': 0,
                'total_sum': 0,
                'total_files': 0,
                'duplicates': 0,
                'loaded_files': []
            }
            
            self.counter_value.configure(text="0")
            self.files_value.configure(text="0")
            self.sum_value.configure(text="$0")
            self.duplicate_value.configure(text="0")
            self.files_label.configure(text="📎 Загруженные файлы: —")
            self.search_var.set("")
            
            # Сбрасываем фильтры
            self.current_filter = 'all'
            self.set_filter('all')
            
            self.render_staff()
            self.show_tooltip("🗑 Все данные очищены")
    
    def export_json(self):
        """Экспорт в JSON"""
        if not self.data:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'stats': self.stats,
                'files': self.stats.get('loaded_files', []),
                'data': self.data,
                'favorites': self.favorites
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.show_tooltip(f"✅ Экспортировано: {len(self.data)} записей")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать:\n{str(e)}")
    
    def get_all_data(self):
        """Получение всех данных с заполненными статьями"""
        result = []
        for item in self.data:
            if item.get('articles') and item.get('sum', 0) > 0:
                result.append({
                    'rank': item['rank'],
                    'full_name': item['name'],
                    'id': item['id'],
                    'articles': item['articles'],
                    'sum': f"${item['sum']:,}".replace(",", " "),
                    'numeric_sum': item['sum'],
                    'source': item['source'],
                    'status': item.get('status', 'red')
                })
        
        result.sort(key=lambda x: int(x['rank']) if x['rank'].isdigit() else 0, reverse=True)
        return result
    
    def save_results(self):
        """Сохранение результатов"""
        data = self.get_all_data()
        if not data:
            messagebox.showwarning("Предупреждение", "Нет заполненных статей для сохранения!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            total_sum = sum(item['numeric_sum'] for item in data)
            formatted_total = f"${total_sum:,}".replace(",", " ")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("=" * 120 + "\n")
                f.write("ОТЧЕТ GovYPT PRO v3.1\n")
                f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
                f.write("=" * 120 + "\n\n")
                
                f.write(f"📁 Файлы: {', '.join(self.stats.get('loaded_files', []))}\n")
                f.write(f"👥 Всего записей: {len(data)}\n")
                f.write(f"💰 Общая сумма: {formatted_total}\n")
                f.write(f"⚠ Дубликаты: {self.stats.get('duplicates', 0)}\n\n")
                
                f.write("-" * 120 + "\n")
                f.write(f"{'№':4} {'Ранг':6} {'Имя_Фамилия':30} {'ID':12} {'Статьи':20} {'Сумма':12} {'Статус':8} {'Источник':20}\n")
                f.write("-" * 120 + "\n")
                
                status_symbols = {'red': '🔴', 'yellow': '🟡', 'green': '🟢'}
                
                for i, row in enumerate(data, 1):
                    articles_str = ", ".join(row['articles'])[:20]
                    status = status_symbols.get(row.get('status', 'red'), '🔴')
                    f.write(f"{i:4} {row['rank']:6} {row['full_name']:30} ")
                    f.write(f"{row['id']:12} {articles_str:20} {row['sum']:12} ")
                    f.write(f"{status:8} {os.path.basename(row['source']):20}\n")
                
                f.write("\n" + "=" * 120 + "\n")
                f.write(f"ИТОГО: {formatted_total}\n")
                f.write("=" * 120 + "\n")
            
            self.show_tooltip(f"✅ Сохранено: {len(data)} записей, сумма: {formatted_total}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{str(e)}")
    
    def show_articles(self):
        """Показ справочника статей"""
        win = ctk.CTkToplevel(self)
        win.title("📚 Справочник статей")
        win.geometry("500x700")
        win.configure(fg_color=self.colors['bg_dark'])
        
        # Заголовок
        ctk.CTkLabel(
            win,
            text="📋 СТАТЬИ И СУММЫ",
            font=self.fonts['h2'],
            text_color=self.colors['text_primary']
        ).pack(pady=20)
        
        # Скролл с контентом
        scroll = ctk.CTkScrollableFrame(
            win,
            fg_color=self.colors['bg_light']
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        for article in self.articles_data:
            frame = ctk.CTkFrame(scroll, fg_color="transparent")
            frame.pack(fill="x", pady=2, padx=5)
            
            ctk.CTkLabel(
                frame,
                text=article['code'],
                font=self.fonts['body_bold'],
                text_color=self.colors['accent'],
                width=100,
                anchor="w"
            ).pack(side="left", padx=10)
            
            ctk.CTkLabel(
                frame,
                text="→",
                font=self.fonts['body'],
                text_color=self.colors['text_secondary']
            ).pack(side="left", padx=5)
            
            price_formatted = f"${article['price']:,}".replace(",", " ")
            ctk.CTkLabel(
                frame,
                text=price_formatted,
                font=self.fonts['body_bold'],
                text_color=self.colors['accent_green']
            ).pack(side="left", padx=10)
        
        # Кнопка закрытия
        ctk.CTkButton(
            win,
            text="ЗАКРЫТЬ",
            command=win.destroy,
            fg_color=self.colors['accent_red'],
            hover_color=self.lighten_color(self.colors['accent_red']),
            font=self.fonts['small_bold'],
            width=200,
            height=40
        ).pack(pady=20)
    
    def setup_hotkeys(self):
        """Настройка горячих клавиш"""
        self.bind('<Control-o>', lambda e: self.load_multiple_files())
        self.bind('<Control-s>', lambda e: self.save_results())
        self.bind('<Control-f>', lambda e: self.search_entry.focus())
        self.bind('<Control-d>', lambda e: self.clear_all())
        self.bind('<Control-e>', lambda e: self.export_json())
        self.bind('<Escape>', lambda e: self.search_entry.delete(0, 'end'))

if __name__ == "__main__":
    app = PeopleApp()
    app.mainloop()