"""
デイリーノートに天気情報を追記するスクリプト
"""

import os
import datetime
import requests
import re
from pathlib import Path
from dotenv import load_dotenv

# --- 設定読み込み ---

SCRIPT_DIR = Path(__file__).parent
env_path = SCRIPT_DIR / ".env"
load_dotenv(env_path)

# 環境変数を展開する関数
def expand_env_path(path_str):
    if not path_str:
        return None
    expanded = os.path.expandvars(path_str)
    return Path(expanded)

# 設定の取得と展開
_vault_path_raw = expand_env_path(os.getenv("VAULT_PATH"))
if not _vault_path_raw:
    raise ValueError("エラー: .envファイルに 'VAULT_PATH' が設定されていません。")
VAULT_PATH: Path = _vault_path_raw

daily_folder_raw = os.getenv("DAILY_NOTE_FOLDER", "")
DAILY_NOTE_FOLDER_STR = os.path.expandvars(daily_folder_raw)

try:
    DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", "35.6812"))
    DEFAULT_LON = float(os.getenv("DEFAULT_LON", "139.7671"))
except ValueError:
    print("警告: 座標の設定が不正です。デフォルト座標を使用します。")
    DEFAULT_LAT = 35.6812
    DEFAULT_LON = 139.7671

# --- 関数定義 ---

def get_weather_data(date_str, lat, lon):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date_str,
        "end_date": date_str,
        "daily": ["weathercode", "temperature_2m_max", "temperature_2m_min", "surface_pressure_max", "surface_pressure_min"],
        "timezone": "auto"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        daily = data.get("daily", {})

        wmo_code = daily.get("weathercode", [None])[0]
        weather_text = wmo_code_to_text(wmo_code)

        return {
            "weather": weather_text,
            "max_temp": daily.get("temperature_2m_max", [None])[0],
            "min_temp": daily.get("temperature_2m_min", [None])[0],
            "max_pressure": daily.get("surface_pressure_max", [None])[0],
            "min_pressure": daily.get("surface_pressure_min", [None])[0]
        }
    except Exception as e:
        print(f"天気情報の取得に失敗しました: {e}")
        return None

def wmo_code_to_text(code):
    if code is None: return "不明"
    if code == 0: return "快晴"
    if code in [1, 2, 3]: return "晴れ/曇り"
    if code in [45, 48]: return "霧"
    if code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: return "雨"
    if code in [71, 73, 75, 77, 85, 86]: return "雪"
    if code in [95, 96, 99]: return "雷雨"
    return f"その他({code})"

def update_frontmatter(content, weather_data):
    fm_pattern = r"^---\n(.*?)\n---"
    match = re.search(fm_pattern, content, re.DOTALL)

    new_properties = [
        f"天気: {weather_data['weather']}",
        f"最高気温: {weather_data['max_temp']}",
        f"最低気温: {weather_data['min_temp']}",
        f"最高気圧: {weather_data['max_pressure']}",
        f"最低気圧: {weather_data['min_pressure']}"
    ]
    prop_block = "\n".join(new_properties)

    if match:
        original_fm = match.group(1)
        new_fm = f"---\n{original_fm}\n{prop_block}\n---"
        return content.replace(match.group(0), new_fm)
    else:
        return f"---\n{prop_block}\n---\n\n{content}"

def update_weather_in_note(note_path, date_str, lat=None, lon=None):
    """指定されたノートに天気情報を追記"""
    if lat is None:
        lat = DEFAULT_LAT
    if lon is None:
        lon = DEFAULT_LON

    print(f"天気情報を取得中 (座標: {lat}, {lon})...")
    weather_data = get_weather_data(date_str, lat, lon)

    if not weather_data:
        print("天気情報の取得に失敗したため、スキップします。")
        return False

    if not note_path.exists():
        print(f"エラー: ノートが見つかりません -> {note_path}")
        return False

    try:
        with open(note_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"エラー: ノートの読み込みに失敗しました: {e}")
        return False

    try:
        updated_content = update_frontmatter(content, weather_data)
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        print("天気情報をノートに追記しました。")
        return True
    except Exception as e:
        print(f"エラー: ノートの書き込みに失敗しました: {e}")
        return False

if __name__ == "__main__":
    import sys

    # デフォルトの日付（前日）
    today = datetime.date.today()
    target_date = today - datetime.timedelta(days=1)
    target_date_str = target_date.strftime("%Y-%m-%d")

    # デフォルトのノートパス
    daily_note_path = VAULT_PATH / DAILY_NOTE_FOLDER_STR / f"{target_date_str}.md"

    # 引数処理
    note_path = Path(sys.argv[1]) if len(sys.argv) > 1 else daily_note_path
    date_str = sys.argv[2] if len(sys.argv) > 2 else target_date_str
    lat = float(sys.argv[3]) if len(sys.argv) > 3 else None
    lon = float(sys.argv[4]) if len(sys.argv) > 4 else None

    update_weather_in_note(note_path, date_str, lat, lon)
