import boto3
import os
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd
from io import BytesIO
import sys
import uuid

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

def get_partition_prefix(base_prefix: str = "views_from_postgre") -> str:
    now = datetime.now()
    return f"{base_prefix}/year={now.year}/month={now.month:02d}/day={now.day:02d}"


def upload_as_csv(df: pd.DataFrame, base_prefix: str = "views_from_postgre", filename: str = "data.csv"):
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


def upload_as_parquet(df: pd.DataFrame, base_prefix: str = "views_from_postgre", filename: str = "data.parquet"):
    try:
        df = df.copy()
        
        # Convert UUIDs to string
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]):
                sample = df[col].dropna().iloc[:5] if len(df[col].dropna()) > 0 else []
                if any(isinstance(x, uuid.UUID) for x in sample):
                    print(f"🔄 Converting UUID column '{col}' to string")
                    df[col] = df[col].astype(str)
        
        partition_path = get_partition_prefix(base_prefix)
        s3_key = f"{partition_path}/{filename}"
        
        parquet_buffer = BytesIO()
        df.to_parquet(parquet_buffer, index=False, compression='snappy', engine='pyarrow')
        parquet_buffer.seek(0)

        s3.put_object(Bucket=BUCKET, Key=s3_key, Body=parquet_buffer.getvalue())
        print(f"✅ Parquet uploaded: {s3_key}")
        
    except Exception as e:
        print(f"❌ Error uploading Parquet: {e}")



# ========================= MAIN =========================
if __name__ == "__main__":
    try:
        from sqlalchemy import create_engine

        engine = create_engine(os.getenv('fullpath'))
        
        print("📊 Fetching data from database...")

        # Table 1
        df1 = pd.read_sql_query("SELECT * FROM esports_dev.int_player_match_summary limit 1000", engine)
        print(f"✅ Fetched int_player_match_summary: {df1.shape[0]:,} rows")
        
        upload_as_csv(df1, filename="int_player_match_summary.csv")
        upload_as_parquet(df1, filename="int_player_match_summary.parquet")
       

        # Table 2 - Check if table exists first
        try:
            df2 = pd.read_sql_query("SELECT * FROM esports_dev.int_team_match_summary_aggregated limit 1000", engine)
            print(f"✅ Fetched int_team_match_summary_aggregated: {df2.shape[0]:,} rows")
            
            upload_as_csv(df2, filename="int_team_match_summary_aggregated.csv")
            upload_as_parquet(df2, filename="int_team_match_summary_aggregated.parquet")
           
        except Exception as e:
            print(f"⚠️  Skipping aggregated table: {e}")

        # Table 3
        try:
            df3 = pd.read_sql_query("SELECT * FROM esports_dev.tournament_standings limit 1000", engine)
            print(f"✅ Fetched tournament_standings: {df3.shape[0]:,} rows")
            
            upload_as_csv(df3, filename="tournament_standings.csv")
            upload_as_parquet(df3, filename="tournament_standings.parquet")
            
        except Exception as e:
            print(f"⚠️  Skipping tournament_standings: {e}")

    except Exception as e:
        print(f"❌ Critical error: {e}")


