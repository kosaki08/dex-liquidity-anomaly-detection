"""pool_iforest 推論ユーティリティ  (mid-level 品質版)"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, Final, Optional

import pandas as pd
from bentoml import models as bentoml_models
from bentoml import sklearn
from bentoml._internal.runner import Runner
from bentoml.exceptions import NotFound
from snowflake.connector import connect

from config.snowflake import SnowflakeConfig

# ---------- 設定 & ロギング ----------
logger: Final = logging.getLogger(__name__)

MODEL_NAME = "pool_iforest"
STAGE = "production"
FEATURE_TABLE = "DEX_RAW.RAW.MART_POOL_FEATURES_LABELED"

# ---------- BentoML Runner 取得 ----------
def _latest_tag_by_stage(name: str, stage: str) -> str:
    """labels.stage == stage の最新 Bento モデルタグを返す."""
    candidates = [
        m for m in bentoml_models.list(name) if m.info.labels.get("stage") == stage.lower()
    ]
    if not candidates:
        raise NotFound(f"{name} (stage={stage}) が BentoML Store に見つかりません")
    return str(max(candidates, key=lambda m: m.creation_time).tag)


def _resolve_tag(model_name: str, stage: str) -> str:
    try:
        return _latest_tag_by_stage(model_name, stage)
    except NotFound:
        # 見つからなければ MLflow から自動インポート
        from scripts.model.import_iforest_from_mlflow import import_iforest

        logger.info("MLflow Registry から %s(stage=%s) をインポートします", model_name, stage)
        import_iforest(stage)
        return _latest_tag_by_stage(model_name, stage)


@lru_cache(maxsize=1)
def get_runner(model_tag: str) -> Runner:
    """Runner をプロセス内でキャッシュして返す."""
    runner = sklearn.get(model_tag).to_runner()
    runner.init_local()  # Airflow ではプロセスごとに実行される
    logger.info("Runner(%s) を初期化しました", model_tag)
    return runner


# ---------- Snowflake ユーティリティ ----------
def _fetch_latest_row(cfg: Optional[SnowflakeConfig] = None) -> pd.DataFrame:
    """最新 1 レコードを取得."""
    cfg = cfg or SnowflakeConfig() 
    query = f"""
        SELECT *
          FROM {FEATURE_TABLE}
         ORDER BY hour_ts DESC
         LIMIT 1
    """
    with connect(**cfg.dict()) as conn:
        df = pd.read_sql(query, conn)
    return df

# ---- Airflow PythonOperator 用コールバック -------------------------------
def load_latest_model_from_registry(
    model_name: str = MODEL_NAME,
    stage: str = STAGE,
) -> None:
    """Registry から最新モデルを取得してローカルにキャッシュ"""
    tag = _resolve_tag(model_name, stage)
    get_runner(tag)  


# ---------- 前処理・推論パイプライン ----------
def _prep_features(df: pd.DataFrame) -> pd.DataFrame:
    """学習時と同じ前処理を適用して特徴量 DataFrame を返す."""
    df = df.copy()
    df.columns = df.columns.str.lower()
    return df.drop(columns=["dex", "pool_id", "hour_ts", "y"], errors="ignore")


def score_latest_row(
    threshold: float,
    *,
    model_name: str = MODEL_NAME,
    stage: str = STAGE,
    snowflake_cfg: SnowflakeConfig | None = None,
) -> Dict[str, Any]:
    """最新行に対して IsolationForest スコアを算出.

    Args:
        threshold: 異常判定閾値（score ≥ threshold → 異常）
    Returns:
        dict: {"pool_id": str, "score": float, "is_anomaly": bool}
    """
    tag = _resolve_tag(model_name, stage)
    runner = get_runner(tag)

    cfg = snowflake_cfg or SnowflakeConfig.from_env()
    df_latest = _fetch_latest_row(cfg)
    X = _prep_features(df_latest)

    # Bento Runner は ndarray 返し  (IsolationForest.score_samples)
    score_val = float(-runner.run(X)[0])  # 大きいほど異常

    result = {
        "pool_id": df_latest["pool_id"].iloc[0],
        "score": score_val,
        "is_anomaly": score_val >= threshold,
    }
    logger.info("スコアリング結果: %s", result)
    return result


