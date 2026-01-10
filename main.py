import subprocess
import sys

# デバッグ用
print(sys.executable)

scripts = [
    "exportDailyLocation.py",
    "getLocationData.py",
    "getChromeHistory.py",
    "exportDailyNote.py", # デイリーノート追加用スクリプトのため最後に実行すること
]

for script in scripts:
    print(f"Running {script}...")
    result = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error in {script}: {result.stderr}")
        break
    else:
        print(f"Completed {script}")

print("All scripts completed.")
