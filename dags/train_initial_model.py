import importlib
import sys
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

scripts_dir = Path(__file__).resolve().parents[1] / "project" / "scripts"
sys.path.insert(0, str(scripts_dir))

# importlib で model.train_initial モジュールをロード
train_mod = importlib.import_module("model.train_initial")
train_initial_main = train_mod.main

with DAG(
    dag_id="train_initial_model",
    start_date=datetime(2025, 5, 1),
    schedule=None,
    catchup=False,
    tags=["ml", "river"],
) as dag:
    PythonOperator(
        task_id="train_initial",
        python_callable=train_initial_main,
    )
