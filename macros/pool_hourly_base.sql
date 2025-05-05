{% macro pool_hourly_base(source_name) %}
with src as (

    -- Snowflake／DuckDB 共通
    -- RAW テーブルを読み込み、raw カラムをエイリアス r に変換しておく
    select
        raw        as r,
        load_ts
    from {{ source('raw', source_name) }}

), parsed as (

    select
        {{ json_ts   ("r:periodStartUnix") }}    as hour_ts,
        {{ json_str  ("r:pool:id") }}            as pool_id,
        {{ json_str  ("r:pool:token0:id") }}     as token0_id,
        {{ json_str  ("r:pool:token1:id") }}     as token1_id,
        {{ json_float("r:tvlUSD") }}             as tvl_usd,
        {{ json_float("r:volumeUSD") }}          as volume_usd,
        {{ json_float("r:liquidity") }}          as liquidity,
        {{ json_float("r:open") }}               as open,
        {{ json_float("r:high") }}               as high,
        {{ json_float("r:low") }}                as low,
        {{ json_float("r:close") }}              as close,
        load_ts
    from src

)

select * from parsed
{% endmacro %}
