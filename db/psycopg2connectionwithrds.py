import psycopg2
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

def connection_establish():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        # Optional: better defaults
        connect_timeout=10,
    )

# ============== Retry with Exponential Backoff ==============
max_retries = 3
backoff_time = 1
con = None

for attempt in range(1, max_retries + 1):
    try:
        con = connection_establish()
        
        print("✅ Database connection successful!")
        print(f"Connection closed? {con.closed}")           # Should be 0
        print(f"Connection status: {con.info.status}")
        print(f"PostgreSQL version: {con.server_version}")
        print(f"Connected to database: {con.info.dbname}")
        
        # Test query
        with con.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"✅ Server responded: {version}")
        
        break  # Success → exit retry loop

    except psycopg2.OperationalError as e:
        print(f"❌ Attempt {attempt}/{max_retries} failed: {e}")
        
        if attempt == max_retries:
            print("\n🔴 All retry attempts failed!")
            print("💡 Please check your credentials in the .env file")
            con = None
            break
        else:
            sleep_seconds = backoff_time * (2 ** (attempt - 1))
            print(f"   Retrying in {sleep_seconds} seconds...")
            time.sleep(sleep_seconds)
    
    except Exception as e:
        print(f"❌ Unexpected error on attempt {attempt}: {e}")
        con = None
        break

    finally:
        # Cleanup only if connection was created but failed later
        if con is not None and not con.closed and attempt == max_retries:
            con.close()
            print("🔌 Connection closed after failure.")

# Final success cleanup
if con is not None and not con.closed:
    # You can keep it open if you want to use it further,
    # or close it here.
    # con.close()
    # print("🔌 Connection closed.")
    pass

with con.cursor() as cursor:
    cursor.execute("select 1")
    print(cursor.fetchone())