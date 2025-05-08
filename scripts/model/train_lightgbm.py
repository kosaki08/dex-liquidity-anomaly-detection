import os

import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd
from mlflow.models.signature import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.metrics import average_precision_score
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


def train() -> None:
    """LightGBM モデルを訓練して Registry に登録"""
    # データ取得
    df = load_data(30)
    y = df["y"]
    X = df.drop(columns=["dex", "pool_id", "hour_ts", "y"]).astype(np.float64)

    # モデル定義
    model = lgb.LGBMClassifier(num_leaves=63, learning_rate=0.05)

    # MLflow でランを開始
    with mlflow.start_run() as run:
        # 自動ロギングを有効化
        mlflow.lightgbm.autolog()

        # モデルの学習を開始
        model.fit(X, y)
        # 予測スコアを計算
        y_scores = model.predict_proba(X)[:, 1]

        # PR-AUC
        pr_auc = average_precision_score(y, y_scores)
        # Precision@10: スコア上位10件中の正例割合
        top_idx = np.argsort(y_scores)[-10:]
        precision_at_10 = y.iloc[top_idx].mean()
        # Recall@10: 正例総数に対するトップ10でのカバー率
        recall_at_10 = y.iloc[top_idx].sum() / y.sum()

        # メトリクスを追以下
        mlflow.log_metric("pr_auc", pr_auc)
        mlflow.log_metric("precision_at_10", precision_at_10)
        mlflow.log_metric("recall_at_10", recall_at_10)

        # モデル入出力のシグネチャを推定
        signature = infer_signature(X, y.astype(np.float64))

        # Input Example を作成
        input_example = X.iloc[[0]]

        # モデルを保存
        mlflow.lightgbm.log_model(model, "model", signature=signature, input_example=input_example)

        # モデルを Registry に登録して Production ステージへ
        client = MlflowClient()

        # すでに登録済みかチェック
        try:
            client.get_registered_model("volume_spike_lgbm")
        except Exception:
            # 存在しなければ作成
            client.create_registered_model("volume_spike_lgbm")

        # モデルバージョンを追加
        mv = client.create_model_version(
            name="volume_spike_lgbm",
            source=f"runs:/{run.info.run_id}/model",
            run_id=run.info.run_id,
        )
        # 最新を Production に昇格（既存を archive）
        client.set_registered_model_alias(
            name="volume_spike_lgbm",
            alias="production",
            version=mv.version,
        )


if __name__ == "__main__":
    train()
