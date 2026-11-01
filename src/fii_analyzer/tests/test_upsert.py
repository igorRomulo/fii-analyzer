from unittest.mock import patch, call

from fii_analyzer.ingestion.upsert import insert_data


class TestInsertData:
    @patch("fii_analyzer.ingestion.upsert.insert_data_in_database")
    def test_routes_ativo_passivo_to_balanco(self, mock_insert):
        from fii_analyzer.db.model import FiiBalancoMensal

        insert_data("inf_mensal_fii_ativo_passivo_2024.csv", [{"row": 1}], 2024)
        mock_insert.assert_called_once_with(FiiBalancoMensal, [{"row": 1}])

    @patch("fii_analyzer.ingestion.upsert.insert_data_in_database")
    def test_routes_complemento_to_metrica(self, mock_insert):
        from fii_analyzer.db.model import FiiMetricaMensal

        insert_data("inf_mensal_fii_complemento_2024.csv", [{"row": 1}], 2024)
        mock_insert.assert_called_once_with(FiiMetricaMensal, [{"row": 1}])

    @patch("fii_analyzer.ingestion.upsert.insert_data_in_database")
    def test_routes_geral_to_fundo_mensal(self, mock_insert):
        from fii_analyzer.db.model import FiiFundoMensal

        insert_data("inf_mensal_fii_geral_2024.csv", [{"row": 1}], 2024)
        mock_insert.assert_called_once_with(FiiFundoMensal, [{"row": 1}])

    @patch("fii_analyzer.ingestion.upsert.insert_data_in_database")
    def test_no_match_does_nothing(self, mock_insert):
        insert_data("unknown_file.csv", [{"row": 1}], 2024)
        mock_insert.assert_not_called()
