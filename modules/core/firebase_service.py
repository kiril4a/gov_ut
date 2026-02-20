import os

from modules.core.utils import get_resource_path

_initialized = False
_db = None


def init_firestore(service_account_path: str | None = None):
    """Initialize and return a Firestore client.
    Attempts to load service account from provided path or from assets/service_account.json.
    Raises ImportError if firebase_admin is not installed.
    """
    global _initialized, _db
    if (_initialized and _db is not None):
        return _db

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except Exception as e:
        raise ImportError("firebase_admin is required for Firestore operations. Install 'firebase-admin'.")

    if service_account_path is None:
        # try to load from assets
        service_account_path = get_resource_path('service_account.json')

    # If the resolved path doesn't exist, try common fallbacks (assets/ in project root)
    if not os.path.exists(service_account_path):
        # project root is two levels up from modules/core
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        alt_path = os.path.join(project_root, 'assets', 'service_account.json')
        if os.path.exists(alt_path):
            service_account_path = alt_path
        else:
            # also try current working dir assets (in case script run from project root)
            cwd_alt = os.path.join(os.getcwd(), 'assets', 'service_account.json')
            if os.path.exists(cwd_alt):
                service_account_path = cwd_alt

    if not os.path.exists(service_account_path):
        raise FileNotFoundError(f"Service account file not found: {service_account_path}")

    cred = credentials.Certificate(service_account_path)
    try:
        # initialize only once
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    _initialized = True
    return _db


def get_usernames():
    """Return a list of usernames from collection 'users'. If collection doesn't exist return []."""
    try:
        db = init_firestore()
    except Exception:
        return []

    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        names = []
        for d in docs:
            data = d.to_dict() or {}
            name = data.get('username') or data.get('Username') or data.get('login')
            if name:
                names.append(name)
        return sorted(set(names))
    except Exception:
        return []


def save_role_config(username: str, roles: list, departments: list):
    """Save role configuration for a user into 'role_settings' collection.
    Overwrites existing document with same username.
    """
    if not username:
        raise ValueError('username required')

    db = init_firestore()
    try:
        doc_ref = db.collection('role_settings').document(username)
        doc_ref.set({
            'username': username,
            'roles': roles,
            'departments': departments,
        })
        return True
    except Exception as e:
        raise


def list_users():
    """Return list of user documents (dicts) from 'users'."""
    db = init_firestore()
    users = []
    try:
        docs = db.collection('users').stream()
        for d in docs:
            data = d.to_dict() or {}
            data.setdefault('username', d.id)
            users.append(data)
    except Exception:
        pass
    return users


def get_user(username: str):
    """Return user dict from 'users' or None."""
    db = init_firestore()
    try:
        doc = db.collection('users').document(username).get()
        if doc.exists:
            d = doc.to_dict() or {}
            d.setdefault('username', username)
            return d
    except Exception:
        pass
    return None


def create_user(username: str, password: str, role: str = None, departments: list | None = None, permissions: list | None = None):
    """Create user document in 'users'. Password is stored as SHA256 hash (existing apps expect this).
    If document exists, raises ValueError.
    """
    db = init_firestore()
    doc_ref = db.collection('users').document(username)
    if doc_ref.get().exists:
        raise ValueError('User exists')
    import hashlib
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    data = {
        'username': username,
        'hashpassword': pw_hash,
        'roles': [role] if role else [],
        'departments': departments or [],
        'permissions': permissions or [],
    }
    doc_ref.set(data)
    return True


def update_user(username: str, data: dict):
    """Merge update fields into user document."""
    db = init_firestore()
    doc_ref = db.collection('users').document(username)
    doc_ref.set(data, merge=True)
    return True


def update_user_password(username: str, new_password: str):
    db = init_firestore()
    import hashlib
    pw_hash = hashlib.sha256(new_password.encode()).hexdigest()
    db.collection('users').document(username).set({'hashpassword': pw_hash}, merge=True)
    return True


def delete_user(username: str) -> bool:
    """Delete a user document from 'users' collection. Returns True if deleted or False if not found."""
    if not username:
        raise ValueError('username required')
    db = init_firestore()
    doc_ref = db.collection('users').document(username)
    try:
        if doc_ref.get().exists:
            doc_ref.delete()
            return True
        return False
    except Exception:
        raise


# Role model definitions (simple, stored in code)
ROLE_DEFS = {
    'Admin': {'rank': 0, 'permissions': ['admin.full'], 'departments': []},
    # Governor has same effective rights as Admin per requirement
    'Governor': {'rank': 1, 'permissions': ['governor.access', 'admin.full'], 'departments': []},
    'Minister': {'rank': 2, 'permissions': [], 'departments': []},
    # Head (Начальник)
    'Head': {'rank': 3, 'permissions': [], 'departments': []},
    'Deputy': {'rank': 4, 'permissions': [], 'departments': []},
    'Employee': {'rank': 5, 'permissions': [], 'departments': []},
    # Special role for UT responsibilities
    'UT_Role': {'rank': 2, 'permissions': ['ut.view','ut.upload'], 'departments': ['УТ']},
    'Visitor': {'rank': 99, 'permissions': [], 'departments': []},
}

# Default permissions associated with departments (department-scoped defaults).
# This ensures that when a user has a department (e.g., 'УТ'), the common department
# permissions are visible and can be selected in the UI.
DEPT_DEFAULT_PERMS = {
    'УТ': ['ut.view', 'ut.edit', 'ut.upload'],
}


