import importlib

from airflow.models import DagBag


def test_dag_imports_ok():
    """
    DAG ファイルが SyntaxError 無しで読み込めるのみを検査します
    （Airflow オブジェクトの詳細は Integration で別途テスト）
    """
    modules = [
        "dags.check_snowflake_connection",
        "dags.dex_pipeline",
        "dags.predict_pool_iforest",
        "dags.retrain_isolation_forest",
    ]
    for m in modules:
        importlib.import_module(m)  # シンタックスエラー検知用

    # safe_mode=False で高速ロード
    dag_bag = DagBag(include_examples=False, safe_mode=False)
    # 登録された DAG が 4 つあるはず
    assert len(dag_bag.dags) >= 4
    # 登録された DAG が 4 つあるはず
    assert len(dag_bag.dags) >= 4
