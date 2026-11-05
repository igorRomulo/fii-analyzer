from fii_analyzer.db.model import create_tables
from fii_analyzer.ingestion.pipeline import run_pipeline
from fii_analyzer.config import setup_logging

if __name__ == "__main__":
    setup_logging()
    create_tables()
    run_pipeline()