import duckdb


def build_raw_clean_table(data_dir: str, db_path: str = ":memory:"):
    con = duckdb.connect(database=db_path)

    # 生 JSONL を UNION ALL で読み込み raw テーブルを作成
    protocols = ["uniswap", "sushiswap"]
    union_sql = "\nUNION ALL\n".join(f"SELECT * FROM read_json_auto('{data_dir}/{p}/*_pool.jsonl')" for p in protocols)
    con.execute(f"CREATE OR REPLACE TABLE raw AS {union_sql}")

    # まず pool メタデータテーブルを作成
    con.execute("""
    CREATE OR REPLACE TABLE pool_metadata AS
    SELECT DISTINCT
        id,
        pool['feeTier'] AS fee_tier,
        pool['token0']['id'] AS token0_id,
        pool['token0']['symbol'] AS token0_symbol,
        pool['token0']['name'] AS token0_name,
        pool['token0']['decimals'] AS token0_decimals,
        pool['token1']['id'] AS token1_id,
        pool['token1']['symbol'] AS token1_symbol,
        pool['token1']['name'] AS token1_name,
        pool['token1']['decimals'] AS token1_decimals
    FROM raw
    WHERE pool IS NOT NULL
    """)

    # キャスト済みのクリーンテーブルを作成
    con.execute("""
    CREATE OR REPLACE TABLE raw_clean AS
    SELECT
        periodStartUnix           AS hour_ts,
        CAST(volumeUSD            AS DOUBLE)  AS volume_usd,
        CAST(tvlUSD               AS DOUBLE)  AS tvl_usd,
        CAST(id                   AS VARCHAR) AS id,
        CAST(liquidity            AS DOUBLE)  AS liquidity,
        CAST(volumeToken0         AS DOUBLE)  AS volume_token0,
        CAST(volumeToken1         AS DOUBLE)  AS volume_token1,
        CAST(feesUSD              AS DOUBLE)  AS fees_usd,
        CAST(open                 AS DOUBLE)  AS open_price,
        CAST(high                 AS DOUBLE)  AS high_price,
        CAST(low                  AS DOUBLE)  AS low_price,
        CAST(close                AS DOUBLE)  AS close_price,
        -- カウント系は BIGINT でキャスト
        CAST(txCount              AS BIGINT)  AS tx_count,
        CAST(tick                 AS DOUBLE)  AS tick,
        CAST(sqrtPrice            AS DOUBLE)  AS sqrt_price,
        CAST(token0Price          AS DOUBLE)  AS token0_price,
        CAST(token1Price          AS DOUBLE)  AS token1_price
    FROM raw
    """)

    # pool メタデータと結合したテーブルを作成
    con.execute("""
    CREATE OR REPLACE TABLE raw_clean_with_pool AS
    SELECT 
        r.*,
        p.fee_tier,
        p.token0_id, p.token0_symbol, p.token0_name, p.token0_decimals,
        p.token1_id, p.token1_symbol, p.token1_name, p.token1_decimals
    FROM raw_clean r
    LEFT JOIN pool_metadata p ON r.id = p.id
    """)

    print("raw_clean テーブルと pool_metadata テーブルの作成が完了しました。")
    print("raw_clean_with_pool 結合テーブルも作成しました。")
    con.close()
