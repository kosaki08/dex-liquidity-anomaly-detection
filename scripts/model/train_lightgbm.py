import os

import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.metrics import average_precision_score
from snowflake.connector import connect


def load_data(days: int = 30) -> pd.DataFrame:
    """Snowflake から mart_pool_features_labeled の直近 days 日分を取得"""
    conn = connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )
    query = f"""
        SELECT *
        FROM DEX_RAW.RAW.MART_POOL_FEATURES_LABELED
        WHERE hour_ts >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    """
    df = pd.read_sql(query, conn)
    # カラム名を小文字に変換
    df.columns = df.columns.str.lower()
    conn.close()
    return df


def train() -> None:
    """LightGBM モデルを訓練して Registry に登録"""
    # データ取得
    df = load_data(30)
    y = df["y"]
    X = df.drop(columns=["dex", "pool_id", "hour_ts", "y"])

    # モデル定義
    model = lgb.LGBMClassifier(num_leaves=63, learning_rate=0.05)

    # MLflow でランを開始
    with mlflow.start_run() as run:
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

        # メトリクスをログ
        mlflow.log_metric("pr_auc", pr_auc)
        mlflow.log_metric("precision_at_10", precision_at_10)
        mlflow.log_metric("recall_at_10", recall_at_10)

        # モデルをテキスト形式で保存 & artifact 登録
        model.booster_.save_model("model.txt")
        mlflow.log_artifact("model.txt")

        # モデルを Registry に登録して Production ステージへ
        client = MlflowClient()
        client.create_registered_model("volume_spike_lgbm")
        mv = client.create_model_version(
            name="volume_spike_lgbm",
            source=f"runs:/{run.info.run_id}/model.txt",
            run_id=run.info.run_id,
        )
        client.transition_model_version_stage(
            name=mv.name,
            version=mv.version,
            stage="Production",
            archive_existing_versions=True,
        )


if __name__ == "__main__":
    train()
