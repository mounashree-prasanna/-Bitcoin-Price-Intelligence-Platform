from airflow import DAG
from airflow.decorators import task
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.models import Variable
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
import logging
import os

def return_snowflake_conn():
    hook = SnowflakeHook(snowflake_conn_id='snowflake_conn_ml')
    conn = hook.get_conn()
    return conn.cursor()

@task
def train(crypto_data_table, crypto_forecast_view, crypto_forecast_model):
    """
     - Create a view with training related columns
     - Create a model with the view above
    """
    conn.execute(f"USE WAREHOUSE {warehouse};")
    create_view_sql = f"""CREATE OR REPLACE VIEW {schema1}.{crypto_forecast_view} AS 
        SELECT TIME_PERIOD_START, PRICE_OPEN, ASSET_PAIR 
        FROM {schema}.{crypto_data_table}"""

    create_model_sql = f"""CREATE OR REPLACE SNOWFLAKE.ML.FORECAST {schema1}.{crypto_forecast_model} (
        INPUT_DATA => SYSTEM$REFERENCE('VIEW', '{schema1}.{crypto_forecast_view}'),
        SERIES_COLNAME => 'ASSET_PAIR',
        TIMESTAMP_COLNAME => 'TIME_PERIOD_START',
        TARGET_COLNAME => 'PRICE_OPEN',
        CONFIG_OBJECT => {{ 'ON_ERROR': 'SKIP' }}
    )"""

    try:
        conn.execute(create_view_sql)
        conn.execute(create_model_sql)
        conn.execute(f"CALL {schema1}.{crypto_forecast_model}!SHOW_EVALUATION_METRICS();")
    except Exception as e:
        print(e)
        raise

@task
def predict(crypto_forecast_model, crypto_data_table, crypto_predictions_table, crypto_final_table):
    """
     - Generate predictions and store the results to a table named forecast_table.
     - Union your predictions with your historical data, then create the final table
    """
    conn.execute(f"USE WAREHOUSE {warehouse};")
    make_prediction_sql = f"""BEGIN
        -- This is the step that creates your predictions.
        CALL {schema1}.{crypto_forecast_model}!FORECAST(
            FORECASTING_PERIODS => 7,
            -- Here we set your prediction interval.
            CONFIG_OBJECT => {{'prediction_interval': 0.95}}
        );
        -- These steps store your predictions to a table.
        LET x := SQLID;
        CREATE OR REPLACE TABLE {schema1}.{crypto_predictions_table} AS SELECT * FROM TABLE(RESULT_SCAN(:x));
    END;"""
    create_final_table_sql = f"""CREATE OR REPLACE TABLE {schema1}.{crypto_final_table} AS
        SELECT ASSET_PAIR, TIME_PERIOD_START, PRICE_OPEN AS actual, NULL AS forecast, NULL AS lower_bound, NULL AS upper_bound
        FROM {schema}.{crypto_data_table}
        UNION ALL
        SELECT replace(series, '"', '') as ASSET_PAIR, ts as TIME_PERIOD_START, NULL AS actual, forecast, lower_bound, upper_bound
        FROM {schema1}.{crypto_predictions_table};"""

    try:
        conn.execute(make_prediction_sql)
        conn.execute(create_final_table_sql)
    except Exception as e:
        print(e)
        raise


with DAG(
    dag_id = 'DAG3_ML',
    start_date = datetime(2024,6,21),
    catchup=False,
    tags=['ML', 'ELT'],
    schedule_interval = None
) as dag:
    
    schema = "user_db_jellyfish.raw"
    schema1 = "user_db_jellyfish.analytics"
    warehouse = 'JELLYFISH_QUERY_WH'
    table = "historical_data"
    view = "train_view"
    func_name = "forecast_function_name"
    crypto_tbl = "crypto_forecast_table"
    crypto_final_table = "crypto_forecast_final_table"
    conn = return_snowflake_conn()
    
    ml_train = train(table, view, func_name)
    ml_predict = predict(func_name, table, crypto_tbl, crypto_final_table)

    ml_train >> ml_predict