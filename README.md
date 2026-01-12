# PersonlDataExport

## 実装したもの

### Google Chrome 閲覧履歴取得

Chrome の History からその日閲覧したページの履歴を取得する。

### Google Map 移動データ取得

#### exportDailyLocation.py

- 日次でエクスポートされた移動履歴データからその日分のデータを抽出して JSON で出力する。

#### getLocationData.py 

- exportDailyLocation.py で 出力された JSON データを解析して、場所の履歴を取得する。

### Obsidian Export 機能

- exportDailyNote.py
- 取得したデータを Obsidian のデイリーノートに張り付ける
  - 必要に応じて、プロパティに追加する。


### 気象情報書き込み機能

- update_weather.py
  - 指定されたデイリーノート内のプロパティに天気情報を追記する。
  - 場所については、.env 内の `DEFAULT_LAT`, `DEFAULT_LON` にて指定。

### Vault のバックアップ

- backup_vault.py
  - .env で指定したフォルダに Obsidian の Vault 全体をバックアップした。

## 今後実装したいもの

### Google カレンダー履歴取得


### Spotify 聴取データ取得


### Fitbit 健康データ取得


### Youtube 閲覧履歴取得


### 各種 LLM プロンプト取得


### GitHub のコミット量取得


## アーキテクチャ

- 毎日午前0時03分に実行を開始する。
  - exportDailyLocation.py → getLocationData.py
  - getChromeHistory.py
  - すべてが終わった後に、exportDailyNote.py を実行する。

## 実行方法

```powershell
powershell.exe -Command "uv run main.py"
```

## 環境構築手順

### 前提条件

- Windows 11 を使用
- 環境上に uv 未インストール
- git for windows はインストール済み

### 手順

1. 以下のコマンドを実行して uv をインストールする。
   - `irm https://astral.sh/uv/install.ps1 | iex`
2. 以下のコマンドを実行して、git clone する。
   - `git clone https://github.com/doich0508/getPersonalData`
3. 以下のコマンドを実行して uv を初期化する。
   - `uv sync`


