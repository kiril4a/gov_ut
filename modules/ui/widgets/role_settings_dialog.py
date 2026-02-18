from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QDialogButtonBox, QMenu, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QStringListModel
from PyQt6.QtWidgets import QCompleter

from modules.core.firebase_service import get_usernames, get_user, list_users, can_assign_role, save_user_roles, resolve_user_permissions, DEPT_DEFAULT_PERMS, can_manage_user, can_assign_departments, create_user, delete_user


class SelectionPopup(QDialog):
    """Popup-style centered selection menu with rounded dark background and gray border."""
    def __init__(self, parent=None, title="", items=None, preselected=None):
        super().__init__(parent, Qt.WindowType.Popup)
        # Frameless popup without translucent background to avoid showing underlying UI.
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        # Unified visual style: two gray tones (#2b2b2b dark, #353535 mid), rounded elements, bold small text
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: #eaeaea; border: 1px solid #404040; border-radius: 12px; }
            /* Titles / labels and inputs share same height and boxed appearance */
            QLabel { background-color: #353535; color: #eaeaea; padding: 6px; border: 1px solid #404040; border-radius: 8px; font-weight: bold; min-height: 32px; max-height: 32px; }
            QLineEdit { background-color: #353535; color: #ffffff; border: 1px solid #404040; padding: 6px; border-radius: 8px; font-weight: bold; min-height: 32px; max-height: 32px; }
            QListWidget { background: transparent; color: #eaeaea; border: none; }
            QListWidget::item { padding: 8px 10px; margin: 6px; border-radius: 8px; background: #353535; border: 1px solid #404040; font-weight: bold; }
            /* Buttons slightly smaller than inputs */
            QPushButton { background: #2a82da; color: white; border: none; border-radius: 7px; padding: 6px 10px; font-weight: bold; min-height: 28px; max-height: 28px; }
            QPushButton[secondary='true'] { background: #444444; border-radius: 7px; }
            QDialogButtonBox { background: transparent; border: none; }
            /* Menus rounded with border */
            QMenu { background-color: #2b2b2b; color: #eaeaea; border: 1px solid #404040; border-radius: 10px; padding: 6px; font-weight: bold; }
        """)
        self.resize(360, 300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        # title label should match input height
        title_label = QLabel(title)
        title_label.setFixedHeight(32)
        layout.addWidget(title_label)
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        for it in (items or []):
            li = QListWidgetItem(it)
            li.setFlags(li.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            li.setCheckState(Qt.CheckState.Checked if (preselected and it in preselected) else Qt.CheckState.Unchecked)
            self.list.addItem(li)
        layout.addWidget(self.list)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected(self):
        return [self.list.item(i).text() for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.CheckState.Checked]


class RoleSettingsDialog(QDialog):
    def __init__(self, parent=None, current_user=None):
        self.current_user = current_user if current_user is not None else getattr(parent, 'user_data', None)
        super().__init__(parent)
        # Use a frameless Dialog (not Qt.Popup) so exec() keeps it open reliably.
        # Use solid background (no translucent attribute) so dialog is opaque.
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle("Настройка ролей пользователя")
        self.setModal(True)
        self.resize(520, 360)

        # Dark theme: rounded rectangles, two grays, blue buttons, labels boxed and bold text
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: #eaeaea; border-radius: 10px; }
            /* Labels are boxed */
            QLabel { background-color: #353535; color: #eaeaea; padding: 6px; border: 1px solid #404040; border-radius: 8px; font-weight: bold; min-height: 32px; max-height: 32px; }
            /* Inputs */
            QLineEdit { background-color: #353535; color: #ffffff; border: 1px solid #404040; padding: 6px; border-radius: 8px; font-weight: bold; min-height: 32px; max-height: 32px; }
            /* Buttons: blue rectangular with rounded corners */
            QPushButton { background-color: #2a82da; color: white; border: none; border-radius: 7px; padding: 6px 10px; font-weight: bold; min-height: 28px; max-height: 28px; }
            QPushButton[secondary='true'] { background-color: #444444; border-radius: 7px; }
            /* Lists and popups */
            QListWidget, QMenu { background-color: #2b2b2b; color: #eaeaea; border: 1px solid #404040; border-radius: 8px; font-weight: bold; }
            QListWidget::item { background: #353535; border: 1px solid #404040; border-radius: 6px; margin: 6px; padding: 6px; }
            /* Dialog buttons area */
            QDialogButtonBox { background: transparent; border: none; }
            /* Small text bold */
            QWidget { font-weight: bold; }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)

        # Top row: mode menu (left) + username label + input
        hl = QHBoxLayout()
        hl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # mode/menu button (shows dropdown to switch between modes)
        self.mode_button = QPushButton("▾")
        self.mode_button.setFixedSize(28, 28)
        self.mode_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        hl.addWidget(self.mode_button)
        self.username_label = QLabel("Логин пользователя:")
        # match label height to input
        self.username_label.setFixedHeight(32)
        hl.addWidget(self.username_label)
        self.input_username = QLineEdit()
        self.input_username.setFixedHeight(32)
        self.input_username.setMaximumWidth(320)
        hl.addWidget(self.input_username)
        hl.addStretch()
        self.layout.addLayout(hl)

        # Build mode menu; restrict add/delete options to Admin/Governor
        self.mode_menu = QMenu(self)
        self.action_roles = self.mode_menu.addAction("Настройка ролей")
        self.action_add = self.mode_menu.addAction("Добавить пользователя")
        self.action_delete = self.mode_menu.addAction("Удалить пользователя")
        # Show add/delete only for Admin/Governor (and Admin via admin.full)
        try:
            res = resolve_user_permissions(self.current_user) if self.current_user else {}
            roles = set(res.get('roles', []))
            is_global = bool(roles & {'Admin', 'Governor'}) or ('admin.full' in res.get('permissions', set()))
        except Exception:
            is_global = False
        self.action_add.setVisible(is_global)
        self.action_delete.setVisible(is_global)
        self.mode_button.setMenu(self.mode_menu)
        # default mode
        self.mode = 'roles'
        self.action_roles.triggered.connect(lambda: self.set_mode('roles'))
        self.action_add.triggered.connect(lambda: self.set_mode('add'))
        self.action_delete.triggered.connect(lambda: self.set_mode('delete'))

        # Add / Delete panels (hidden by default)
        self.add_panel = QHBoxLayout()
        self.add_login = QLineEdit()
        self.add_login.setPlaceholderText('Логин')
        self.add_login.setFixedHeight(32)
        self.add_password = QLineEdit()
        self.add_password.setPlaceholderText('Пароль')
        self.add_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_password.setFixedHeight(32)
        self.add_create_btn = QPushButton('Создать пользователя')
        self.add_create_btn.setFixedHeight(28)
        self.add_create_btn.clicked.connect(self._on_create_user)
        # place into a widget so we can show/hide easily
        self._add_widget = QWidget()
        aw = QHBoxLayout(self._add_widget)
        aw.setContentsMargins(0,0,0,0)
        aw.addWidget(self.add_login)
        aw.addWidget(self.add_password)
        aw.addWidget(self.add_create_btn)
        self._add_widget.setVisible(False)
        self.layout.addWidget(self._add_widget)

        self._del_widget = QWidget()
        dw = QHBoxLayout(self._del_widget)
        dw.setContentsMargins(0,0,0,0)
        self.del_login = QLineEdit()
        self.del_login.setPlaceholderText('Логин для удаления')
        self.del_login.setFixedHeight(32)
        self.del_delete_btn = QPushButton('Удалить пользователя')
        self.del_delete_btn.setFixedHeight(28)
        self.del_delete_btn.clicked.connect(self._on_delete_user)
        dw.addWidget(self.del_login)
        dw.addWidget(self.del_delete_btn)
        self._del_widget.setVisible(False)
        self.layout.addWidget(self._del_widget)

        # Use standard QCompleter for suggestions (lighter and avoids custom popup lag)
        self.completer_model = QStringListModel(self)
        self.completer = QCompleter(self.completer_model, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        # prefer contains-based matching if available
        try:
            self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        except Exception:
            try:
                self.completer.setFilterMode(Qt.MatchContains)
            except Exception:
                pass
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.input_username.setCompleter(self.completer)
        self.input_username.textChanged.connect(self.on_username_typed)
        # When user selects suggestion, handle selection
        try:
            self.completer.activated.connect(self.on_username_selected)
        except Exception:
            pass

        # User info display (shows roles and permissions after selection)
        self.info_label = QLabel("")
        self.info_label.setStyleSheet('color: #dcdcdc; padding: 6px;')
        self.info_label.setVisible(False)
        self.layout.addWidget(self.info_label)

        # Buttons row, hidden until valid user selected
        btn_row = QHBoxLayout()
        self.btn_roles = QPushButton("Выбрать роли")
        self.btn_roles.setProperty('secondary', True)
        self.btn_roles.setVisible(False)
        self.btn_roles.clicked.connect(self.open_roles_popup)
        btn_row.addWidget(self.btn_roles)

        self.btn_depts = QPushButton("Выбрать отделы")
        self.btn_depts.setProperty('secondary', True)
        self.btn_depts.setVisible(False)
        self.btn_depts.clicked.connect(self.open_depts_popup)
        btn_row.addWidget(self.btn_depts)

        # Permissions button (local-only picker)
        self.btn_perms = QPushButton("Выбрать разрешения")
        self.btn_perms.setProperty('secondary', True)
        self.btn_perms.setVisible(False)
        self.btn_perms.clicked.connect(self.open_perms_popup)
        btn_row.addWidget(self.btn_perms)

        self.layout.addLayout(btn_row)

        # Save/Cancel
        footer = QHBoxLayout()
        footer.addStretch()
        self.btn_save = QPushButton("Сохранить в БД")
        self.btn_cancel = QPushButton("Отмена")
        footer.addWidget(self.btn_save)
        footer.addWidget(self.btn_cancel)
        self.layout.addLayout(footer)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.on_save)

        # role definitions
        self.role_hierarchy = [
            'Администратор',
            'Губернатор',
            'Министр',
            'Начальник',
            'Заместитель',
            'Подчиненный',
            'Посетитель'
        ]
        self.role_to_depts = {
            'Администратор': ['УТ', 'ЭУ', 'УК'],
            'Губернатор': ['УТ', 'ЭУ', 'УК'],
            'Министр': ['ЭУ', 'УК','УК'],
            'Начальник': ['УТ', 'ЭУ', 'УК'],
            'Заместитель': ['УТ', 'ЭУ', 'УК'],
            'Подчиненный': ['УТ', 'ЭУ', 'УК'],
        }
        self.label_to_key = {
            'Администратор': 'Admin',
            'Губернатор': 'Governor',
            'Министр': 'Minister',
            'Начальник': 'Head',
            'Заместитель': 'Deputy',
            'Подчиненный': 'Employee',
            'Посетитель': 'Visitor',
        }

        # internal state
        self.loaded_user = None
        self.selected_roles = []
        self.selected_depts = []
        self.selected_perms = []
        # cache for user docs to avoid repeated DB calls while typing
        self._all_user_docs = None

    def on_username_typed(self, text: str):
        txt = text.strip()
        if not txt:
            # if empty, show all manageable users (from cache)
            if self._all_user_docs is None:
                try:
                    self._all_user_docs = list_users() or []
                except Exception:
                    self._all_user_docs = []
            suggestions = []
            for d in self._all_user_docs:
                try:
                    name = d.get('username') or d.get('login') or ''
                    if not name:
                        continue
                    try:
                        if not can_manage_user(self.current_user, d):
                            continue
                    except Exception:
                        continue
                    suggestions.append(name)
                except Exception:
                    continue
            self.completer_model.setStringList(sorted(suggestions))
            self.loaded_user = None
            self.btn_roles.setVisible(False)
            self.btn_depts.setVisible(False)
            self.btn_perms.setVisible(False)
            self.update_info_label()
            return

        # Lazy-load all user documents once to avoid repeated DB calls
        if self._all_user_docs is None:
            try:
                self._all_user_docs = list_users() or []

            except Exception:
                self._all_user_docs = []

        # Build suggestions from cached docs and filter by manageability
        suggestions = []
        ltxt = txt.lower()
        for d in self._all_user_docs:
            try:
                name = d.get('username') or d.get('login') or ''
                if not name:
                    continue
                if ltxt not in name.lower():
                    continue
                # check once if current_user can manage this doc (pass doc to avoid extra DB fetch)
                try:
                    if not can_manage_user(self.current_user, d):
                        continue
                except Exception:
                    continue
                suggestions.append(name)
                if len(suggestions) >= 200:
                    break
            except Exception:
                continue

        # populate completer model (QCompleter will display popup)
        self.completer_model.setStringList(sorted(suggestions))

    def on_username_selected(self, name: str):
        # populate input and load user
        self.input_username.setText(name)
        # try to find doc in cache to avoid extra DB call
        doc = None
        if self._all_user_docs is not None:
            for d in self._all_user_docs:
                if (d.get('username') or d.get('login')) == name:
                    doc = d
                    break

        # ensure current_user can manage selected (use doc when available)
        if not can_manage_user(self.current_user, doc or name):
            QMessageBox.warning(self, "Доступ запрещен", "Вы не можете редактировать этого пользователя.")
            return
        self.load_user(name)

    def load_user(self, username: str):
        try:
            u = get_user(username)
        except Exception:
            u = None
        self.loaded_user = u
        # show role/dept buttons only if user exists
        if u:
            # disable controls if current_user cannot manage this user
            manageable = can_manage_user(self.current_user, u)
            self.btn_roles.setVisible(manageable)
            self.btn_depts.setVisible(manageable)
            self.btn_perms.setVisible(manageable)
            if not manageable:
                QMessageBox.information(self, "Ограничение", "Вы видите этого пользователя, но не можете изменять его роли/отделы.")

            # Note: do not force-show buttons here; keep them hidden when not manageable.

            # read current stored values from DB but convert role keys properly
            db_roles = set(u.get('roles') or [])
            valid_keys = set(self.label_to_key.values())
            # keep only known role keys
            self.selected_roles = [r for r in db_roles if r in valid_keys]
            # departments and permissions
            self.selected_depts = list(u.get('departments') or [])
            self.selected_perms = list(u.get('permissions') or [])

            # update displays
            self.update_info_label()
        else:
            self.btn_roles.setVisible(False)
            self.btn_depts.setVisible(False)
            self.btn_perms.setVisible(False)
            self.info_label.setVisible(False)
            self.selected_roles = []
            self.selected_depts = []
            self.selected_perms = []

    def open_roles_popup(self):
        # Build list of roles that the current_user is allowed to assign. Do not show roles that
        # the assigner has no right to grant.
        allowed = []
        for lbl, key in self.label_to_key.items():
            try:
                if can_assign_role(self.current_user, key):
                    allowed.append(lbl)
            except Exception:
                # on error, be conservative and skip the role
                continue

        if not allowed:
            QMessageBox.information(self, "Нет доступных ролей", "У вас нет прав назначать какие-либо роли.")
            return

        # preselect only those selected roles that are actually presented in the allowed list
        pre = [lbl for lbl, key in self.label_to_key.items() if key in self.selected_roles and lbl in allowed]
        popup = SelectionPopup(self, title="Выберите роли", items=allowed, preselected=pre)
        # center popup in this dialog
        center = self.mapToGlobal(self.rect().center())
        popup.move(int(center.x() - popup.width()/2), int(center.y() - popup.height()/2))
        if popup.exec() == QDialog.DialogCode.Accepted:
            selected = popup.selected()
            # convert selected labels to internal keys
            self.selected_roles = [self.label_to_key.get(s) for s in selected if self.label_to_key.get(s)]
            # after roles selected, update departments available but keep previously selected depts that are still allowed
            allowed = set()
            for lbl, key in self.label_to_key.items():
                if key in self.selected_roles:
                    allowed.update(self.role_to_depts.get(lbl, []))
            if not allowed:
                allowed = set(['УТ', 'ЭУ', 'УК'])
            # keep only previously chosen departments that are still allowed
            self.selected_depts = [d for d in self.selected_depts if d in allowed]
            self.update_info_label()

    def open_depts_popup(self):
        # departments available derived from selected roles
        allowed = set()
        for lbl, key in self.label_to_key.items():
            if key in self.selected_roles:
                allowed.update(self.role_to_depts.get(lbl, []))
        # if none selected, allow all
        if not allowed:
            allowed = set(['УТ', 'ЭУ', 'УК'])

        # Enforce assigner department scope: Admin/Governor/Minister may assign any department.
        # Other users (e.g., Head) may only assign departments that they themselves belong to.
        try:
            assigner_res = resolve_user_permissions(self.current_user) if self.current_user else {}
        except Exception:
            assigner_res = {}
        assigner_roles = set(assigner_res.get('roles', []))
        # roles allowed to assign any department
        global_assign_roles = {'Admin', 'Governor', 'Minister'}
        if not (assigner_roles & global_assign_roles):
            # restrict allowed departments to assigner's departments
            assigner_depts = set(assigner_res.get('departments', []))
            if assigner_depts:
                allowed = allowed & assigner_depts
            else:
                # If assigner has no departments, they should not be able to assign any department
                allowed = set()

        if not allowed:
            QMessageBox.information(self, "Нет доступных отделов", "У вас нет прав назначать доступные отделы для этого пользователя.")
            return
        pre = list(self.selected_depts)
        popup = SelectionPopup(self, title="Выберите отделы", items=list(allowed), preselected=pre)
        # center popup in this dialog
        center = self.mapToGlobal(self.rect().center())
        popup.move(int(center.x() - popup.width()/2), int(center.y() - popup.height()/2))
        if popup.exec() == QDialog.DialogCode.Accepted:
            self.selected_depts = popup.selected()
            self.update_info_label()

    def open_perms_popup(self):
        # derive available permissions from the synthetic user composed from local selections
        synth = {
            'roles': self.selected_roles,
            'departments': self.selected_depts,
            'permissions': self.selected_perms or []
        }
        try:
            resolved = resolve_user_permissions(synth)
            # Build permission list from department defaults and resolved explicit perms
            perms_set = set()
            # include department defaults for selected departments
            for d in self.selected_depts:
                perms_set.update(DEPT_DEFAULT_PERMS.get(d, []))
            # include any resolved explicit permissions (but filter legacy ones)
            perms_set.update([p for p in resolved.get('permissions', []) if p not in ('ut.sync', 'ut.access')])
            perms_list = sorted(perms_set)
        except Exception:
            perms_list = []
        popup = SelectionPopup(self, title="Выберите разрешения", items=perms_list, preselected=self.selected_perms)
        center = self.mapToGlobal(self.rect().center())
        popup.move(int(center.x() - popup.width()/2), int(center.y() - popup.height()/2))
        if popup.exec() == QDialog.DialogCode.Accepted:
            # ensure legacy permissions are not selected
            self.selected_perms = [p for p in popup.selected() if p not in ('ut.sync', 'ut.access')]
            self.update_info_label()

    def update_info_label(self):
        # Build and show info from local selections (prefer local selected_perms if present)
        username = self.input_username.text().strip() or '-'
        # reverse mapping key -> label
        key_to_label = {v: k for k, v in self.label_to_key.items()}
        role_labels = [key_to_label.get(k, k) for k in self.selected_roles]
        perms = self.selected_perms if self.selected_perms else (self.loaded_user.get('permissions') if self.loaded_user else [])
        info = f"Пользователь: {username}\nРоли: {', '.join(role_labels) if role_labels else '-'}\nОтделы: {', '.join(self.selected_depts) if self.selected_depts else '-'}\nРазрешения: {', '.join(perms) if perms else '-'}"
        self.info_label.setText(info)
        # Only show info label in 'roles' mode
        try:
            is_roles = (getattr(self, 'mode', 'roles') == 'roles')
        except Exception:
            is_roles = True
        self.info_label.setVisible(is_roles)

    def on_save(self):
        username = self.input_username.text().strip()
        if not username:
            QMessageBox.warning(self, "Ошибка", "Введите логин пользователя.")
            return

        # Authorization: if current_user exists and is not admin, ensure they can assign selected roles
        if self.current_user:
            for rk in self.selected_roles:
                if not can_assign_role(self.current_user, rk):
                    QMessageBox.warning(self, "Доступ запрещен", f"Вы не можете назначать роль {rk}.")
                    return

            # Ensure assigner can assign selected departments
            if self.selected_depts:
                try:
                    if not can_assign_departments(self.current_user, self.selected_depts):
                        QMessageBox.warning(self, "Доступ запрещен", "Вы не можете назначать выбранные отделы.")
                        return
                except Exception:
                    QMessageBox.warning(self, "Ошибка проверки", "Не удалось проверить права на назначение отделов.")
                    return

        try:
            # persist selected roles/departments/permissions into DB
            save_user_roles(username, self.selected_roles, self.selected_depts, permissions=self.selected_perms)
            QMessageBox.information(self, "Готово", "Настройки сохранены в базе.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка при сохранении", str(e))

    def set_mode(self, mode: str):
        # only Admin/Governor (or admin.full) can access add/delete modes
        try:
            res = resolve_user_permissions(self.current_user) if self.current_user else {}
            roles = set(res.get('roles', []))
            is_global = bool(roles & {'Admin', 'Governor'}) or ('admin.full' in res.get('permissions', set()))
        except Exception:
            is_global = False
        if mode in ('add', 'delete') and not is_global:
            QMessageBox.warning(self, 'Доступ запрещен', 'У вас нет прав на добавление/удаление пользователей.')
            return
        self.mode = mode
        # update visible panels
        self._add_widget.setVisible(mode == 'add')
        self._del_widget.setVisible(mode == 'delete')
        # hide username input & label in add/delete modes
        is_roles = (mode == 'roles')
        self.username_label.setVisible(is_roles)
        self.input_username.setVisible(is_roles)
        # hide completer suggestions when input hidden
        if not is_roles:
            try:
                self.completer_model.setStringList([])
            except Exception:
                pass
        # hide role/dept/perm controls when not in roles mode
        self.btn_roles.setVisible(is_roles and (self.loaded_user is not None and can_manage_user(self.current_user, self.loaded_user)))
        self.btn_depts.setVisible(is_roles and (self.loaded_user is not None and can_manage_user(self.current_user, self.loaded_user)))
        self.btn_perms.setVisible(is_roles and (self.loaded_user is not None and can_manage_user(self.current_user, self.loaded_user)))
        self.btn_save.setVisible(is_roles)
        # hide info label when not in roles mode
        self.info_label.setVisible(is_roles)
        if not is_roles:
            # clear selection state to avoid accidental edits
            self.input_username.clear()
            self.loaded_user = None
            self.selected_roles = []
            self.selected_depts = []
            self.selected_perms = []
        # when switching back to roles mode ensure focus on username input
        if mode == 'roles':
            try:
                self.input_username.setFocus()
            except Exception:
                pass

    def _on_create_user(self):
        login = self.add_login.text().strip()
        pwd = self.add_password.text()
        if not login or not pwd:
            QMessageBox.warning(self, 'Ошибка', 'Укажите логин и пароль для нового пользователя.')
            return
        try:
            create_user(login, pwd)
            QMessageBox.information(self, 'Готово', f'Пользователь {login} создан.')
            # refresh cache
            self._all_user_docs = None
            self.set_mode('roles')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def _on_delete_user(self):
        login = self.del_login.text().strip()
        if not login:
            QMessageBox.warning(self, 'Ошибка', 'Укажите логин для удаления.')
            return
        ok = QMessageBox.question(self, 'Подтвердите', f'Удалить пользователя {login}?')
        if ok != QMessageBox.StandardButton.Yes:
            return
        try:
            if delete_user(login):
                QMessageBox.information(self, 'Готово', f'Пользователь {login} удалён.')
                self._all_user_docs = None
                self.set_mode('roles')
            else:
                QMessageBox.information(self, 'Инфо', 'Пользователь не найден.')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))
