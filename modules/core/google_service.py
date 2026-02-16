import gspread
import hashlib
from modules.core.utils import get_resource_path
from typing import List, Dict, Union

class GoogleService:
    def __init__(self, key_file='assets/service_account.json', spread_name="Gov UT", target_spreadsheet_id=None):
        """
        :param target_spreadsheet_id: Optional ID of the specific spreadsheet to limit scope.
        """
        self.key_file = get_resource_path(key_file)
        self.spread_name = spread_name
        self.target_spreadsheet_id = target_spreadsheet_id
        self.gc = None
        self.sh = None
        self.doc = None # Specific document reference if needed (like the one provided by user)

    def _ensure_connection(self):
        if not self.gc:
            self.gc = gspread.service_account(filename=self.key_file)
        
        if not self.sh:
            try:
                # Try opening by name first
                self.sh = self.gc.open(self.spread_name)
            except gspread.SpreadsheetNotFound:
                try:
                    # Try creating if not found
                    self.sh = self.gc.create(self.spread_name)
                except Exception as e:
                    print(f"Error connecting to main spreadsheet: {e}")
                    
        # Connect to the target spreadsheet if ID provided (for sync)
        if self.target_spreadsheet_id and not self.doc:
            try:
                self.doc = self.gc.open_by_key(self.target_spreadsheet_id)
            except Exception as e:
                print(f"Error connecting to target spreadsheet {self.target_spreadsheet_id}: {e}")

    def sync_sheet_data(self, sheet_title: str, data: List[List[Union[str, int, float]]]):
        """
        Syncs data a specific sheet in the target document using batch mechanism.
        """
        # Delegate to batch updater for single-sheet payload
        self.sync_multiple_sheets({sheet_title: data})

    def _col_to_letter(self, col: int) -> str:
        """Convert 1-based column index to Excel-style letters."""
        letters = ''
        while col > 0:
            col, rem = divmod(col - 1, 26)
            letters = chr(65 + rem) + letters
        return letters

    def sync_multiple_sheets(self, updates: Dict[str, List[List[Union[str, int, float]]]]):
        """
        Sync multiple sheets in a single batch update to minimize API calls.
        :param updates: dict mapping sheet_title -> 2D list of rows
        """
        self._ensure_connection()
        if not self.doc:
            return

        data_blocks = []
        for title, rows in updates.items():
            # Ensure worksheet exists
            try:
                ws = self.doc.worksheet(title)
            except Exception:
                # Create worksheet with reasonable size
                rows_count = max(1, len(rows))
                cols_count = 1
                for r in rows:
                    cols_count = max(cols_count, len(r))
                try:
                    ws = self.doc.add_worksheet(title=title, rows=max(100, rows_count + 10), cols=max(10, cols_count))
                except Exception as e:
                    # If another process/thread created the sheet concurrently, ignore "already exists" error
                    msg = str(e).lower()
                    if 'already exists' in msg or 'alreadyExists' in msg or 'a sheet with the name' in msg:
                        try:
                            ws = self.doc.worksheet(title)
                        except Exception:
                            # fallback: continue without ws (batch update will attempt to create range and may fail)
                            ws = None
                    else:
                        raise

            if not rows:
                # no-op but include a minimal clear
                data_blocks.append({'range': f"{title}!A1:A1", 'values': [['']]})
                continue

            rows_count = len(rows)
            cols_count = max((len(r) for r in rows), default=1)
            end_col = self._col_to_letter(cols_count)
            range_a1 = f"{title}!A1:{end_col}{rows_count}"
            data_blocks.append({'range': range_a1, 'values': rows})

        if not data_blocks:
            return

        body = {'valueInputOption': 'RAW', 'data': data_blocks}
        try:
            # Use batch_update on the Spreadsheet to perform one network call
            self.doc.batch_update(body)
        except Exception as e:
            # If batch_update failed due to addSheet already existing, try to detect and continue
            msg = str(e).lower()
            if 'addsheet' in msg and 'already exists' in msg:
                # Ignore and attempt per-sheet updates
                pass
            # Fallback: per-sheet clear+update
            for title, rows in updates.items():
                try:
                    ws = self.doc.worksheet(title)
                except Exception:
                    try:
                        ws = self.doc.add_worksheet(title=title, rows=max(100, len(rows) + 10), cols=max(10, max((len(r) for r in rows), default=1)))
                    except Exception as e2:
                        msg2 = str(e2).lower()
                        if 'already exists' in msg2 or 'a sheet with the name' in msg2:
                            try:
                                ws = self.doc.worksheet(title)
                            except Exception:
                                ws = None
                        else:
                            ws = None
                try:
                    if ws is not None:
                        try:
                            ws.clear()
                        except Exception:
                            pass
                        if rows:
                            try:
                                ws.update(range_name='A1', values=rows)
                            except Exception:
                                for r in rows:
                                    try:
                                        ws.append_row(r)
                                    except Exception:
                                        pass
                except Exception:
                    # ignore per-sheet failures here
                    pass

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

    def create_user(self, username, password, role="User", can_edit="0", can_upload="0"):
        """Creates a new user if not exists."""
        self._ensure_connection()
        ws = self.sh.worksheet("Users")
        
        # Check existence
        existing_users = ws.col_values(1)
        if username in existing_users:
            raise ValueError("Пользователь уже существует")
            
        phash = hashlib.sha256(password.encode()).hexdigest()
        ws.append_row([username, phash, role, can_edit, can_upload])

    def update_user_password(self, username, new_password):
        """Updates the password for an existing user."""
        self._ensure_connection()
        ws = self.sh.worksheet("Users")
        
        # Find row by username
        users = self.get_users()
        row_idx = None
        for i, u in enumerate(users):
            if str(u.get('Username')) == username:
                row_idx = i + 2 # +1 for header, +1 for 0-index
                break
        
        if not row_idx:
            raise ValueError("Пользователь не найден")
            
        new_hash = hashlib.sha256(new_password.encode()).hexdigest()
        # Password is in column 2 (B)
        ws.update_cell(row_idx, 2, new_hash)

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

    def get_sheet_data(self, sheet_title: str):
        """Returns all values from a sheet in the target document (list of rows).
        Returns None if document or sheet not available.
        """
        self._ensure_connection()
        if not self.doc:
            return None
        try:
            ws = self.doc.worksheet(sheet_title)
            return ws.get_all_values()
        except gspread.WorksheetNotFound:
            return None
        except Exception as e:
            print(f"Error fetching sheet {sheet_title}: {e}")
            return None
