import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))  # nopep8

from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.providers.standard.operators.python import PythonOperator
from scripts.fetcher.run_fetch import fetch_pool_data


def put_and_copy(protocol: str, ts_nodash: str) -> None:
    """
    - @RAW.DEX_STAGE へ file:///opt/airflow/data/raw/{protocol}/{ts_nodash}_pool.jsonl を PUT
    - RAW.pool_hourly_{protocol} へ COPY
    """
    local_file = f"/opt/airflow/data/raw/{protocol}/{ts_nodash}_pool.jsonl"
    stage_path = f"@RAW.DEX_STAGE/{ts_nodash}_pool.jsonl"
    target_table = f"RAW.pool_hourly_{protocol}"

    hook = SnowflakeHook(snowflake_conn_id="snowflake_default")
    with hook.get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"PUT file://{local_file} @RAW.DEX_STAGE AUTO_COMPRESS=FALSE")
        cur.execute(
            f"""
            COPY INTO {target_table} (raw)          -- 列リストを指定
            FROM {stage_path}
            FILE_FORMAT = (FORMAT_NAME = RAW.JSONL_FMT)
            ON_ERROR = 'CONTINUE'
            """
        )


with DAG(
    dag_id="dex_liquidity_raw",
    start_date=datetime(2025, 5, 1),
    schedule="@hourly",
    catchup=False,
    tags=["dex", "snowflake"],
) as dag:
    for proto in ["uniswap", "sushiswap"]:
        # データ抽出
        extract = PythonOperator(
            task_id=f"extract_{proto}_pool_hourly",
            python_callable=fetch_pool_data,
            op_kwargs={
                "protocol": proto,
                # 例: 20250505T090000Z_pool.jsonl
                "output_path": f"/opt/airflow/data/raw/{proto}/{{{{ ts_nodash }}}}_pool.jsonl",
                "data_interval_end": "{{ data_interval_end }}",
            },
        )

        # PUT + COPY
        put_and_copy_task = PythonOperator(
            task_id=f"put_and_copy_{proto}",
            python_callable=put_and_copy,
            op_kwargs={
                "protocol": proto,
                "ts_nodash": "{{ ts_nodash }}",
            },
        )

        extract >> put_and_copy_task
