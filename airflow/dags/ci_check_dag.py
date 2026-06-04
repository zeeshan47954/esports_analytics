from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def hello_world():
    print("✅ DAG check successful! Hello from CI pipeline.")

with DAG(
    dag_id='ci_check_dag',
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,  # Manual only
    catchup=False,
    tags=['ci', 'test'],
) as dag:

    test_task = PythonOperator(
        task_id='hello_world',
        python_callable=hello_world,
    )