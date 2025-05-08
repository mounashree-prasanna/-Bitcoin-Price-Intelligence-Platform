from airflow import DAG
from airflow.decorators import task
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.models import Variable
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
import os
import logging

def return_snowflake_conn():
    hook = SnowflakeHook(snowflake_conn_id='snowflake_conn_etl')
    conn = hook.get_conn()
    return conn.cursor()

@task
def extract_real_time(file_path):
    API_KEY = Variable.get("api_key")
    headers = {'X-CoinAPI-Key': API_KEY}

    asset_pair = "BINANCE_SPOT_BTC_USDT"
    url = f"https://rest.coinapi.io/v1/ohlcv/{asset_pair}/latest"
    params = {'period_id': '1HRS', 'limit': 1}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if data:
            df = pd.DataFrame(data)
            df['asset_pair'] = asset_pair
            df.to_csv(file_path, index=False)
            logging.info(f"Saved real-time BTC data to: {file_path}")
        else:
            logging.warning("No real-time data received.")
    except Exception as e:
        logging.error(f"Failed to fetch real-time BTC data: {e}")
        raise

@task
def create_table_real_time():
    conn = return_snowflake_conn()
    target_table = "USER_DB_JELLYFISH.raw.real_time_data"

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
        # Optional: You can delete based on timestamp to prevent duplicates
        conn.execute(f"""
            DELETE FROM {target_table}
            WHERE time_period_start >= DATEADD(hour, -2, CURRENT_TIMESTAMP())
        """)
        conn.execute("COMMIT;")
        logging.info(f"Real-time table {target_table} created and cleaned.")
    except Exception as e:
        conn.execute("ROLLBACK;")
        logging.error(f"Error creating real-time table: {e}")
        raise
    finally:
        conn.close()

@task
def load_to_snowflake_real_time(file_path):
    table = "real_time_data"
    schema = "USER_DB_JELLYFISH.raw"
    stage_name = f"TEMP_STAGE_{table}"
    staging_table = f"stage_{table}"
    file_name = os.path.basename(file_path)
    conn = return_snowflake_conn()

    try:
        # 1. Create or replace temporary stage
        conn.execute(f"CREATE OR REPLACE TEMPORARY STAGE {stage_name}")

        # 2. Upload the CSV file to the Snowflake stage
        conn.execute(f"PUT file://{file_path} @{stage_name} OVERWRITE = TRUE")

        # 3. Create a temporary table to load data from the staged file
        conn.execute(f"CREATE OR REPLACE TEMPORARY TABLE {staging_table} LIKE {schema}.{table}")

        # 4. Load staged data into the temporary staging table
        conn.execute(f"""
            COPY INTO {staging_table}
            FROM @{stage_name}/{file_name}
            FILE_FORMAT = (TYPE = CSV, SKIP_HEADER = 1, FIELD_OPTIONALLY_ENCLOSED_BY = '"')
        """)

        # 5. Begin transaction
        conn.execute("BEGIN;")

        # 6. Delete any overlapping data in the target table
        conn.execute(f"""
            DELETE FROM {schema}.{table}
            WHERE time_period_start IN (
                SELECT time_period_start FROM {staging_table}
            )
        """)

        # 7. Insert the new data into the target table
        conn.execute(f"""
            INSERT INTO {schema}.{table}
            SELECT * FROM {staging_table}
        """)

        # 8. Commit transaction
        conn.execute("COMMIT;")
        logging.info(f"Real-time data loaded into {schema}.{table} safely.")

    except Exception as e:
        conn.execute("ROLLBACK;")
        logging.error(f"Failed to load real-time BTC data into Snowflake: {e}")
        raise
    finally:
        conn.close()



# DAG definition
with DAG(
    dag_id='DAG2_Real_Time_ETL',
    start_date=datetime(2024, 6, 21),
    catchup=False,
    tags=['ETL', 'crypto', 'real-time'],
    schedule_interval='@hourly',
    default_args={'retries': 1, 'retry_delay': timedelta(minutes=5)}
) as dag:

    file_path = "/opt/airflow/dags/real_time_btc.csv"
    
    extract = extract_real_time(file_path)
    create = create_table_real_time()
    load = load_to_snowflake_real_time(file_path)

    extract >> create >> load

