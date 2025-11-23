"""
Nature Remo 温度モニタリング ダッシュボード
Streamlitで温度データを可視化
"""

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import libsql_experimental as libsql

# ページ設定
st.set_page_config(
    page_title="温度モニター",
    page_icon="🌡️",
    layout="centered",  # スマホ対応のためcentered
    initial_sidebar_state="collapsed"  # 初期状態でサイドバーを閉じる
)

# カスタムCSS - モダン&ミニマル&スマホ対応
st.markdown("""
<style>
    /* メインコンテナ */
    .main {
        padding-top: 2rem;
    }

    /* タイトル */
    h1 {
        font-size: 2rem !important;
        font-weight: 700 !important;
        margin-bottom: 1.5rem !important;
    }

    /* メトリックカード */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem;
        font-weight: 700;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.875rem;
        opacity: 0.7;
    }

    /* グラフコンテナ */
    .plot-container {
        border-radius: 12px;
        overflow: hidden;
    }

    /* セレクトボックス */
    .stSelectbox {
        margin-bottom: 1.5rem;
    }

    /* キャプション */
    .stCaption {
        text-align: center;
        opacity: 0.6;
        margin-top: 0.5rem;
    }

    /* ボタン */
    .stButton button {
        width: 100%;
        border-radius: 8px;
        font-weight: 500;
    }

    /* スマホ対応 */
    @media (max-width: 768px) {
        h1 {
            font-size: 1.75rem !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 2rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# タイトル
st.markdown("# 🌡️ 温度モニター")

# Turso接続情報を取得
database_url = st.secrets.get("TURSO_DATABASE_URL") or os.getenv("TURSO_DATABASE_URL")
auth_token = st.secrets.get("TURSO_AUTH_TOKEN") or os.getenv("TURSO_AUTH_TOKEN")

if not database_url or not auth_token:
    st.error("⚠️ データベース接続情報が設定されていません")
    st.stop()

@st.cache_data(ttl=60)
def load_data():
    """Tursoからデータを取得"""
    try:
        conn = libsql.connect(database_url, auth_token=auth_token)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT timestamp, device_name, temperature
            FROM temperature_logs
            ORDER BY timestamp DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return None

        df = pd.DataFrame(rows, columns=['timestamp', 'device_name', 'temperature'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        # 日本時間（JST）に変換
        df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Tokyo')

        return df

    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return None

# データ読み込み
df = load_data()

if df is None or len(df) == 0:
    st.info("📭 データ収集中...")
    st.caption("5分ごとに自動でデータが追加されます")
    st.stop()

# 最新データ
latest = df.iloc[0]
current_temp = latest['temperature']
device_name = latest['device_name']
last_updated = latest['timestamp']

# 現在の温度（大きく表示）
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.metric(
        label="現在の温度",
        value=f"{current_temp}°C"
    )

st.caption(f"📍 {device_name}")
st.caption(f"🕐 {last_updated.strftime('%m/%d %H:%M')} 更新 (JST)")

st.divider()

# 統計情報（コンパクト）
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="最高",
        value=f"{df['temperature'].max()}°C"
    )

with col2:
    st.metric(
        label="最低",
        value=f"{df['temperature'].min()}°C"
    )

with col3:
    st.metric(
        label="平均",
        value=f"{df['temperature'].mean():.1f}°C"
    )

st.divider()

# 期間選択（よりシンプルに）
period = st.selectbox(
    "表示期間",
    ["過去24時間", "過去12時間", "過去6時間", "全期間"],
    index=0,
    label_visibility="collapsed"
)

# 期間でフィルタリング
if period != "全期間":
    # 日本時間で現在時刻を取得
    import pytz
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)

    hours_map = {
        "過去6時間": 6,
        "過去12時間": 12,
        "過去24時間": 24
    }
    hours = hours_map[period]
    cutoff = now - timedelta(hours=hours)
    df_filtered = df[df['timestamp'] >= cutoff]
else:
    df_filtered = df

# グラフ作成（ミニマルデザイン）
if len(df_filtered) > 0:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_filtered.sort_values('timestamp')['timestamp'],
        y=df_filtered.sort_values('timestamp')['temperature'],
        mode='lines',
        line=dict(
            color='#FF6B6B',
            width=3,
            shape='spline'  # スムーズな曲線
        ),
        fill='tozeroy',
        fillcolor='rgba(255, 107, 107, 0.1)',
        hovertemplate='<b>%{y}°C</b><br>%{x|%m/%d %H:%M}<extra></extra>'
    ))

    fig.update_layout(
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            showgrid=False,
            showline=False,
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(128,128,128,0.1)',
            showline=False,
            zeroline=False,
        ),
        hovermode='x unified',
        height=350,
        font=dict(size=12)
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("この期間にデータがありません")

# フッター
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.caption(f"📊 {len(df)}件のデータ")

with col2:
    if st.button("🔄", help="データを再読み込み"):
        st.cache_data.clear()
        st.rerun()
