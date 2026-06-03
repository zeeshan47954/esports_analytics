import pandas as pd
from sqlalchemy import create_engine
import os

engine = create_engine(os.getenv('fullpath'))

df3 = pd.read_sql_query("SELECT * FROM esports_dev.tournament_standings limit 1000", engine)

for col in df3.select_dtypes(include='object').columns:
    try:
        sample = df3[col].astype(str).iloc[:10].to_json()
        print(f"✅ Column '{col}' looks clean")
    except Exception as e:
        print(f"❌ Problem in column '{col}': {e}")
        
        # Show suspicious values
        print("Sample values:")
        print(df3[col].astype(str).head(10))        