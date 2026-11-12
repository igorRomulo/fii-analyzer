import logging
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+psycopg2://fii:fii123@localhost:5432/fii_analyzer"

    #Log
    log_level: str = "INFO"

    # CVM
    cvm_base_url: str = "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS"
    cvm_url_monthly_fii: str = "inf_mensal_fii_"
    data_start_year: int = 2016

    # Gemini (ADR-001)
    google_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"

    model_config = {"env_file": ".env"}


settings = Settings()


def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )