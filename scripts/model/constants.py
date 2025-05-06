import os

FEATURE_COLS = [
    "tvl_usd",
    "volume_usd",
    "liquidity",
    "vol_rate_24h",
    "tvl_rate_24h",
    "vol_ma_6h",
    "vol_ma_24h",
    "vol_tvl_ratio",
]


SNOW_CONN = {
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "warehouse": "ETL_WH",
    "database": "DEX_RAW",
    "schema": "RAW",
    "role": os.getenv("SNOWFLAKE_ROLE"),
}
