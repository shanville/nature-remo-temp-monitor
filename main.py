"""
main.py
手動デバッグ用に Nature Remo デバイスの最新値を一覧表示するスクリプト。
データ収集が失敗した際の診断チェックとして利用する。
"""

import os
import requests
from dotenv import load_dotenv

from config import DEFAULT_DEVICE_ENDPOINT, REQUEST_TIMEOUT_SECONDS

def main():
    # .envファイルから環境変数を読み込む
    load_dotenv()

    # APIキーを取得
    api_key = os.getenv("NATURE_REMO_API_KEY")

    if not api_key or api_key == "your_api_key_here":
        print("エラー: .envファイルにNATURE_REMO_API_KEYを設定してください")
        return

    # Nature Remo APIのエンドポイント
    url = DEFAULT_DEVICE_ENDPOINT

    # リクエストヘッダー（認証情報を含む）
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        # APIリクエストを送信
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)

        # ステータスコードをチェック
        response.raise_for_status()

        # JSON形式でデータを取得
        devices = response.json()

        # デバイスがない場合
        if not devices:
            print("デバイスが見つかりませんでした")
            return

        # 各デバイスの情報を表示
        print("=== Nature Remo デバイス情報 ===\n")

        for device in devices:
            print(f"デバイス名: {device['name']}")

            # センサーデータを取得
            if 'newest_events' in device:
                events = device['newest_events']

                # 温度
                if 'te' in events:
                    temp = events['te']['val']
                    print(f"  温度: {temp}°C")

                # 湿度
                if 'hu' in events:
                    humidity = events['hu']['val']
                    print(f"  湿度: {humidity}%")

                # 照度
                if 'il' in events:
                    illuminance = events['il']['val']
                    print(f"  照度: {illuminance} lx")

                # 人感センサー
                if 'mo' in events:
                    motion = events['mo']['val']
                    print(f"  人感センサー: {motion}")

            print()  # 空行

    except requests.exceptions.RequestException as e:
        print(f"APIリクエストエラー: {e}")

if __name__ == "__main__":
    main()
