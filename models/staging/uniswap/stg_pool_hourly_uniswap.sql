{{ config(materialized='view') }}

with src as (

    select
        raw        as r,
        load_ts
    from {{ source('raw', 'pool_hourly_uniswap') }}

), parsed as (

    select
        {{ json_ts   ("r:periodStartUnix") }}    as hour,
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

select * from parsed;
