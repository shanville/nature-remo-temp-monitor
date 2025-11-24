"""
collect_data.py
Nature Remoの最新温度を取得しTursoへ永続化するCI用スクリプト。
コードの責務をAPI取得とDB保存に分けてテストしやすくしている。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional, Protocol

import requests
import libsql_experimental as libsql
from dotenv import load_dotenv

from config import (
    DEFAULT_DEVICE_ENDPOINT,
    DEFAULT_TABLE_NAME,
    REQUEST_TIMEOUT_SECONDS,
    EnvConfig,
    load_env_config,
)

# .envファイルを読み込む（ローカル実行時のみ）
load_dotenv()


class CursorLike(Protocol):
    """libsqlカーソルが備えるメソッドの最小限セット"""

    def execute(self, query: str, params: tuple | None = None) -> None: ...

    def fetchone(self) -> tuple: ...


class ConnectionLike(Protocol):
    """libsql接続が備えるメソッドの最小限セット"""

    def cursor(self) -> CursorLike: ...

    def commit(self) -> None: ...

    def close(self) -> None: ...


def fetch_latest_temperature(
    api_key: str,
    *,
    endpoint: str = DEFAULT_DEVICE_ENDPOINT,
    session: Optional[requests.Session] = None,
) -> tuple[str, float]:
    """Nature Remo APIから温度データを取得"""

    if not api_key:
        raise ValueError("NATURE_REMO_API_KEY が設定されていません")

    client = session or requests.Session()
    headers = {"Authorization": f"Bearer {api_key}"}

    response = client.get(endpoint, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    devices = response.json()

    if not devices:
        raise ValueError("デバイスが見つかりませんでした")

    # 最初のデバイスから温度を取得
    device = devices[0]
    device_name = device["name"]
    events = device.get("newest_events", {})

    if "te" not in events:
        raise ValueError("温度データが見つかりませんでした")

    temperature = events["te"]["val"]
    return device_name, temperature


def _ensure_table(cursor, table_name: str) -> None:
    """テーブルが存在しない場合は作成"""

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            device_name TEXT NOT NULL,
            temperature REAL NOT NULL
        )
        """
    )


def save_to_turso(
    device_name: str,
    temperature: float,
    *,
    env: EnvConfig,
    table_name: str = DEFAULT_TABLE_NAME,
    connect: Callable[..., ConnectionLike] = libsql.connect,
) -> str:
    """Tursoデータベースに温度データを保存"""

    conn = connect(env.turso_database_url, auth_token=env.turso_auth_token)
    cursor = conn.cursor()

    _ensure_table(cursor, table_name)

    timestamp = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        f"INSERT INTO {table_name} (timestamp, device_name, temperature) VALUES (?, ?, ?)",
        (timestamp, device_name, temperature),
    )

    conn.commit()

    cursor.execute(
        f"SELECT COUNT(*) FROM {table_name} WHERE timestamp = ?",
        (timestamp,),
    )
    count = cursor.fetchone()[0]

    print(
        f"✓ データを保存しました: {timestamp} | {device_name} | {temperature}°C (確認: {count}件)"
    )

    conn.close()
    return timestamp


def collect_once(
    *,
    endpoint: str = DEFAULT_DEVICE_ENDPOINT,
    session: Optional[requests.Session] = None,
    connect: Callable[..., ConnectionLike] = libsql.connect,
) -> None:
    """温度取得から保存までを1回分まとめて実行"""

    env = load_env_config()
    device_name, temperature = fetch_latest_temperature(
        env.nature_remo_api_key, endpoint=endpoint, session=session
    )
    print(f"温度取得: {device_name} = {temperature}°C")
    save_to_turso(
        device_name,
        temperature,
        env=env,
        table_name=DEFAULT_TABLE_NAME,
        connect=connect,
    )


def main():
    try:
        collect_once()
    except Exception as exc:  # noqa: BLE001 - 失敗を確実にCIへ伝える
        print(f"エラー: {exc}")
        raise


if __name__ == "__main__":
    main()
