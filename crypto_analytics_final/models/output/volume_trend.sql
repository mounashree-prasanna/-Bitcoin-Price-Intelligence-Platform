
select
  date,
  price_close,
  volume_traded,
  (price_close / nullif(volume_traded, 0)) as price_volume_ratio
from {{ ref('historical_data') }}
