import logging
import os
from typing import Final

import bentoml
import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient

logger: Final = logging.getLogger(__name__)


@bentoml.service(resources={"cpu": "2"}, traffic={"timeout": 60})
class PoolIForestService:
    def __init__(self):
        mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        client = MlflowClient(tracking_uri=mlflow_uri)
        mv = client.get_model_version_by_alias("pool_iforest", "production")
        self.model = mlflow.pyfunc.load_model(f"runs:/{mv.run_id}/model")

    @bentoml.api
    def predict(self, input_data: list[dict]) -> list[float]:
        df = pd.DataFrame(input_data)
        # カラム名をすべて小文字に
        df.columns = df.columns.str.lower()

        logger.info(f"predictリクエストを受信しました（小文字化反映済）: {df.columns.tolist()}")
        try:
            scores = (-self.model.predict(df)).tolist()
            logger.info(f"予測が完了しました: {scores}")
            return scores
        except Exception as e:
            logger.error(f"予測処理でエラーが発生しました: {e}")
            raise
