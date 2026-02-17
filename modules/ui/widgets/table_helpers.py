from PyQt6.QtWidgets import QPushButton, QFrame, QVBoxLayout, QWidget, QHBoxLayout, QAbstractSpinBox, QSizePolicy
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QCursor
from .custom_controls import NoScrollSpinBox, NoScrollDoubleSpinBox

def create_delete_button(callback):
    """
    Creates a styled delete button (red square with trash can/brush) wrapped in a frame.
    Returns the container QFrame.
    """
    del_btn = QPushButton()
    # Use simple unicode or icon as requested
    del_btn.setText("🧹")
    del_btn.setIcon(QIcon()) 
    del_btn.setFixedSize(30, 30) 
    del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    del_btn.setStyleSheet("background: transparent; border: none; font-size: 16px; color: white;")
    del_btn.clicked.connect(lambda: callback(del_btn))

    container_del = QFrame()
    container_del.setFrameShape(QFrame.Shape.Box)
    container_del.setStyleSheet("""
        QFrame {
            border: 2px solid #ff5555; 
            border-radius: 4px;
            background-color: #ff5555;
        }
        QFrame:hover {
            background-color: #ff7777; /* Lighter red on hover */
            border: 2px solid #ff7777;
        }
    """)
    # Layout to center the button
    layout = QVBoxLayout(container_del)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    del_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    layout.addWidget(del_btn)
    
    return container_del

def create_plus_button(callback):
    """
    Creates the big dashed '+' button for adding rows.
    """
    btn_add = QPushButton("+")
    btn_add.setStyleSheet("""
        QPushButton {
            background-color: transparent; 
            font-size: 24px; 
            font-weight: bold; 
            color: #4aa3df; 
            border: 1px dashed #404040; 
            border-radius: 8px;
            margin: 0px;
            padding: 0px;
        }
        QPushButton:hover {
            background-color: #252525;
        }
    """)
    btn_add.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    btn_add.clicked.connect(callback)
    return btn_add

def create_centered_spinbox(value=0, min_val=-999999, max_val=999999, on_change=None, suffix="", prefix=""):
    """
    Creates a styled NoScrollSpinBox wrapped in a QWidget for centering.
    Returns the container QWidget.
    """
    spin = NoScrollSpinBox()
    spin.setRange(min_val, max_val)
    spin.setValue(int(value))
    spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if suffix: spin.setSuffix(suffix)
    if prefix: spin.setPrefix(prefix)
    
    # Remove up/down buttons for cleaner look
    try:
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    except Exception:
        pass

    if on_change:
        spin.valueChanged.connect(on_change)
    
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(spin)
    
    return container

def create_date_button(text, callback):
    """Creates a transparent button showing date."""
    date_btn = QPushButton(text)
    date_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    date_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            border: none;
            font-weight: bold;
            color: #dddddd;
        }
        QPushButton:hover {
            color: #4aa3df;
        }
    """)
    date_btn.clicked.connect(lambda checked: callback(date_btn))
    
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(date_btn)
    
    return container
