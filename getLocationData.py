"""
Google Maps Places API (New) を使用して、指定された日のタイムラインJSON内の訪問場所情報を更新するスクリプト。
キャッシュ機能を備えており、既に取得した場所情報はCSVファイルに保存され、再利用されます。
"""

import json
import csv
import os
import requests
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- 設定 ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
CACHE_CSV = "placeLocation.csv"

def load_cache(file_path):
    """CSVから場所情報を読み込み辞書形式で返す"""
    cache = {}
    if os.path.exists(file_path):
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cache[row['placeID']] = {
                    'name': row['name'],
                    'address': row['address'],
                    'placeLocation': row['placeLocation']
                }
    return cache

def save_cache(file_path, cache):
    """辞書形式の場所情報をCSVに保存する"""
    with open(file_path, mode='w', encoding='utf-8', newline='') as f:
        fieldnames = ['placeID', 'name', 'address', 'placeLocation']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for pid, info in cache.items():
            writer.writerow({
                'placeID': pid,
                'name': info['name'],
                'address': info['address'],
                'placeLocation': info['placeLocation']
            })

def get_place_details_from_api(place_id, api_key):
    """Places API (New) を叩いて情報を取得する。取得できない場合はNoneを返す"""
    if not api_key:
        print("エラー: APIキーが設定されていません。")
        return None

    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "displayName,formattedAddress,location"
    }
    params = {"languageCode": "ja"}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return None
        
        data = response.json()
        loc = data.get("location", {})
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        location_str = f"geo:{lat},{lng}" if lat and lng else ""

        return {
            "name": data.get("displayName", {}).get("text", "Unknown Name"),
            "address": data.get("formattedAddress", "Unknown Address"),
            "placeLocation": location_str
        }
    except:
        return None

def main():
    # 1. コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="Google Map タイムラインJSON更新スクリプト")
    parser.add_argument("date", nargs="?", help="対象日付 (YYYY-MM-DD)。指定しない場合は昨日が対象になります。")
    args = parser.parse_args()

    # 日付指定がない場合は昨日を対象にする
    if args.date is None:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        print(f"日付が指定されなかったため、昨日 ({target_date}) を対象とします。")
    else:
        target_date = args.date

    input_json = f"filtered_{target_date}.json"
    output_json = f"updated_{target_date}.json"

    if not os.path.exists(input_json):
        print(f"エラー: {input_json} が存在しません。")
        return

    # 2. キャッシュとJSONの読み込み
    cache = load_cache(CACHE_CSV)
    
    with open(input_json, 'r', encoding='utf-8') as f:
        timeline_data = json.load(f)

    updated_count = 0
    skipped_count = 0

    # 3. データの処理
    for entry in timeline_data:
        # 訪問(visit)データ以外はスキップ
        if "visit" not in entry:
            continue
        
        visit_info = entry["visit"]
        top_candidate = visit_info.get("topCandidate", {})
        place_id = top_candidate.get("placeID")

        # placeIDがない場合は不明な場所としてスキップ
        if not place_id:
            skipped_count += 1
            continue

        # キャッシュ確認またはAPI取得
        if place_id in cache:
            info = cache[place_id]
        else:
            print(f"新規PlaceIDを照会中: {place_id}")
            info = get_place_details_from_api(place_id, API_KEY)
            
            if info:
                cache[place_id] = info
            else:
                # APIでも取得できなかった場合はスキップ
                print(f"場所を特定できませんでした。スキップします: {place_id}")
                skipped_count += 1
                continue

        # JSON情報を更新
        top_candidate["name"] = info["name"]
        top_candidate["formatted_address"] = info["address"]
        top_candidate["placeLocation"] = info["placeLocation"]
        updated_count += 1

    # 4. 保存
    save_cache(CACHE_CSV, cache)
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(timeline_data, f, ensure_ascii=False, indent=2)

    print(f"\n--- 完了 ({target_date}) ---")
    print(f"成功: {updated_count} 件")
    print(f"スキップ（不明な場所）: {skipped_count} 件")

if __name__ == "__main__":
    main()
