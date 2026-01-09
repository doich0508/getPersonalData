"""
1. Obsidian の Vault のバックアップの作成
2. 指定日のデイリーノートに天気情報、訪問場所、閲覧履歴を追記
3. 使用後のJSONファイルをアーカイブフォルダに移動
"""


import os
import json
import shutil
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

_backup_dir_raw = expand_env_path(os.getenv("BACKUP_DIR"))
if not _backup_dir_raw:
    raise ValueError("エラー: .envファイルに 'BACKUP_DIR' が設定されていません。")
BACKUP_DIR: Path = _backup_dir_raw

daily_folder_raw = os.getenv("DAILY_NOTE_FOLDER", "")
DAILY_NOTE_FOLDER_STR = os.path.expandvars(daily_folder_raw)

try:
    BACKUP_GENERATIONS = int(os.getenv("BACKUP_GENERATIONS", "5"))
except ValueError:
    BACKUP_GENERATIONS = 5
    print("警告: BACKUP_GENERATIONS の設定が不正です。デフォルト値(5)を使用します。")

try:
    DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", "35.6812"))
    DEFAULT_LON = float(os.getenv("DEFAULT_LON", "139.7671"))
except ValueError:
    print("警告: 座標の設定が不正です。デフォルト座標を使用します。")
    DEFAULT_LAT = 35.6812
    DEFAULT_LON = 139.7671

ARCHIVE_DIR = SCRIPT_DIR / "archive"


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

def format_time(iso_str):
    try:
        dt = datetime.datetime.fromisoformat(iso_str)
        return dt.strftime("%H:%M")
    except:
        return "??"

def rotate_backups(backup_dir, max_generations):
    """古いバックアップを削除して世代数を維持する"""
    backups = []
    try:
        for p in backup_dir.iterdir():
            if p.is_dir() and p.name.startswith("backup_"):
                backups.append(p)
    except FileNotFoundError:
        return 
    
    backups.sort(key=lambda x: x.name)
    
    if len(backups) > max_generations:
        excess_count = len(backups) - max_generations
        print(f"バックアップ世代管理: 古いバックアップを {excess_count} 件削除します...")
        
        for i in range(excess_count):
            old_backup = backups[i]
            try:
                print(f"  削除中: {old_backup.name}")
                shutil.rmtree(old_backup)
            except Exception as e:
                print(f"  削除失敗 {old_backup.name}: {e}")
        print("バックアップ世代管理完了。")

# --- メイン処理 ---

