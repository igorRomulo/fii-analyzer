import logging
from unittest.mock import patch

from fii_analyzer.config import Settings, setup_logging


class TestSettings:
    def test_default_database_url(self):
        with patch.dict("os.environ", {}, clear=True):
            s = Settings(_env_file=None)
        assert "postgresql" in s.database_url
        assert "fii_analyzer" in s.database_url

    def test_default_cvm_base_url(self):
        with patch.dict("os.environ", {}, clear=True):
            s = Settings(_env_file=None)
        assert "dados.cvm.gov.br" in s.cvm_base_url

    def test_default_data_start_year(self):
        with patch.dict("os.environ", {}, clear=True):
            s = Settings(_env_file=None)
        assert s.data_start_year == 2016

    def test_env_override(self):
        with patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"}, clear=False):
            s = Settings(_env_file=None)
        assert s.log_level == "DEBUG"


class TestSetupLogging:
    def test_configures_logging(self):
        setup_logging()
        root = logging.getLogger()
        assert root.level is not None
