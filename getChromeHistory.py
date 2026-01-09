import os
import time
import shutil
import sqlite3
import json
import subprocess
import datetime
from dotenv import load_dotenv

# .env ファイルをロード
load_dotenv()

# ==========================================
# 【設定】環境変数を取得
# ==========================================

# .envからパスを取得。見つからない場合はNoneになるため、後のチェックでエラーハンドリング可能
raw_history_path = os.getenv("CHROME_HISTORY_PATH")
raw_exe_path = os.getenv("CHROME_EXE_PATH")

# 変数を展開 (例: %USERPROFILE% -> C:\Users\Name)
# 値が None の場合は None のままにする
CHROME_HISTORY_PATH = os.path.expandvars(raw_history_path) if raw_history_path else None
CHROME_EXE_PATH = os.path.expandvars(raw_exe_path) if raw_exe_path else None

# 動作確認用プリント（不要なら削除）
if CHROME_HISTORY_PATH:
    print(f"History Path: {CHROME_HISTORY_PATH}")

# 作業用の一時ファイル名
TEMP_HISTORY_PATH = "History_temp_copy"

# ==========================================
# メインロジック
# ==========================================

def get_webkit_timestamp_24h_ago():
    """現在時刻から24時間前を WebKit Timestamp (マイクロ秒) で計算"""
    # 1601年1月1日と1970年1月1日の差分（秒）
    WEBKIT_EPOCH_DIFF = 11644473600
    
    # 現在のUnixタイムスタンプ
    now_unix = time.time()
    
    # 24時間前 (秒)
    one_day_ago_unix = now_unix - (24 * 60 * 60)
    
    # WebKitタイムスタンプ（マイクロ秒）に変換
    webkit_timestamp = int((one_day_ago_unix + WEBKIT_EPOCH_DIFF) * 1000000)
    
    return webkit_timestamp

def main():
    # 環境変数の設定チェック
    if not CHROME_HISTORY_PATH or not CHROME_EXE_PATH:
        print("エラー: .env ファイルに CHROME_HISTORY_PATH または CHROME_EXE_PATH が設定されていません。")
        return

    # 1. History ファイルの更新日時（タイムスタンプ）を取得
    if not os.path.exists(CHROME_HISTORY_PATH):
        print(f"エラー: Historyファイルが見つかりません: {CHROME_HISTORY_PATH}")
        return

    mtime = os.path.getmtime(CHROME_HISTORY_PATH)
    current_time = time.time()
    time_diff_seconds = current_time - mtime
    
    print(f"最終更新からの経過時間: {time_diff_seconds:.1f} 秒")

    # 2-1. タイムスタンプの時刻が3分(180秒)以上離れている時
    if time_diff_seconds >= 180:
        print("3分以上更新されていないため、Google Chrome を起動します...")
        
        # Chromeを起動（非同期で実行し、Pythonスクリプトは待機しない）
        try:
            subprocess.Popen([CHROME_EXE_PATH])
        except Exception as e:
            print(f"Chromeの起動に失敗しました: {e}")
            return

        # 2-3 のループ処理
        while True:
            # 2-2. 2分間待機する
            print("2分間待機します...")
            time.sleep(120) 

            # 再度タイムスタンプを確認
            mtime = os.path.getmtime(CHROME_HISTORY_PATH)
            current_time = time.time()
            new_diff = current_time - mtime
            
            print(f"再チェック: 経過時間 {new_diff:.1f} 秒")

            # タイムスタンプが2分(120秒)以内になればループを抜けて 3 へ
            if new_diff <= 120:
                print("Historyファイルが更新されました。処理を続行します。")
                break
            else:
                print("まだ更新されていません。再度待機ループに入ります。")
                # ループ継続 (2-2に戻る)
    else:
        print("Historyファイルは最近(3分以内)更新されています。そのまま続行します。")

    # 3-1. History に対して Select 文を実行
    # ロック回避のためコピーを作成
    try:
        shutil.copy2(CHROME_HISTORY_PATH, TEMP_HISTORY_PATH)
    except IOError as e:
        print(f"ファイルのコピーに失敗しました: {e}")
        return

    results = []
    
    try:
        conn = sqlite3.connect(TEMP_HISTORY_PATH)
        cursor = conn.cursor()

        # 24時間前のタイムスタンプ取得
        cutoff_time = get_webkit_timestamp_24h_ago()

        # 1日以内の URL と タイトルを取得するSQL
        # last_visit_time は WebKit Timestamp 形式
        sql = """
        SELECT url, title, last_visit_time
        FROM urls
        WHERE last_visit_time > ?
        ORDER BY last_visit_time DESC
        """
        
        cursor.execute(sql, (cutoff_time,))
        rows = cursor.fetchall()

        for row in rows:
            # WebKit Timestamp を読みやすい形式に変換
            webkit_time = row[2]
            unix_time = (webkit_time / 1000000) - 11644473600
            dt_obj = datetime.datetime.fromtimestamp(unix_time)
            
            results.append({
                "url": row[0],
                "title": row[1],
                "visit_time": dt_obj.strftime('%Y-%m-%d %H:%M:%S')
            })

    except sqlite3.Error as e:
        print(f"SQLite エラー: {e}")
    finally:
        if conn:
            conn.close()
        # 一時ファイルの削除
        if os.path.exists(TEMP_HISTORY_PATH):
            os.remove(TEMP_HISTORY_PATH)

    # 4. JSON で出力する
    json_output = json.dumps(results, indent=2, ensure_ascii=False)
    
    
    # ファイルに保存する場合
    with open("history_output.json", "w", encoding="utf-8") as f:
        f.write(json_output)
    print("history_output.json に保存しました。")

if __name__ == "__main__":
    main()
