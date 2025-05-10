import json
import os

import duckdb
import pandas as pd
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()


def fetch_raw_from_snowflake(conn) -> pd.DataFrame:
    """
    Snowflake から生データを取得します
    """
    sql = """
    SELECT raw, load_ts, 'uniswap' AS protocol
      FROM DEX_RAW.RAW.pool_hourly_uniswap
    UNION ALL
    SELECT raw, load_ts, 'sushiswap' AS protocol
      FROM DEX_RAW.RAW.pool_hourly_sushiswap
    """
    # Snowflake から DataFrame を取得
    df_raw = pd.read_sql(sql, conn)
    # 列名をすべて小文字に
    df_raw.columns = df_raw.columns.str.lower()

    # raw 列(JSON)を dict 化してから normalize、sep="_" でネストをフラット化
    def parse_maybe_json(x):
        if isinstance(x, (bytes, bytearray)):
            x = x.decode()
        return json.loads(x) if isinstance(x, str) else x

    raw_dicts = df_raw["raw"].apply(parse_maybe_json)
    df_json = pd.json_normalize(raw_dicts, sep="_")

    # load_ts / protocol をマージ
    df_json["load_ts"] = df_raw["load_ts"]
    df_json["protocol"] = df_raw["protocol"]
    return df_json


def main():
    """
    Snowflake から生データを取得して DuckDB に保存します
    """
    # 環境変数から Snowflake 接続情報を取得
    sf_conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )
    # フラット化済み DF を取得
    df_json = fetch_raw_from_snowflake(sf_conn)
    sf_conn.close()

    # 重複排除: id と periodStartUnix でグルーピングして load_ts を残す
    df_json["id"] = df_json["id"].astype(str)
    df_json["periodStartUnix"] = df_json["periodStartUnix"].astype(int)
    df_clean = df_json.sort_values("load_ts").drop_duplicates(subset=["id", "periodStartUnix"], keep="last")

    # DuckDB に書き出し
    duckdb_path = os.getenv("DUCKDB_PATH", "data/raw/etl_from_sf.duckdb")
    con = duckdb.connect(duckdb_path)

    # raw_clean テーブルを作成
    con.register("df_clean", df_clean)

    # raw_clean テーブルを作成
    con.execute("""
    CREATE OR REPLACE TABLE raw_clean AS
    SELECT
        periodStartUnix     AS hour_ts,
        CAST(id             AS VARCHAR) AS id,
        CAST(volumeUSD      AS DOUBLE)  AS volume_usd,
        CAST(tvlUSD         AS DOUBLE)  AS tvl_usd,
        CAST(liquidity      AS DOUBLE)  AS liquidity,
        CAST(volumeToken0   AS DOUBLE)  AS volume_token0,
        CAST(volumeToken1   AS DOUBLE)  AS volume_token1,
        CAST(feesUSD        AS DOUBLE)  AS fees_usd,
        CAST(open           AS DOUBLE)  AS open_price,
        CAST(high           AS DOUBLE)  AS high_price,
        CAST(low            AS DOUBLE)  AS low_price,
        CAST(close          AS DOUBLE)  AS close_price,
        -- カウント系は BIGINT でキャスト
        CAST(txCount        AS BIGINT)  AS tx_count,
        CAST(tick           AS DOUBLE)  AS tick,
        CAST(sqrtPrice      AS DOUBLE)  AS sqrt_price,
        CAST(token0Price    AS DOUBLE)  AS token0_price,
        CAST(token1Price    AS DOUBLE)  AS token1_price,
        protocol,
        load_ts
    FROM df_clean
    """)

    # pool_metadata テーブルを作成
    con.execute("""
    CREATE OR REPLACE TABLE pool_metadata AS
    SELECT DISTINCT
      id,
      pool_feeTier         AS fee_tier,
      pool_token0_id       AS token0_id,
      pool_token0_symbol   AS token0_symbol,
      pool_token0_name     AS token0_name,
      pool_token0_decimals AS token0_decimals,
      pool_token1_id       AS token1_id,
      pool_token1_symbol   AS token1_symbol,
      pool_token1_name     AS token1_name,
      pool_token1_decimals AS token1_decimals
    FROM df_clean
    """)

    # raw_clean_with_pool テーブルを作成
    con.execute("""
    CREATE OR REPLACE TABLE raw_clean_with_pool AS
    SELECT
      r.*,
      p.fee_tier,
      p.token0_id, p.token0_symbol, p.token0_name, p.token0_decimals,
      p.token1_id, p.token1_symbol, p.token1_name, p.token1_decimals
    FROM raw_clean AS r
    LEFT JOIN pool_metadata AS p
      ON r.id = p.id
    """)

    con.close()
    print(f"DuckDB にデータを保存しました: {duckdb_path}")


if __name__ == "__main__":
    main()
