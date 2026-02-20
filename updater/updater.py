import sys
import os
import time
import argparse
import urllib.request
import subprocess
import tempfile
import shutil

def wait_for_file_release(filepath, timeout=30):
    """Wait until the file is no longer locked by another process."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Try to rename the file to itself to check if it's locked
            os.rename(filepath, filepath)
            return True
        except OSError:
            time.sleep(1)
    return False

def main():
    parser = argparse.ArgumentParser(description="Updater")
    parser.add_argument("--url", required=True, help="Download URL for the new executable")
    parser.add_argument("--target", required=True, help="Path to the executable to replace")
    args = parser.parse_args()

    url = args.url
    target_path = args.target

    print(f"Downloading update from {url}...")
    
    temp_dir = tempfile.gettempdir()
    temp_file = os.path.join(temp_dir, "new_app_update.exe")
    
    try:
        urllib.request.urlretrieve(url, temp_file)
        print("Download complete.")
    except Exception as e:
        print(f"Failed to download update: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

    print(f"Waiting for {os.path.basename(target_path)} to close...")
    if os.path.exists(target_path):
        if not wait_for_file_release(target_path):
            print("Timeout waiting for the application to close.")
            input("Press Enter to exit...")
            sys.exit(1)

    print("Replacing old executable...")
    try:
        backup_path = target_path + ".bak"
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        if os.path.exists(target_path):
            os.rename(target_path, backup_path)
            
        shutil.move(temp_file, target_path)
        print("Update installed successfully.")
    except Exception as e:
        print(f"Failed to replace executable: {e}")
        if os.path.exists(backup_path) and not os.path.exists(target_path):
            os.rename(backup_path, target_path)
        input("Press Enter to exit...")
        sys.exit(1)

    print("Starting new version...")
    try:
        subprocess.Popen([target_path])
    except Exception as e:
        print(f"Failed to start new executable: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
