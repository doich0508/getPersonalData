# PersonlDataExport

## やりたいこと

### Google Chrome 閲覧履歴取得

Chrome の History からその日閲覧したページの履歴を取得する。

### Google Map 移動データ取得

#### exportDailyLocation.py

- 日次でエクスポートされた移動履歴データからその日分のデータを抽出して JSON で出力する。

#### getLocationData.py 

- exportDailyLocation.py で 出力された JSON データを解析して、場所の履歴を取得する。

### Spotify 聴取データ取得


### Fitbit 健康データ取得


### Youtube 閲覧履歴取得


### 各種 LLM プロンプト取得


### Obsidian Export 機能

- exportDailyNote.py
- 取得したデータを Obsidian のデイリーノートに張り付ける
  - 必要に応じて、プロパティに追加する。

## アーキテクチャ

- 毎日午前0時03分に実行を開始する。
  - exportDailyLocation.py → getLocationData.py
  - getChromeHistory.py
  - すべてが終わった後に、exportDailyNote.py を実行する。
