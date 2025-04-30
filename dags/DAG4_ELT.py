"""
A basic dbt DAG that shows how to run dbt commands via the BashOperator
Follows the standard dbt seed, run, and test pattern.
"""
from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.hooks.base import BaseHook
from airflow.models import Variable



DBT_PROJECT_DIR = Variable.get("DBT_PROJECT_DIR", default_var="/opt/airflow/crypto_analytics_final")


conn = BaseHook.get_connection('snowflake_conn_ml')

dbt_env = {
    "DBT_USER": conn.login,
    "DBT_PASSWORD": conn.password,
    "DBT_ACCOUNT": conn.extra_dejson.get("account", ""),
    "DBT_SCHEMA": conn.schema,
    "DBT_DATABASE": conn.extra_dejson.get("database", ""),
    "DBT_ROLE": conn.extra_dejson.get("role", ""),
    "DBT_WAREHOUSE": conn.extra_dejson.get("warehouse", ""),
    "DBT_TYPE": "snowflake"
}

with DAG(
    "crypto_analytics",
    start_date=datetime(2025, 4, 22),
    description="A Airflow DAG to invoke dbt runs using a BashOperator",
    schedule=None,
    catchup=False,
) as dag:
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"/home/airflow/.local/bin/dbt run --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}",
        env=dbt_env
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"/home/airflow/.local/bin/dbt test --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}",
        env=dbt_env
    )

    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=f"/home/airflow/.local/bin/dbt snapshot --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}",
        env=dbt_env
    )

    # print_env_var = BashOperator(
    #    task_id='print_aa_variable',
    #    bash_command='echo "The value of AA is: $DBT_ACCOUNT,$DBT_ROLE,$DBT_DATABASE,$DBT_WAREHOUSE,$DBT_USER,$DBT_TYPE,$DBT_SCHEMA"'
    # )

    dbt_run >> dbt_test >> dbt_snapshot