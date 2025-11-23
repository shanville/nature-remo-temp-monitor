"""
Nature Remo 温度モニタリング ダッシュボード
Streamlitで温度データを可視化
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import libsql_experimental as libsql

# ページ設定
st.set_page_config(
    page_title="温度モニター",
    page_icon="🌡️",
    layout="wide"
)

# タイトル
st.title("🌡️ Nature Remo 温度モニター")

# Turso接続情報を取得
database_url = st.secrets.get("TURSO_DATABASE_URL") or os.getenv("TURSO_DATABASE_URL")
auth_token = st.secrets.get("TURSO_AUTH_TOKEN") or os.getenv("TURSO_AUTH_TOKEN")

if not database_url or not auth_token:
    st.error("⚠️ データベース接続情報が設定されていません")
    st.stop()

@st.cache_data(ttl=60)  # 1分間キャッシュ
def load_data():
    """Tursoからデータを取得"""
    try:
        conn = libsql.connect(database_url, auth_token=auth_token)
        cursor = conn.cursor()

        # 全データを取得
        cursor.execute("""
            SELECT timestamp, device_name, temperature
            FROM temperature_logs
            ORDER BY timestamp DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return None

        # DataFrameに変換
        df = pd.DataFrame(rows, columns=['timestamp', 'device_name', 'temperature'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        return df

    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return None

# データ読み込み
df = load_data()

if df is None or len(df) == 0:
    st.warning("📭 データがまだありません。GitHub Actionsが動作するまでお待ちください。")
    st.stop()

# 最新データ
latest = df.iloc[0]
current_temp = latest['temperature']
device_name = latest['device_name']
last_updated = latest['timestamp']

# 統計情報
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="現在の温度",
        value=f"{current_temp}°C",
        delta=None
    )

with col2:
    max_temp = df['temperature'].max()
    st.metric(
        label="最高温度",
        value=f"{max_temp}°C"
    )

with col3:
    min_temp = df['temperature'].min()
    st.metric(
        label="最低温度",
        value=f"{min_temp}°C"
    )

with col4:
    avg_temp = df['temperature'].mean()
    st.metric(
        label="平均温度",
        value=f"{avg_temp:.1f}°C"
    )

st.caption(f"📍 {device_name} | 最終更新: {last_updated.strftime('%Y-%m-%d %H:%M:%S')}")

# 期間選択
st.subheader("📊 温度推移グラフ")

period = st.selectbox(
    "表示期間",
    ["全期間", "過去24時間", "過去12時間", "過去6時間", "過去1時間"],
    index=0
)

# 期間でフィルタリング
if period != "全期間":
    now = datetime.now(timezone.utc)
    hours_map = {
        "過去1時間": 1,
        "過去6時間": 6,
        "過去12時間": 12,
        "過去24時間": 24
    }
    hours = hours_map[period]
    cutoff = now - timedelta(hours=hours)
    df_filtered = df[df['timestamp'] >= cutoff]
else:
    df_filtered = df

# グラフ作成
if len(df_filtered) > 0:
    fig = px.line(
        df_filtered.sort_values('timestamp'),
        x='timestamp',
        y='temperature',
        title=f"温度の推移 ({period})",
        labels={'timestamp': '時刻', 'temperature': '温度 (°C)'}
    )

    # グラフのスタイル調整
    fig.update_traces(
        line_color='#FF6B6B',
        line_width=2
    )

    fig.update_layout(
        hovermode='x unified',
        xaxis_title="時刻",
        yaxis_title="温度 (°C)",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(f"選択した期間({period})にデータがありません")

# データテーブル
with st.expander("📋 データ詳細"):
    st.dataframe(
        df_filtered[['timestamp', 'temperature']].sort_values('timestamp', ascending=False),
        use_container_width=True,
        hide_index=True
    )

# サイドバー - 統計情報
st.sidebar.header("📈 統計情報")
st.sidebar.metric("データ件数", len(df))
st.sidebar.metric("記録開始", df['timestamp'].min().strftime('%Y-%m-%d %H:%M'))

# 再読み込みボタン
if st.sidebar.button("🔄 データを再読み込み"):
    st.cache_data.clear()
    st.rerun()
