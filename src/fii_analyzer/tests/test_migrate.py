import re
import tempfile
import zipfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlalchemy import BigInteger, Date, Integer, Numeric, String, Text

from fii_analyzer.ingestion.migrate import (
    FUND_ANNUAL_COLUMNS,
    FUND_MONTHLY_COLUMNS,
    MONTHLY_BALANCE_COLUMNS,
    MONTHLY_METRICS_COLUMNS,
    TABLE_CONFIGS,
    _build_shareholder_dist_columns,
    _cols,
    _dedupe_batch,
    _zip_sort_key,
    convert_value,
    discover_zips,
    find_config,
    normalize_df,
    strip_accents,
)
from fii_analyzer.db.model import (
    FiiBalancoMensal,
    FiiFundoAnual,
    FiiFundoMensal,
    FiiMetricaMensal,
)


class TestStripAccents:
    def test_removes_diacritics(self):
        assert strip_accents("Número") == "Numero"

    def test_plain_ascii_unchanged(self):
        assert strip_accents("hello") == "hello"

    def test_empty(self):
        assert strip_accents("") == ""


class TestConvertValue:
    def test_none_returns_none(self):
        assert convert_value(None, String()) is None

    def test_nan_returns_none(self):
        assert convert_value(float("nan"), Integer()) is None

    def test_empty_string_returns_none(self):
        assert convert_value("", String()) is None
        assert convert_value("  ", String()) is None

    def test_date_valid(self):
        result = convert_value("2024-01-15", Date())
        assert result == date(2024, 1, 15)

    def test_date_invalid(self):
        assert convert_value("not-a-date", Date()) is None

    def test_integer(self):
        assert convert_value("42", Integer()) == 42

    def test_integer_from_float_string(self):
        assert convert_value("42.7", Integer()) == 42

    def test_integer_invalid(self):
        assert convert_value("abc", Integer()) is None

    def test_biginteger(self):
        assert convert_value("1000000000", BigInteger()) == 1000000000

    def test_numeric(self):
        result = convert_value("123.45", Numeric())
        assert result == Decimal("123.45")

    def test_numeric_invalid(self):
        assert convert_value("abc", Numeric()) is None

    def test_string(self):
        assert convert_value("hello", String()) == "hello"

    def test_text(self):
        assert convert_value("long text here", Text()) == "long text here"


class TestNormalizeDf:
    def test_renames_cnpj_fundo_classe(self):
        df = pd.DataFrame({"CNPJ_Fundo_Classe": ["123"], "Data_Referencia": ["2024-01-01"]})
        result = normalize_df(df)
        assert "CNPJ_Fundo" in result.columns
        assert "CNPJ_Fundo_Classe" not in result.columns

    def test_renames_nome_fundo_classe(self):
        df = pd.DataFrame({"Nome_Fundo_Classe": ["FII Test"], "Other": ["x"]})
        result = normalize_df(df)
        assert "Nome_Fundo" in result.columns

    def test_strips_accents_from_columns(self):
        df = pd.DataFrame({"Número_Cotistas": [100]})
        result = normalize_df(df)
        assert "Numero_Cotistas" in result.columns

    def test_no_rename_when_columns_absent(self):
        df = pd.DataFrame({"CNPJ_Fundo": ["123"], "Nome_Fundo": ["Test"]})
        result = normalize_df(df)
        assert list(result.columns) == ["CNPJ_Fundo", "Nome_Fundo"]


class TestCols:
    def test_maps_names_to_lowercase(self):
        result = _cols("CNPJ_Fundo", "Data_Referencia")
        assert result == {"CNPJ_Fundo": "cnpj_fundo", "Data_Referencia": "data_referencia"}


class TestBuildShareholderDistColumns:
    def test_contains_all_faixas(self):
        cols = _build_shareholder_dist_columns()
        assert "CNPJ_Fundo" in cols
        assert "Data_Referencia" in cols
        assert "Numero_Cotistas_Faixa_Ate_5" in cols
        assert "Numero_Cotistas_Faixa_Acima_50" in cols
        assert "Percentual_Detido_PJ_Faixa_30a40" in cols

    def test_values_are_lowercase(self):
        cols = _build_shareholder_dist_columns()
        for v in cols.values():
            assert v == v.lower()


class TestDedupeBatch:
    def test_keeps_last_duplicate(self):
        batch = [
            {"pk": "a", "val": 1},
            {"pk": "a", "val": 2},
            {"pk": "b", "val": 3},
        ]
        result = _dedupe_batch(batch, ["pk"])
        assert len(result) == 2
        vals = {r["pk"]: r["val"] for r in result}
        assert vals["a"] == 2
        assert vals["b"] == 3

    def test_composite_pk(self):
        batch = [
            {"k1": "a", "k2": 1, "val": "first"},
            {"k1": "a", "k2": 1, "val": "second"},
            {"k1": "a", "k2": 2, "val": "third"},
        ]
        result = _dedupe_batch(batch, ["k1", "k2"])
        assert len(result) == 2

    def test_no_duplicates(self):
        batch = [{"pk": "a", "val": 1}, {"pk": "b", "val": 2}]
        result = _dedupe_batch(batch, ["pk"])
        assert len(result) == 2


