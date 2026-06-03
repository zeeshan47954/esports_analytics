import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import json
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("fullpath")
engine = create_engine(url)
Session = sessionmaker(bind=engine)
session = Session()

# ====================== CONFIG ======================
EXPORT_DIR = r"D:\my-postgres-project\exports\ranking"
os.makedirs(EXPORT_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename_base = f"top_100_players_{timestamp}"

csv_path = os.path.join(EXPORT_DIR, f"{filename_base}.csv")
json_path = os.path.join(EXPORT_DIR, f"{filename_base}.json")

# ====================== Fetch Data ======================
query = """
    SELECT * 
    FROM players 
    ORDER BY elo_rating DESC 
    LIMIT 100
"""

df = pd.read_sql(text(query), engine)

# ====================== CLEAN DATA (Very Important) ======================
# Remove or fix problematic Unicode characters
for col in df.select_dtypes(include=['object']).columns:
    df[col] = df[col].astype(str).apply(
        lambda x: x.encode('utf-8', errors='replace').decode('utf-8')
    )

# Optional: Replace any remaining bad characters
df = df.replace({r'[\ud800-\udfff]': ''}, regex=True)

# ====================== Save Files ======================
df.to_csv(csv_path, index=False, encoding='utf-8')

# Safer JSON export using Python's json module
records = df.to_dict(orient='records')

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(
        records, 
        f, 
        indent=2, 
        ensure_ascii=False,      # Allows real Unicode characters
        default=str              # Handles datetime, UUID etc.
    )

print(f"✅ Export completed successfully!")
print(f"   • CSV  → {csv_path}")
print(f"   • JSON → {json_path}")
print(f"   • Total rows: {len(df)}")

session.close()