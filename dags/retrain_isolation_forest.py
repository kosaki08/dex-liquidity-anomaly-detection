from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from scripts.model.train_isolation_forest import train as train_iforest

with DAG(
    dag_id="retrain_isolation_forest",
    start_date=datetime(2025, 4, 1),
    schedule="@weekly",
    catchup=False,
    tags=["retrain", "ml", "iforest"],
) as dag:
    PythonOperator(
        task_id="train_iforest",
        python_callable=train_iforest,
    )
