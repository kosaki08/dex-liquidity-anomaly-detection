import os

import bentoml
import pandas as pd
from snowflake.connector import connect


def load_latest_model_from_registry(model_name: str, stage: str) -> None:
    # BentoML からモデルをランナーとしてロード
    runner = bentoml.lightgbm.get(model_name + ":" + stage).to_runner()
    runner.init_local()  # Runner を初期化
    return


def score_latest_row(threshold: float) -> dict:
    # Snowflake から最新 1 行を取得
    conn = connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )
    query = """
        SELECT *
        FROM DEX_RAW.RAW.MART_POOL_FEATURES_LABELED
        ORDER BY hour_ts DESC
        LIMIT 1
    """
    df = pd.read_sql(query, conn)
    conn.close()

    # 特徴量だけ選択
    X = df.drop(columns=["dex", "pool_id", "hour_ts", "y"])
    # BentoML runner を使って予測
    from bentoml import Runner

    runner: Runner = Runner.get("volume_spike_lgbm:Production")
    score = runner.run(X)[0]

    result = {
        "pool_id": df["pool_id"].iloc[0],
        "score": float(score),
    }
    return result
