"""
Firebase users migration playground

Usage:
  py .\firebase_playground.py recreate   - delete users collection content and recreate from Google Sheets
  py .\firebase_playground.py migrate    - merge users from Google Sheets into Firestore (create/update)
  py .\firebase_playground.py read_users - print users currently in Firestore

This script centralizes the migration logic; other code should keep using the Firestore `users` collection.
"""

import sys
import traceback
from pprint import pprint

try:
    from modules.core.firebase_service import init_firestore
    from modules.core.google_service import GoogleService
except Exception as e:
    print("Не удалось импортировать необходимые модули:", e)
    traceback.print_exc()
    sys.exit(1)


def _normalize_bool(val):
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ("1", "true", "yes", "on")


def fetch_sheet_users():
    """Return list of dicts read from Users sheet via GoogleService."""
    gs = GoogleService()
    try:
        users = gs.get_users()
        return users
    except Exception as e:
        print('Ошибка чтения Users листа:', e)
        return []


def recreate_users_collection():
    """Delete all documents in collection 'users' and repopulate from Google Sheets."""
    try:
        db = init_firestore()
    except Exception as e:
        print('Не удалось инициализировать Firestore:', e)
        return

    # Delete all existing documents in 'users'
    try:
        print('Удаляю все документы в коллекции users...')
        col = db.collection('users')
        docs = list(col.stream())
        for d in docs:
            try:
                col.document(d.id).delete()
            except Exception:
                pass
        print(f'Удалено {len(docs)} документов (или по крайней мере потрачено попыток).')
    except Exception as e:
        print('Ошибка при удалении документов:', e)

    # Read sheet and create docs
    sheet_users = fetch_sheet_users()
    created = 0
    errors = []
    for r in sheet_users:
        try:
            username = str(r.get('Username') or r.get('username') or '').strip()
            if not username:
                continue
            password_hash = r.get('PasswordHash') or r.get('PasswordHash'.lower()) or ''
            role_raw = str(r.get('Role') or '').strip()

            # Keep roles/departments but DO NOT assign any explicit permissions during migration
            roles = [role_raw] if role_raw else []
            permissions = []  # explicit permissions intentionally left empty

            # Basic department inference from role name
            departments = []
            if role_raw.lower() in ('head', 'ut_role', 'ut role', 'начальник'):
                departments = ['УТ']
            # also if role explicitly mentions УТ
            if 'ут' in role_raw.lower():
                if 'УТ' not in departments:
                    departments.append('УТ')

            doc = {
                'username': username,
                'hashpassword': password_hash,
                'roles': roles,
                'permissions': [],  # do not grant explicit permissions here
                'departments': departments,
            }
            db.collection('users').document(username).set(doc)
            created += 1
        except Exception as e:
            errors.append((r, str(e)))

    print(f'Создано/обновлено пользователей: {created}')
    if errors:
        print('Ошибки при создании:')
        for e in errors[:10]:
            pprint(e)


def migrate_users_from_sheets():
    """Merge users from sheet into Firestore (create or update)."""
    try:
        db = init_firestore()
    except Exception as e:
        print('Не удалось инициализировать Firestore:', e)
        return

    sheet_users = fetch_sheet_users()
    created = 0
    updated = 0
    errors = []
    for r in sheet_users:
        try:
            username = str(r.get('Username') or r.get('username') or '').strip()
            if not username:
                continue
            password_hash = r.get('PasswordHash') or r.get('PasswordHash'.lower()) or ''
            role_raw = str(r.get('Role') or '').strip()

            # Keep roles/departments but DO NOT assign any explicit permissions during migration
            roles = [role_raw] if role_raw else []
            permissions = []  # explicit permissions intentionally left empty

            departments = []
            if role_raw.lower() in ('head', 'ut_role', 'ut role', 'начальник'):
                departments = ['УТ']
            if 'ут' in role_raw.lower():
                if 'УТ' not in departments:
                    departments.append('УТ')

            doc_ref = db.collection('users').document(username)
            exists = doc_ref.get().exists
            data = {
                'username': username,
                'hashpassword': password_hash,
                'roles': roles,
                'permissions': [],  # do not grant explicit permissions here
                'departments': departments,
            }
            if exists:
                doc_ref.set(data, merge=True)
                updated += 1
            else:
                doc_ref.set(data)
                created += 1
        except Exception as e:
            errors.append((r, str(e)))

    print(f'Создано: {created}, Обновлено: {updated}')
    if errors:
        print('Ошибки при миграции:')
        for e in errors[:10]:
            pprint(e)


def read_users():
    try:
        db = init_firestore()
    except Exception as e:
        print('Не удалось инициализировать Firestore:', e)
        return
    try:
        docs = db.collection('users').stream()
        for d in docs:
            pprint(d.to_dict() or {})
    except Exception as e:
        print('Ошибка чтения коллекции users:', e)


def fix_user_roles():
    """Replace role 'User' with 'Visitor' in all documents in the users collection.
    Handles both the 'roles' list and legacy single 'role' field.
    """
    try:
        db = init_firestore()
    except Exception as e:
        print('Не удалось инициализировать Firestore:', e)
        return

    changed = 0
    errors = []
    try:
        docs = list(db.collection('users').stream())
        for d in docs:
            try:
                data = d.to_dict() or {}
                to_update = {}

                # Normalize roles field
                roles = data.get('roles')
                if roles is not None:
                    # ensure list
                    if isinstance(roles, str):
                        roles_list = [roles]
                    else:
                        roles_list = list(roles)
                    new_roles = ['Visitor' if (r == 'User' or str(r).lower() == 'user') else r for r in roles_list]
                    if new_roles != roles_list:
                        to_update['roles'] = new_roles

                # Legacy single role field
                legacy_role = data.get('role')
                if legacy_role and (legacy_role == 'User' or str(legacy_role).lower() == 'user'):
                    to_update['role'] = 'Visitor'

                if to_update:
                    db.collection('users').document(d.id).set(to_update, merge=True)
                    changed += 1
            except Exception as e:
                errors.append((d.id, str(e)))
    except Exception as e:
        print('Ошибка получения документов users:', e)
        return

    print(f'Обновлено документов: {changed}')
    if errors:
        print('Ошибки при обновлении:')
        for e in errors[:10]:
            pprint(e)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Firebase users migration playground')
    parser.add_argument('action', nargs='?', default='recreate', choices=['recreate', 'migrate', 'read_users', 'fix_roles'], help='Действие')
    args = parser.parse_args()

    if args.action == 'recreate':
        recreate_users_collection()
    elif args.action == 'migrate':
        migrate_users_from_sheets()
    elif args.action == 'read_users':
        read_users()
    elif args.action == 'fix_roles':
        fix_user_roles()


if __name__ == '__main__':
    main()
