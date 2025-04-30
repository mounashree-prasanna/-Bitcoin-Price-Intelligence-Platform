select
  time_period_end::date as date,
  time_open,
  time_close,
  price_open,
  price_high,
  price_low,
  price_close,
  volume_traded,
  trades_count,
  asset_pair
from {{ source('raw', 'historical_data') }}
