import subprocess
import sys
import logging

# ログ設定
logging.basicConfig(filename='script_execution.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

# デバッグ用
print(sys.executable)
logging.info(f"Python executable: {sys.executable}")

scripts = [
    "backup_vault.py", # バックアップスクリプトのため最初に実行すること
    "exportDailyLocation.py",
    "getLocationData.py",
    "getChromeHistory.py",
    "update_weather.py",
    "exportDailyNote.py", # デイリーノート追加用スクリプトのため最後に実行すること
]

for script in scripts:
    print(f"Running {script}...")
    logging.info(f"Running {script}...")
    result = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    logging.info(result.stdout.strip())
    if result.returncode != 0:
        print(f"Error in {script}: {result.stderr}")
        logging.error(f"Error in {script}: {result.stderr}")
        break
    else:
        print(f"Completed {script}")
        logging.info(f"Completed {script}")

print("All scripts completed.")
logging.info("All scripts completed.")
