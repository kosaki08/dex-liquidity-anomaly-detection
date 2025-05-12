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

    if st.sidebar.button("異常度を確認"):
        with st.spinner(f"{dt_utc.isoformat()} のデータ取得中…"):
            try:
                feature_list = fetch_features_for_datetime(dt_utc)
                df_pred = fetch_predictions(feature_list)
                # 列名が「0」なので「label」に変更
                df_pred.columns = ["label"]
                # 1 → 正常, -1 → 異常 にマッピング
                df_pred["status"] = df_pred["label"].map({1: "正常", -1: "異常"})

                if not feature_list:
                    st.warning("指定日時のデータが見つかりませんでした。")
                    return
                df_pred = fetch_predictions(feature_list)
            except Exception as e:
                st.error(f"データ取得／予測に失敗しました: {e}")
                return

        if "score" in df_pred.columns:
            st.subheader("判定結果")
            st.write(df_pred[["status"]])
        else:
            st.write("予測結果スコア（-1 → 異常, 1 → 正常）:")
            st.dataframe(df_pred)

    else:
        st.info("異常度を確認」ボタンを押してください")


if __name__ == "__main__":
    main()
