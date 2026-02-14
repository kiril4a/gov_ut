import sys
import os

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If running as script, base_path is project root.
        # However, modules/core/utils.py is deeper than root.
        # But we pass absolute paths relative to execution context (usually root).
        # If execution context is NOT root (e.g. running from some other folder), this fails.
        # Better: use sys.modules['__main__'].__file__ if available, or just the file path of this module up two levels.

        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # utils.py is in modules/core/ - that's 2 levels down. 
        # modules/core/ -> modules/ -> root/
        # So we need dirname(dirname(dirname(abspath(utils.py))))?
        # abspath(utils.py) -> .../modules/core/utils.py
        # dirname 1 -> .../modules/core
        # dirname 2 -> .../modules
        # dirname 3 -> .../ (root)
        
        # This is safer than relying on CWD (os.path.abspath("."))
        
        # But wait, original code was: base_path = os.path.abspath(".")
        # If user runs 'python main.py' from root, CWD is root.
        # If user runs 'python c:\path\to\main.py' from elsewhere, CWD is elsewhere.
        # Using __file__ allows us to not depend on CWD.
        
    return os.path.join(base_path, relative_path)