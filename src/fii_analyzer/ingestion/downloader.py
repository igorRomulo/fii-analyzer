import httpx
import pybreaker
import logging
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

from fii_analyzer.config import settings

logger = logging.getLogger(__name__)
breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=30)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((httpx.RequestError, pybreaker.CircuitBreakerError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
@breaker

def fetch_fii_data(url: str):
    year = datetime.now().year
    request_url = f"{settings.cvm_base_url}/{url}{year}.zip"
    logger.info("Downloading FII data from %s", request_url)
    response = httpx.get(request_url)
    response.raise_for_status()
    logger.info("Downloaded %d bytes", len(response.content))
    return response
