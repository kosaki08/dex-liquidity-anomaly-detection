-- スキーマ作成
create schema if not exists RAW;

-- pool_hourly_uniswap テーブル作成
create
or replace table RAW.pool_hourly_uniswap (raw TEXT, load_ts TIMESTAMP);

-- pool_hourly_sushiswap テーブル作成
create
or replace table RAW.pool_hourly_sushiswap (raw TEXT, load_ts TIMESTAMP);