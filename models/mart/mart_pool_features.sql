{{ config(
    materialized = 'table',
    unique_key   = ['pool_id', 'hour_ts'],
    incremental_strategy = 'delete+insert'
) }}

with hourly as (

    select 'uniswap'  as dex, * from {{ ref('stg_pool_hourly_uniswap') }}
    union all
    select 'sushiswap' as dex, * from {{ ref('stg_pool_hourly_sushiswap') }}

), renamed as (

    select
        dex,
        pool_id,
        hour_ts,
        tvl_usd,
        volume_usd,
        liquidity,
        load_ts
    from hourly

)

select
    dex,
    pool_id,
    hour_ts,
    tvl_usd,
    volume_usd,
    liquidity,

    -- 24h 変化率（インライン window）
    (
        NULLIF(volume_usd, 0)
        /
        NULLIF(
        lag(volume_usd, 24) over (partition by pool_id order by hour_ts),
        0
        )
    ) - 1 as vol_rate_24h,

    (
        NULLIF(tvl_usd, 0)
        /
        NULLIF(
        lag(tvl_usd, 24) over (partition by pool_id order by hour_ts),
        0
        )
    ) - 1 as tvl_rate_24h,

    -- 移動平均
    avg(volume_usd) over (
        partition by pool_id order by hour_ts
        rows between 5 preceding and current row
    )              as vol_ma_6h,

    avg(volume_usd) over (
        partition by pool_id order by hour_ts
        rows between 23 preceding and current row
    )              as vol_ma_24h,

    -- TVL 比
    volume_usd / nullif(tvl_usd, 0) as vol_tvl_ratio,

    load_ts

from renamed

{% if is_incremental() %}
where hour_ts > coalesce((select max(hour_ts) from {{ this }}), '1900-01-01'::timestamp)
{% endif %}

