{{ 
  config(
    materialized = 'incremental',
    unique_key   = ['pool_id', 'hour_ts']
  ) 
}}

-- ソースとなる Mart データ
with source as (
  select
    dex,
    pool_id,
    hour_ts,
    tvl_usd,
    volume_usd,
    liquidity,
    vol_rate_24h,
    tvl_rate_24h,
    vol_ma_6h,
    vol_ma_24h,
    vol_tvl_ratio
  from {{ ref('mart_pool_features') }}
),

-- プールごとに 90% パーセンタイルを計算
pct as (
  {% if target.type == 'snowflake' %}
    -- Snowflake なら percentile_cont を使う
    select
      pool_id,
      percentile_cont(0.9) within group (order by volume_usd) as pct_90
    from source
    group by pool_id
  {% else %}
    -- DuckDB なら reservoir_quantile（近似）を使う
    select
      pool_id,
      reservoir_quantile(volume_usd, 0.9) as pct_90
    from source
    group by pool_id
  {% endif %}
)

select
  s.*,
  case 
    when s.volume_usd >= p.pct_90 then 1
    else 0
  end as y

from source s
join pct p using (pool_id)

{% if is_incremental() %}
where s.hour_ts > (
  select max(hour_ts) from {{ this }}
)
{% endif %}
