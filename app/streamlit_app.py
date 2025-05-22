import logging
import os
import sys
from datetime import datetime, time, timezone
from typing import Final

import pandas as pd
import requests
import streamlit as st
from snowflake.connector import connect

logger: Final = logging.getLogger(__name__)

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


# BentoML predict エンドポイント
API_URL = os.getenv("BENTO_API_URL")


def get_snowflake_connection():
    """環境変数を使用してSnowflake接続を作成します。"""
    return connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


@st.cache_data(ttl=300)
def fetch_features_for_datetime(data: datetime) -> list[dict]:
    """Snowflake から指定日時直前最新のプール特徴量を1件取得して返します"""
    logger.info(
        "fetch_features_for_datetime: fetch Snowflake features at %r",
        data,
    )
    with get_snowflake_connection() as conn:
        # hour_ts を厳密一致ではなく <= dt の最新レコードを取る
        query = """
            SELECT
              tvl_usd, volume_usd, liquidity, vol_rate_24h, tvl_rate_24h, vol_ma_6h, vol_ma_24h, vol_tvl_ratio
            FROM DEX_RAW.RAW.MART_POOL_FEATURES_LABELED
            WHERE hour_ts <= %s
            ORDER BY hour_ts DESC
            LIMIT 1
        """
        df = pd.read_sql(query, conn, params=[data])
    # DataFrame → dict に変換
    return df.to_dict(orient="records")


def fetch_predictions(data: list[dict]) -> pd.DataFrame:
    """BentoML predict エンドポイントを叩いて結果を DataFrame で返します"""
    # データを "input_data" キーでラップ
    payload = {"input_data": data}

    # デバッグ用
    st.write("=== payload ===")
    st.json(payload)
    logger.info("POST %s payload=%s", API_URL, payload)
    try:
        res = requests.post(API_URL, json=payload, timeout=10)
        st.write("status:", res.status_code)
        st.text(res.text)
        logger.info(
            "API response status=%d body=%s",
            res.status_code,
            res.text[:200],
        )

        # レスポンスを確認
        res.raise_for_status()
        preds = res.json()

        # レスポンスを DataFrame に変換
        return pd.DataFrame(preds, columns=["label"])
    except Exception as e:
        logger.error("prediction failed: %s", e, exc_info=True)
        st.error(f"データ取得 / 予測に失敗しました: {e}")
        return pd.DataFrame()


def main():
    st.title("DEX Volume Spike Dashboard")

    if not API_URL:
        st.error("BENTO_API_URL が見つかりません。 .env または secrets.toml を確認してください。")
        st.stop()

    # デバッグ用
    st.write("🍵 BENTO_API_URL =", os.getenv("BENTO_API_URL"))

    # サイドバーで日時選択
    st.sidebar.header("日時で検索")
    selected_date = st.sidebar.date_input("日付を選択", datetime.now().date())
    selected_time = st.sidebar.time_input("時刻を選択", time(hour=datetime.now().hour))

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
        st.info("「異常度を確認」ボタンを押してください")


if __name__ == "__main__":
    main()
