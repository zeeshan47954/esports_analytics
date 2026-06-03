import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import redis
import os
from dotenv import load_dotenv
import logging
import sys
import traceback

# ====================== CONFIG ======================
load_dotenv()

LOG_DIR = r"D:\my-postgres-project\logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"pipeline_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

url = os.getenv("fullpath")
engine = create_engine(url)
Session = sessionmaker(bind=engine)

# ====================== FUNCTIONS ======================

def healthcheck_RDS():
    start = datetime.now()
    logger.info(f"healthcheck_RDS STARTED at {start}")
    try:
        session = Session()
        session.execute(text("SELECT 1"))
        session.close()
        end = datetime.now()
        logger.info(f"healthcheck_RDS COMPLETED SUCCESSFULLY at {end} | Duration: {end-start}")
        return True
    except Exception as e:
        logger.error(f"healthcheck_RDS FAILED | Error: {e}")
        logger.error(traceback.format_exc())
        return False


def redischeck():
    start = datetime.now()
    logger.info(f"redischeck STARTED at {start}")
    try:
        r = redis.Redis(
            host='localhost', 
            port=6379, 
            db=0, 
            decode_responses=True, 
            password='secret123',
            socket_connect_timeout=5
        )
        r.ping()                    # Proper health check
        end = datetime.now()
        logger.info(f"redischeck COMPLETED SUCCESSFULLY at {end} | Duration: {end-start}")
        return True
    except Exception as e:
        logger.error(f"redischeck FAILED | Error: {e}")
        logger.error(traceback.format_exc())
        return False


def running_db_maintenace():
    start = datetime.now()
    logger.info(f"running_db_maintenace STARTED at {start}")
    try:
        import db_maintanence          # Better than exec()
        # Call the main function if it exists, otherwise run module level code
        if hasattr(db_maintanence, 'main'):
            db_maintanence.main()
        else:
            # If no main(), just importing might be enough (if it has top-level code)
            pass
        end = datetime.now()
        logger.info(f"running_db_maintenace COMPLETED SUCCESSFULLY at {end} | Duration: {end-start}")
        return True
    except Exception as e:
        logger.error(f"running_db_maintenace FAILED | Error: {e}")
        logger.error(traceback.format_exc())
        return False


def export_matches():
    start = datetime.now()
    logger.info(f"export_matches STARTED at {start}")
    try:
        import exportmatches           # Better to use import instead of exec
        if hasattr(exportmatches, 'main'):
            exportmatches.main()
        end = datetime.now()
        logger.info(f"export_matches COMPLETED SUCCESSFULLY at {end} | Duration: {end-start}")
        return True
    except Exception as e:
        logger.error(f"export_matches FAILED | Error: {e}")
        logger.error(traceback.format_exc())
        return False


def export_rankings():
    start = datetime.now()
    logger.info(f"export_rankings STARTED at {start}")
    try:
        import export_rankings
        if hasattr(export_rankings, 'main'):
            export_rankings.main()
        end = datetime.now()
        logger.info(f"export_rankings COMPLETED SUCCESSFULLY at {end} | Duration: {end-start}")
        return True
    except Exception as e:
        logger.error(f"export_rankings FAILED | Error: {e}")
        logger.error(traceback.format_exc())
        return False


# ====================== PIPELINE ======================

def run_pipeline():
    logger.info("="*80)
    logger.info(f"PIPELINE STARTED at {datetime.now()}")
    logger.info("="*80)

    steps = [
        ("RDS Health Check", healthcheck_RDS),
        ("Redis Health Check", redischeck),
        ("DB Maintenance", running_db_maintenace),
        ("Export Matches", export_matches),
        ("Export Rankings", export_rankings),
    ]

    for step_name, step_func in steps:
        success = step_func()
        if not success:
            logger.critical(f"PIPELINE STOPPED at step: {step_name} due to failure.")
            logger.info(f"PIPELINE ENDED WITH FAILURE at {datetime.now()}")
            return False

    logger.info("="*80)
    logger.info(f"PIPELINE COMPLETED SUCCESSFULLY at {datetime.now()}")
    logger.info("="*80)
    return True


if __name__ == "__main__":
    run_pipeline()