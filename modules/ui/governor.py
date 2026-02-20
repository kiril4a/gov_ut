# order_editor.py - Три вкладки: Поля, Пункты, Просмотр + Загрузка из Google Sheets
import sys
import os
import re
import requests
import json
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QFrame, QGridLayout,
                             QLineEdit, QSpinBox, QComboBox, QDateEdit,
                             QTextEdit, QScrollArea, QSizePolicy, QMessageBox,
                             QApplication, QListWidget, QListWidgetItem, 
                             QInputDialog, QFileDialog, QTabWidget, QSplitter,
                             QGroupBox, QProgressDialog, QDialog, QDialogButtonBox,
                             QFormLayout)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QIcon, QClipboard, QPixmap, QFont
from utils import get_resource_path

# Функция для загрузки изображения на imgbb.com
def upload_to_imgbb(image_path, api_key='6b7a6a3c7f5e8d9c4b3a2f1e0d9c8b7a'):
    try:
        url = "https://api.imgbb.com/1/upload"
        with open(image_path, 'rb') as file:
            payload = {'key': api_key}
            files = {'image': file}
            response = requests.post(url, payload, files=files)
            if response.status_code == 200:
                data = response.json()
                return data['data']['url']
            else:
                return None
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return None

# Диалог для ввода данных Google Sheets
class GoogleSheetsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Загрузка из Google Sheets")
        self.setModal(True)
        self.resize(500, 200)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Поле для ID таблицы
        self.sheet_id_edit = QLineEdit()
        self.sheet_id_edit.setPlaceholderText("17a-Q3tCgAbgRWR3hP9Px6t92hphYDgqcv-dRFcEf8bs")
        form_layout.addRow("ID таблицы:", self.sheet_id_edit)
        
        # Поле для названия листа
        self.sheet_name_edit = QLineEdit()
        self.sheet_name_edit.setPlaceholderText("Лист1 (или оставьте пустым для первого листа)")
        form_layout.addRow("Название листа:", self.sheet_name_edit)
        
        # Пояснение
        info_label = QLabel(
            "ID таблицы можно найти в URL:\n"
            "https://docs.google.com/spreadsheets/d/【ID-ТАБЛИЦЫ】/edit"
        )
        info_label.setStyleSheet("color: #888; font-size: 12px;")
        info_label.setWordWrap(True)
        form_layout.addRow("", info_label)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Устанавливаем значения по умолчанию
        self.sheet_id_edit.setText("17a-Q3tCgAbgRWR3hP9Px6t92hphYDgqcv-dRFcEf8bs")
        self.sheet_name_edit.setText("templates")
    
    def get_values(self):
        return {
            'sheet_id': self.sheet_id_edit.text().strip(),
            'sheet_name': self.sheet_name_edit.text().strip() or None
        }

