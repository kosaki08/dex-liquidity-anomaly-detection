from datetime import datetime

from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.providers.standard.operators.python import PythonOperator


def check_snowflake_connection(conn_id: str = "snowflake_default") -> None:
    """
    1. Airflow Metadata に connection が存在するか
    2. Snowflake に SELECT 1 が通るか
    両方を検証。どちらか失敗で AirflowFailException を raise。
    """
    hook = SnowflakeHook(snowflake_conn_id=conn_id)

    # Metadata に無い場合はここで KeyError
    try:
        conn = hook.get_connection(conn_id)
    except KeyError:
        raise AirflowFailException(f"[{conn_id}] が Airflow に登録されていません")

    # Snowflake 実接続確認
    try:
        with hook.get_conn() as sf:
            with sf.cursor() as cur:
                cur.execute("SELECT 1")
                _ = cur.fetchone()
    except Exception as exc:
        raise AirflowFailException(
            f"[{conn.conn_id}] Snowflake 接続失敗: {exc}"
        ) from exc


with DAG(
    dag_id="check_snowflake_connection",
    start_date=datetime(2025, 5, 1),
    schedule=None,
    catchup=False,
    tags=["check", "snowflake", "connection"],
) as dag:
    PythonOperator(
        task_id="check_connection",
        python_callable=check_snowflake_connection,
        op_kwargs={"conn_id": "snowflake_default"},
    )
