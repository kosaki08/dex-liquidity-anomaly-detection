from datetime import datetime

from airflow import DAG
from airflow.models.variable import Variable
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor

from scripts.model.predict import load_latest_model_from_registry, score_latest_row

with DAG(
    dag_id="predict_pool_iforest",
    start_date=datetime(2025, 5, 1),
    schedule="@hourly",
    catchup=False,
    tags=["predict", "ml", "iforest"],
) as dag:
    # Anomaly スコア閾値
    THRESHOLD = float(Variable.get("iforest_threshold", default_var=2.0))

    # Mart 更新完了を待機
    wait_for_mart = ExternalTaskSensor(
        task_id="wait_for_mart",
        external_dag_id="dex_liquidity_raw",
        external_task_id="dbt_run_mart",
        timeout=600,
        poke_interval=60,
        mode="reschedule",
    )

    # Isolation Forest モデルをロード
    load_model = PythonOperator(
        task_id="load_latest_model",
        python_callable=load_latest_model_from_registry,
        op_kwargs={
            "model_name": "pool_iforest",
            "stage": "Production",
        },
    )

    # 最新データ 1 行をスコアリング
    score = PythonOperator(
        task_id="score_latest_row",
        python_callable=score_latest_row,
        op_kwargs={
            "threshold": THRESHOLD,
        },
    )

    # 依存関係
    wait_for_mart >> load_model >> score
