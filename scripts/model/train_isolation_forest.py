import os

import mlflow
import numpy as np
import pandas as pd
from mlflow.models.signature import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.ensemble import IsolationForest
from sqlalchemy import create_engine


def load_data(days: int = 30) -> pd.DataFrame:
    """Snowflake から mart_pool_features_labeled の直近 days 日分を取得"""
    user = os.getenv("SNOWFLAKE_USER")
    pw = os.getenv("SNOWFLAKE_PASSWORD")
    acct = os.getenv("SNOWFLAKE_ACCOUNT")
    wh = os.getenv("SNOWFLAKE_WAREHOUSE")
    db = os.getenv("SNOWFLAKE_DATABASE")
    schema = os.getenv("SNOWFLAKE_SCHEMA")

    # Snowflake 用 SQLAlchemy URL を組み立て
    url = f"snowflake://{user}:{pw}@{acct}/{db}/{schema}?warehouse={wh}&role={os.getenv('SNOWFLAKE_ROLE')}"
    engine = create_engine(url)

    query = f"""
        SELECT *
        FROM DEX_RAW.RAW.MART_POOL_FEATURES_LABELED
        WHERE hour_ts >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    """
    df = pd.read_sql(query, engine)
    return df


def train():
    df = load_data(30)

    # 目的変数 y は使わない
    X = df.drop(columns=["dex", "pool_id", "hour_ts", "y"]).astype(np.float64)

    model = IsolationForest(
        n_estimators=200,
        contamination="auto",
        random_state=42,
    )

    with mlflow.start_run() as run:
        mlflow.sklearn.autolog()
        model.fit(X)

        # IsolationForest は predict() が {-1,1}、score_samples() が anomaly スコア
        scores = -model.score_samples(X)  # 値が大きいほど異常
        mlflow.log_metric("mean_anomaly_score", float(np.mean(scores)))

        signature = infer_signature(X, scores)
        input_example = X.iloc[[0]]
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            signature=signature,
            input_example=input_example,
        )

        client = MlflowClient()
        try:
            client.get_registered_model("pool_iforest")
        except Exception:
            client.create_registered_model("pool_iforest")

        mv = client.create_model_version(
            name="pool_iforest",
            source=f"runs:/{run.info.run_id}/model",
            run_id=run.info.run_id,
        )
        client.set_registered_model_alias(name="pool_iforest", alias="production", version=mv.version)


if __name__ == "__main__":
    train()
