import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ====================== CONFIG ======================
url = os.getenv("fullpath")
engine = create_engine(url)
Session = sessionmaker(bind=engine)
session = Session()

# ==================== LOG DIRECTORY ====================
LOG_DIR = r"D:\my-postgres-project\logs"

# Create directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Log file name: maintenance_15_05_26.log
today = datetime.now()
log_filename = os.path.join(LOG_DIR, f"maintenance_{today.strftime('%d_%m_%y')}.log")

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)                    # Print to console
    
    try:
        with open(log_filename, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception as e:
        print(f"WARNING: Could not write to log file: {e}")

# ====================== START ======================
log("=== Database Maintenance Started ===")
log(f"Log file: {log_filename}")

# ==================== 1. Check for bloated tables (>= 15% dead) ====================
log("Checking tables with high dead tuples...")

result = session.execute(text("""
    SELECT 
        relname,
        n_live_tup AS live,
        n_dead_tup AS dead,
        ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct,
        seq_scan,
        idx_scan,
        last_autovacuum
    FROM pg_stat_user_tables
    WHERE n_dead_tup > 0.15 * n_live_tup          -- 15% threshold
    ORDER BY n_dead_tup DESC;
"""))

bloated_tables = []

for row in result.mappings():
    log(f"Table: {row['relname']:<20} | "
        f"Live: {row['live']:>8,} | "
        f"Dead: {row['dead']:>8,} | "
        f"Dead%: {row['dead_pct']:>5.1f}%  →  NEEDS VACUUM")
    
    bloated_tables.append(row['relname'])

# ==================== 2. Run VACUUM on bloated tables ====================
if bloated_tables:
    log(f"Found {len(bloated_tables)} table(s) needing VACUUM. Starting vacuum...")
    for table in bloated_tables:
        try:
            log(f"Running VACUUM ANALYZE on {table} ...")
            session.execute(text(f"VACUUM ANALYZE {table};"))
            session.commit()
            log(f"✅ VACUUM ANALYZE completed on {table}")
        except Exception as e:
            log(f"❌ ERROR vacuuming {table}: {e}")
            session.rollback()
else:
    log("✅ No tables need vacuuming (all below 15% dead tuples)")

# ==================== 3. Show final table sizes ====================
log("\n=== Table Sizes After Maintenance ===")

size_query = text("""
    SELECT 
        table_name,
        pg_size_pretty(pg_total_relation_size('public.' || table_name)) AS size
    FROM information_schema.tables 
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name;
""")

result2 = session.execute(size_query)

log(f"{'Table Name':<25} {'Size':>12}")
log("-" * 45)

for row in result2.mappings():
    log(f"{row['table_name']:<25} {row['size']:>12}")

log("=== Database Maintenance Completed Successfully ===\n")

session.close()