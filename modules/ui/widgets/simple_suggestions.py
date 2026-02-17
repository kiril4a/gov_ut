from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QEvent, QTimer
from PyQt6.QtGui import QKeyEvent

class SimpleSuggestionsPopup(QListWidget):
    """Minimal suggestions popup without styling.
    Shows a list of suggestion strings; emits suggestion_selected when user clicks.

    Behavior changes:
    - Do not steal activation (so the editor keeps accepting keyboard input).
    - Install a global event filter while shown to detect outside clicks and close.
    - Apply a dark theme style similar to the original `suggestions_popup.py`.
    """
    suggestion_selected = pyqtSignal(str)
    # Emit the widget that caused the popup to close (or None)
    suggestion_closed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Make popup non-activating so the editor keeps keyboard focus
        # Do not make this a top-level window; keep it as a child widget so
        # it does not steal keyboard focus on Windows. Keep it frameless.
        try:
            self.setWindowFlags(Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint)
        except Exception:
            pass
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Styling and appearance (dark theme) taken from the full SuggestionsPopup
        try:
            self.setMouseTracking(True)
            self.setFrameShape(QListWidget.Shape.NoFrame)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setStyleSheet('''
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
            ''')
        except Exception:
            pass

        self.itemClicked.connect(self._on_item_clicked)
        self._target_widget = None
        self._filter_installed = False
        # track whether app focusChanged signal is connected
        self._focus_connected = False
        self._last_suggestions = None

    def show_suggestions(self, suggestions: list, target_widget):
        # Debug: show invocation and basic info
        try:
            print(f"[SimpleSuggestionsPopup] show_suggestions called. count={len(suggestions)} target={target_widget}")
            print(f"[SimpleSuggestionsPopup] suggestions sample={suggestions[:10]}")
        except Exception:
            pass

        # If already visible for same target and same suggestions, skip to avoid flicker
        try:
            cur_tuple = tuple(suggestions)
            if getattr(self, '_focus_connected', False) and getattr(self, '_target_widget', None) == target_widget and getattr(self, '_last_suggestions', None) == cur_tuple and self.isVisible():
                try:
                    print('[SimpleSuggestionsPopup] same suggestions already visible -> skip')
                except Exception:
                    pass
                return
        except Exception:
            pass

        self.clear()
        if not suggestions:
            try:
                print("[SimpleSuggestionsPopup] no suggestions -> hide")
            except Exception:
                pass
            self.hide()
            return
        for s in suggestions:
            QListWidgetItem(s, self)

        # record last suggestions
        try:
            self._last_suggestions = tuple(suggestions)
        except Exception:
            self._last_suggestions = None

        # place below target: compute global pos now but defer show to avoid stealing focus
        try:
            self._pending_target = target_widget
            self._pending_pos = None
            try:
                self._pending_pos = target_widget.mapToGlobal(target_widget.rect().bottomLeft())
            except Exception:
                try:
                    self._pending_pos = target_widget.mapToGlobal(QPoint(0, target_widget.height()))
                except Exception:
                    self._pending_pos = None
        except Exception:
            self._pending_target = None
            self._pending_pos = None

        # schedule actual show in next event loop turn to avoid interfering with current focus/key processing
        try:
            QTimer.singleShot(0, self._perform_show)
        except Exception:
            # fallback: try immediate
            try:
                self._perform_show()
            except Exception:
                pass

    def _perform_show(self):
        try:
            target_widget = getattr(self, '_pending_target', None)
            gp = getattr(self, '_pending_pos', None)
            if target_widget is None:
                return
            if gp is None:
                try:
                    gp = target_widget.mapToGlobal(target_widget.rect().bottomLeft())
                except Exception:
                    gp = target_widget.mapToGlobal(QPoint(0, target_widget.height()))

            # set width and show without activating
            try:
                self._target_widget = target_widget

                # compute desired height based on item count and cap it
                try:
                    row_height = 36
                    count = len(self._last_suggestions) if getattr(self, '_last_suggestions', None) is not None else self.count()
                    content_height = min(int(count) * row_height + 10, 200)
                    self.setFixedHeight(max(30, content_height))
                except Exception:
                    pass

                # set width and position slightly below the widget
                try:
                    self.setFixedWidth(max(200, target_widget.width()))
                    # If this popup is a child of a parent widget, move expects
                    # parent-local coordinates. Compute the top-left of the
                    # target in the parent's coordinate space and center the
                    # popup horizontally relative to the target. Use a bit
                    # larger vertical gap so the popup doesn't touch the field.
                    try:
                        parent_for_coords = self.parentWidget() or self.window()
                        if parent_for_coords is not None:
                            # target top-left global -> parent-local
                            tgt_top_global = target_widget.mapToGlobal(QPoint(0, 0))
                            tgt_top_local = parent_for_coords.mapFromGlobal(tgt_top_global)
                            v_offset = 10  # vertical gap in pixels
                            # center horizontally relative to target_widget
                            desired_x = int(tgt_top_local.x() + (target_widget.width() - self.width()) / 2)
                            # clamp within parent bounds
                            try:
                                max_x = max(0, parent_for_coords.width() - self.width())
                                desired_x = max(0, min(desired_x, max_x))
                            except Exception:
                                pass
                            desired_y = int(tgt_top_local.y() + target_widget.height() + v_offset)
                            self.move(desired_x, desired_y)
                        else:
                            self.move(gp.x(), gp.y() + 10)
                    except Exception:
                        # Fallback to global coords if conversion fails
                        self.move(gp.x(), gp.y() + 10)
                except Exception:
                    try:
                        self.move(gp)
                    except Exception:
                        pass

                # If already visible with same suggestions, skip
                try:
                    if self.isVisible() and getattr(self, '_last_suggestions', None) is not None:
                        pass
                except Exception:
                    pass
                # Do not set focus proxy (it can intercept keyboard events on some platforms)
                self.show()
                self.raise_()

                # Install global event filter so outside clicks close the popup
                try:
                    app = QApplication.instance()
                    if app and not getattr(self, '_focus_connected', False):
                        try:
                            app.focusChanged.connect(self._on_app_focus_changed)
                            self._focus_connected = True
                        except Exception:
                            self._focus_connected = False
                except Exception:
                    pass

                try:
                    geom = self.geometry().getRect()
                    # log focus info for diagnostics
                    try:
                        cur_focus = QApplication.focusWidget()
                        print(f"[SimpleSuggestionsPopup] shown at {geom} target={target_widget} focus={cur_focus}")
                    except Exception:
                        print(f"[SimpleSuggestionsPopup] shown at {geom} target={target_widget}")
                except Exception:
                    pass

                # NOTE: previously code tried to restore focus to target here. That behavior
                # caused focus/keyboard grabbing on some platforms. We intentionally DO NOT
                # call setFocus() here to avoid stealing keyboard input from the editor.

            except Exception as e:
                try:
                    print(f"[SimpleSuggestionsPopup] failed to show popup: {e}")
                except Exception:
                    pass
        except Exception:
            pass

    def hideEvent(self, ev):
        # Remove global event filter when hiding
        try:
            app = QApplication.instance()
            if app and getattr(self, '_focus_connected', False):
                try:
                    app.focusChanged.disconnect(self._on_app_focus_changed)
                except Exception:
                    pass
                self._focus_connected = False
        except Exception:
            pass
        # clear target
        try:
            self._target_widget = None
        except Exception:
            pass
        # Clear focus proxy so popup no longer forwards events
        try:
            try:
                self.setFocusProxy(None)
            except Exception:
                pass
        except Exception:
            pass
        # Notify listeners that popup closed (useful to suppress immediate re-open)
        try:
            # Emit None to indicate no specific widget
            # log focus info for diagnostics
            try:
                cur_focus = QApplication.focusWidget()
                print(f"[SimpleSuggestionsPopup] hideEvent invoked, current focus={cur_focus}")
            except Exception:
                pass
            self.suggestion_closed.emit(None)
        except Exception:
            pass
        return super().hideEvent(ev)

    def _on_item_clicked(self, item):
        if item:
            self.suggestion_selected.emit(item.text())
            try:
                print(f"[SimpleSuggestionsPopup] item clicked: {item.text()}")
            except Exception:
                pass
            self.hide()

    def _deferred_focus(self, widget):
        try:
            if widget and widget.focusPolicy() != Qt.FocusPolicy.NoFocus:
                try:
                    widget.setFocus()
                except Exception:
                    pass
        except Exception:
            pass

    def eventFilter(self, obj, event):
        # This class no longer installs itself as an application event filter.
        # Keep a stub to satisfy any external callers but do not intercept events.
        return False

    def _on_app_focus_changed(self, old, now):
        """Hide popup when focus moves outside the popup and its target widget."""
        try:
            # If focus moved to popup or the target widget, keep it open
            cur = now
            inside = False
            while cur is not None:
                if cur == self or cur == getattr(self, '_target_widget', None):
                    inside = True
                    break
                cur = cur.parentWidget()

            if not inside:
                try:
                    # Emit closed with the new widget so owner can act (focus etc.)
                    try:
                        self.suggestion_closed.emit(now)
                    except Exception:
                        pass
                    QTimer.singleShot(0, self.hide)
                except Exception:
                    pass
        except Exception:
            pass

    def focusInEvent(self, event):
        # Prevent the popup from taking focus
        try:
            self.clearFocus()
        except Exception:
            pass
        return super().focusInEvent(event)
