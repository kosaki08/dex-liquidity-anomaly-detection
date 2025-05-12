import os
import sys

import bentoml
from mlflow.artifacts import download_artifacts
from mlflow.tracking import MlflowClient


def main():
    """
    MLflow のレジストリから Production ステージの
    pool_iforest モデルを BentoML Store にインポートします。
    """
    uri = os.getenv("MLFLOW_TRACKING_URI")
    if not uri:
        print("MLFLOW_TRACKING_URI が設定されていません")
        sys.exit(1)

    # MLflow クライアントを作成
    client = MlflowClient(tracking_uri=uri)

    # モデルのバージョンを取得
    model_version = client.get_model_version_by_alias("pool_iforest", "production")
    if not model_version:
        print("Production バージョンが見つかりません")
        sys.exit(1)

    # モデルの URI を取得
    artifact_uri = model_version.source
    local_model = download_artifacts(artifact_uri)

    if not os.path.exists(local_model):
        print("モデルファイルが見つかりません:", local_model)
        sys.exit(1)

    # BentoMLへのインポート
    try:
        bentoml.mlflow.import_model(
            "pool_iforest",
            f"runs:/{model_version.run_id}/model",
            labels={"stage": "production"},
        )

    except Exception as e:
        print(f"インポート失敗: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
