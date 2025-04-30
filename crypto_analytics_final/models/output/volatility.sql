with volatility as (
  select
    date,
    price_close,
    stddev_samp(price_close) over (order by date rows between 6 preceding and current row) as volatility_7_day,
    stddev_samp(price_close) over (order by date rows between 29 preceding and current row) as volatility_30_day
  from {{ ref('historical_data') }}
)

select * from volatility
