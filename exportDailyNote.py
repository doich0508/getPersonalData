"""
指定日のデイリーノートに訪問場所、閲覧履歴を追記
使用後のJSONファイルをアーカイブフォルダに移動
"""


import os
import json
import shutil
import datetime
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

ARCHIVE_DIR = SCRIPT_DIR / "archive"


# --- 関数定義 ---

def format_time(iso_str):
    try:
        dt = datetime.datetime.fromisoformat(iso_str)
        return dt.strftime("%H:%M")
    except:
        return "??"

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

    # --- ノート更新処理 ---

    if not daily_note_path.exists():
        print(f"エラー: デイリーノートが見つかりません -> {daily_note_path}")
        return

    try:
        with open(daily_note_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"エラー: デイリーノートの読み込みに失敗しました: {e}")
        return

    # --- 場所データの追記（テーブル形式・不明な場所を除外） ---
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

    # --- 閲覧履歴の追記（3列テーブル形式） ---
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

    # --- ファイルアーカイブ ---
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
