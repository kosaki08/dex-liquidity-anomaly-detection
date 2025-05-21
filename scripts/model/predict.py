import os
from typing import Any, Dict

import bentoml
import pandas as pd
from snowflake.connector import connect

# モデル名とステージ（環境）を指定
_MODEL_NAME: str = "pool_iforest"
_STAGE: str = "Production"

# BentoML から最新モデルを取得して Runner 化
# モジュールロード時に一度だけ実行し、以降はキャッシュ
_RUNNER = bentoml.sklearn.get(f"{_MODEL_NAME}:{_STAGE}").to_runner()
_RUNNER.init_local()  # Runner プロセス起動


def load_latest_model_from_registry(model_name: str = _MODEL_NAME, stage: str = _STAGE) -> None:
    """Registry から最新モデルを取得してローカルにキャッシュ"""
    bentoml.sklearn.get(f"{model_name}:{stage}")

def _fetch_latest_row_from_snowflake() -> pd.DataFrame:
    """
    Snowflake から最新 1 行のプール特徴量を取得して DataFrame で返す。
    """
    conn = connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )

    query = """
        SELECT *
        FROM DEX_RAW.RAW.MART_POOL_FEATURES_LABELED
        ORDER BY hour_ts DESC
        LIMIT 1
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def score_latest_row(
    threshold: float,
    model_name: str = _MODEL_NAME,
    stage: str = _STAGE,
) -> Dict[str, Any]:
    """最新のデータを取得して IsolationForest で予測"""
    # Snowflake から最新 1 行を取得
    runner = _RUNNER
    if model_name != _MODEL_NAME or stage != _STAGE:
        runner = bentoml.sklearn.get(f"{model_name}:{stage}").to_runner()
        runner.init_local()

    df = _fetch_latest_row_from_snowflake()

    # モデル入力用の特徴量のみ抽出
    X = df.drop(columns=["dex", "pool_id", "hour_ts", "y"], errors="ignore")

    # IsolationForest では score_samples() が異常スコア（値が大きいほど異常）
    scores = runner.run(X) 
    score = float(-scores[0])  # -score_samples: 大きいほど異常

    return {
        "pool_id": df["pool_id"].iloc[0],
        "score": score,
        "is_anomaly": score >= threshold,
    }
