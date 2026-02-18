def get_scrollbar_qss():
    """Returns a QSS snippet for rounded dark scrollbars used across the app (Google Chrome style)."""
    return '''
    /* Vertical Scrollbar */
    QScrollBar:vertical {
        background: transparent;  /* Track background transparent */
        width: 12px;
        margin: 0px; 
    }
    
    QScrollBar::handle:vertical {
        background: #555555;      /* Thumb color */
        min-height: 20px;
        margin: 2px 2px 2px 2px;  /* Margin to simulate floating 'pill' inside track */
        border-radius: 4px;       /* Pill shape */
    }
    
    QScrollBar::handle:vertical:hover {
        background: #777777;      /* Hover state lighter */
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
        background: none;
    }
    
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }

    /* Horizontal Scrollbar */
    QScrollBar:horizontal {
        background: transparent;
        height: 12px;
        margin: 0px;
    }
    
    QScrollBar::handle:horizontal {
        background: #555555;
        min-width: 20px;
        margin: 2px 2px 2px 2px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background: #777777;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
        background: none;
    }
    
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
    }

    /* Slider visuals (exported to separate file) */
    QSlider::groove:horizontal { background: #2b2b2b; height: 8px; border-radius: 6px; }
    QSlider::handle:horizontal { background: #4aa3df; width: 18px; height: 18px; margin-top: -5px; margin-bottom: -5px; border-radius: 9px; }
    QSlider::groove:vertical { background: #2b2b2b; width: 8px; border-radius: 6px; }
    QSlider::handle:vertical { background: #4aa3df; width: 18px; height: 18px; margin-left: -5px; margin-right: -5px; border-radius: 9px; }
    '''