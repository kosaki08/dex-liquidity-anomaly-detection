from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from scripts.model.train_lightgbm import train as train_lightgbm_main

with DAG(
    dag_id="retrain_lightgbm",
    start_date=datetime(2025, 5, 1),
    schedule="@weekly",
    catchup=False,
    tags=["retrain", "ml", "lightgbm"],
) as dag:
    run_train = PythonOperator(
        task_id="train_lightgbm",
        python_callable=train_lightgbm_main,
    )