def main():
    today = datetime.date.today()
    target_date = today - datetime.timedelta(days=1)
    target_date_str = target_date.strftime("%Y-%m-%d")
    print(f"処理対象日: {target_date_str}")

    updated_json_name = f"updated_{target_date_str}.json"
    filtered_json_name = f"filtered_{target_date_str}.json"
    history_json_name = f"{target_date_str}_history_output.json"
    
    updated_json_path = SCRIPT_DIR / updated_json_name
    history_json_path = SCRIPT_DIR / history_json_name
    filtered_json_path = SCRIPT_DIR / filtered_json_name
    
    daily_note_path = VAULT_PATH / DAILY_NOTE_FOLDER_STR / f"{target_date_str}.md"

    # --- 1. バックアップ処理 (失敗しても継続) ---
    print("Vaultをバックアップ中...")
    
    if not BACKUP_DIR.exists():
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"警告: バックアップルートフォルダの作成に失敗しました。バックアップをスキップします。\n理由: {e}")
    
    if BACKUP_DIR.exists():
        backup_folder_name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        target_backup_path = BACKUP_DIR / backup_folder_name
        
        try:
            shutil.copytree(VAULT_PATH, target_backup_path)
            print(f"バックアップ完了: {target_backup_path}")
            rotate_backups(BACKUP_DIR, BACKUP_GENERATIONS)
        except Exception as e:
            print(f"警告: バックアップ処理中にエラーが発生しました。バックアップをスキップして続行します。\n理由: {e}")

    # --- 以降、ノート更新処理 ---

    if not daily_note_path.exists():
        print(f"エラー: デイリーノートが見つかりません -> {daily_note_path}")
        return

    try:
        with open(daily_note_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"エラー: デイリーノートの読み込みに失敗しました: {e}")
        return

    # --- 2. 場所データの追記（テーブル形式・不明な場所を除外） ---
    location_text = ""
    if updated_json_path.exists():
        try:
            with open(updated_json_path, 'r', encoding='utf-8') as f:
                loc_data = json.load(f)
                
            if loc_data and isinstance(loc_data, list):
                # ヘッダー作成
                table_lines = ["\n## 訪れた場所\n"]
                table_lines.append("| 時間 | 場所 | 住所 |")
                table_lines.append("| :--- | :--- | :--- |")
                
                has_valid_entry = False
                for entry in loc_data:
                    visit = entry.get("visit", {})
                    candidate = visit.get("topCandidate", {})
                    name = candidate.get("name", "不明な場所")
                    
                    if name == "不明な場所":
                        continue
                        
                    has_valid_entry = True
                    address = candidate.get("formatted_address", "")
                    start_time = format_time(entry.get("startTime", ""))
                    end_time = format_time(entry.get("endTime", ""))
                    
                    # パイプをエスケープ
                    safe_name = name.replace("|", "\\|")
                    safe_address = address.replace("|", "\\|")
                    
                    table_lines.append(f"| {start_time} - {end_time} | **{safe_name}** | {safe_address} |")
                
                if has_valid_entry:
                    location_text = "\n".join(table_lines) + "\n"
                else:
                    location_text = "\n## 訪れた場所\n- (有効な移動履歴はありません)\n"

        except Exception as e:
            print(f"位置情報JSONの読み込みエラー: {e}")

    # --- 3. 天気データの追記 ---
    lat, lon = DEFAULT_LAT, DEFAULT_LON
    print(f"天気情報を取得中 (Default座標: {lat}, {lon})...")
    weather_data = get_weather_data(target_date_str, lat, lon)
    
    if weather_data:
        content = update_frontmatter(content, weather_data)

    # --- 4. 閲覧履歴の追記（3列テーブル形式） ---
    history_text = ""
    if history_json_path.exists():
        try:
            with open(history_json_path, 'r', encoding='utf-8') as f:
                hist_data = json.load(f)
            
            # ヘッダー作成: | 時間 | タイトル | URL |
            table_lines = ["\n## 閲覧履歴\n"]
            table_lines.append("| 時間 | タイトル | URL |")
            table_lines.append("| :--- | :--- | :--- |")
            
            count = 0
            for item in hist_data:
                visit_time_str = item.get("visit_time", "")
                if visit_time_str.startswith(target_date_str):
                    time_part = visit_time_str.split(" ")[1][:5] if " " in visit_time_str else "??"
                    title = item.get("title", "No Title")
                    url = item.get("url", "#")
                    
                    # Markdownテーブル用にパイプをエスケープ
                    safe_title = title.replace("|", "\\|")
                    # URL自体にパイプが含まれることは稀ですが、一応エスケープ
                    safe_url = url.replace("|", "\\|")
                    
                    table_lines.append(f"| {time_part} | {safe_title} | {safe_url} |")
                    count += 1
            
            if count > 0:
                history_text = "\n".join(table_lines) + "\n"
            else:
                history_text = "\n## 閲覧履歴\n- (昨日の履歴はありません)\n"
                
        except Exception as e:
            print(f"履歴JSONの読み込みエラー: {e}")

    # 保存
    try:
        new_content = content + location_text + history_text
        with open(daily_note_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("デイリーノートを更新しました。")
    except Exception as e:
        print(f"エラー: デイリーノートの書き込みに失敗しました: {e}")
        return

    # --- 5. ファイルアーカイブ ---
    if not ARCHIVE_DIR.exists():
        try:
            ARCHIVE_DIR.mkdir()
        except Exception as e:
             print(f"アーカイブフォルダの作成に失敗したため、ファイル移動をスキップします: {e}")
             return

    files_to_archive = [updated_json_path, history_json_path, filtered_json_path]
    print("ファイルをアーカイブ中...")
    for file_path in files_to_archive:
        if file_path.exists():
            try:
                shutil.move(str(file_path), str(ARCHIVE_DIR / file_path.name))
                print(f"アーカイブ完了: {file_path.name}")
            except Exception as e:
                print(f"アーカイブ失敗 {file_path.name}: {e}")
        else:
            print(f"ファイルが見つからないためスキップ: {file_path.name}")

if __name__ == "__main__":
    main()
