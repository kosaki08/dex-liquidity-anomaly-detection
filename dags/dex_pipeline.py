import sys
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from scripts.fetcher.run_fetch import fetch_pool_data

sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))


with DAG(
    dag_id="dex_liquidity_raw",
    start_date=datetime(2025, 5, 1),
    schedule="@hourly",
    catchup=False,
) as dag:

    for proto in ["uniswap", "sushiswap"]:
        PythonOperator(
            task_id=f"extract_{proto}_pool_hourly",
            python_callable=fetch_pool_data,
            op_kwargs={
                "protocol": proto,
                "output_path": f"/opt/airflow/data/raw/{proto}/{{{{ ds }}}}_pool.jsonl",
                "data_interval_end": "{{ data_interval_end }}",
            },
        )
