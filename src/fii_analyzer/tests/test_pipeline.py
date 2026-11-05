from unittest.mock import MagicMock, patch

from fii_analyzer.ingestion.pipeline import run_pipeline


class TestRunPipeline:
    @patch("fii_analyzer.ingestion.pipeline.extract_data")
    @patch("fii_analyzer.ingestion.pipeline.fetch_fii_data")
    def test_calls_extract_on_success(self, mock_fetch, mock_extract):
        mock_response = MagicMock()
        mock_fetch.return_value = mock_response

        run_pipeline()

        mock_fetch.assert_called_once()
        mock_extract.assert_called_once_with(mock_response)

    @patch("fii_analyzer.ingestion.pipeline.extract_data")
    @patch("fii_analyzer.ingestion.pipeline.fetch_fii_data")
    def test_does_not_extract_on_download_failure(self, mock_fetch, mock_extract):
        mock_fetch.side_effect = RuntimeError("network error")

        run_pipeline()

        mock_extract.assert_not_called()