class TestFindConfig:
    def test_matches_monthly_geral(self):
        cfg = find_config("inf_mensal_fii_geral_2024.csv")
        assert cfg is not None
        assert cfg["model"].__tablename__ == "fii_fundo_mensal"

    def test_matches_annual_geral(self):
        cfg = find_config("inf_anual_fii_geral_2023.csv")
        assert cfg is not None
        assert cfg["model"].__tablename__ == "fii_fundo_anual"

    def test_matches_complemento(self):
        cfg = find_config("inf_mensal_fii_complemento_2024.csv")
        assert cfg is not None
        assert cfg["model"].__tablename__ == "fii_metrica_mensal"

    def test_matches_ativo_passivo(self):
        cfg = find_config("inf_mensal_fii_ativo_passivo_2024.csv")
        assert cfg is not None
        assert cfg["model"].__tablename__ == "fii_balanco_mensal"

    def test_matches_annual_complemento(self):
        cfg = find_config("inf_anual_fii_complemento_2024.csv")
        assert cfg is not None
        assert cfg["model"].__tablename__ == "fii_narrativa_anual"

    def test_matches_transaction(self):
        cfg = find_config("inf_anual_fii_ativo_transacao_2024.csv")
        assert cfg is not None
        assert cfg["model"].__tablename__ == "fii_transacao_anual"

    def test_matches_lawsuit(self):
        cfg = find_config("inf_anual_fii_processo_2024.csv")
        assert cfg is not None
        assert cfg["model"].__tablename__ == "fii_processo_anual"

    def test_no_match(self):
        assert find_config("random_file.csv") is None


class TestZipSortKey:
    def test_sorts_by_year(self):
        p2023 = Path("inf_mensal_fii_geral_2023.zip")
        p2024 = Path("inf_mensal_fii_geral_2024.zip")
        assert _zip_sort_key(p2023) < _zip_sort_key(p2024)

    def test_mensal_before_anual_same_year(self):
        mensal = Path("inf_mensal_fii_geral_2024.zip")
        anual = Path("inf_anual_fii_geral_2024.zip")
        assert _zip_sort_key(mensal) < _zip_sort_key(anual)

    def test_no_year_in_name(self):
        p = Path("some_file.zip")
        year, kind = _zip_sort_key(p)
        assert year == 0


class TestDiscoverZips:
    def test_seed_returns_all(self, tmp_path):
        for name in ["inf_mensal_fii_geral_2023.zip", "inf_mensal_fii_geral_2024.zip", "inf_anual_fii_geral_2024.zip"]:
            (tmp_path / name).touch()
        result = discover_zips(tmp_path, "seed")
        assert len(result) == 3

    def test_update_returns_latest_of_each(self, tmp_path):
        for name in [
            "inf_mensal_fii_geral_2023.zip",
            "inf_mensal_fii_geral_2024.zip",
            "inf_anual_fii_geral_2023.zip",
            "inf_anual_fii_geral_2024.zip",
        ]:
            (tmp_path / name).touch()
        result = discover_zips(tmp_path, "update")
        names = [p.name for p in result]
        assert "inf_mensal_fii_geral_2024.zip" in names
        assert "inf_anual_fii_geral_2024.zip" in names
        assert len(result) == 2

    def test_no_zips_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            discover_zips(tmp_path, "seed")


def _model_columns(model) -> set[str]:
    return {
        col.name for col in model.__table__.columns
        if col.name not in ("created_at", "updated_at")
    }


class TestColumnMapCompleteness:
    def test_fund_monthly_covers_all_model_columns(self):
        mapped = set(FUND_MONTHLY_COLUMNS.values())
        model_cols = _model_columns(FiiFundoMensal)
        assert model_cols - mapped == set()

    def test_fund_annual_covers_all_model_columns(self):
        mapped = set(FUND_ANNUAL_COLUMNS.values())
        model_cols = _model_columns(FiiFundoAnual)
        assert model_cols - mapped == set()

    def test_monthly_metrics_covers_all_model_columns(self):
        mapped = set(MONTHLY_METRICS_COLUMNS.values())
        model_cols = _model_columns(FiiMetricaMensal)
        assert model_cols - mapped == set()

    def test_monthly_balance_covers_all_model_columns(self):
        mapped = set(MONTHLY_BALANCE_COLUMNS.values())
        model_cols = _model_columns(FiiBalancoMensal)
        assert model_cols - mapped == set()
