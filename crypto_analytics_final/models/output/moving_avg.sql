with moving_avg as (
  select
    date,
    price_close,
    avg(price_close) over (order by date rows between 6 preceding and current row) as ma_7_day,
    avg(price_close) over (order by date rows between 29 preceding and current row) as ma_30_day
  from {{ ref('historical_data') }}
)

select * from moving_avg
