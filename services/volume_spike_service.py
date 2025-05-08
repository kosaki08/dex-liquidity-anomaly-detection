import logging
import os

import bentoml
import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient

from scripts.logging_config import setup_logging

setup_logging()

logger = logging.getLogger("volume_spike_service")


@bentoml.service(
    resources={"cpu": "2"},
    traffic={"timeout": 60},
)
class VolumeSpikeService:
    def __init__(self):
        # MLflow クライアントを作成
        mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        client = MlflowClient(tracking_uri=mlflow_uri)

        # モデル情報を取得
        try:
            logger.info("production モデルのロードを開始します")
            model_version = client.get_model_version_by_alias("volume_spike_lgbm", "production")
            if model_version:
                run_id = model_version.run_id
                # run_idを直接使用してモデルをロード
                self.model = mlflow.pyfunc.load_model(model_uri=f"runs:/{run_id}/model")
                logger.info(f"production モデルロード成功: run_id={run_id}")
            else:
                logger.error("production モデルが見つかりません")
                raise ValueError("production モデルが見つかりません")
        except Exception as e:
            logger.error(f"production モデルロード失敗: {str(e)}")
            # フォールバック方法: 最新のバージョンを手動で検索
            latest_model = client.search_model_versions("name='volume_spike_lgbm'")
            if latest_model:
                logger.info("フォールバックでモデルロードを開始します")
                run_id = latest_model[0].run_id
                self.model = mlflow.pyfunc.load_model(f"runs:/{run_id}/model")
                logger.info(f"フォールバックでモデルロードします: run_id={run_id}")
            else:
                logger.error("有効なモデルバージョンが見つかりません")
                raise ValueError("有効なモデルバージョンが見つかりません")

    @bentoml.api
    def predict(self, input_data: list[dict]) -> list[float]:
        logger.info(f"predictリクエストを受信しました: {input_data}")
        # 入力データをDataFrameに変換
        df = pd.DataFrame(input_data)
        # 列名を小文字に変換
        df.columns = df.columns.str.lower()

        # 予測実行
        logger.info(f"予測を実行します: shape={df.shape}, columns={df.columns.tolist()}")
        logger.debug(f"predictリクエスト詳細: {input_data}")
        logger.debug(f"DataFrameプレビュー: {df.head()}")
        try:
            predictions = self.model.predict(df).tolist()
            logger.info(f"予測が完了しました: {predictions}")
            return predictions
        except Exception as e:
            logger.error(f"予測処理でエラーが発生しました: {str(e)}")
            raise
