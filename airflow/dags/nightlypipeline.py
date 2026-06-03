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
    dag_id='nightly_pipeline',
    default_args=default_args,
    description='The Mighty Nightly Pipeline - Matches, Validation, DBT, Cache & Maintenance',
    schedule_interval=timedelta(days=1),
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

    def load_new_matches_from_rds(**context):
        """Load new matches using watermark pattern with proper rollback"""
        src_conn = None
        tgt_conn = None
        try:
            src_conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                connect_timeout=10,
            )
            tgt_conn = psycopg2.connect(
                host=os.getenv("DB_HOST1"),
                port=os.getenv("DB_PORT1"),
                database=os.getenv("DB_NAME1"),
                user=os.getenv("DB_USER1"),
                password=os.getenv("DB_PASSWORD1"),
                connect_timeout=10,
            )

            s3 = boto3.client(
                "s3",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION")
            )
            BUCKET = os.getenv("BUCKET")

            src_cur = src_conn.cursor()
            tgt_cur = tgt_conn.cursor()
            now = datetime.now()

            # Watermark Logic
            src_cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'watermark_pipeline'
                );
            """)
            watermark_exists = src_cur.fetchone()[0]

            if not watermark_exists:
                logger.info("📌 Creating watermark_pipeline table...")
                src_cur.execute("""
                    CREATE TABLE IF NOT EXISTS watermark_pipeline (
                        id SERIAL PRIMARY KEY,
                        point_of_time TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                src_cur.execute("INSERT INTO watermark_pipeline DEFAULT VALUES;")
                src_conn.commit()
                last_point = datetime(2020, 1, 1)
            else:
                src_cur.execute("SELECT point_of_time FROM watermark_pipeline ORDER BY id DESC LIMIT 1;")
                last_point = src_cur.fetchone()[0] or datetime(2020, 1, 1)

            logger.info(f"📅 Last successful run: {last_point}")

            # New Matches Table
            tgt_cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'new_matches'
                );
            """)
            if not tgt_cur.fetchone()[0]:
                logger.info("📌 Creating new_matches table...")
                tgt_cur.execute("""
                    CREATE TABLE new_matches (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tournament_id UUID,
                        team_a_id UUID,
                        team_b_id UUID,
                        winner_id UUID,
                        played_at TIMESTAMPTZ,
                        created_by TEXT,
                        loaded_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                tgt_conn.commit()
                logger.info("✅ new_matches table created successfully")

            # Fetch data
            src_cur.execute("""
                SELECT * FROM matches 
                WHERE played_at > %s AND played_at <= %s
                ORDER BY played_at
                LIMIT 5000;
            """, (last_point, now))

            rows = src_cur.fetchall()
            columns = [desc[0] for desc in src_cur.description]

            if rows:
                logger.info(f"📦 Found {len(rows)} new matches to process")

                inserted = 0
                try:
                    for row in rows:
                        tgt_cur.execute("""
                            INSERT INTO new_matches 
                            (id, tournament_id, team_a_id, team_b_id, winner_id, played_at, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            row[columns.index('id')],
                            row[columns.index('tournament_id')],
                            row[columns.index('team_a_id')],
                            row[columns.index('team_b_id')],
                            row[columns.index('winner_id')],
                            row[columns.index('played_at')],
                            row[columns.index('created_by')] if 'created_by' in columns else None,
                        ))
                        inserted += 1

                    tgt_conn.commit()
                    logger.info(f"✅ Successfully inserted {inserted} matches")

                except Exception as insert_err:
                    tgt_conn.rollback()
                    logger.error(f"❌ Insert failed. Transaction rolled back: {insert_err}")
                    raise

                # Update watermark
                src_cur.execute("INSERT INTO watermark_pipeline DEFAULT VALUES;")
                src_conn.commit()

                # S3 Upload
                df = pd.DataFrame(rows, columns=columns)
                s3_key = f"matches/new_matches/match_{now.strftime('%Y%m%d_%H%M%S')}.csv"
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)

                s3.put_object(
                    Bucket=BUCKET,
                    Key=s3_key,
                    Body=csv_buffer.getvalue(),
                    ContentType="text/csv"
                )
                logger.info(f"✅ Uploaded {len(rows)} matches to S3 → {s3_key}")
            else:
                logger.info(f"✅ No new matches found between {last_point} and {now}")

            return 1

        except Exception as e:
            logger.error(f"❌ Critical Error in load_new_matches_from_rds: {str(e)}", exc_info=True)
            if src_conn and not src_conn.closed:
                try: src_conn.rollback()
                except: pass
            if tgt_conn and not tgt_conn.closed:
                try: tgt_conn.rollback()
                except: pass
            raise AirflowException("load_new_matches_from_rds failed") from e

        finally:
            if src_conn: src_conn.close()
            if tgt_conn: tgt_conn.close()

    def bulk_validate_player_status(**context):
        try:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
            )
            cur = conn.cursor()
            cur.execute("SELECT player_id, kills, assists, deaths FROM player_stats")

            log_content = ""
            issues = 0

            while True:
                rows = cur.fetchmany(1000)
                if not rows:
                    break
                for row in rows:
                    pid = row[0]
                    if row[1] is not None and row[1] < 0:
                        log_content += f"Negative kills for player {pid}: {row[1]}\n"
                        issues += 1
                    if row[2] is not None and row[2] < 0:
                        log_content += f"Negative assists for player {pid}: {row[2]}\n"
                        issues += 1
                    if row[3] is not None and row[3] < 0:
                        log_content += f"Negative deaths for player {pid}: {row[3]}\n"
                        issues += 1

            log_path = "/opt/airflow/logs/player_status.log"
            os.makedirs(os.path.dirname(log_path), exist_ok=True)

            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n--- Player Validation Run: {datetime.now()} ---\n")
                f.write(log_content)
                f.write(f"Total issues found: {issues}\n")

            logger.info(f"✅ Player status validation completed. Issues: {issues}")
            return 1

        except Exception as e:
            logger.error(f"❌ Player validation failed: {str(e)}", exc_info=True)
            raise AirflowException("Player validation failed") from e
        finally:
            if 'conn' in locals() and conn:
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
                # Optional: Show last few lines of output
                logger.info("DBT Output (last 10 lines):\n" + "\n".join(result.stdout.splitlines()[-10:]))
            else:
                logger.error(f"❌ DBT Build Failed with return code {result.returncode}")
                logger.error(f"DBT Error: {result.stderr}")
                raise AirflowException("DBT Build Failed")

            return 1

        except subprocess.TimeoutExpired:
            logger.error("❌ DBT Build Timed Out (600 seconds)")
            raise AirflowException("DBT Build Timeout") from None
        except Exception as e:
            logger.error(f"❌ DBT Build Error: {str(e)}")
            raise AirflowException("DBT Build failed") from e
    def refresh_redis_cache(**context):
        try:
            engine = create_engine(os.getenv('fullpath'))
            Session = sessionmaker(bind=engine)
            session = Session()

            query = "SELECT * FROM players"
            result = session.execute(text(query))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())

            row_count = len(df)
            logger.info(f"✅ Fetched {row_count:,} players from database")

            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str)

            json_data = df.to_json(orient='records', date_format='iso')
            r.setex("cache:players:all", 3600, json_data)

            memory_mb = len(json_data) / (1024 * 1024)
            logger.info(f"✅ Cached {row_count:,} players ({memory_mb:.2f} MB) in Redis")
            return 1

        except Exception as e:
            logger.error(f"❌ Redis Cache Refresh Failed: {str(e)}")
            raise AirflowException("Redis Cache Refresh Failed") from e
        finally:
            if 'session' in locals(): session.close()

    def maintenance(**context):
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

            # Check for bloated tables
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

                        # IMPORTANT: VACUUM must run with autocommit
                        with engine.connect() as conn:
                            conn.execution_options(isolation_level="AUTOCOMMIT")
                            conn.execute(text(f"VACUUM ANALYZE {table};"))

                        log(f"✅ VACUUM ANALYZE completed on {table}")

                    except Exception as ve:
                        log(f"❌ Failed to vacuum {table}: {ve}")
                        # Don't raise here, continue with other tables
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
    t3 = PythonOperator(task_id="load_new_matches_from_rds", python_callable=load_new_matches_from_rds)
    t4 = PythonOperator(task_id="bulk_validate_player_status", python_callable=bulk_validate_player_status)
    t5 = PythonOperator(task_id="refresh_redis_cache", python_callable=refresh_redis_cache)
    t6 = PythonOperator(task_id="dbt_build", python_callable=dbt_build_with_xcom)
    t7 = PythonOperator(task_id="maintenance", python_callable=maintenance)

    # Task Flow - Now if any task fails, downstream tasks will be marked as Upstream Failed
    t1 >> t2 >> t3 >> t4 >> t5 >> t6 >> t7