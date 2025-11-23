"""
Nature Remo APIから温度データを取得してTursoに保存するスクリプト
GitHub Actionsで定期実行される
"""

import os
import requests
from datetime import datetime, timezone
import libsql_experimental as libsql
from dotenv import load_dotenv

# .envファイルを読み込む（ローカル実行時のみ）
load_dotenv()

def get_temperature():
    """Nature Remo APIから温度データを取得"""
    api_key = os.getenv("NATURE_REMO_API_KEY")

    if not api_key:
        raise ValueError("NATURE_REMO_API_KEY が設定されていません")

    url = "https://api.nature.global/1/devices"
    headers = {"Authorization": f"Bearer {api_key}"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    devices = response.json()

    if not devices:
        raise ValueError("デバイスが見つかりませんでした")

    # 最初のデバイスから温度を取得
    device = devices[0]
    device_name = device['name']

    if 'newest_events' in device and 'te' in device['newest_events']:
        temperature = device['newest_events']['te']['val']
        return device_name, temperature
    else:
        raise ValueError("温度データが見つかりませんでした")

def save_to_turso(device_name, temperature):
    """Tursoデータベースに温度データを保存"""
    database_url = os.getenv("TURSO_DATABASE_URL")
    auth_token = os.getenv("TURSO_AUTH_TOKEN")

    if not database_url or not auth_token:
        raise ValueError("Tursoの接続情報が設定されていません")

    # Tursoクライアントを作成
    conn = libsql.connect(database_url, auth_token=auth_token)
    cursor = conn.cursor()

    # テーブルが存在しない場合は作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temperature_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            device_name TEXT NOT NULL,
            temperature REAL NOT NULL
        )
    """)

    # データを挿入
    timestamp = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        "INSERT INTO temperature_logs (timestamp, device_name, temperature) VALUES (?, ?, ?)",
        (timestamp, device_name, temperature)
    )

    conn.commit()

    # データが正しく挿入されたか確認
    cursor.execute("SELECT COUNT(*) FROM temperature_logs WHERE timestamp = ?", (timestamp,))
    count = cursor.fetchone()[0]

    print(f"✓ データを保存しました: {timestamp} | {device_name} | {temperature}°C (確認: {count}件)")

    # クライアントをクローズ
    conn.close()

def main():
    try:
        # 温度データを取得
        device_name, temperature = get_temperature()
        print(f"温度取得: {device_name} = {temperature}°C")

        # Tursoに保存
        save_to_turso(device_name, temperature)

    except Exception as e:
        print(f"エラー: {e}")
        raise

if __name__ == "__main__":
    main()