def resolve_user_permissions(user_doc: dict | str):
    """Given a user dict or username string, return resolved permissions, roles set and departments set.
    Returns dict: {'roles': set, 'permissions': set, 'departments': set, 'rank': int}
    """
    if isinstance(user_doc, str):
        user_doc = get_user(user_doc) or {}

    roles = set([r for r in (user_doc.get('roles') or []) if r])
    # if no roles assigned, give Visitor
    if not roles:
        roles = {'Visitor'}

    permissions = set(user_doc.get('permissions') or [])
    departments = set(user_doc.get('departments') or [])

    # merge role permissions and departments
    min_rank = None
    for r in roles:
        info = ROLE_DEFS.get(r)
        if info:
            permissions.update(info.get('permissions', []))
            departments.update(info.get('departments', []))
            rrank = info.get('rank')
            if rrank is not None:
                if min_rank is None or rrank < min_rank:
                    min_rank = rrank
    if min_rank is None:
        min_rank = ROLE_DEFS.get('Visitor', {}).get('rank', 99)

    # NOTE: Do NOT automatically grant department default permissions here.
    # DEPT_DEFAULT_PERMS is used to populate the UI picker so admins can assign
    # department-related permissions explicitly. Granting should happen only
    # via explicit 'permissions' field or via role defaults above.
    # (Previously we auto-added DEPT_DEFAULT_PERMS here; that caused users
    # with only a department membership to get full department rights.)

    return {
        'roles': roles,
        'permissions': permissions,
        'departments': departments,
        'rank': min_rank,
    }


def user_has_permission(user_doc: dict | str, permission: str) -> bool:
    res = resolve_user_permissions(user_doc)
    return permission in res.get('permissions', set()) or ('admin.full' in res.get('permissions', set()))


def role_rank(role_id: str) -> int:
    return ROLE_DEFS.get(role_id, {}).get('rank', 99)


def can_assign_role(assigner_doc: dict | str, target_role: str) -> bool:
    """Return True if assigner is allowed to assign target_role.
    Admin can assign any role. Otherwise assigner may assign only strictly junior roles
    (target_rank must be greater than assigner_rank).
    """
    res = resolve_user_permissions(assigner_doc)
    if 'admin.full' in res.get('permissions', set()):
        return True
    assigner_rank = res.get('rank', 99)
    target_rank = role_rank(target_role)
    # allow assigning only roles with rank > assigner_rank (strictly junior)
    return target_rank > assigner_rank


def save_user_roles(username: str, roles: list, departments: list, permissions: list | None = None):
    """Helper to set roles/departments/permissions for a user document."""
    db = init_firestore()
    data = {
        'roles': roles or [],
        'departments': departments or [],
    }
    if permissions is not None:
        data['permissions'] = permissions
    db.collection('users').document(username).set(data, merge=True)
    return True


def can_open_role_settings(assigner_doc: dict | str) -> bool:
    """Return True if the assigner is allowed to open role-settings UI.
    Rule: only users with rank <= Deputy (i.e., Deputy and above) or admins can open.
    """
    res = resolve_user_permissions(assigner_doc)
    if 'admin.full' in res.get('permissions', set()):
        return True
    deputy_rank = ROLE_DEFS.get('Deputy', {}).get('rank', 99)
    return res.get('rank', 99) <= deputy_rank


def can_manage_user(assigner_doc: dict | str, target_doc: dict | str) -> bool:
    """Return True if assigner is allowed to manage (see/modify) target user according to rules:
    - Admin may manage anyone.
    - Assigner may manage only users with strictly greater numeric rank (i.e., strictly junior).
    - If assigner has role 'Head', they can manage only users that have no department or all target departments are within the assigner's departments.
    """
    # normalize
    if isinstance(assigner_doc, str):
        assigner_doc = get_user(assigner_doc) or {}
    if isinstance(target_doc, str):
        target_doc = get_user(target_doc) or {}

    assigner = resolve_user_permissions(assigner_doc)
    target = resolve_user_permissions(target_doc)

    # admins can manage anyone
    if 'admin.full' in assigner.get('permissions', set()):
        return True

    assigner_rank = assigner.get('rank', 99)
    target_rank = target.get('rank', 99)

    # cannot manage users with higher or equal privilege (i.e., target_rank <= assigner_rank)
    if target_rank <= assigner_rank:
        return False

    # Restricted roles (Minister, Head, Deputy) special rule:
    # They can manage only users that share at least one department with them.
    # Targets without departments are NOT manageable by these restricted assigners.
    restricted_roles = {'Minister', 'Head', 'Deputy'}
    assigner_roles = set(assigner.get('roles', []))
    
    if assigner_roles & restricted_roles:
        assigner_depts = set(assigner.get('departments', []))
        target_depts = set(target.get('departments', []))
        
        if not target_depts:
            return False
        if not (assigner_depts & target_depts):
            return False

    # default: allow managing strictly juniors
    return True


def can_assign_departments(assigner_doc: dict | str, target_departments: list | set) -> bool:
    """Return True if assigner is allowed to assign the provided departments.
    Admin/Governor/Minister may assign any department. Other users may assign only
    departments that they themselves belong to. If assigner has no departments,
    they cannot assign any department (unless they are Admin/Governor/Minister).
    """
    # normalize
    if isinstance(assigner_doc, str):
        assigner_doc = get_user(assigner_doc) or {}

    res = resolve_user_permissions(assigner_doc)
    # admin override
    if 'admin.full' in res.get('permissions', set()):
        return True
    roles = set(res.get('roles', []))
    # roles that can assign any department
    if roles & {'Admin', 'Governor', 'Minister'}:
        return True

    assigner_depts = set(res.get('departments', []))
    if not assigner_depts:
        return False

    target_set = set(target_departments or [])
    return target_set.issubset(assigner_depts)
