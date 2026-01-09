import argparse
import json
import os
from datetime import datetime, time, timedelta, timezone
from dotenv import load_dotenv

# 日本時間 (UTC+9) を定義
JST = timezone(timedelta(hours=9), 'JST')

def parse_dt(s: str) -> datetime:
    """ISO8601文字列を datetime(JST) に変換"""
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    return dt.astimezone(JST)

def overlaps(start: datetime, end: datetime, win_start: datetime, win_end: datetime) -> bool:
    """期間が重複しているか判定"""
    return start < win_end and end > win_start

def main():
    # .env ファイルをロード
    load_dotenv(dotenv_path=".env")

    # 環境変数からファイルパスを取得
    input_path = os.getenv("LOCATION_HISTORY_PATH")

    # OS環境変数が設定されている場合は展開した値に上書きする。
    if input_path:
        input_path = os.path.expandvars(input_path)

    if not input_path:
        print("エラー: 環境変数 'LOCATION_HISTORY_PATH' が設定されていません。")
        print(".env ファイルを確認してください。")
        return

    # コマンドライン引数の設定 (日付のみ必須)
    ap = argparse.ArgumentParser(description="Google Maps Timeline JSONから特定日(JST)を抽出 (.env対応版)")
    ap.add_argument("day", help="抽出したい日 (YYYY-MM-DD)")
    ap.add_argument("-o", "--output", default=None, help="出力ファイル名 (省略可)")
    args = ap.parse_args()

    # 日付範囲の定義 (JST)
    try:
        target_date = datetime.strptime(args.day, "%Y-%m-%d").date()
    except ValueError:
        print("エラー: 日付の形式が正しくありません。YYYY-MM-DD で指定してください。")
        return

    day_start = datetime.combine(target_date, time.min).replace(tzinfo=JST)
    day_end = day_start + timedelta(days=1)

    print(f"読み込みファイル: {input_path}")
    print(f"抽出対象日:       {args.day} (JST)")

    # JSON読み込み
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            items = json.load(f)
    except FileNotFoundError:
        print("エラー: 指定されたJSONファイルが見つかりません。パスを確認してください。")
        return
    except json.JSONDecodeError:
        print("エラー: JSONファイルの形式が不正です。")
        return

    # 抽出処理
    picked = []
    for it in items:
        if "startTime" not in it or "endTime" not in it:
            continue
            
        st = parse_dt(it["startTime"])
        en = parse_dt(it["endTime"])
        
        if overlaps(st, en, day_start, day_end):
            picked.append(it)

    # 保存処理
    out_path = args.output or f"filtered_{args.day}.json"
    
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(picked, f, ensure_ascii=False, indent=2)
            
        print("-" * 30)
        print(f"元データ件数: {len(items)}")
        print(f"抽出件数:     {len(picked)}")
        print(f"保存完了:     {out_path}")
        
    except IOError as e:
        print(f"エラー: ファイルの書き込みに失敗しました。\n{e}")

if __name__ == "__main__":
    main()
