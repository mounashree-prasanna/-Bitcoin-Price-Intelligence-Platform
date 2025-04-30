with base as (
  select
    date,
    price_close,
    lag(price_close) over (order by date) as prev_close
  from {{ ref('historical_data') }}
),

gains_losses as (
  select
    date,
    case when price_close - prev_close > 0 then price_close - prev_close else 0 end as gain,
    case when price_close - prev_close < 0 then abs(price_close - prev_close) else 0 end as loss
  from base
),

rsi_calc as (
  select
    date,
    avg(gain) over (order by date rows between 13 preceding and current row) as avg_gain,
    avg(loss) over (order by date rows between 13 preceding and current row) as avg_loss
  from gains_losses
)

select
  date,
  avg_gain,
  avg_loss,
  case when avg_loss = 0 then 100 else 100 - (100 / (1 + (avg_gain / avg_loss))) end as rsi_14_day
from rsi_calc
