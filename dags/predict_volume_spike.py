from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor

from scripts.model.predict import (
    load_latest_model_from_registry,
    score_latest_row,
)

THRESHOLD = 0.8

with DAG(
    dag_id="predict_volume_spike",
    start_date=datetime(2025, 5, 1),
    schedule="@hourly",
    catchup=False,
    tags=["predict", "ml", "slack"],
) as dag:
    # Mart 更新完了を待機
    wait_for_mart = ExternalTaskSensor(
        task_id="wait_for_mart",
        external_dag_id="dex_liquidity_raw",
        external_task_id="dbt_run_mart",
        timeout=600,  # 最大 10 分待機
        poke_interval=60,
        mode="reschedule",
    )

    # モデルを Registry からロード
    load_model = PythonOperator(
        task_id="load_latest_model",
        python_callable=load_latest_model_from_registry,
        op_kwargs={
            "model_name": "volume_spike_lgbm",
            "stage": "Production",
        },
    )

    # 最新行を推論
    score = PythonOperator(
        task_id="score_latest_row",
        python_callable=score_latest_row,
        op_kwargs={
            "threshold": THRESHOLD,
        },
    )

    wait_for_mart >> load_model >> score