# Класс для загрузки шаблонов из Google Sheets в отдельном потоке
class TemplateLoader(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, sheet_id, sheet_name=None):
        super().__init__()
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        
    def run(self):
        try:
            self.progress.emit("Загрузка шаблонов из Google Sheets...")
            templates = self.load_from_google_sheets()
            if templates:
                self.finished.emit(templates)
            else:
                self.error.emit("Не удалось загрузить шаблоны. Проверьте ID таблицы и название листа.")
        except Exception as e:
            self.error.emit(f"Ошибка загрузки: {str(e)}")
    
    def load_from_google_sheets(self):
        """Загрузка шаблонов из Google Sheets"""
        try:
            # Формируем URL для экспорта в CSV
            if self.sheet_name:
                # Если указано название листа, используем gid (нужно преобразовать название в gid)
                # Для простоты сначала пробуем без указания листа
                csv_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/export?format=csv"
                self.progress.emit("Пробуем загрузить первый лист...")
            else:
                csv_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/export?format=csv"
            
            response = requests.get(csv_url, timeout=10)
            if response.status_code == 200:
                templates = self.parse_csv_templates(response.text)
                if templates:
                    return templates
            
            # Если не получилось, пробуем опубликованную версию
            pub_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/pub?output=csv"
            response = requests.get(pub_url, timeout=10)
            if response.status_code == 200:
                templates = self.parse_csv_templates(response.text)
                if templates:
                    return templates
            
            return None
            
        except Exception as e:
            print(f"Ошибка загрузки из Google Sheets: {e}")
            return None
    
    def parse_csv_templates(self, csv_data):
        """Парсинг CSV данных в формат шаблонов"""
        import csv
        from io import StringIO
        
        templates = {}
        
        try:
            reader = csv.DictReader(StringIO(csv_data))
            
            for row_num, row in enumerate(reader, start=1):
                template_id = row.get('id', '').strip()
                if not template_id:
                    # Если нет ID, используем номер строки
                    template_id = f"template_{row_num}"
                
                # Проверяем обязательные поля
                name = row.get('name', '').strip()
                if not name:
                    name = f"Шаблон {row_num}"
                
                # Создаем структуру шаблона
                template = {
                    "name": name,
                    "title": row.get('title', 'ПОСТАНОВЛЕНИЕ № {number}'),
                    "header_img": row.get('header_img', '[IMG size="1280x446"]{header_url}[/IMG]'),
                    "body": row.get('body', ''),
                    "items": [],
                    "footer": row.get('footer', ''),
                    "fields": {}
                }
                
                # Загружаем пункты (items)
                items_str = row.get('items', '[]')
                if items_str:
                    try:
                        # Пробуем распарсить как JSON
                        items = json.loads(items_str)
                        if isinstance(items, list):
                            template["items"] = items
                        else:
                            template["items"] = [str(items)]
                    except:
                        # Если не JSON, используем как есть
                        template["items"] = [items_str]
                
                # Загружаем поля (fields)
                fields_str = row.get('fields', '{}')
                if fields_str:
                    try:
                        fields = json.loads(fields_str)
                        if isinstance(fields, dict):
                            template["fields"] = fields
                    except:
                        # Если не JSON, создаем пустой словарь
                        template["fields"] = {}
                
                templates[template_id] = template
                self.progress.emit(f"Загружен шаблон: {name}")
            
            return templates if templates else None
            
        except Exception as e:
            print(f"Ошибка парсинга CSV: {e}")
            return None

