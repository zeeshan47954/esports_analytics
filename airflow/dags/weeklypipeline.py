from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException
from datetime import datetime, timedelta
import pandas as pd
import redis
import boto3
import io
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import logging
import subprocess
from dotenv import load_dotenv

load_dotenv()

# ========================= LOGGING SETUP =========================
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

file_handler = logging.FileHandler('/opt/airflow/logs/nightly_pipeline.log', mode='a')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

default_args = {
    'owner': 'you',
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
}

# Global Redis connection
r = redis.Redis(
    host='host.docker.internal',
    port=6379,
    db=0,
    password='secret123',
    decode_responses=True
)

with DAG(
    dag_id='weekly_pipeline',
    default_args=default_args,
    description='The Mighty Nightly Pipeline',
    schedule_interval=timedelta(days=1),                    # Daily at 2 AM
    start_date=datetime(2026, 5, 19),
    catchup=False,
    tags=['etl', 'esports', 'pipeline'],
) as dag:

    def check_rds_connection(**context):
        try:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                connect_timeout=10,
            )
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            logger.info("✅ RDS Connection Successful")
            return 1
        except Exception as e:
            logger.error(f"❌ RDS Connection Failed: {str(e)}")
            raise AirflowException("RDS Connection Failed") from e

    def check_redis_health(**context):
        try:
            if r.ping():
                logger.info("✅ Redis Health Check Passed")
                return 1
            else:
                raise AirflowException("Redis Ping Failed")
        except Exception as e:
            logger.error(f"❌ Redis Health Check Error: {str(e)}")
            raise AirflowException("Redis Health Check Failed") from e

    def cache_top_50_players(**context):
        conn = None
        try:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                connect_timeout=10,
            )

            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM players 
                    ORDER BY elo_rating DESC 
                    LIMIT 50
                """)
                
                data = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

                if not data:
                    logger.info("No players found to cache")
                    r.setex("topplayers", 3600, "[]")
                    return 1

                df = pd.DataFrame(data, columns=columns)
                json_data = df.to_json(orient='records', date_format='iso')

                r.setex("topplayers", 3600, json_data)

                logger.info(f"✅ Successfully cached top {len(df)} players in Redis (key: topplayers)")
                return 1

        except Exception as e:
            logger.error(f"❌ Error in cache_top_50_players: {str(e)}", exc_info=True)
            raise AirflowException("cache_top_50_players failed") from e

        finally:
            if conn:
                conn.close()

    def dbt_build_with_xcom(**context):
        try:
            result = subprocess.run(
                ["docker", "exec", "esports-dbt", "bash", "-c",
                 "cd /usr/app/esports_dbt && dbt build --select stg_players"],
                capture_output=True,
                text=True,
                timeout=600
            )

            status = 'success' if result.returncode == 0 else 'failed'
            
            context['task_instance'].xcom_push(key='dbt_status', value=status)
            context['task_instance'].xcom_push(key='dbt_rows_processed', value=1)

            if status == 'success':
                logger.info("✅ DBT Build Completed Successfully")
                if result.stdout:
                    logger.info("DBT Output (last 10 lines):\n" + "\n".join(result.stdout.splitlines()[-10:]))
            else:
                logger.error(f"❌ DBT Build Failed with return code {result.returncode}")
                if result.stderr:
                    logger.error(f"DBT Error: {result.stderr}")
                raise AirflowException("DBT Build Failed")

            return 1

        except subprocess.TimeoutExpired:
            logger.error("❌ DBT Build Timed Out (600 seconds)")
            raise AirflowException("DBT Build Timeout") from None
        except Exception as e:
            logger.error(f"❌ DBT Build Error: {str(e)}")
            raise AirflowException("DBT Build failed") from e

    def maintenance(**context):
        # (Your improved maintenance function from previous response)
        try:
            engine = create_engine(os.getenv("fullpath"))
            Session = sessionmaker(bind=engine)
            session = Session()

            LOG_DIR = "/opt/airflow/logs"
            os.makedirs(LOG_DIR, exist_ok=True)
            today = datetime.now()
            log_filename = os.path.join(LOG_DIR, f"maintenance_{today.strftime('%d_%m_%y')}.log")

            def log(message):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_line = f"[{timestamp}] {message}"
                print(log_line)
                try:
                    with open(log_filename, "a", encoding="utf-8") as f:
                        f.write(log_line + "\n")
                except:
                    pass

            log("=== Database Maintenance Started ===")

            result = session.execute(text("""
                SELECT relname, n_live_tup, n_dead_tup,
                       ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct
                FROM pg_stat_user_tables
                WHERE n_dead_tup > 0.15 * n_live_tup
                ORDER BY n_dead_tup DESC;
            """))

            bloated_tables = [row['relname'] for row in result.mappings()]

            if bloated_tables:
                log(f"Found {len(bloated_tables)} bloated tables. Running VACUUM...")

                for table in bloated_tables:
                    try:
                        log(f"Vacuuming {table}...")
                        with engine.connect() as conn:
                            conn.execution_options(isolation_level="AUTOCOMMIT")
                            conn.execute(text(f"VACUUM ANALYZE {table};"))
                        log(f"✅ VACUUM ANALYZE completed on {table}")
                    except Exception as ve:
                        log(f"❌ Failed to vacuum {table}: {ve}")
            else:
                log("✅ No bloated tables found.")

            log("=== Database Maintenance Completed Successfully ===")
            return 1

        except Exception as e:
            logger.error(f"❌ Maintenance Task Failed: {str(e)}")
            raise AirflowException("Maintenance Task Failed") from e
        finally:
            if 'session' in locals() and session:
                session.close()

    # ====================== TASKS ======================
    t1 = PythonOperator(task_id="check_rds_connection", python_callable=check_rds_connection)
    t2 = PythonOperator(task_id="check_redis_health", python_callable=check_redis_health)
    t3 = PythonOperator(task_id="cache_top_50_players", python_callable=cache_top_50_players)
    t4 = PythonOperator(task_id="dbt_build", python_callable=dbt_build_with_xcom)
    t5 = PythonOperator(task_id="maintenance", python_callable=maintenance)

    # Task Flow
    t1 >> t2 >> t3 >> t4 >> t5