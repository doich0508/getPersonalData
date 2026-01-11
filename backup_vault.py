"""
Obsidian Vault のバックアップを作成するスクリプト
"""

import os
import shutil
import datetime
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

try:
    BACKUP_GENERATIONS = int(os.getenv("BACKUP_GENERATIONS", "5"))
except ValueError:
    BACKUP_GENERATIONS = 5
    print("警告: BACKUP_GENERATIONS の設定が不正です。デフォルト値(5)を使用します。")

# --- 関数定義 ---

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

def create_backup():
    """Vault のバックアップを作成"""
    print("Vaultをバックアップ中...")

    if not BACKUP_DIR.exists():
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"警告: バックアップルートフォルダの作成に失敗しました。バックアップをスキップします。\n理由: {e}")
            return False

    if BACKUP_DIR.exists():
        backup_folder_name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        target_backup_path = BACKUP_DIR / backup_folder_name

        try:
            shutil.copytree(VAULT_PATH, target_backup_path)
            print(f"バックアップ完了: {target_backup_path}")
            rotate_backups(BACKUP_DIR, BACKUP_GENERATIONS)
            return True
        except Exception as e:
            print(f"警告: バックアップ処理中にエラーが発生しました。バックアップをスキップして続行します。\n理由: {e}")
            return False

if __name__ == "__main__":
    create_backup()