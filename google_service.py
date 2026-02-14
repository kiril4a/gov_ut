import gspread
import hashlib
from utils import get_resource_path

class GoogleService:
    def __init__(self, key_file='service_account.json', spread_name="Gov UT"):
        self.key_file = get_resource_path(key_file)
        self.spread_name = spread_name
        self.gc = None
        self.sh = None

    def _ensure_connection(self):
        if not self.gc:
            self.gc = gspread.service_account(filename=self.key_file)
        if not self.sh:
            try:
                self.sh = self.gc.open(self.spread_name)
            except gspread.SpreadsheetNotFound:
                self.sh = self.gc.create(self.spread_name)

    def get_users(self):
        """Fetches all users from Users sheet, creating it if needed."""
        self._ensure_connection()
        try:
            ws = self.sh.worksheet("Users")
        except gspread.WorksheetNotFound:
            ws = self.sh.add_worksheet(title="Users", rows=100, cols=5)
            ws.append_row(["Username", "PasswordHash", "Role", "CanEdit", "CanUpload"])
            # Create default admin
            default_hash = hashlib.sha256("admin".encode()).hexdigest()
            ws.append_row(["admin", default_hash, "Admin", "1", "1"])
        
        return ws.get_all_records()

    def create_user(self, username, password, role, can_edit, can_upload):
        """Creates a new user if not exists."""
        self._ensure_connection()
        ws = self.sh.worksheet("Users")
        
        # Check existence
        existing_users = ws.col_values(1)
        if username in existing_users:
            raise ValueError("Пользователь уже существует")
            
        phash = hashlib.sha256(password.encode()).hexdigest()
        ws.append_row([username, phash, role, can_edit, can_upload])

    def connect_worksheet(self, title):
        """Connects to or creates a worksheet with headers."""
        self._ensure_connection()
        try:
            ws = self.sh.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = self.sh.add_worksheet(title=title, rows=100, cols=10)
            ws.append_row(["Name", "Static ID", "Rank", "Articles", "Sum", "Processed"])
        return ws

    def fetch_all_values(self, worksheet):
        """Wrapper for get_all_values."""
        return worksheet.get_all_values()

    def update_row_data(self, worksheet, name, articles_str, sum_val, processed_val):
        """Updates a row by name using optimized batch update."""
        cell = worksheet.find(name)
        if cell:
            # Prepare the range (Columns 4, 5, 6 -> D, E, F)
            # Example range: "D5:F5"
            range_str = f"D{cell.row}:F{cell.row}"
            # Update the range in one API call
            worksheet.update(range_name=range_str, values=[[articles_str, sum_val, processed_val]])
        else:
            # Handle case where row is missing in sheet? 
            pass

    def upload_sheet_data(self, sheet_name, data, include_header=True):
        """Uploads list of dicts to a new or existing worksheet."""
        self._ensure_connection()
        
        # Prepare header and rows
        # We need to map our internal dict keys to columns
        rows_to_upload = []
        if include_header:
            header = ["Name", "Statik", "Rank", "Articles", "Sum", "Processed"]
            rows_to_upload.append(header)
        
        for item in data:
            arts = ",".join(item.get('articles', []))
            row = [
                item.get('name', ''),
                item.get('statik', ''),
                item.get('rank', ''),
                arts,
                item.get('sum', 0),
                item.get('processed', 1)
            ]
            rows_to_upload.append(row)
            
        try:
            ws = self.sh.worksheet(sheet_name)
            ws.clear()
        except gspread.WorksheetNotFound:
            ws = self.sh.add_worksheet(title=sheet_name, rows=len(rows_to_upload)+10, cols=6)
            
        ws.update(rows_to_upload)
        return ws
