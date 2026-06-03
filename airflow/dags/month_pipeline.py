from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException
from datetime import datetime, timedelta, timezone
import os
import logging
import subprocess
import gzip
import boto3
from dotenv import load_dotenv

load_dotenv()

# ========================= LOGGING SETUP =========================
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

file_handler = logging.FileHandler('/opt/airflow/logs/monthly_pipeline.log', mode='a', encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

default_args = {
    'owner': 'you',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='monthly_pipeline',
    default_args=default_args,
    description='Monthly Pipeline - RDS Backup + Old Backup Cleanup',
    schedule="0 2 * * *",
    start_date=datetime(2026, 5, 19),
    catchup=False,
    tags=['etl', 'backup', 'maintenance'],
) as dag:

    def backup_rds_to_local_and_s3(**context):
        """Backup RDS using PostgreSQL 18 client"""
        try:
            host = os.getenv("DB_HOST")
            user = os.getenv("DB_USER")
            password = os.getenv("DB_PASSWORD")
            database = os.getenv("DB_NAME")
            bucket_name = os.getenv("BUCKET")

            local_backup_dir = r"D:\dbeaverbackup"
            os.makedirs(local_backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.sql.gz"
            local_backup_path = os.path.join(local_backup_dir, backup_filename)
            s3_backup_key = f"backup/{backup_filename}"

            logger.info(f"Starting RDS Backup for database: {database}")

            cmd = [
                "docker", "run", "--rm",
                "-e", f"PGPASSWORD={password}",
                "postgres:18",
                "pg_dump",
                "-h", host,
                "-U", user,
                "-d", database,
                "--clean",
                "--if-exists",
                "--verbose"
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=1800
            )

            if result.returncode != 0:
                logger.error(f"pg_dump failed: {result.stderr.decode()}")
                raise AirflowException("pg_dump failed")

            with gzip.open(local_backup_path, 'wb') as f:
                f.write(result.stdout)

            file_size_mb = os.path.getsize(local_backup_path) / (1024 * 1024)
            logger.info(f"✅ Local backup created ({file_size_mb:.2f} MB)")

            s3_client = boto3.client(
                "s3",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION")
            )

            s3_client.upload_file(
                local_backup_path,
                bucket_name,
                s3_backup_key,
                ExtraArgs={'ContentType': 'application/gzip'}
            )

            logger.info(f"✅ Backup uploaded to S3: s3://{bucket_name}/{s3_backup_key}")

            context['task_instance'].xcom_push(key='backup_file', value=backup_filename)
            context['task_instance'].xcom_push(key='backup_s3_key', value=s3_backup_key)

            return 1

        except Exception as e:
            logger.error(f"❌ Backup failed: {str(e)}", exc_info=True)
            raise AirflowException("RDS Backup Failed") from e

    def cleanup_old_s3_backups(**context):
        """Delete backup files older than 90 days"""
        try:
            bucket_name = os.getenv("BUCKET")
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION")
            )

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
            deleted_count = 0
            deleted_size_mb = 0

            logger.info(f"Starting cleanup: Deleting objects older than 90 days in bucket '{bucket_name}'")

            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name, Prefix="backup/")

            for page in pages:
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    key = obj['Key']
                    last_modified = obj['LastModified']
                    size_mb = obj['Size'] / (1024 * 1024)

                    if last_modified < cutoff_date:
                        try:
                            s3_client.delete_object(Bucket=bucket_name, Key=key)
                            deleted_count += 1
                            deleted_size_mb += size_mb
                            logger.info(f"🗑️ Deleted: {key} ({size_mb:.2f} MB)")
                        except Exception as del_err:
                            logger.warning(f"Failed to delete {key}: {del_err}")

            logger.info(f"✅ Cleanup completed. Deleted {deleted_count} files ({deleted_size_mb:.2f} MB)")

            context['task_instance'].xcom_push(key='deleted_count', value=deleted_count)
            context['task_instance'].xcom_push(key='deleted_size_mb', value=round(deleted_size_mb, 2))

            return 1

        except Exception as e:
            logger.error(f"❌ S3 Cleanup failed: {str(e)}", exc_info=True)
            raise AirflowException("S3 Cleanup Failed") from e

    # ====================== TASKS ======================
    t_backup = PythonOperator(
        task_id="backup_rds_to_s3",
        python_callable=backup_rds_to_local_and_s3,
    )

    t_cleanup = PythonOperator(
        task_id="cleanup_old_backups",
        python_callable=cleanup_old_s3_backups,
    )

    # Task Flow
    t_backup >> t_cleanup