import boto3
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
import sys
import uuid  # added for safety

# Load environment variables
load_dotenv()

# ========================= CONFIG =========================
BUCKET = os.getenv("BUCKET")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

# Initialize S3 client
try:
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    print("✅ Successfully connected to S3")
except Exception as e:
    print(f"❌ Failed to connect to S3: {e}")
    sys.exit(1)


# ======================= HELPER FUNCTIONS =======================

def get_partition_prefix(base_prefix: str = "match-exports") -> str:
    now = datetime.now()
    return f"{base_prefix}/year={now.year}/month={now.month:02d}/day={now.day:02d}"


def upload_as_csv(df: pd.DataFrame, base_prefix: str = "match-exports", filename: str = "matches.csv"):
    try:
        partition_path = get_partition_prefix(base_prefix)
        s3_key = f"{partition_path}/{filename}"
        
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        s3.put_object(Bucket=BUCKET, Key=s3_key, Body=csv_buffer.getvalue())
        print(f"✅ CSV uploaded: {s3_key}")
        
    except Exception as e:
        print(f"❌ Error uploading CSV: {e}")


def upload_as_parquet(df: pd.DataFrame, base_prefix: str = "match-exports", filename: str = "matches.parquet"):
    """Fixed version - handles UUID columns"""
    try:
        # === FIX: Convert UUID columns to string ===
        df = df.copy()  # avoid modifying original
        
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]):
                # Check if column contains UUIDs
                sample = df[col].dropna().iloc[:5] if len(df[col].dropna()) > 0 else []
                if any(isinstance(x, uuid.UUID) for x in sample):
                    print(f"🔄 Converting UUID column '{col}' to string")
                    df[col] = df[col].astype(str)
        
        # Now write to Parquet
        partition_path = get_partition_prefix(base_prefix)
        s3_key = f"{partition_path}/{filename}"
        
        parquet_buffer = BytesIO()
        df.to_parquet(
            parquet_buffer, 
            index=False, 
            compression='snappy',
            engine='pyarrow'
        )
        parquet_buffer.seek(0)

        s3.put_object(Bucket=BUCKET, Key=s3_key, Body=parquet_buffer.getvalue())
        print(f"✅ Parquet uploaded: {s3_key}")
        
    except Exception as e:
        print(f"❌ Error uploading Parquet: {e}")


def delete_old_partitions(prefix: str = "match-exports", days_to_keep: int = 90, dry_run: bool = True):
    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        print(f"🗑️  Finding files older than {days_to_keep} days (before {cutoff_date.date()})...")

        paginator = s3.get_paginator('list_objects_v2')
        delete_candidates = []
        total_files = 0

        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
            if "Contents" not in page:
                continue
            for obj in page["Contents"]:
                total_files += 1
                last_modified = obj['LastModified'].replace(tzinfo=None)
                
                if last_modified < cutoff_date:
                    delete_candidates.append({"Key": obj['Key']})

        print(f"📊 Found {len(delete_candidates)} files to delete out of {total_files} total files.")

        if not delete_candidates:
            print("✅ No old files to delete.")
            return

        if dry_run:
            print("\n🔍 DRY RUN: These files would be deleted:")
            for item in delete_candidates[:15]:
                print(f"   - {item['Key']}")
            if len(delete_candidates) > 15:
                print(f"   ... and {len(delete_candidates)-15} more")
            return

        # Batch delete
        deleted_count = 0
        for i in range(0, len(delete_candidates), 1000):
            batch = delete_candidates[i:i+1000]
            s3.delete_objects(Bucket=BUCKET, Delete={'Objects': batch, 'Quiet': True})
            deleted_count += len(batch)
            print(f"🗑️  Deleted {len(batch)} files")

        print(f"✅ Successfully deleted {deleted_count} old files.")

    except Exception as e:
        print(f"❌ Error during deletion: {e}")


# ========================= MAIN =========================
if __name__ == "__main__":
    try:
        from sqlalchemy import create_engine

        engine = create_engine(os.getenv('fullpath'))
        
        print("📊 Fetching data from database...")
        df = pd.read_sql_query("SELECT * FROM matches LIMIT 10000", engine)
        print(f"✅ Fetched {df.shape[0]:,} rows")

        upload_as_csv(df, base_prefix="match-exports", filename="matches.csv")
        upload_as_parquet(df, base_prefix="match-exports", filename="matches.parquet")

        # delete_old_partitions(days_to_keep=90, dry_run=True)

    except Exception as e:
        print(f"❌ Critical error: {e}")