import os
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError

load_dotenv()

# ============== Configuration ==============
DATABASE_URL = os.getenv("fullpath")   # Better to rename this to DATABASE_URL in .env

if not DATABASE_URL:
    raise ValueError("❌ No database URL found in .env file. Check 'fullpath' variable.")

# ============== Create Engine ==============
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,           # Helps detect dead connections
    pool_recycle=3600,            # Recycle connections after 1 hour
    connect_args={"connect_timeout": 10},
    echo=False                    # Set True for debugging SQL
)

# ============== Retry Logic ==============
max_retries = 3
backoff_time = 1

SessionLocal = sessionmaker(bind=engine)   # Factory, don't overwrite it
global session
for attempt in range(1, max_retries + 1):
    session = None
    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            print(f"✅ Test query result: {result.scalar()}")   # Should print 1

        # Create session for further use
        session = SessionLocal()
        
        print("✅ SQLAlchemy session created successfully")
        print(f"Connected to: {engine.url.database}")
        
        break  # Success → exit loop

    except OperationalError as e:
        print(f"❌ Attempt {attempt}/{max_retries} failed: {e}")
        
        if attempt == max_retries:
            print("\n🔴 All retry attempts failed!")
            print("💡 Please check your DATABASE_URL in the .env file")
            break
        else:
            sleep_seconds = backoff_time * (2 ** (attempt - 1))
            print(f"   Retrying in {sleep_seconds} seconds...")
            import time
            time.sleep(sleep_seconds)

    except SQLAlchemyError as e:
        print(f"❌ SQLAlchemy error on attempt {attempt}: {e}")
        break

    except Exception as e:
        print(f"❌ Unexpected error on attempt {attempt}: {e}")
        break

    finally:
        if session:
            session.close()

print("🔧 Setup completed.")
from models_recreation import Base
print(Base.metadata.tables.keys())   # Should print your table names