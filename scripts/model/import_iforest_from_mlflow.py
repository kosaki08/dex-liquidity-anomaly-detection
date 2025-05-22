import logging
import os
from typing import Final

import bentoml
from bentoml.exceptions import NotFound
from mlflow.tracking import MlflowClient

logger: Final = logging.getLogger(__name__)


def import_iforest(stage: str = "Production") -> None:
    """
    MLflow Registry から IsolationForest を BentoML Store にインポートします

    Args:
        stage: MLflow モデルのステージ（Production / Staging など）

    Raises:
        RuntimeError: MLFLOW_TRACKING_URI が未設定の場合
        ValueError:   指定ステージのモデルが見つからない場合
    """
    tag = f"pool_iforest:{stage}"
    try:
        bentoml.sklearn.get(tag)
        logger.info("Skip import: %s は既に存在します", tag)
        return
    except NotFound:
        logger.info("%s が見つからないため MLflow から取得します", tag)

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        raise RuntimeError("MLFLOW_TRACKING_URI が環境変数に設定されていません")

    client = MlflowClient(tracking_uri=tracking_uri)
    # alias は MLflow 側で小文字登録なので lower() で合わせる
    try:
        mv = client.get_model_version_by_alias("pool_iforest", stage.lower())
    except Exception as exc:
        raise ValueError(f"MLflow に '{stage}' ステージの pool_iforest が見つかりません") from exc

    bentoml.mlflow.import_model(
        "pool_iforest",
        f"runs:/{mv.run_id}/model",  # ここで直接 URI を渡す
        labels={"stage": stage.lower()},
    )
    logger.info("Import 完了: %s を BentoML Store に保存しました", tag)
