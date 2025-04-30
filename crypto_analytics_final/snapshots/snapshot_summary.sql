-- Snapshot for Moving Average
{% snapshot snapshot_moving_avg %}
{{
  config(
    target_schema='analytics',
    unique_key='date',
    strategy='timestamp',
    updated_at='date',
    invalidate_hard_deletes=True
  )
}}
select * from {{ ref('moving_avg') }}
{% endsnapshot %}

-- Snapshot for Volatility
{% snapshot snapshot_volatility %}
{{
  config(
    target_schema='analytics',
    unique_key='date',
    strategy='timestamp',
    updated_at='date',
    invalidate_hard_deletes=True
  )
}}
select * from {{ ref('volatility') }}
{% endsnapshot %}

-- Snapshot for RSI
{% snapshot snapshot_rsi %}
{{
  config(
    target_schema='analytics',
    unique_key='date',
    strategy='timestamp',
    updated_at='date',
    invalidate_hard_deletes=True
  )
}}
select * from {{ ref('rsi') }}
{% endsnapshot %}

-- Snapshot for Volume Trend
{% snapshot snapshot_volume_trend %}
{{
  config(
    target_schema='analytics',
    unique_key='date',
    strategy='timestamp',
    updated_at='date',
    invalidate_hard_deletes=True
  )
}}
select * from {{ ref('volume_trend') }}
{% endsnapshot %}
