import logging

from fii_analyzer.ingestion.downloader import fetch_fii_data
from fii_analyzer.ingestion.ingest import extract_data
from fii_analyzer.config import settings

logger = logging.getLogger(__name__)

def run_pipeline():
    try:
        data = fetch_fii_data(settings.cvm_url_monthly_fii)
    except Exception:
        logger.exception("Failed to download FII data after all retries")
        return
    extract_data(data)