# ==================== СТАНДАРТНЫЕ ШАБЛОНЫ ПОСТАНОВЛЕНИЙ ====================
DEFAULT_TEMPLATES = {
    "health": {
        "name": "🏥 Управление здравоохранения",
        "title": "ПОСТАНОВЛЕНИЕ УПРАВЛЕНИЯ ЗДРАВООХРАНЕНИЯ № {number}",
        "header_img": "[IMG size=\"1280x446\"]{header_url}[/IMG]",
        "body": """[JUSTIFY][SIZE=5][FONT=book antiqua][B]Я, {position} Сан-Андреас, {full_name}, в соответствии с действующей Конституцией штата Сан-Андреаса, положением о медицинских проверках государственных организаций и другими нормативно-правовыми актами штата Сан-Андреас, постановляю:[/B][/FONT][/SIZE][/JUSTIFY]""",
        "items": [
            "Признать плановую медицинскую и санитарную проверку государственной организации [COLOR=rgb(184, 49, 47)][B]{organization}[/B][/COLOR], назначенную на [COLOR=rgb(184, 49, 47)][B]{weekday}[/B][/COLOR], [COLOR=rgb(184, 49, 47)][B]{date}[/B][/COLOR] в [COLOR=rgb(184, 49, 47)][B]{time}[/B][/COLOR] [COLOR=rgb(184, 49, 47)][B]{status}[/B][/COLOR];",
            "По итогам плановой медицинской и санитарной проверки признать результаты медицинской проверки — [COLOR=rgb(184, 49, 47)][B]{med_result}[/B][/COLOR], а санитарной проверки — [COLOR=rgb(184, 49, 47)][B]{san_result}[/B][/COLOR];",
            "Наложить на руководство [COLOR=rgb(184, 49, 47)][B]{organization}[/B][/COLOR] штраф в размере [COLOR=rgb(184, 49, 47)][B]{fine}[/B][/COLOR] согласно статье [COLOR=rgb(184, 49, 47)][B]{article}[/B][/COLOR] Положение о медицинских проверках государственных организаций;",
            "Обязать руководство государственной организации [COLOR=rgb(184, 49, 47)][B]{organization}[/B][/COLOR] исправить нарушения санитарных норм в течение 24 часов с момента публикации настоящего постановления;",
            "Обязать руководство государственной организации [COLOR=rgb(184, 49, 47)][B]{organization}[/B][/COLOR] оплатить штраф в течение 24 часов с момента публикации настоящего постановления;\n*Примечание: Штраф может быть оплачен Руководству Управления Здравоохранения, Губернатору, Вице-Губернатору.",
            "Настоящее постановление вступает в силу с момента его публикации."
        ],
        "footer": """[RIGHT][FONT=book antiqua][COLOR=rgb(184, 49, 47)][SIZE=5][B]{sign_position}[/B][/SIZE][/COLOR][SIZE=5] штата Сан-Андреас[/SIZE]
[COLOR=rgb(184, 49, 47)][SIZE=5][B]{sign_name}[/B][/SIZE][/COLOR]
[COLOR=rgb(184, 49, 47)][SIZE=5][B]{signature}[/B][/SIZE][/COLOR]

[SIZE=5]г. Лос-Сантос, штат Сан-Андреас[/SIZE]
[COLOR=rgb(184, 49, 47)][SIZE=5][B]{sign_date}[/B][/SIZE][/COLOR][SIZE=5] года[/SIZE][/FONT][/RIGHT]""",
        "fields": {
            "position": "Начальник Управления Здравоохранения",
            "full_name": "Lon LaVibe",
            "organization": "Los Santos Sheriff Department",
            "weekday": "понедельник",
            "date": "09.02.2026",
            "time": "19:30",
            "status": "состоявшейся",
            "med_result": "удовлетворительными",
            "san_result": "удовлетворительными",
            "fine": "25 000 $",
            "article": "10.1",
            "sign_position": "Начальник Управления Здравоохранения",
            "sign_name": "Lon LaVibe",
            "signature": "(подпись)",
            "sign_date": "13 февраля 2026"
        }
    },
    "prosecutor": {
        "name": "⚖️ Прокуратура",
        "title": "ПОСТАНОВЛЕНИЕ ПРОКУРАТУРЫ DJP-Nº {number}",
        "header_img": "[IMG size=\"1280x446\"]{header_url}[/IMG]",
        "body": "Руководствуясь своими полномочиями, а также опираясь на действующие законодательные акты, постановляю:",
        "items": [
            "Усмотреть в действиях сотрудника {org_department} [COLOR=rgb(184, 49, 47)][B]{org_name}[/B][/COLOR] [{org_id}] признаки состава преступления, предусмотренного статьями [COLOR=rgb(184, 49, 47)][B]{article}[/B][/COLOR] Уголовного Кодекса штата SA.",
            "Привлечь сотрудника {org_department} [COLOR=rgb(184, 49, 47)][B]{org_name}[/B][/COLOR] [{org_id}] к уголовной ответственности, предусмотренной Уголовным Кодексом штата SA: [COLOR=rgb(184, 49, 47)][B]{punishment}[/B][/COLOR].",
            "Руководству {org_department} расторгнуть трудовой договор с указанным лицом по факту привлечения к уголовной ответственности, заключенному между ними.",
            "После исполнения третьего пункта настоящего постановления направить доказательства на электронную почту прокурора [COLOR=rgb(184, 49, 47)][B]{prosecutor_email}[/B][/COLOR].",
            "Ответственность за исполнение настоящего постановления возложить на руководство {org_department} в лице Директора и его заместителей."
        ],
        "footer": """Комментарий: Для связи с сотрудником прокуратуры используйте почту: [COLOR=rgb(184, 49, 47)][B]{contact_email}[/B][/COLOR]

Обращаю внимание на то, что игнорирование данного постановления, а как следствие его неисполнение, может повлечь за собой наказание в рамках Уголовного Кодекса Штата San Andreas и иных нормативно-правовых актов. Постановление вступает в силу с момента публикации и может быть обжаловано в установленном законом порядке.

Срок на исполнение настоящего постановления установить равным 24 часам с момента публикации.

[RIGHT]{sign_date} года
г. Лос-Сантос, Штат Сан-Андреас
{sign_position}
{sign_name}
{signature}[/RIGHT]""",
        "fields": {
            "org_department": "сотрудника FIB",
            "org_name": "Macan Satoru",
            "org_id": "175083",
            "article": "12.7.1",
            "punishment": "1 год лишения свободы в Федеральной Тюрьме Болингброук",
            "prosecutor_email": "sasha_bezgin@ls.gov",
            "contact_email": "sasha_bezgin@ls.gov",
            "sign_position": "Младший прокурор",
            "sign_name": "Alexs Fox",
            "signature": "A.Fox",
            "sign_date": "13 февраля 2026"
        }
    },
    "gp_office": {
        "name": "👑 Офис Генерального прокурора",
        "title": "Постановление офиса Генерального прокурора штата ОАГ-№{number}:",
        "header_img": "[IMG size=\"1280x446\"]{header_url}[/IMG]",
        "body": "Руководствуясь своими полномочиями, а также опираясь на действующие законодательные акты, постановляю:",
        "items": [
            "На основании проведенного расследования аннулировать запись о судимости гражданина [COLOR=rgb(184, 49, 47)][B]{full_name}[/B][/COLOR] [{id}] полученную [COLOR=rgb(184, 49, 47)][B]{crime_date}[/B][/COLOR] в [COLOR=rgb(184, 49, 47)][B]{crime_time}[/B][/COLOR].",
            "Обязать Главу Коллегии Адвокатов и его заместителей восстановить лицензию частного адвоката без взимания государственной пошлины и проведения экзамена, в случае обращения к ним со стороны гражданина [COLOR=rgb(184, 49, 47)][B]{full_name}[/B][/COLOR] [{id}].\nПримечание: В случае наличия активных судимостей Глава Коллегии Адвокатов и его заместители могут отказаться в восстановлении лицензии и уведомить об этом Генерального Прокурора."
        ],
        "footer": """**Комментарий:** Для связи с прокурором используйте почту: [COLOR=rgb(184, 49, 47)][B]{contact_email}[/B][/COLOR]

*Обращаю внимание на то, что игнорирование данного постановления, а как следствие его неисполнение, может понести за собой наказание в рамках Уголовного Кодекса Штата San Andreas и иных нормативно-правовых актов. Постановление вступает в силу с момента публикации и может быть обжаловано в установленном законом порядке.*

[RIGHT]{sign_date} года
г. Лос-Сантос, Штат Сан-Андреас
{sign_position}
{sign_name}
{signature}[/RIGHT]""",
        "fields": {
            "full_name": "Madkid BossPsewdyan",
            "id": "182753",
            "crime_date": "07.02.2026",
            "crime_time": "19:08",
            "contact_email": "depressed_dead",
            "sign_position": "Генеральный Прокурор",
            "sign_name": "Rimuru Arthas",
            "signature": "R.Arthas",
            "sign_date": "13 февраля 2026"
        }
    },
    "governor": {
        "name": "🏛️ Губернатор / Вице-губернатор",
        "title": "ПОСТАНОВЛЕНИЕ ГУБЕРНАТОРА ШТАТА SAN ANDREAS № {number}",
        "header_img": "[IMG size=\"1280x446\"]{header_url}[/IMG]",
        "body": "Я, {position} штата Сан-Андреас, {full_name}, действуя в соответствии с Конституцией штата и наделенными полномочиями, постановляю:",
        "items": [
            "{item1}",
            "{item2}",
            "{item3}"
        ],
        "footer": """[RIGHT]{sign_date} года
г. Лос-Сантос, Штат Сан-Андреас
{sign_position}
{sign_name}
{signature}[/RIGHT]""",
        "fields": {
            "position": "Губернатор",
            "full_name": "Имя Фамилия",
            "item1": "Текст первого пункта",
            "item2": "Текст второго пункта",
            "item3": "Текст третьего пункта",
            "sign_position": "Губернатор",
            "sign_name": "Имя Фамилия",
            "signature": "И.Ф.",
            "sign_date": "13 февраля 2026"
        }
    },
    "labor": {
        "name": "🔨 Управление труда",
        "title": "ПОСТАНОВЛЕНИЕ УПРАВЛЕНИЯ ТРУДА № {number}",
        "header_img": "[IMG size=\"1280x446\"]{header_url}[/IMG]",
        "body": "Я, {position} Управления Труда Сан-Андреас, {full_name}, в соответствии с Трудовым Кодексом штата, постановляю:",
        "items": [
            "{item1}",
            "{item2}",
            "{item3}"
        ],
        "footer": """[RIGHT]{sign_date} года
г. Лос-Сантос, Штат Сан-Андреас
{sign_position}
{sign_name}
{signature}[/RIGHT]""",
        "fields": {
            "position": "Начальник Управления Труда",
            "full_name": "Имя Фамилия",
            "item1": "Пункт первый",
            "item2": "Пункт второй",
            "item3": "Пункт третий",
            "sign_position": "Начальник Управления Труда",
            "sign_name": "Имя Фамилия",
            "signature": "И.Ф.",
            "sign_date": "13 февраля 2026"
        }
    }
}

class OrderEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Редактор постановлений — GIH")
        self.setWindowIcon(QIcon(get_resource_path("image.png")))
        
        self.setMinimumSize(1300, 850)
        self.resize(1300, 850)

        self.current_template = "health"
        self.fields_widgets = {}
        self.header_url = ""
        self.items_list = None
        self.templates = DEFAULT_TEMPLATES.copy()  # Копируем стандартные шаблоны

        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QLabel { color: white; font-size: 14px; }
            QFrame { border-radius: 12px; background-color: #1e1e1e; border: 1px solid #333; }
            QGroupBox {
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #333;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4facfe;
            }
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                padding: 8px 15px;
            }
            QPushButton:hover { background-color: #3a92ea; }
            QPushButton:pressed { background-color: #1a72ca; }
            QPushButton:disabled { background-color: #3d3d3d; color: #888; }
            QLineEdit, QSpinBox, QComboBox, QDateEdit, QTextEdit, QListWidget {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
            }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background-color: #2a82da; }
            QTabWidget::pane { border: 1px solid #333; background-color: #1e1e1e; border-radius: 8px; }
            QTabBar::tab { 
                background-color: #2d2d2d; 
                color: white; 
                padding: 12px 30px; 
                margin-right: 2px; 
                font-size: 15px;
                font-weight: bold;
            }
            QTabBar::tab:selected { background-color: #2a82da; }
            QTabBar::tab:hover { background-color: #3d3d3d; }
            QScrollArea { border: none; background-color: transparent; }
            QDialog { background-color: #1e1e1e; color: white; }
            QDialog QLabel { color: white; }
            QDialog QLineEdit { background-color: #2d2d2d; color: white; }
        """)

        self.init_ui()
        self.load_template()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ===== ВЕРХНЯЯ ПАНЕЛЬ С ВЫБОРОМ ШАБЛОНА =====
        top_frame = QFrame()
        top_frame.setFixedHeight(70)
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(15, 10, 15, 10)

        top_layout.addWidget(QLabel("Выберите ведомство:"))

        self.template_combo = QComboBox()
        self.update_template_combo()  # Заполняем комбобокс
        self.template_combo.currentIndexChanged.connect(self.on_template_changed)
        self.template_combo.setMinimumWidth(250)
        top_layout.addWidget(self.template_combo)

        # Кнопка загрузки из Google Sheets
        self.load_sheet_btn = QPushButton("📊 Загрузить из Google Sheets")
        self.load_sheet_btn.clicked.connect(self.manual_load_templates)
        top_layout.addWidget(self.load_sheet_btn)

        top_layout.addStretch()

        self.number_spin = QSpinBox()
        self.number_spin.setRange(1, 9999)
        self.number_spin.setValue(928)
        self.number_spin.setPrefix("№ ")
        self.number_spin.valueChanged.connect(self.generate)
        top_layout.addWidget(QLabel("Номер:"))
        top_layout.addWidget(self.number_spin)

        main_layout.addWidget(top_frame)

        # ===== ПАНЕЛЬ ЗАГРУЗКИ ШАПКИ =====
        header_frame = QFrame()
        header_frame.setFixedHeight(60)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 5, 15, 5)

        header_layout.addWidget(QLabel("Шапка постановления:"))

        self.header_url_edit = QLineEdit()
        self.header_url_edit.setPlaceholderText("Ссылка на изображение или загрузите файл...")
        self.header_url_edit.textChanged.connect(self.update_header_url)
        header_layout.addWidget(self.header_url_edit)

        self.upload_btn = QPushButton("📁 Загрузить")
        self.upload_btn.clicked.connect(self.upload_image)
        header_layout.addWidget(self.upload_btn)

        self.clear_header_btn = QPushButton("❌ Очистить")
        self.clear_header_btn.clicked.connect(self.clear_header)
        header_layout.addWidget(self.clear_header_btn)

        main_layout.addWidget(header_frame)

        # ===== ОСНОВНЫЕ ВКЛАДКИ =====
        self.main_tabs = QTabWidget()
        
        # Вкладка 1: Поля для заполнения
        self.create_fields_tab()
        
        # Вкладка 2: Пункты постановления
        self.create_items_tab()
        
        # Вкладка 3: Просмотр результата
        self.create_preview_tab()
        
        main_layout.addWidget(self.main_tabs)

        # ===== НИЖНЯЯ ПАНЕЛЬ =====
        bottom_frame = QFrame()
        bottom_frame.setFixedHeight(50)
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(15, 5, 15, 5)

        self.info_label = QLabel("⚡ Готов к работе")
        self.info_label.setStyleSheet("color: #888;")
        bottom_layout.addWidget(self.info_label)

        bottom_layout.addStretch()

        self.copy_btn = QPushButton("📋 Копировать BBCode")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setMinimumHeight(35)
        bottom_layout.addWidget(self.copy_btn)

        main_layout.addWidget(bottom_frame)

    def update_template_combo(self):
        """Обновляет комбобокс с шаблонами"""
        self.template_combo.clear()
        for key, tmpl in self.templates.items():
            self.template_combo.addItem(tmpl["name"], key)

    def manual_load_templates(self):
        """Ручная загрузка шаблонов с выбором листа"""
        dialog = GoogleSheetsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            
            if not values['sheet_id']:
                QMessageBox.warning(self, "Ошибка", "Введите ID таблицы")
                return
            
            # Создаем прогресс диалог
            self.progress = QProgressDialog("", "Отмена", 0, 0, self)
            self.progress.setWindowTitle("Загрузка шаблонов")
            self.progress.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress.show()
            
            # Запускаем загрузку
            self.loader = TemplateLoader(values['sheet_id'], values['sheet_name'])
            self.loader.finished.connect(self.on_templates_loaded)
            self.loader.error.connect(self.on_templates_error)
            self.loader.progress.connect(self.on_load_progress)
            self.loader.start()

    def on_load_progress(self, message):
        """Обновление прогресса загрузки"""
        self.progress.setLabelText(message)

    def on_templates_loaded(self, new_templates):
        """Обработчик успешной загрузки шаблонов"""
        self.progress.close()
        
        # Обновляем шаблоны, сохраняя стандартные как резервные
        self.templates.update(new_templates)
        
        # Обновляем комбобокс
        self.update_template_combo()
        
        # Показываем сообщение
        count = len(new_templates)
        QMessageBox.information(
            self, 
            "Успех", 
            f"Загружено {count} новых шаблонов из Google Sheets!\n"
            f"Всего доступно шаблонов: {len(self.templates)}"
        )
        
        # Переключаемся на первый новый шаблон (если есть)
        if new_templates:
            first_key = list(new_templates.keys())[0]
            index = self.template_combo.findData(first_key)
            if index >= 0:
                self.template_combo.setCurrentIndex(index)

    def on_templates_error(self, error_msg):
        """Обработчик ошибки загрузки"""
        self.progress.close()
        QMessageBox.warning(
            self, 
            "Ошибка", 
            f"{error_msg}\n\nИспользуются стандартные шаблоны."
        )

    def create_fields_tab(self):
        """Вкладка с полями для заполнения"""
        fields_tab = QWidget()
        fields_layout = QVBoxLayout(fields_tab)
        fields_layout.setContentsMargins(15, 15, 15, 15)

        # Область с прокруткой для полей
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        fields_container = QWidget()
        self.fields_layout = QVBoxLayout(fields_container)
        self.fields_layout.setSpacing(10)
        self.fields_layout.setContentsMargins(5, 5, 5, 5)

        scroll.setWidget(fields_container)
        fields_layout.addWidget(scroll)

        self.main_tabs.addTab(fields_tab, "📝 Поля для заполнения")

    def create_items_tab(self):
        """Вкладка с пунктами постановления"""
        items_tab = QWidget()
        items_layout = QVBoxLayout(items_tab)
        items_layout.setContentsMargins(15, 15, 15, 15)
        items_layout.setSpacing(15)

        # Кнопки управления пунктами
        btn_layout = QHBoxLayout()
        
        self.add_item_btn = QPushButton("➕ Добавить пункт")
        self.add_item_btn.clicked.connect(self.add_list_item)
        btn_layout.addWidget(self.add_item_btn)

        self.remove_item_btn = QPushButton("➖ Удалить пункт")
        self.remove_item_btn.clicked.connect(self.remove_list_item)
        btn_layout.addWidget(self.remove_item_btn)

        items_layout.addLayout(btn_layout)

        # Список пунктов
        self.items_list = QListWidget()
        self.items_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        # Исправлено: подключаем правильный сигнал для изменения элементов
        self.items_list.itemChanged.connect(self.on_item_changed)
        items_layout.addWidget(self.items_list)

        self.main_tabs.addTab(items_tab, "📋 Пункты постановления")

    def create_preview_tab(self):
        """Вкладка с предпросмотром"""
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        preview_layout.setContentsMargins(15, 15, 15, 15)

        # Вкладки для разных форматов просмотра
        self.preview_tabs = QTabWidget()

        # BBCode
        bbcode_tab = QWidget()
        bbcode_layout = QVBoxLayout(bbcode_tab)
        self.bbcode_text = QTextEdit()
        self.bbcode_text.setReadOnly(True)
        self.bbcode_text.setFontFamily("Courier New")
        self.bbcode_text.setFontPointSize(12)
        bbcode_layout.addWidget(self.bbcode_text)
        self.preview_tabs.addTab(bbcode_tab, "📟 BBCode")

        # Обычный текст
        text_tab = QWidget()
        text_layout = QVBoxLayout(text_tab)
        self.plain_text = QTextEdit()
        self.plain_text.setReadOnly(True)
        self.plain_text.setFontFamily("Arial")
        self.plain_text.setFontPointSize(12)
        text_layout.addWidget(self.plain_text)
        self.preview_tabs.addTab(text_tab, "📄 Обычный текст")

        preview_layout.addWidget(self.preview_tabs)

        # Кнопка обновления
        update_btn = QPushButton("🔄 Обновить предпросмотр")
        update_btn.clicked.connect(self.generate)
        update_btn.setMinimumHeight(40)
        preview_layout.addWidget(update_btn)

        self.main_tabs.addTab(preview_tab, "👁️ Просмотр")

    def update_header_url(self, text):
        self.header_url = text
        self.generate()

    def upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Выберите изображение для шапки", 
            "", 
            "Изображения (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        
        if not file_path:
            return

        self.info_label.setText("⏫ Загрузка изображения...")
        
        url = upload_to_imgbb(file_path)
        
        if url:
            self.header_url_edit.setText(url)
            self.info_label.setText("✅ Изображение загружено!")
            QMessageBox.information(self, "Успех", "Изображение успешно загружено и ссылка добавлена.")
        else:
            self.info_label.setText("❌ Ошибка загрузки")
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить изображение. Попробуйте вставить ссылку вручную.")

    def clear_header(self):
        self.header_url_edit.clear()
        self.header_url = ""

    def on_template_changed(self):
        self.current_template = self.template_combo.currentData()
        self.load_template()

    def load_template(self):
        tmpl = self.templates[self.current_template]

        # Очищаем старые поля
        self.clear_layout(self.fields_layout)
        self.fields_widgets.clear()
        
        # Очищаем список пунктов, если он существует
        if self.items_list is not None:
            self.items_list.clear()

        # Создаем поля для текущего шаблона
        for key, default_value in tmpl["fields"].items():
            field_frame = QFrame()
            field_frame.setStyleSheet("QFrame { background-color: #2a2a2a; border-radius: 6px; padding: 5px; }")
            field_layout = QHBoxLayout(field_frame)
            field_layout.setContentsMargins(5, 2, 5, 2)

            label = QLabel(f"{key}:")
            label.setFixedWidth(120)
            field_layout.addWidget(label)

            edit = QLineEdit(default_value)
            edit.textChanged.connect(self.generate)
            field_layout.addWidget(edit)

            self.fields_layout.addWidget(field_frame)
            self.fields_widgets[key] = edit

        # Загружаем пункты для текущего шаблона, если список существует
        if self.items_list is not None:
            for item_text in tmpl["items"]:
                item = QListWidgetItem(item_text)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.items_list.addItem(item)

        self.fields_layout.addStretch()
        self.generate()

    def add_list_item(self):
        new_item, ok = QInputDialog.getText(self, "Новый пункт", "Введите текст пункта:")
        if ok and new_item and self.items_list is not None:
            item = QListWidgetItem(new_item)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.items_list.addItem(item)
            self.generate()

    def remove_list_item(self):
        if self.items_list is not None:
            current_row = self.items_list.currentRow()
            if current_row >= 0:
                self.items_list.takeItem(current_row)
                self.generate()

    def on_item_changed(self, item):
        """Обработчик изменения элемента списка"""
        self.generate()

    def strip_bbcode(self, text):
        """Удаляет BBCode теги из текста"""
        text = re.sub(r'\[\*\]', '• ', text)
        text = re.sub(r'\[/?[A-Za-z0-9_=\"]*\]', '', text)
        text = re.sub(r'\[COLOR=[^\]]*\]|\[/COLOR\]', '', text)
        text = re.sub(r'\[SIZE=[^\]]*\]|\[/SIZE\]', '', text)
        text = re.sub(r'\[FONT=[^\]]*\]|\[/FONT\]', '', text)
        text = re.sub(r'\[B\]|\[/B\]', '', text)
        text = re.sub(r'\[I\]|\[/I\]', '', text)
        text = re.sub(r'\[U\]|\[/U\]', '', text)
        text = re.sub(r'\[JUSTIFY\]|\[/JUSTIFY\]', '', text)
        text = re.sub(r'\[CENTER\]|\[/CENTER\]', '', text)
        text = re.sub(r'\[RIGHT\]|\[/RIGHT\]', '', text)
        text = re.sub(r'\[LIST=1\]|\[/LIST\]', '', text)
        text = re.sub(r'\[IMG[^\]]*\]|\[/IMG\]', '', text)
        return text

    def generate(self):
        try:
            tmpl = self.templates[self.current_template]
            number = self.number_spin.value()

            values = {key: w.text() for key, w in self.fields_widgets.items()}
            values["number"] = number
            values["header_url"] = self.header_url if self.header_url else ""

            items_text = []
            # Проверяем, существует ли items_list
            if self.items_list is not None:
                for i in range(self.items_list.count()):
                    item = self.items_list.item(i)
                    if item is not None:
                        item_text = item.text()
                        try:
                            formatted_item = item_text.format(**values)
                        except KeyError as e:
                            # Если ключ не найден, оставляем как есть
                            formatted_item = item_text
                        except Exception:
                            formatted_item = item_text
                        items_text.append(f"[*][JUSTIFY][SIZE=5][FONT=book antiqua]{formatted_item}[/FONT][/SIZE][/JUSTIFY]")

            full_text = []

            # Шапка
            if tmpl["header_img"] and self.header_url:
                full_text.append(tmpl["header_img"].format(**values))
                full_text.append("[JUSTIFY][/JUSTIFY]")

            # Заголовок
            title = tmpl["title"].format(**values)
            full_text.append(f"[CENTER][SIZE=5][FONT=book antiqua][B]{title}[/B][/FONT][/SIZE][/CENTER]")

            # Тело
            body = tmpl["body"].format(**values)
            full_text.append(f"[JUSTIFY][SIZE=5][FONT=book antiqua][B]{body}[/B][/FONT][/SIZE][/JUSTIFY]")

            # Список пунктов
            if items_text:
                full_text.append("[LIST=1]")
                full_text.extend(items_text)
                full_text.append("[/LIST]")

            # Подвал
            footer = tmpl["footer"].format(**values)
            full_text.append(footer)

            bbcode_result = "\n".join(full_text)
            self.bbcode_text.setPlainText(bbcode_result)
            
            plain_result = self.strip_bbcode(bbcode_result)
            self.plain_text.setPlainText(plain_result)
            
            self.info_label.setText("✅ Сгенерировано успешно")

        except Exception as e:
            self.info_label.setText(f"❌ Ошибка: {str(e)}")
            # Выводим ошибку в консоль для отладки
            import traceback
            traceback.print_exc()

    def copy_to_clipboard(self):
        text = self.bbcode_text.toPlainText()
        if not text:
            QMessageBox.information(self, "Информация", "Нет текста для копирования.")
            return
        QApplication.clipboard().setText(text)
        self.info_label.setText("📋 Скопировано в буфер обмена")
        QMessageBox.information(self, "Успех", "Текст скопирован в буфер обмена.")

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                if item.layout():
                    self.clear_layout(item.layout())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = OrderEditorWindow()
    w.show()
    sys.exit(app.exec())