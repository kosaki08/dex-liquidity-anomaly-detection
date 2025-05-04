-- ロールの使用
USE ROLE ACCOUNTADMIN;

-- DATABASE の使用
USE DATABASE DEX_RAW;

-- SCHEMA の使用
USE SCHEMA RAW;

-- RAW スキーマに pool_hourly_uniswap テーブルを作成
CREATE
OR REPLACE TABLE RAW.pool_hourly_uniswap (
    raw VARIANT,
    load_ts TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP
);

-- RAW スキーマに pool_hourly_sushiswap テーブルを作成
CREATE
OR REPLACE TABLE RAW.pool_hourly_sushiswap (
    raw VARIANT,
    load_ts TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP
);