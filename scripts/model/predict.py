import os
from typing import Any, Dict, Optional

import pandas as pd
from bentoml import models as bentoml_models
from bentoml import sklearn
from bentoml._internal.runner import Runner
from bentoml.exceptions import NotFound
from snowflake.connector import connect

_MODEL_NAME = "pool_iforest"
_STAGE = "production" 
_RUNNER: Optional[Runner] = None  # 遅延ロード＆キャッシュ

def _prep_features(df: pd.DataFrame) -> pd.DataFrame:
    # 列名をすべて小文字へ
    df.columns = df.columns.str.lower()
    # 不要列を除外
    return df.drop(columns=["dex", "pool_id", "hour_ts", "y"], errors="ignore")


def _latest_tag_by_stage(name: str, stage: str) -> str:
    """labels.stage == stage で最新の Bento を返す"""
    candidates = [
        m for m in bentoml_models.list(name)
        if m.info.labels.get("stage") == stage.lower()
    ]
    if not candidates:
        raise NotFound(f"{name} の stage={stage} が BentoML Store に見つかりません")
    # creation_time は datetime なので最大値＝最新
    return str(max(candidates, key=lambda m: m.creation_time).tag)

def _resolve_tag(model_name: str, stage: str) -> str:
    try:
        return _latest_tag_by_stage(model_name, stage)
    except NotFound:
        # 足りなければ自動インポート
        from scripts.model.import_iforest_from_mlflow import import_iforest
        import_iforest(stage)
        return _latest_tag_by_stage(model_name, stage)


def _get_runner(model_tag: str, *, dev: bool = False) -> Runner:
    runner = sklearn.get(model_tag).to_runner()
    global _RUNNER
    if _RUNNER is None or _RUNNER.tag != model_tag:
        _RUNNER = runner
        _RUNNER.init_local() 
    return _RUNNER


# ---- Airflow PythonOperator 用コールバック -------------------------------


def load_latest_model_from_registry(
    model_name: str = _MODEL_NAME,
    stage: str = _STAGE,
) -> None:
    """Registry から最新モデルを取得してローカルにキャッシュ"""
    tag = _resolve_tag(model_name, stage)
    _get_runner(tag, dev=True)  


def _fetch_latest_row_from_snowflake() -> pd.DataFrame:
    """
    Snowflake から最新 1 行のプール特徴量を取得して DataFrame で返します
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
    df = pd.read_sql(
        """
        SELECT *
          FROM DEX_RAW.RAW.MART_POOL_FEATURES_LABELED
         ORDER BY hour_ts DESC
         LIMIT 1
        """,
        conn,
    )
    conn.close()
    return df


def score_latest_row(
    threshold: float,
    model_name: str = _MODEL_NAME,
    stage: str = _STAGE,
) -> Dict[str, Any]:
    """最新のデータを取得して IsolationForest で予測します"""
    tag = _resolve_tag(model_name, stage)
    runner = _get_runner(tag)           # 本番は dev=False 
    df = _fetch_latest_row_from_snowflake()
    X = _prep_features(df)
    score_val = float(-runner.run(X)[0])  # -score_samples: 大きいほど異常
    return {
        "pool_id": df["pool_id"].iloc[0],
        "score": score_val,
        "is_anomaly": score_val >= threshold,
    }
