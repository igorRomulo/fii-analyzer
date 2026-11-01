import csv
import io
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from fii_analyzer.ingestion.ingest import build_data, extract_data, strip_accents


class TestStripAccents:
    def test_removes_accents(self):
        assert strip_accents("ação") == "acao"

    def test_handles_cedilla(self):
        assert strip_accents("preço") == "preco"

    def test_leaves_plain_ascii(self):
        assert strip_accents("hello") == "hello"

    def test_empty_string(self):
        assert strip_accents("") == ""

    def test_mixed_accents(self):
        assert strip_accents("Número_Cotistas_Não_Financeira") == "Numero_Cotistas_Nao_Financeira"


class TestBuildData:
    def _make_csv_in_memory(self, filename: str, rows: list[dict], encoding: str = "utf-8"):
        buf = io.BytesIO()
        text = io.TextIOWrapper(buf, encoding=encoding)
        writer = csv.DictWriter(text, fieldnames=list(rows[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
        text.flush()
        buf.seek(0)
        raw = buf.read()

        result = io.BytesIO(raw)
        result.name = filename
        return result

    def test_renames_cnpj_fundo_classe(self):
        year = 2024
        f = self._make_csv_in_memory(
            f"inf_mensal_fii_ativo_passivo_{year}.csv",
            [{"CNPJ_Fundo_Classe": "12.345.678/0001-00", "Data_Referencia": "2024-01-31"}],
            encoding="utf-8",
        )
        rows = build_data(f, year)
        assert len(rows) == 1
        assert "cnpj_fundo" in rows[0]
        assert "cnpj_fundo_classe" not in rows[0]

    def test_renames_nome_fundo_classe_for_geral(self):
        year = 2024
        f = self._make_csv_in_memory(
            f"inf_mensal_fii_geral_{year}.csv",
            [{"CNPJ_Fundo_Classe": "12.345.678/0001-00", "Nome_Fundo_Classe": "FII Test", "Versao": "1"}],
            encoding="cp1252",
        )
        rows = build_data(f, year)
        assert "nome_fundo" in rows[0]
        assert "nome_fundo_classe" not in rows[0]

    def test_empty_values_become_none(self):
        year = 2024
        f = self._make_csv_in_memory(
            f"inf_mensal_fii_ativo_passivo_{year}.csv",
            [{"CNPJ_Fundo_Classe": "12.345.678/0001-00", "Some_Field": ""}],
            encoding="utf-8",
        )
        rows = build_data(f, year)
        assert rows[0]["some_field"] is None

    def test_keys_are_lowercased_and_accent_stripped(self):
        year = 2024
        f = self._make_csv_in_memory(
            f"inf_mensal_fii_ativo_passivo_{year}.csv",
            [{"CNPJ_Fundo_Classe": "123", "Descrição": "text"}],
            encoding="utf-8",
        )
        rows = build_data(f, year)
        assert "descricao" in rows[0]


class TestExtractData:
    def _make_zip_response(self, files: dict[str, str]) -> MagicMock:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for name, content in files.items():
                zf.writestr(name, content)
        buf.seek(0)
        response = MagicMock()
        response.content = buf.getvalue()
        return response

    @patch("fii_analyzer.ingestion.ingest.insert_data")
    @patch("fii_analyzer.ingestion.ingest.datetime")
    def test_dispatches_ativo_passivo(self, mock_dt, mock_insert):
        mock_dt.now.return_value.year = 2024
        csv_content = "CNPJ_Fundo_Classe;Data_Referencia\n12.345;2024-01-31\n"
        response = self._make_zip_response({f"inf_mensal_fii_ativo_passivo_2024.csv": csv_content})

        extract_data(response)

        mock_insert.assert_called_once()
        call_args = mock_insert.call_args
        assert call_args[0][0] == "inf_mensal_fii_ativo_passivo_2024.csv"

    @patch("fii_analyzer.ingestion.ingest.insert_data")
    @patch("fii_analyzer.ingestion.ingest.datetime")
    def test_skips_unrecognized_files(self, mock_dt, mock_insert):
        mock_dt.now.return_value.year = 2024
        response = self._make_zip_response({"random_file_2024.csv": "col1;col2\na;b\n"})

        extract_data(response)

        mock_insert.assert_not_called()

    @patch("fii_analyzer.ingestion.ingest.insert_data")
    @patch("fii_analyzer.ingestion.ingest.datetime")
    def test_continues_on_failure(self, mock_dt, mock_insert):
        mock_dt.now.return_value.year = 2024
        csv1 = "CNPJ_Fundo_Classe;Data_Referencia\n12.345;2024-01-31\n"
        csv2 = "CNPJ_Fundo_Classe;Data_Referencia\n67.890;2024-01-31\n"
        files = {
            f"inf_mensal_fii_ativo_passivo_2024.csv": csv1,
            f"inf_mensal_fii_complemento_2024.csv": csv2,
        }
        response = self._make_zip_response(files)

        mock_insert.side_effect = [RuntimeError("boom"), None]
        extract_data(response)

        assert mock_insert.call_count == 2
