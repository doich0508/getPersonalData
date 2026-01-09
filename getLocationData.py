import json
import csv
import os
import requests
import argparse
from dotenv import load_dotenv

# --- 設定 ---
# .env ファイルから環境変数を読み込む
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
    """辞書形式の場所情報をCSVに保存する（placeLocationカラムを追加）"""
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
    """Places API (New) を叩いて名前、住所、緯度経度を取得する"""
    if not api_key:
        print("エラー: APIキーが設定されていません。.envファイルを確認してください。")
        return None

    print(f"API実行中: {place_id}")
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "displayName,formattedAddress,location"
    }
    params = {"languageCode": "ja"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
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
    except Exception as e:
        print(f"APIエラー ({place_id}): {e}")
        return None

def main():
    # 1. コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="Google Map タイムラインJSONに場所名を追加します。")
    parser.add_argument("date", help="対象日付を YYYY-MM-DD 形式で入力してください (例: 2026-01-08)")
    args = parser.parse_args()

    target_date = args.date
    input_json = f"filtered_{target_date}.json"
    output_json = f"updated_{target_date}.json"

    # 入力ファイルの存在確認
    if not os.path.exists(input_json):
        print(f"エラー: 入力ファイル {input_json} が見つかりません。")
        return

    # 2. キャッシュとJSONの読み込み
    cache = load_cache(CACHE_CSV)
    with open(input_json, 'r', encoding='utf-8') as f:
        timeline_data = json.load(f)

    updated_count = 0

    # 3. データの処理
    for entry in timeline_data:
        if "visit" in entry:
            visit_info = entry["visit"]
            top_candidate = visit_info.get("topCandidate", {})
            place_id = top_candidate.get("placeID")

            if place_id:
                if place_id in cache:
                    info = cache[place_id]
                else:
                    info = get_place_details_from_api(place_id, API_KEY)
                    if info:
                        cache[place_id] = info 
                    else:
                        continue

                top_candidate["name"] = info["name"]
                top_candidate["formatted_address"] = info["address"]
                top_candidate["placeLocation"] = info["placeLocation"]
                updated_count += 1

    # 4. 成果物の保存
    save_cache(CACHE_CSV, cache)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(timeline_data, f, ensure_ascii=False, indent=2)

    print(f"\n--- 処理完了 ---")
    print(f"対象ファイル: {input_json}")
    print(f"更新件数    : {updated_count} 件")
    print(f"保存先      : {output_json}")

if __name__ == "__main__":
    main()
