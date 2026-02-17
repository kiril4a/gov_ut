def get_scrollbar_qss():
    """Returns a QSS snippet for rounded dark scrollbars used across the app."""
    return '''
    QScrollBar:vertical {
        background: rgba(40,40,40,1);
        width: 12px;
        margin: 4px 2px 4px 2px;
        border-radius: 8px;
    }
    QScrollBar::handle:vertical {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5aa9ea, stop:1 #2b7fbf);
        min-height: 20px;
        border-radius: 8px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
        background: none;
    }
    QScrollBar:horizontal {
        background: rgba(40,40,40,1);
        height: 12px;
        margin: 2px 4px 2px 4px;
        border-radius: 8px;
    }
    QScrollBar::handle:horizontal {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5aa9ea, stop:1 #2b7fbf);
        min-width: 20px;
        border-radius: 8px;
    }

    /* Slider visuals (exported to separate file) */
    QSlider::groove:horizontal { background: #2b2b2b; height: 8px; border-radius: 6px; }
    QSlider::handle:horizontal { background: #4aa3df; width: 18px; height: 18px; margin-top: -5px; margin-bottom: -5px; border-radius: 9px; }
    QSlider::groove:vertical { background: #2b2b2b; width: 8px; border-radius: 6px; }
    QSlider::handle:vertical { background: #4aa3df; width: 18px; height: 18px; margin-left: -5px; margin-right: -5px; border-radius: 9px; }
    '''