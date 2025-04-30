from airflow import DAG
from airflow.decorators import task
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
import os
from datetime import datetime, timedelta, timezone
import pandas as pd
import yfinance as yf
import requests
from airflow.models import Variable
import logging

def return_snowflake_conn():
    hook = SnowflakeHook(snowflake_conn_id='snowflake_conn_etl')
    conn = hook.get_conn()
    return conn.cursor()


@task
def extract(file_path):
    API_KEY = Variable.get("api_key")
    headers = {
        'X-CoinAPI-Key': API_KEY
    }

    end_date = datetime.now(timezone.utc)
    # Always get 3 years of data
    start_date = end_date - timedelta(days=1095)
    
    logging.info(f"Extracting data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    asset_pair = "BINANCE_SPOT_BTC_USDT"
    url = f"https://rest.coinapi.io/v1/ohlcv/{asset_pair}/history"
    params = {
        'period_id': '1DAY',
        'time_start': start_date.strftime('%Y-%m-%dT00:00:00'),
        'time_end': end_date.strftime('%Y-%m-%dT00:00:00'),
        'limit': 2000
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        df = pd.DataFrame(data)
        df['asset_pair'] = asset_pair
        df['time_period_start'] = pd.to_datetime(df['time_period_start']).dt.strftime('%Y-%m-%d')
        # df.rename(columns={'time_period_start': 'Date'}, inplace=True)
        df.to_csv(file_path, index=False)
        logging.info(f"Saved {len(df)} rows of BTC data to: {file_path}")
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        raise

@task
def create_table():
    conn = return_snowflake_conn()
    target_table = "USER_DB_JELLYFISH.raw.historical_data"  

    try:
        conn.execute("BEGIN;")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {target_table} (
                time_period_start TIMESTAMP,
                time_period_end TIMESTAMP,
                time_open TIMESTAMP,
                time_close TIMESTAMP,
                price_open FLOAT,
                price_high FLOAT,
                price_low FLOAT,
                price_close FLOAT,
                volume_traded FLOAT,
                trades_count INTEGER,
                asset_pair VARCHAR
            )
        """)
        conn.execute("COMMIT;")
        logging.info(f"Table {target_table} created and cleaned.")
    except Exception as e:
        conn.execute("ROLLBACK;")
        logging.error(f"Error creating table: {e}")
        raise
    finally:
        conn.close()

@task
def populate_table_via_stage(file_path):
    table = "historical_data"
    schema = "USER_DB_JELLYFISH.raw"
    stage_name = f"TEMP_STAGE_{table}"
    temp_table = f"TEMP_LOAD_{table}"  # ⬅️ New temp table name
    file_name = os.path.basename(file_path)
    conn = return_snowflake_conn()

    try:
        conn.execute(f"CREATE OR REPLACE TEMPORARY STAGE {stage_name}")
        conn.execute(f"PUT file://{file_path} @{stage_name} AUTO_COMPRESS=TRUE OVERWRITE=TRUE")
        
        # Step 1: Create a temporary table to first load data
        conn.execute(f"""
            CREATE OR REPLACE TEMPORARY TABLE {schema}.{temp_table} (
                time_period_start TIMESTAMP,
                time_period_end TIMESTAMP,
                time_open TIMESTAMP,
                time_close TIMESTAMP,
                price_open FLOAT,
                price_high FLOAT,
                price_low FLOAT,
                price_close FLOAT,
                volume_traded FLOAT,
                trades_count INTEGER,
                asset_pair VARCHAR
            )
        """)

        # Step 2: Copy data from stage into the temp table
        conn.execute(f"""
            COPY INTO {schema}.{temp_table}
            FROM @{stage_name}/{file_name}
            FILE_FORMAT = (TYPE = CSV, SKIP_HEADER = 1, FIELD_OPTIONALLY_ENCLOSED_BY = '"')
        """)

        # Step 3: Now MERGE from temp table into target table
        merge_query = f"""
            MERGE INTO {schema}.{table} target
            USING {schema}.{temp_table} source
            ON target.time_period_start = source.time_period_start 
               AND target.asset_pair = source.asset_pair
            WHEN NOT MATCHED THEN
                INSERT (
                    time_period_start, time_period_end, 
                    time_open, time_close, price_open, price_high, 
                    price_low, price_close, volume_traded, trades_count, asset_pair
                )
                VALUES (
                    source.time_period_start, source.time_period_end, 
                    source.time_open, source.time_close, source.price_open, source.price_high, 
                    source.price_low, source.price_close, source.volume_traded, source.trades_count, source.asset_pair
                )
        """
        
        conn.execute(merge_query)
        logging.info(f"Data loaded from stage to temp table and merged into {schema}.{table} successfully!")
    except Exception as e:
        logging.error(f"Error populating Snowflake table: {e}")
        raise
    finally:
        conn.close()




with DAG(
    dag_id='DAG1_ETL',
    start_date=datetime(2024, 6, 21),
    catchup=False,
    tags=['ETL', 'crypto', 'bitcoin'],
    schedule_interval=None,
    default_args={'retries': 1, 'retry_delay': timedelta(minutes=5)}
) as dag:

    file_path = "/opt/airflow/dags/historical_btc.csv"
    
    extracted = extract(file_path)
    table_created = create_table()
    loaded = populate_table_via_stage(file_path)

    extracted >> table_created >> loaded
