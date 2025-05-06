import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "scripts"))  # nopep8

import logging
import os
import pickle

import mlflow
import pandas as pd
from mlflow.models.signature import infer_signature
from mlflow.tracking import MlflowClient
from river import anomaly, compose, preprocessing
from river.compose import Pipeline
from snowflake.connector import connect

from scripts.model.constants import FEATURE_COLS

SNOW_CONN = {
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "warehouse": "ETL_WH",
    "database": "DEX_RAW",
    "schema": "RAW",
    "role": os.getenv("SNOWFLAKE_ROLE"),
}

SQL = """
SELECT
  dex,
  pool_id,
  hour_ts,
  tvl_usd,
  volume_usd,
  liquidity,
  vol_rate_24h,
  tvl_rate_24h,
  vol_ma_6h,
  vol_ma_24h,
  vol_tvl_ratio
FROM mart_pool_features
WHERE hour_ts >= DATEADD('day', -30, CURRENT_TIMESTAMP)  -- 直近30日
ORDER BY hour_ts
"""


logger = logging.getLogger(__name__)


class RiverModelWrapper(mlflow.pyfunc.PythonModel):
    def load_context(self, context) -> None:
        with open(context.artifacts["model_file"], "rb") as f:
            self.model = pickle.load(f)

    def predict(self, model_input: pd.DataFrame) -> pd.Series:
        return model_input.apply(lambda row: self.model.score_one(row.to_dict()), axis=1)


def load_features() -> pd.DataFrame:
    with connect(**SNOW_CONN) as cnn:
        df = pd.read_sql(SQL, cnn)

    # Snowflake は大文字カラムなので小文字に
    df.columns = df.columns.str.lower()

    # 欠損値（NULL/None）が残っている行は、一旦学習対象外に
    df = df.dropna(subset=FEATURE_COLS)
    return df


def build_pipeline() -> Pipeline:
    pipeline = (
        # 必要なカラムだけ抜き出す
        compose.Select(*FEATURE_COLS)
        # 特徴量を [0,1] にスケーリング
        | preprocessing.MinMaxScaler()
        # オンライン HalfSpaceTrees で異常スコアを算出
        | anomaly.HalfSpaceTrees(
            n_trees=50,
            height=8,
            window_size=256,
            seed=42,
        )
    )
    return pipeline


def main():
    df = load_features()
    logger.info(f"loaded features: {len(df)} rows from Snowflake")

    # 必要なカラムだけ抜き出す
    df.columns = df.columns.str.lower()
    numeric = [
        "tvl_usd",
        "volume_usd",
        "liquidity",
        "vol_rate_24h",
        "tvl_rate_24h",
        "vol_ma_6h",
        "vol_ma_24h",
        "vol_tvl_ratio",
    ]
    df = df.dropna(subset=numeric)

    # パイプラインを作成
    model = build_pipeline()

    # 学習
    for _, row in df.iterrows():
        x = row.drop(["dex", "pool_id", "hour_ts"]).to_dict()
        model.learn_one(x)

    # 学習済み river モデルを持つラッパーを作成
    wrapper = RiverModelWrapper()
    wrapper.model = model

    # input_example を作成
    input_example = df.drop(columns=["dex", "pool_id", "hour_ts"]).head(5).reset_index(drop=True)
    input_example = input_example.astype("float64")

    # 学習済みモデルを pickle で保存
    os.makedirs("model_artifact", exist_ok=True)
    model_path = os.path.join("model_artifact", "model.pkl")
    model_file = "model_artifact/model.pkl"
    with open(model_file, "wb") as f:
        pickle.dump(model, f)

    # ラッパーで予測例を作成し signature を推論
    y_example = wrapper.predict(input_example)
    signature = infer_signature(input_example, y_example)

    # mlflow にログ
    mlflow.pyfunc.log_model(
        artifact_path="model",
        python_model=RiverModelWrapper(),
        artifacts={"model_file": model_path},
        signature=signature,
        input_example=input_example,
    )
    mlflow.log_param("rows", len(df))
    mlflow.log_param("start", df.hour_ts.min())
    mlflow.log_param("end", df.hour_ts.max())

    # mlflow の run_id を取得
    run_id = mlflow.active_run().info.run_id
    logger.info(f"logged run {run_id}")

    # Registry へ登録
    client = MlflowClient()
    # モデルを登録
    client.create_registered_model("river_isoforest")
    mv = client.create_model_version(
        name="river_isoforest",
        source=f"runs:/{run_id}/model",
        run_id=run_id,
    )
    # Production ステージに遷移
    client.transition_model_version_stage(
        name="river_isoforest",
        version=mv.version,
        stage="Production",
    )
    logger.info(f"registered model river_isoforest v{mv.version} → Production")


if __name__ == "__main__":
    main()
