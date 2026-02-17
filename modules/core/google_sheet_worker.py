from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from PyQt6.QtCore import QThread, pyqtSignal


@dataclass
class SheetPayload:
    objects: Optional[list] = None
    stats: Optional[list] = None


class GoogleSheetLoadThread(QThread):
    """Loads required sheets in a background thread."""

    loaded = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, google_service, spreadsheet_id: str, parent=None):
        super().__init__(parent)
        self.google_service = google_service
        self.spreadsheet_id = spreadsheet_id

    def run(self) -> None:
        try:
            fetched: Dict[str, Any] = {}
            objs = self.google_service.get_sheet_data('objects')
            stats = self.google_service.get_sheet_data('stats')
            if objs is not None:
                fetched['objects'] = objs
            if stats is not None:
                fetched['stats'] = stats
            self.loaded.emit(fetched)
        except Exception as e:
            self.error.emit(str(e))


class GoogleSheetSyncThread(QThread):
    """Exports provided payloads in a background thread."""

    finished_ok = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, google_service, spreadsheet_id: str, payload: dict, parent=None):
        super().__init__(parent)
        self.google_service = google_service
        self.spreadsheet_id = spreadsheet_id
        self.payload = payload

    def run(self) -> None:
        try:
            # Export payloads in a single batch when possible
            batch_updates = {}
            if 'objects' in self.payload and self.payload['objects'] is not None:
                batch_updates['objects'] = self.payload['objects']
            if 'stats' in self.payload and self.payload['stats'] is not None:
                batch_updates['stats'] = self.payload['stats']

            if batch_updates:
                # Use a single call to sync multiple sheets
                try:
                    self.google_service.sync_multiple_sheets(batch_updates)
                except Exception as e:
                    # Fall back to per-sheet calls if needed
                    for sheet, rows in batch_updates.items():
                        try:
                            self.google_service.sync_sheet_data(sheet, rows)
                        except Exception:
                            pass
            self.finished_ok.emit()
        except Exception as e:
            self.error.emit(str(e))
