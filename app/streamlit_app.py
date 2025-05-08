import os
from datetime import datetime, time, timezone

import pandas as pd
import requests
import streamlit as st
from snowflake.connector import connect

# BentoML predict エンドポイント
API_URL = os.getenv("BENTO_API_URL", "http://bento:3000/predict")


@st.cache_data(ttl=300)
def fetch_features_for_datetime(dt: datetime) -> list[dict]:
    """選択された日時の直前最新レコードを Snowflake から取得し、dict のリストにして返す"""
    conn = connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )
    # hour_ts を厳密一致ではなく <= dt の最新レコードを取る
    query = """
        SELECT
          tvl_usd, volume_usd, liquidity, vol_rate_24h, tvl_rate_24h, vol_ma_6h, vol_ma_24h, vol_tvl_ratio 
        FROM DEX_RAW.RAW.MART_POOL_FEATURES_LABELED
        WHERE hour_ts <= %s
        ORDER BY hour_ts DESC
        LIMIT 1
    """
    df = pd.read_sql(query, conn, params=[dt])
    conn.close()
    # DataFrame → dict に変換
    return df.to_dict(orient="records")


@st.cache_data(ttl=300)
def fetch_predictions(data: list[dict]) -> pd.DataFrame:
    # データを "input_data" キーでラップ
    payload = {"input_data": data}
    resp = requests.post(API_URL, json=payload, timeout=10)

    # レスポンスを確認
    resp.raise_for_status()
    results = resp.json()

    # レスポンスをDataFrameに変換
    return pd.DataFrame(results)


def main():
    st.title("DEX Volume Spike Dashboard")

    # サイドバーで日時選択
    st.sidebar.header("日時で検索")
    selected_date = st.sidebar.date_input("日付を選択", datetime.now().date())
    selected_time = st.sidebar.time_input("時刻を選択", time(hour=datetime.now().hour))
    # Combine into timezone-aware UTC
    dt_local = datetime.combine(selected_date, selected_time)
    dt_utc = dt_local.astimezone(timezone.utc)

    threshold = st.sidebar.slider("スコア閾値", 0.1, 1.0, 0.8, 0.01)

    if st.sidebar.button("予測を取得"):
        with st.spinner(f"{dt_utc.isoformat()} のデータ取得中…"):
            try:
                feature_list = fetch_features_for_datetime(dt_utc)
                if not feature_list:
                    st.warning("指定日時のデータが見つかりませんでした。")
                    return
                df_pred = fetch_predictions(feature_list)
            except Exception as e:
                st.error(f"データ取得／予測に失敗しました: {e}")
                return

        if "score" in df_pred.columns:
            df_filtered = df_pred[df_pred["score"] >= threshold]
            st.write(f"閾値 {threshold} 以上: {len(df_filtered)} 件")
            st.dataframe(df_filtered.sort_values("score", ascending=False))
        else:
            st.write("予測結果スコア:")
            st.dataframe(df_pred)

    else:
        st.info("「予測を取得」ボタンを押してください")


if __name__ == "__main__":
    main()
