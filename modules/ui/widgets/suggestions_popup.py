from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, pyqtSignal, QPoint

class SuggestionsPopup(QListWidget):
    """
    Custom popup for suggestions.
    - Shows suggestions below the input.
    - Matches generic dark theme style.
    """
    suggestion_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self.setFrameShape(QListWidget.Shape.NoFrame)
        # Style matches dark theme requirements
        self.setStyleSheet("""
            QListWidget { 
                background: #232323; 
                color: #f2f2f2; 
                border: 1px solid #3a3a3a; 
                border-radius: 6px; 
                padding: 4px; 
                outline: 0;
            }
            QListWidget::item { 
                padding: 8px 12px; 
                border-radius: 4px; 
                color: #f2f2f2;
                margin-bottom: 2px;
                border: none;
            }
            QListWidget::item:hover { 
                background: #3a3a3a; 
            }
            QListWidget::item:selected { 
                background: #4aa3df; 
                color: white; 
            }
        """)
        self.itemClicked.connect(self._on_item_clicked)
        # Hide horizontal scrollbar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def show_suggestions(self, suggestions, target_widget):
        self.clear()
        if not suggestions:
            self.hide()
            return

        for s in suggestions:
            # Simple item add
            QListWidgetItem(s, self)

        # Calculate position and size
        # Position below the target widget
        global_pos = target_widget.mapToGlobal(QPoint(0, target_widget.height()))
        
        # Calculate needed height
        row_height = 36 # approx height per item including padding
        content_height = min(len(suggestions) * row_height + 10, 200) # Cap at 200px
        
        self.setGeometry(global_pos.x(), global_pos.y() + 4, target_widget.width(), content_height)
        self.show()
        self.raise_()

    def _on_item_clicked(self, item):
        if item:
            self.suggestion_selected.emit(item.text())
            self.hide()
