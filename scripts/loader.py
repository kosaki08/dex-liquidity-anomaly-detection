import duckdb

# モジュール読み込み時に一度接続を作成
_con = duckdb.connect(database=":memory:")


def load_raw(data_dir: str, protocols: list[str]):
    """
    データを読み込みテーブルを作成します

    Args:
        data_dir (str): データのディレクトリ
        protocols (list[str]): プロトコルのリスト

    Returns:
        duckdb.Relation: テーブル
    """
    # UNION ALL でまとめる SQL を組み立て
    union_sql = "\nUNION ALL\n".join(f"SELECT * FROM read_json_auto('{data_dir}/{p}/*_pool.jsonl')" for p in protocols)
    _con.execute(f"CREATE OR REPLACE TABLE raw AS {union_sql}")
    # connection は閉じずに Relation を返す
    return _con.table("raw")
