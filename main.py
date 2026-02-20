import sys
import os
import subprocess
import re
import logging

# Add the project root to sys.path so that modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from modules.ui.auth import LoginWindow
from modules.ui.launcher import LauncherWindow
from modules.core.utils import get_resource_path

APP_VERSION = "1.2.9"
GITHUB_OWNER = "kiril4a"
GITHUB_REPO = "gov_ut"

logging.basicConfig(level=logging.DEBUG, filename="update.log", filemode="w",
                    format="%(asctime)s - %(levelname)s - %(message)s")

def parse_version_tuple(vstr):
    parts = re.findall(r"\d+", vstr)
    return tuple(int(p) for p in parts)

def is_version_greater(v_new, v_old):
    try:
        return parse_version_tuple(v_new) > parse_version_tuple(v_old)
    except Exception:
        return False

def check_for_update(parent_widget=None):
    """Check GitHub Releases for newer vX.Y.Z.exe asset. If newer and user agrees,
    launch the local updater.exe and exit.
    Returns True if updater was launched (caller should exit)."""
    logging.info("Starting update check...")
    try:
        import requests
    except Exception as e:
        logging.error(f"Failed to import requests: {e}")
        return False

    try:
        # Используем /releases вместо /releases/latest, так как latest не видит pre-release
        api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
        logging.info(f"Fetching releases from {api_url}")
        r = requests.get(api_url, headers={"Accept": "application/vnd.github.v3+json"}, timeout=10)
        r.raise_for_status()
        releases = r.json()
        
        if not releases:
            logging.warning("No releases found.")
            return False
            
        # Берем самый первый (самый новый) релиз из списка
        release = releases[0]
        logging.info(f"Latest release tag: {release.get('tag_name')}")
        assets = release.get("assets", [])
        logging.info(f"Found {len(assets)} assets in the latest release.")

        latest_asset = None
        latest_ver = None
        for a in assets:
            name = a.get("name", "")
            logging.debug(f"Checking asset: {name}")
            # Allow v1.2.8.exe, v 1.2.8.exe, v.1.2.8.exe, etc.
            m = re.match(r"^v[\s\.]*(\d+(?:\.\d+)*)\.exe$", name, re.IGNORECASE)
            if m:
                ver = m.group(1)
                logging.debug(f"Matched version: {ver}")
                if latest_ver is None or is_version_greater(ver, latest_ver):
                    latest_ver = ver
                    latest_asset = a

        if not latest_asset:
            logging.warning("No matching executable asset found.")
            return False
            
        logging.info(f"Latest version found: {latest_ver}, Current version: {APP_VERSION}")
        if not is_version_greater(latest_ver, APP_VERSION):
            logging.info("Current version is up to date.")
            return False

        # Ask user
        title = "Доступно обновление"
        msg = f"Найдена версия {latest_ver} (у вас {APP_VERSION}). Скачать и установить?"
        logging.info("Prompting user for update...")
        answer = QMessageBox.question(parent_widget, title, msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            logging.info("User declined the update.")
            return False

        download_url = latest_asset.get("browser_download_url") or latest_asset.get("url")
        if not download_url:
            logging.error("No download URL found for the asset.")
            QMessageBox.warning(parent_widget, "Ошибка", "Не удалось получить URL для загрузки новой версии.")
            return False

        logging.info(f"Download URL: {download_url}")

        # Look for local updater.exe in the same directory as the current executable
        current_exe = sys.executable
        exe_dir = os.path.dirname(current_exe)
        updater_path = os.path.join(exe_dir, "updater.exe")
        logging.info(f"Looking for updater at: {updater_path}")

        if not os.path.exists(updater_path):
            logging.warning("updater.exe not found, falling back to updater.py")
            # Fallback for development environment
            updater_path = os.path.join(exe_dir, "updater", "updater.py")
            if not os.path.exists(updater_path):
                logging.error("updater.py also not found.")
                QMessageBox.warning(parent_widget, "Ошибка", "Файл updater.exe не найден в папке с приложением.")
                return False
            
            logging.info(f"Launching python updater: {updater_path}")
            # Run python script in dev
            subprocess.Popen([sys.executable, updater_path, "--url", download_url, "--target", current_exe], shell=False)
            return True

        logging.info(f"Launching compiled updater: {updater_path}")
        # Run compiled updater.exe
        subprocess.Popen([updater_path, "--url", download_url, "--target", current_exe], shell=False)
        return True

    except Exception as e:
        logging.exception(f"Error during update check: {e}")
        try:
            QMessageBox.warning(parent_widget, "Обновление не удалось", f"Ошибка при проверке обновлений:\n{e}")
        except Exception:
            pass
        return False

def start_launcher(user_data):
    global launcher_window
    launcher_window = LauncherWindow(user_data)
    launcher_window.launch_main.connect(start_main_app)
    launcher_window.show()

def start_main_app(user_data):
    from modules.ui.app_ui import MainWindow
    global main_window
    main_window = MainWindow(user_data)
    main_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Try to run updater if newer release available. If it was launched, exit so updater can run.
    try:
        if check_for_update():
            sys.exit(0)
    except Exception:
        # do not block normal startup on errors
        pass

    # Needs to handle asset path correctly based on moved assets
    # In utils.py get_resource_path likely defaults to '.'
    # We moved image.png to assets/image.png
    # Let's check get_resource_path behavior or just pass 'assets/image.png'
    
    app.setWindowIcon(QIcon(get_resource_path("assets/image.png")))

    login = LoginWindow()
    login.login_success.connect(start_launcher)
    login.show()

    sys.exit(app.exec())