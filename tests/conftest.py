import os
from pathlib import Path

# Airflow が見る最低限の環境をダミーで構築
os.environ.setdefault("AIRFLOW_HOME", "/tmp/airflow-unit")
os.environ.setdefault("AIRFLOW__CORE__SQL_ALCHEMY_CONN", "sqlite:///:memory:")
os.environ.setdefault("AIRFLOW__CORE__UNIT_TEST_MODE", "True")
os.environ.setdefault("AIRFLOW__CORE__LOAD_EXAMPLES", "False")
# リポジトリの dags フォルダを明示
os.environ.setdefault("AIRFLOW__CORE__DAGS_FOLDER", str(Path(__file__).resolve().parents[1] / "dags"))


import logging
from datetime import datetime, timezone

import pytest
import responses

# ---------- 全テスト共通の設定 ----------


@pytest.fixture(autouse=True)
def _configure_logging():
    """
    pytest 実行時のログを INFO 以上に統一します
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


@pytest.fixture(autouse=True)
def _dummy_env(monkeypatch, tmp_path_factory):
    """
    コード側が参照する環境変数をダミーで注入します
    """
    dummy_env = {
        # Snowflake
        "SNOWFLAKE_USER": "DUMMY",
        "SNOWFLAKE_PASSWORD": "DUMMY",
        "SNOWFLAKE_ACCOUNT": "dummy-account",
        "SNOWFLAKE_WAREHOUSE": "TEST_WH",
        "SNOWFLAKE_DATABASE": "TEST_DB",
        "SNOWFLAKE_SCHEMA": "RAW",
        "SNOWFLAKE_ROLE": "SYSADMIN",
        # MLflow
        "MLFLOW_TRACKING_URI": "http://localhost:5000",
        # The Graph API キー（protocols.yml で ${…} 展開される想定）
        "UNI_API_KEY": "fake-key",
        "SUSHI_API_KEY": "fake-key",
    }
    for k, v in dummy_env.items():
        monkeypatch.setenv(k, v)

    # データ保存先をテスト用の一時フォルダに差し替える
    data_dir = tmp_path_factory.mktemp("data")
    monkeypatch.setenv("DATA_DIR", str(data_dir))  # 必要ならコード側で参照

    yield  # ここでテスト実行
    # pytest 終了時に monkeypatch が自動で環境変数を戻す


# ---------- ネットワークモック用ヘルパ ----------


@pytest.fixture
def mocked_responses():
    """
    tests に `responses` を渡して HTTP モックを使えるようにします
    """
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


# ---------- ダミー GraphQL レスポンス生成ヘルパ ----------


@pytest.fixture
def graph_dummy_payload():
    """
    The Graph API の最小ダミー JSON を返す共通ヘルパです
    """
    now_ts = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "data": {
            "poolHourDatas": [
                {
                    "id": "1",
                    "periodStartUnix": now_ts,
                    "liquidity": "123",
                    "volumeUSD": "456",
                }
            ]
        }
    }
    return payload
