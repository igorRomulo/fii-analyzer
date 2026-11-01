from unittest.mock import MagicMock, patch

import httpx
import pytest

from fii_analyzer.ingestion.downloader import fetch_fii_data


class TestFetchFiiData:
    @patch("fii_analyzer.ingestion.downloader.httpx.get")
    @patch("fii_analyzer.ingestion.downloader.datetime")
    def test_builds_correct_url(self, mock_dt, mock_get):
        mock_dt.now.return_value.year = 2024
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"zipdata"
        mock_get.return_value = mock_response

        result = fetch_fii_data("inf_mensal_fii_")

        mock_get.assert_called_once_with(
            "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_2024.zip"
        )
        mock_response.raise_for_status.assert_called_once()
        assert result is mock_response

    @patch("fii_analyzer.ingestion.downloader.httpx.get")
    @patch("fii_analyzer.ingestion.downloader.datetime")
    def test_raises_on_http_error(self, mock_dt, mock_get):
        mock_dt.now.return_value.year = 2024
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )
        mock_get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            fetch_fii_data("inf_mensal_fii_")
