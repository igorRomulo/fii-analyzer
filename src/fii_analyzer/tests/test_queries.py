import pytest
from unittest.mock import MagicMock, call
from datetime import date
from decimal import Decimal

from fii_analyzer.db.queries import (
    find_fund_by_name,
    get_fund_info,
    list_funds_by_segment,
    list_funds_by_administrator,
    list_funds_by_state,
    list_all_segments,
    list_all_administrators,
    count_total_funds,
    count_funds_by_segment,
    get_fund_age,
    get_available_months,
    get_patrimonio_liquido,
    get_valor_ativo,
    get_valor_patrimonial_cotas,
    get_dividend_yield,
    get_rentabilidade_efetiva,
    get_rentabilidade_patrimonial,
    get_total_cotistas,
    get_cotistas_pf,
    get_cotistas_pj,
    get_cotas_emitidas,
    get_taxa_administracao,
    get_taxa_custodiante,
    get_amortizacao,
    get_total_investido,
    get_imoveis_renda,
    get_cri_cra,
    get_fii_holdings,
    get_total_passivo,
    get_disponibilidades,
    get_rendimentos_distribuir,
    get_valores_receber,
    get_contas_aluguel,
    get_liquidez,
    get_obrigacoes_securitizacao,
    get_provisoes,
    history_patrimonio_liquido,
    history_valor_ativo,
    history_valor_patrimonial,
    history_dividend_yield,
    history_rentabilidade_efetiva,
    history_rentabilidade_patrimonial,
    history_cotistas,
    history_cotistas_pf,
    history_cotas_emitidas,
    history_taxa_administracao,
    history_total_investido,
    history_imoveis_renda,
    history_cri_cra,
    history_fii_holdings,
    history_total_passivo,
    history_disponibilidades,
    history_rendimentos_distribuir,
    history_contas_aluguel,
    history_amortizacao,
    history_liquidez,
    rank_by_dividend_yield,
    rank_by_patrimonio_liquido,
    rank_by_valor_ativo,
    rank_by_cotistas,
    rank_by_cotistas_pf,
    rank_by_vpa,
    rank_by_rentabilidade,
    rank_by_cotas_emitidas,
    rank_by_total_investido,
    rank_by_imoveis,
    rank_by_cri_cra,
    rank_by_fii_holdings,
    rank_by_total_passivo,
    rank_by_disponibilidades,
    rank_by_lowest_admin_fee,
    rank_by_contas_aluguel,
    rank_by_rendimentos_distribuir,
    rank_smallest_funds,
    compare_funds_single_metric,
    compare_funds_full,
    compare_funds_dy_history,
    compare_funds_pl_history,
    compare_funds_cotistas_history,
    compare_funds_balance_sheet,
    compare_funds_fees,
    accumulated_dy,
    average_dy,
    annualized_dy,
    dy_last_12_months,
    average_rentabilidade,
    pl_variation,
    cotistas_variation,
    vpa_variation,
    dividend_per_cota_estimate,
    max_dy_period,
    min_dy_period,
    average_pl_period,
    cotas_emitidas_change,
    total_return_estimate,
    segment_average_dy,
    segment_average_pl,
    segment_total_pl,
    segment_fund_count,
    segment_average_cotistas,
    segment_average_vpa,
    segment_average_rentabilidade,
    segment_average_fee,
    segment_total_investido,
    segment_comparison,
    fund_complete_profile,
    fund_asset_composition,
    fund_asset_composition_pct,
    fund_liquidity_analysis,
    fund_liability_breakdown,
    fund_real_estate_detail,
    fund_securities_detail,
    fund_receivables_detail,
    fund_metrics_with_segment,
    funds_filtered_dy_and_pl,
    funds_filtered_multi,
    fund_dy_with_balance_summary,
    dy_drop_mom,
    dy_increase_mom,
    cotistas_drop,
    cotistas_increase,
    pl_drop,
    pl_increase,
    vpa_drop,
    funds_with_negative_dy,
    funds_with_negative_pl,
    funds_stopped_distributing,
    share_dilution,
    new_funds,
    passivo_increase,
    calc_dy_anualizado,
    calc_dy_acumulado_12m,
    calc_dividend_per_cota,
    calc_total_dividends,
    calc_real_estate_pct,
    calc_paper_pct,
    calc_fof_pct,
    calc_cash_pct,
)

SAMPLE_CNPJ = "00.332.266/0001-31"
SAMPLE_CNPJ_2 = "01.234.567/0001-89"
SAMPLE_DATE = date(2026, 9, 1)


class FakeRow:
    def __init__(self, **kwargs):
        self._mapping = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)


def make_row(**kwargs):
    return FakeRow(**kwargs)


@pytest.fixture
def session():
    s = MagicMock()
    s.execute.return_value = MagicMock()
    return s


def _setup_rows(session, rows):
    result = MagicMock()
    result.first.return_value = rows[0] if rows else None
    result.all.return_value = rows
    result.fetchall.return_value = rows
    result.fetchone.return_value = rows[0] if rows else None
    result.__iter__ = MagicMock(return_value=iter(rows))
    session.execute.return_value = result


def _assert_sql_contains(session, *keywords):
    call_args = session.execute.call_args
    sql_text = str(call_args[0][0])
    for kw in keywords:
        assert kw.lower() in sql_text.lower(), f"SQL missing keyword: {kw}"


def _get_bind_params(session):
    call_args = session.execute.call_args
    if len(call_args[0]) > 1:
        return call_args[0][1]
    return call_args[1].get("parameters", {}) if call_args[1] else {}


# =============================================================================
# Category 1: Fund Identification & Basic Info
# =============================================================================


class TestFindFundByName:
    def test_returns_list_of_dicts(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="VIA PARQUE SHOPPING FII",
                     segmento_atuacao="Shoppings", tipo_gestao="Ativa"),
        ])
        result = find_fund_by_name(session, "via parque")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["cnpj_fundo"] == SAMPLE_CNPJ

    def test_sql_uses_ilike(self, session):
        _setup_rows(session, [])
        find_fund_by_name(session, "hglg")
        _assert_sql_contains(session, "ILIKE", "nome_fundo")

    def test_empty_result(self, session):
        _setup_rows(session, [])
        result = find_fund_by_name(session, "nonexistent")
        assert result == []


class TestGetFundInfo:
    def test_returns_dict(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="VIA PARQUE",
                     segmento_atuacao="Shoppings", tipo_gestao="Ativa",
                     publico_alvo="INVESTIDORES EM GERAL", prazo_duracao="Indeterminado",
                     fundo_exclusivo="N", data_funcionamento=date(1994, 11, 24),
                     nome_administrador="BTG Pactual", estado="RJ", cidade="RIO DE JANEIRO",
                     mercado_negociacao_bolsa="S", codigo_isin="BRFVPQCTF015"),
        ])
        result = get_fund_info(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)
        assert result["cnpj_fundo"] == SAMPLE_CNPJ
        assert result["nome_fundo"] == "VIA PARQUE"

    def test_not_found_returns_none(self, session):
        _setup_rows(session, [])
        result = get_fund_info(session, "99.999.999/9999-99")
        assert result is None

    def test_sql_filters_by_cnpj(self, session):
        _setup_rows(session, [])
        get_fund_info(session, SAMPLE_CNPJ)
        _assert_sql_contains(session, "cnpj_fundo", "MAX(versao)")


class TestListFundsBySegment:
    def test_returns_list(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A", tipo_gestao="Ativa"),
            make_row(cnpj_fundo=SAMPLE_CNPJ_2, nome_fundo="FUND B", tipo_gestao="Definida"),
        ])
        result = list_funds_by_segment(session, "Logística")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_sql_filters_segment(self, session):
        _setup_rows(session, [])
        list_funds_by_segment(session, "Shoppings")
        _assert_sql_contains(session, "segmento_atuacao", "ILIKE")

    def test_with_optional_date(self, session):
        _setup_rows(session, [])
        list_funds_by_segment(session, "Logística", ref=SAMPLE_DATE)
        params = _get_bind_params(session)
        assert "ref" in params or "segment" in params


class TestListFundsByAdministrator:
    def test_returns_list(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A", tipo_gestao="Ativa"),
        ])
        result = list_funds_by_administrator(session, "BTG")
        assert isinstance(result, list)

    def test_sql_filters_admin(self, session):
        _setup_rows(session, [])
        list_funds_by_administrator(session, "XP")
        _assert_sql_contains(session, "nome_administrador", "ILIKE")


class TestListFundsByState:
    def test_returns_list(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A", tipo_gestao="Ativa"),
        ])
        result = list_funds_by_state(session, "SP")
        assert isinstance(result, list)

    def test_sql_filters_state(self, session):
        _setup_rows(session, [])
        list_funds_by_state(session, "RJ")
        _assert_sql_contains(session, "estado")


class TestListAllSegments:
    def test_returns_list_of_segments(self, session):
        _setup_rows(session, [
            make_row(segmento_atuacao="Logística", num_funds=120),
            make_row(segmento_atuacao="Shoppings", num_funds=65),
        ])
        result = list_all_segments(session)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_sql_has_group_by(self, session):
        _setup_rows(session, [])
        list_all_segments(session)
        _assert_sql_contains(session, "GROUP BY", "COUNT")


class TestListAllAdministrators:
    def test_returns_list(self, session):
        _setup_rows(session, [
            make_row(nome_administrador="BTG Pactual", num_funds=243),
        ])
        result = list_all_administrators(session)
        assert isinstance(result, list)


class TestCountTotalFunds:
    def test_returns_int(self, session):
        _setup_rows(session, [make_row(total=1428)])
        result = count_total_funds(session)
        assert isinstance(result, int)
        assert result == 1428

    def test_with_date(self, session):
        _setup_rows(session, [make_row(total=1300)])
        result = count_total_funds(session, ref=SAMPLE_DATE)
        assert isinstance(result, int)
        assert result == 1300


class TestCountFundsBySegment:
    def test_returns_list(self, session):
        _setup_rows(session, [
            make_row(segmento_atuacao="Logística", count=120),
        ])
        result = count_funds_by_segment(session)
        assert isinstance(result, list)


class TestGetFundAge:
    def test_returns_dict_with_age(self, session):
        _setup_rows(session, [
            make_row(nome_fundo="VIA PARQUE", data_funcionamento=date(1994, 11, 24)),
        ])
        result = get_fund_age(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)
        assert "data_funcionamento" in result

    def test_not_found(self, session):
        _setup_rows(session, [])
        result = get_fund_age(session, "99.999.999/9999-99")
        assert result is None


class TestGetAvailableMonths:
    def test_returns_list_of_dates(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 1, 1)),
            make_row(data_referencia=date(2026, 2, 1)),
        ])
        result = get_available_months(session, SAMPLE_CNPJ)
        assert isinstance(result, list)
        assert len(result) == 2


# =============================================================================
# Category 2: Factual Lookups — Single Fund, Single Metric
# =============================================================================


class TestFactualLookupMetrica:
    def test_get_patrimonio_liquido(self, session):
        _setup_rows(session, [make_row(patrimonio_liquido=Decimal("104000000.00"))])
        result = get_patrimonio_liquido(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)
        assert "patrimonio_liquido" in result

    def test_get_dividend_yield(self, session):
        _setup_rows(session, [make_row(percentual_dividend_yield_mes=Decimal("0.00800000"))])
        result = get_dividend_yield(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)
        assert "percentual_dividend_yield_mes" in result

    def test_get_valor_ativo(self, session):
        _setup_rows(session, [make_row(valor_ativo=Decimal("127000000.00"))])
        result = get_valor_ativo(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_valor_patrimonial_cotas(self, session):
        _setup_rows(session, [make_row(valor_patrimonial_cotas=Decimal("101.50000000"))])
        result = get_valor_patrimonial_cotas(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_rentabilidade_efetiva(self, session):
        _setup_rows(session, [make_row(percentual_rentabilidade_efetiva_mes=Decimal("0.00200000"))])
        result = get_rentabilidade_efetiva(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_rentabilidade_patrimonial(self, session):
        _setup_rows(session, [make_row(percentual_rentabilidade_patrimonial_mes=Decimal("-0.00030000"))])
        result = get_rentabilidade_patrimonial(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_total_cotistas(self, session):
        _setup_rows(session, [make_row(total_numero_cotistas=15000)])
        result = get_total_cotistas(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_cotistas_pf(self, session):
        _setup_rows(session, [make_row(numero_cotistas_pessoa_fisica=14000)])
        result = get_cotistas_pf(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_cotistas_pj(self, session):
        _setup_rows(session, [make_row(numero_cotistas_pessoa_juridica_nao_financeira=50)])
        result = get_cotistas_pj(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_cotas_emitidas(self, session):
        _setup_rows(session, [make_row(cotas_emitidas=Decimal("957266.00"))])
        result = get_cotas_emitidas(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_taxa_administracao(self, session):
        _setup_rows(session, [make_row(percentual_despesas_taxa_administracao=Decimal("0.00050000"))])
        result = get_taxa_administracao(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_taxa_custodiante(self, session):
        _setup_rows(session, [make_row(percentual_despesas_agente_custodiante=Decimal("0.00000000"))])
        result = get_taxa_custodiante(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_amortizacao(self, session):
        _setup_rows(session, [make_row(percentual_amortizacao_cotas_mes=Decimal("0.00000000"))])
        result = get_amortizacao(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_with_specific_date(self, session):
        _setup_rows(session, [make_row(patrimonio_liquido=Decimal("100000000.00"))])
        result = get_patrimonio_liquido(session, SAMPLE_CNPJ, ref=SAMPLE_DATE)
        assert isinstance(result, dict)

    def test_not_found_returns_none(self, session):
        _setup_rows(session, [])
        result = get_patrimonio_liquido(session, "99.999.999/9999-99")
        assert result is None


class TestFactualLookupBalanco:
    def test_get_total_investido(self, session):
        _setup_rows(session, [make_row(total_investido=Decimal("500000000.00"))])
        result = get_total_investido(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)
        assert "total_investido" in result

    def test_get_imoveis_renda(self, session):
        _setup_rows(session, [make_row(imoveis_renda_acabados=Decimal("300000000.00"))])
        result = get_imoveis_renda(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_cri_cra(self, session):
        _setup_rows(session, [make_row(cri_cra=Decimal("200000000.00"))])
        result = get_cri_cra(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_fii_holdings(self, session):
        _setup_rows(session, [make_row(fii=Decimal("100000000.00"))])
        result = get_fii_holdings(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_total_passivo(self, session):
        _setup_rows(session, [make_row(total_passivo=Decimal("50000000.00"))])
        result = get_total_passivo(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_disponibilidades(self, session):
        _setup_rows(session, [make_row(disponibilidades=Decimal("10000000.00"))])
        result = get_disponibilidades(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_rendimentos_distribuir(self, session):
        _setup_rows(session, [make_row(rendimentos_distribuir=Decimal("5000000.00"))])
        result = get_rendimentos_distribuir(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_valores_receber(self, session):
        _setup_rows(session, [make_row(valores_receber=Decimal("8000000.00"))])
        result = get_valores_receber(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_contas_aluguel(self, session):
        _setup_rows(session, [make_row(contas_receber_aluguel=Decimal("2000000.00"))])
        result = get_contas_aluguel(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_liquidez(self, session):
        _setup_rows(session, [make_row(total_necessidades_liquidez=Decimal("15000000.00"))])
        result = get_liquidez(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_obrigacoes_securitizacao(self, session):
        _setup_rows(session, [make_row(obrigacoes_securitizacao_recebiveis=Decimal("0.00"))])
        result = get_obrigacoes_securitizacao(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_get_provisoes(self, session):
        _setup_rows(session, [make_row(provisoes_contigencias=Decimal("0.00"))])
        result = get_provisoes(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)


# =============================================================================
# Category 3: Historical / Time Series
# =============================================================================


class TestHistoricalQueries:
    def test_history_dividend_yield_returns_list(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 1, 1), percentual_dividend_yield_mes=Decimal("0.008")),
            make_row(data_referencia=date(2026, 2, 1), percentual_dividend_yield_mes=Decimal("0.009")),
            make_row(data_referencia=date(2026, 3, 1), percentual_dividend_yield_mes=Decimal("0.007")),
        ])
        result = history_dividend_yield(session, SAMPLE_CNPJ)
        assert isinstance(result, list)
        assert len(result) == 3

    def test_history_with_months(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 7, 1), percentual_dividend_yield_mes=Decimal("0.008")),
        ])
        result = history_dividend_yield(session, SAMPLE_CNPJ, months=6)
        assert isinstance(result, list)

    def test_history_with_date_range(self, session):
        _setup_rows(session, [])
        history_dividend_yield(
            session, SAMPLE_CNPJ,
            start_date=date(2025, 1, 1), end_date=date(2025, 12, 1),
        )
        _assert_sql_contains(session, "data_referencia")

    def test_history_patrimonio_liquido(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 1, 1), patrimonio_liquido=Decimal("100000000")),
        ])
        result = history_patrimonio_liquido(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_valor_ativo(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 1, 1), valor_ativo=Decimal("127000000")),
        ])
        result = history_valor_ativo(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_valor_patrimonial(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 1, 1), valor_patrimonial_cotas=Decimal("101.50")),
        ])
        result = history_valor_patrimonial(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_cotistas(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 1, 1), total_numero_cotistas=15000),
        ])
        result = history_cotistas(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_total_investido(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 1, 1), total_investido=Decimal("500000000")),
        ])
        result = history_total_investido(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_cri_cra(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 1, 1), cri_cra=Decimal("200000000")),
        ])
        result = history_cri_cra(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_total_passivo(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 1, 1), total_passivo=Decimal("50000000")),
        ])
        result = history_total_passivo(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_disponibilidades(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 1, 1), disponibilidades=Decimal("10000000")),
        ])
        result = history_disponibilidades(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_rentabilidade_efetiva(self, session):
        _setup_rows(session, [])
        result = history_rentabilidade_efetiva(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_rentabilidade_patrimonial(self, session):
        _setup_rows(session, [])
        result = history_rentabilidade_patrimonial(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_cotistas_pf(self, session):
        _setup_rows(session, [])
        result = history_cotistas_pf(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_cotas_emitidas(self, session):
        _setup_rows(session, [])
        result = history_cotas_emitidas(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_taxa_administracao(self, session):
        _setup_rows(session, [])
        result = history_taxa_administracao(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_imoveis_renda(self, session):
        _setup_rows(session, [])
        result = history_imoveis_renda(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_fii_holdings(self, session):
        _setup_rows(session, [])
        result = history_fii_holdings(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_rendimentos_distribuir(self, session):
        _setup_rows(session, [])
        result = history_rendimentos_distribuir(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_contas_aluguel(self, session):
        _setup_rows(session, [])
        result = history_contas_aluguel(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_amortizacao(self, session):
        _setup_rows(session, [])
        result = history_amortizacao(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_history_liquidez(self, session):
        _setup_rows(session, [])
        result = history_liquidez(session, SAMPLE_CNPJ)
        assert isinstance(result, list)

    def test_sql_has_order_by_date(self, session):
        _setup_rows(session, [])
        history_dividend_yield(session, SAMPLE_CNPJ)
        _assert_sql_contains(session, "ORDER BY", "data_referencia")

    def test_sql_uses_versao_cte(self, session):
        _setup_rows(session, [])
        history_dividend_yield(session, SAMPLE_CNPJ)
        _assert_sql_contains(session, "MAX(versao)")


# =============================================================================
# Category 4: Rankings / Top-N
# =============================================================================


class TestRankingQueries:
    def test_rank_by_dividend_yield_returns_list(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A",
                     segmento_atuacao="Logística",
                     percentual_dividend_yield_mes=Decimal("0.012")),
            make_row(cnpj_fundo=SAMPLE_CNPJ_2, nome_fundo="FUND B",
                     segmento_atuacao="Shoppings",
                     percentual_dividend_yield_mes=Decimal("0.010")),
        ])
        result = rank_by_dividend_yield(session)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_rank_with_limit(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A",
                     segmento_atuacao="Logística",
                     percentual_dividend_yield_mes=Decimal("0.012")),
        ])
        result = rank_by_dividend_yield(session, n=5)
        assert isinstance(result, list)

    def test_rank_with_segment_filter(self, session):
        _setup_rows(session, [])
        rank_by_dividend_yield(session, segment="Logística")
        _assert_sql_contains(session, "segmento_atuacao")

    def test_rank_with_date(self, session):
        _setup_rows(session, [])
        rank_by_dividend_yield(session, ref=SAMPLE_DATE)
        session.execute.assert_called_once()

    def test_rank_by_patrimonio_liquido(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="BIG FUND",
                     segmento_atuacao="Logística",
                     patrimonio_liquido=Decimal("11000000000")),
        ])
        result = rank_by_patrimonio_liquido(session)
        assert isinstance(result, list)

    def test_rank_by_lowest_admin_fee_uses_asc(self, session):
        _setup_rows(session, [])
        rank_by_lowest_admin_fee(session)
        _assert_sql_contains(session, "ASC")

    def test_rank_smallest_funds_uses_asc(self, session):
        _setup_rows(session, [])
        rank_smallest_funds(session)
        _assert_sql_contains(session, "ASC")

    def test_rank_by_cotistas(self, session):
        _setup_rows(session, [])
        result = rank_by_cotistas(session)
        assert isinstance(result, list)

    def test_rank_by_total_investido(self, session):
        _setup_rows(session, [])
        result = rank_by_total_investido(session)
        assert isinstance(result, list)

    def test_rank_by_imoveis(self, session):
        _setup_rows(session, [])
        result = rank_by_imoveis(session)
        assert isinstance(result, list)

    def test_rank_by_cri_cra(self, session):
        _setup_rows(session, [])
        result = rank_by_cri_cra(session)
        assert isinstance(result, list)

    def test_rank_by_fii_holdings(self, session):
        _setup_rows(session, [])
        result = rank_by_fii_holdings(session)
        assert isinstance(result, list)

    def test_rank_by_total_passivo(self, session):
        _setup_rows(session, [])
        result = rank_by_total_passivo(session)
        assert isinstance(result, list)

    def test_rank_by_disponibilidades(self, session):
        _setup_rows(session, [])
        result = rank_by_disponibilidades(session)
        assert isinstance(result, list)

    def test_rank_by_valor_ativo(self, session):
        _setup_rows(session, [])
        result = rank_by_valor_ativo(session)
        assert isinstance(result, list)

    def test_rank_by_cotistas_pf(self, session):
        _setup_rows(session, [])
        result = rank_by_cotistas_pf(session)
        assert isinstance(result, list)

    def test_rank_by_vpa(self, session):
        _setup_rows(session, [])
        result = rank_by_vpa(session)
        assert isinstance(result, list)

    def test_rank_by_rentabilidade(self, session):
        _setup_rows(session, [])
        result = rank_by_rentabilidade(session)
        assert isinstance(result, list)

    def test_rank_by_cotas_emitidas(self, session):
        _setup_rows(session, [])
        result = rank_by_cotas_emitidas(session)
        assert isinstance(result, list)

    def test_rank_by_contas_aluguel(self, session):
        _setup_rows(session, [])
        result = rank_by_contas_aluguel(session)
        assert isinstance(result, list)

    def test_rank_by_rendimentos_distribuir(self, session):
        _setup_rows(session, [])
        result = rank_by_rendimentos_distribuir(session)
        assert isinstance(result, list)

    def test_sql_has_limit(self, session):
        _setup_rows(session, [])
        rank_by_dividend_yield(session, n=10)
        _assert_sql_contains(session, "LIMIT")

    def test_sql_has_order_by_desc(self, session):
        _setup_rows(session, [])
        rank_by_dividend_yield(session)
        _assert_sql_contains(session, "DESC")


# =============================================================================
# Category 5: Comparisons
# =============================================================================


class TestComparisonQueries:
    def test_compare_funds_full(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A",
                     patrimonio_liquido=Decimal("100000000"),
                     valor_patrimonial_cotas=Decimal("101.50"),
                     percentual_dividend_yield_mes=Decimal("0.008"),
                     total_numero_cotistas=15000,
                     total_investido=Decimal("500000000"),
                     total_passivo=Decimal("50000000")),
            make_row(cnpj_fundo=SAMPLE_CNPJ_2, nome_fundo="FUND B",
                     patrimonio_liquido=Decimal("200000000"),
                     valor_patrimonial_cotas=Decimal("95.00"),
                     percentual_dividend_yield_mes=Decimal("0.010"),
                     total_numero_cotistas=25000,
                     total_investido=Decimal("800000000"),
                     total_passivo=Decimal("70000000")),
        ])
        result = compare_funds_full(session, [SAMPLE_CNPJ, SAMPLE_CNPJ_2])
        assert isinstance(result, list)
        assert len(result) == 2

    def test_compare_funds_single_metric(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A",
                     percentual_dividend_yield_mes=Decimal("0.008")),
            make_row(cnpj_fundo=SAMPLE_CNPJ_2, nome_fundo="FUND B",
                     percentual_dividend_yield_mes=Decimal("0.010")),
        ])
        result = compare_funds_single_metric(
            session, [SAMPLE_CNPJ, SAMPLE_CNPJ_2], "percentual_dividend_yield_mes",
        )
        assert isinstance(result, list)
        assert len(result) == 2

    def test_compare_funds_dy_history(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, data_referencia=date(2026, 1, 1),
                     percentual_dividend_yield_mes=Decimal("0.008")),
        ])
        result = compare_funds_dy_history(session, [SAMPLE_CNPJ, SAMPLE_CNPJ_2])
        assert isinstance(result, list)

    def test_compare_funds_pl_history(self, session):
        _setup_rows(session, [])
        result = compare_funds_pl_history(session, [SAMPLE_CNPJ, SAMPLE_CNPJ_2])
        assert isinstance(result, list)

    def test_compare_funds_cotistas_history(self, session):
        _setup_rows(session, [])
        result = compare_funds_cotistas_history(session, [SAMPLE_CNPJ, SAMPLE_CNPJ_2])
        assert isinstance(result, list)

    def test_compare_funds_balance_sheet(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A",
                     total_investido=Decimal("500000000"),
                     imoveis_renda_acabados=Decimal("300000000"),
                     cri_cra=Decimal("0"), fii=Decimal("0"),
                     total_passivo=Decimal("50000000")),
        ])
        result = compare_funds_balance_sheet(session, [SAMPLE_CNPJ, SAMPLE_CNPJ_2])
        assert isinstance(result, list)

    def test_compare_funds_fees(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A",
                     percentual_despesas_taxa_administracao=Decimal("0.0005"),
                     percentual_despesas_agente_custodiante=Decimal("0.0001")),
        ])
        result = compare_funds_fees(session, [SAMPLE_CNPJ, SAMPLE_CNPJ_2])
        assert isinstance(result, list)

    def test_compare_sql_uses_in_clause(self, session):
        _setup_rows(session, [])
        compare_funds_full(session, [SAMPLE_CNPJ, SAMPLE_CNPJ_2])
        _assert_sql_contains(session, "cnpj_fundo")


# =============================================================================
# Category 6: Aggregations
# =============================================================================


class TestAggregationQueries:
    def test_accumulated_dy(self, session):
        _setup_rows(session, [make_row(accumulated_dy=Decimal("0.096"))])
        result = accumulated_dy(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_average_dy(self, session):
        _setup_rows(session, [make_row(average_dy=Decimal("0.008"))])
        result = average_dy(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_annualized_dy(self, session):
        _setup_rows(session, [make_row(annualized_dy=Decimal("0.096"))])
        result = annualized_dy(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_dy_last_12_months(self, session):
        _setup_rows(session, [make_row(dy_12m=Decimal("0.096"))])
        result = dy_last_12_months(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_average_rentabilidade(self, session):
        _setup_rows(session, [make_row(avg_rent=Decimal("0.002"))])
        result = average_rentabilidade(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_pl_variation(self, session):
        _setup_rows(session, [
            make_row(start_pl=Decimal("100000000"), end_pl=Decimal("110000000"),
                     variation=Decimal("10000000"), pct_change=Decimal("10.0")),
        ])
        result = pl_variation(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_cotistas_variation(self, session):
        _setup_rows(session, [
            make_row(start_cotistas=10000, end_cotistas=15000,
                     variation=5000, pct_change=Decimal("50.0")),
        ])
        result = cotistas_variation(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_vpa_variation(self, session):
        _setup_rows(session, [
            make_row(start_vpa=Decimal("100"), end_vpa=Decimal("105"),
                     variation=Decimal("5"), pct_change=Decimal("5.0")),
        ])
        result = vpa_variation(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_dividend_per_cota_estimate(self, session):
        _setup_rows(session, [make_row(dividend_per_cota=Decimal("0.81"))])
        result = dividend_per_cota_estimate(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_max_dy_period(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 3, 1), max_dy=Decimal("0.015")),
        ])
        result = max_dy_period(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_min_dy_period(self, session):
        _setup_rows(session, [
            make_row(data_referencia=date(2026, 7, 1), min_dy=Decimal("0.002")),
        ])
        result = min_dy_period(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_average_pl_period(self, session):
        _setup_rows(session, [make_row(avg_pl=Decimal("105000000"))])
        result = average_pl_period(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_cotas_emitidas_change(self, session):
        _setup_rows(session, [
            make_row(start_cotas=Decimal("900000"), end_cotas=Decimal("1000000"),
                     change=Decimal("100000"), pct_change=Decimal("11.1")),
        ])
        result = cotas_emitidas_change(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_total_return_estimate(self, session):
        _setup_rows(session, [make_row(total_return=Decimal("0.024"))])
        result = total_return_estimate(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_accumulated_dy_sql_has_sum(self, session):
        _setup_rows(session, [make_row(accumulated_dy=Decimal("0.096"))])
        accumulated_dy(session, SAMPLE_CNPJ, months=12)
        _assert_sql_contains(session, "SUM")

    def test_annualized_dy_sql_has_avg(self, session):
        _setup_rows(session, [make_row(annualized_dy=Decimal("0.096"))])
        annualized_dy(session, SAMPLE_CNPJ)
        _assert_sql_contains(session, "AVG")


# =============================================================================
# Category 7: Segment Analysis
# =============================================================================


class TestSegmentAnalysisQueries:
    def test_segment_average_dy(self, session):
        _setup_rows(session, [
            make_row(segmento_atuacao="Logística", avg_dy=Decimal("0.008")),
            make_row(segmento_atuacao="Shoppings", avg_dy=Decimal("0.006")),
        ])
        result = segment_average_dy(session)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_segment_average_dy_with_filter(self, session):
        _setup_rows(session, [
            make_row(segmento_atuacao="Logística", avg_dy=Decimal("0.008")),
        ])
        result = segment_average_dy(session, segment="Logística")
        assert isinstance(result, list)

    def test_segment_average_pl(self, session):
        _setup_rows(session, [
            make_row(segmento_atuacao="Logística", avg_pl=Decimal("500000000")),
        ])
        result = segment_average_pl(session)
        assert isinstance(result, list)

    def test_segment_total_pl(self, session):
        _setup_rows(session, [
            make_row(segmento_atuacao="Logística", total_pl=Decimal("5000000000")),
        ])
        result = segment_total_pl(session)
        assert isinstance(result, list)

    def test_segment_fund_count(self, session):
        _setup_rows(session, [
            make_row(segmento_atuacao="Logística", count=120),
        ])
        result = segment_fund_count(session)
        assert isinstance(result, list)

    def test_segment_average_cotistas(self, session):
        _setup_rows(session, [])
        result = segment_average_cotistas(session)
        assert isinstance(result, list)

    def test_segment_average_vpa(self, session):
        _setup_rows(session, [])
        result = segment_average_vpa(session)
        assert isinstance(result, list)

    def test_segment_average_rentabilidade(self, session):
        _setup_rows(session, [])
        result = segment_average_rentabilidade(session)
        assert isinstance(result, list)

    def test_segment_average_fee(self, session):
        _setup_rows(session, [])
        result = segment_average_fee(session)
        assert isinstance(result, list)

    def test_segment_total_investido(self, session):
        _setup_rows(session, [])
        result = segment_total_investido(session)
        assert isinstance(result, list)

    def test_segment_comparison(self, session):
        _setup_rows(session, [
            make_row(segmento_atuacao="Logística", avg_dy=Decimal("0.008"),
                     avg_pl=Decimal("500000000"), num_funds=120),
            make_row(segmento_atuacao="Shoppings", avg_dy=Decimal("0.006"),
                     avg_pl=Decimal("400000000"), num_funds=65),
        ])
        result = segment_comparison(session, ["Logística", "Shoppings"])
        assert isinstance(result, list)

    def test_segment_average_dy_sql_has_group_by(self, session):
        _setup_rows(session, [])
        segment_average_dy(session)
        _assert_sql_contains(session, "GROUP BY", "AVG")


# =============================================================================
# Category 8: Cross-Table Queries
# =============================================================================


class TestCrossTableQueries:
    def test_fund_complete_profile(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="VIA PARQUE",
                     segmento_atuacao="Shoppings", tipo_gestao="Ativa",
                     patrimonio_liquido=Decimal("100000000"),
                     valor_patrimonial_cotas=Decimal("101.50"),
                     percentual_dividend_yield_mes=Decimal("0.008"),
                     total_numero_cotistas=15000,
                     total_investido=Decimal("500000000"),
                     total_passivo=Decimal("50000000")),
        ])
        result = fund_complete_profile(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)
        assert result["cnpj_fundo"] == SAMPLE_CNPJ

    def test_fund_complete_profile_not_found(self, session):
        _setup_rows(session, [])
        result = fund_complete_profile(session, "99.999.999/9999-99")
        assert result is None

    def test_fund_asset_composition(self, session):
        _setup_rows(session, [
            make_row(imoveis_renda_acabados=Decimal("300000000"),
                     cri_cra=Decimal("0"), fii=Decimal("0"),
                     acoes=Decimal("0"),
                     fundos_renda_fixa=Decimal("50000000"),
                     disponibilidades=Decimal("10000000"),
                     total_investido=Decimal("500000000")),
        ])
        result = fund_asset_composition(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_fund_asset_composition_pct(self, session):
        _setup_rows(session, [
            make_row(imoveis_pct=Decimal("60.0"), cri_pct=Decimal("0.0"),
                     fii_pct=Decimal("0.0"), acoes_pct=Decimal("0.0"),
                     renda_fixa_pct=Decimal("10.0"), cash_pct=Decimal("2.0")),
        ])
        result = fund_asset_composition_pct(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_fund_liquidity_analysis(self, session):
        _setup_rows(session, [
            make_row(disponibilidades=Decimal("10000000"),
                     titulos_publicos=Decimal("5000000"),
                     fundos_renda_fixa=Decimal("50000000"),
                     total_investido=Decimal("500000000")),
        ])
        result = fund_liquidity_analysis(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_fund_liability_breakdown(self, session):
        _setup_rows(session, [
            make_row(rendimentos_distribuir=Decimal("5000000"),
                     taxa_administracao_pagar=Decimal("1000000"),
                     obrigacoes_aquisicao_imoveis=Decimal("0"),
                     obrigacoes_securitizacao_recebiveis=Decimal("0"),
                     provisoes_contigencias=Decimal("0"),
                     total_passivo=Decimal("50000000")),
        ])
        result = fund_liability_breakdown(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_fund_real_estate_detail(self, session):
        _setup_rows(session, [
            make_row(imoveis_renda_acabados=Decimal("300000000"),
                     imoveis_renda_construcao=Decimal("0"),
                     imoveis_venda_acabados=Decimal("0"),
                     terrenos=Decimal("0"),
                     direitos_bens_imoveis=Decimal("300000000")),
        ])
        result = fund_real_estate_detail(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_fund_securities_detail(self, session):
        _setup_rows(session, [
            make_row(cri_cra=Decimal("200000000"), lci_lca=Decimal("0"),
                     acoes=Decimal("0"), debentures=Decimal("0"),
                     fii=Decimal("0"), fip=Decimal("0")),
        ])
        result = fund_securities_detail(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_fund_receivables_detail(self, session):
        _setup_rows(session, [
            make_row(valores_receber=Decimal("8000000"),
                     contas_receber_aluguel=Decimal("2000000"),
                     contas_receber_venda_imoveis=Decimal("0"),
                     outros_valores_receber=Decimal("6000000")),
        ])
        result = fund_receivables_detail(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_fund_metrics_with_segment(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="VIA PARQUE",
                     segmento_atuacao="Shoppings",
                     percentual_dividend_yield_mes=Decimal("0.008"),
                     patrimonio_liquido=Decimal("100000000")),
        ])
        result = fund_metrics_with_segment(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_funds_filtered_dy_and_pl(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A",
                     percentual_dividend_yield_mes=Decimal("0.010"),
                     patrimonio_liquido=Decimal("200000000")),
        ])
        result = funds_filtered_dy_and_pl(session, min_dy=0.008, min_pl=100000000)
        assert isinstance(result, list)

    def test_funds_filtered_multi(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A",
                     segmento_atuacao="Logística",
                     percentual_dividend_yield_mes=Decimal("0.010"),
                     patrimonio_liquido=Decimal("200000000"),
                     total_numero_cotistas=15000),
        ])
        result = funds_filtered_multi(
            session, segment="Logística", min_dy=0.005,
            min_pl=50000000, min_cotistas=100, listed_only=True,
        )
        assert isinstance(result, list)

    def test_fund_dy_with_balance_summary(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ,
                     percentual_dividend_yield_mes=Decimal("0.008"),
                     patrimonio_liquido=Decimal("100000000"),
                     valor_patrimonial_cotas=Decimal("101.50"),
                     total_investido=Decimal("500000000"),
                     total_passivo=Decimal("50000000"),
                     disponibilidades=Decimal("10000000")),
        ])
        result = fund_dy_with_balance_summary(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_fund_complete_profile_sql_has_join(self, session):
        _setup_rows(session, [])
        fund_complete_profile(session, SAMPLE_CNPJ)
        _assert_sql_contains(session, "JOIN")


# =============================================================================
# Category 9: Alerts / Anomalies
# =============================================================================


class TestAlertQueries:
    def test_dy_drop_mom(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A",
                     current_dy=Decimal("0.003"), previous_dy=Decimal("0.008"),
                     drop_pct=Decimal("-62.5")),
        ])
        result = dy_drop_mom(session, threshold=0.3)
        assert isinstance(result, list)

    def test_dy_increase_mom(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A",
                     current_dy=Decimal("0.012"), previous_dy=Decimal("0.008"),
                     increase_pct=Decimal("50.0")),
        ])
        result = dy_increase_mom(session, threshold=0.3)
        assert isinstance(result, list)

    def test_cotistas_drop(self, session):
        _setup_rows(session, [])
        result = cotistas_drop(session, threshold=0.1)
        assert isinstance(result, list)

    def test_cotistas_increase(self, session):
        _setup_rows(session, [])
        result = cotistas_increase(session, threshold=0.1)
        assert isinstance(result, list)

    def test_pl_drop(self, session):
        _setup_rows(session, [])
        result = pl_drop(session, threshold=0.1)
        assert isinstance(result, list)

    def test_pl_increase(self, session):
        _setup_rows(session, [])
        result = pl_increase(session, threshold=0.1)
        assert isinstance(result, list)

    def test_vpa_drop(self, session):
        _setup_rows(session, [])
        result = vpa_drop(session, threshold=0.1)
        assert isinstance(result, list)

    def test_funds_with_negative_dy(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A",
                     percentual_dividend_yield_mes=Decimal("-0.002")),
        ])
        result = funds_with_negative_dy(session)
        assert isinstance(result, list)

    def test_funds_with_negative_pl(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A",
                     patrimonio_liquido=Decimal("-135000000")),
        ])
        result = funds_with_negative_pl(session)
        assert isinstance(result, list)

    def test_funds_stopped_distributing(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="FUND A"),
        ])
        result = funds_stopped_distributing(session)
        assert isinstance(result, list)

    def test_share_dilution(self, session):
        _setup_rows(session, [])
        result = share_dilution(session, threshold=0.1)
        assert isinstance(result, list)

    def test_new_funds(self, session):
        _setup_rows(session, [
            make_row(cnpj_fundo=SAMPLE_CNPJ, nome_fundo="NEW FUND"),
        ])
        result = new_funds(session)
        assert isinstance(result, list)

    def test_passivo_increase(self, session):
        _setup_rows(session, [])
        result = passivo_increase(session, threshold=0.2)
        assert isinstance(result, list)

    def test_dy_drop_with_segment(self, session):
        _setup_rows(session, [])
        result = dy_drop_mom(session, threshold=0.3, segment="Logística")
        assert isinstance(result, list)

    def test_funds_with_negative_dy_sql(self, session):
        _setup_rows(session, [])
        funds_with_negative_dy(session)
        _assert_sql_contains(session, "< 0")

    def test_funds_with_negative_pl_sql(self, session):
        _setup_rows(session, [])
        funds_with_negative_pl(session)
        _assert_sql_contains(session, "< 0")


# =============================================================================
# Category 10: Calculated Metrics
# =============================================================================


class TestCalculatedMetricQueries:
    def test_calc_dy_anualizado(self, session):
        _setup_rows(session, [
            make_row(dy_anualizado=Decimal("9.6")),
        ])
        result = calc_dy_anualizado(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_calc_dy_acumulado_12m(self, session):
        _setup_rows(session, [
            make_row(dy_12m=Decimal("9.6")),
        ])
        result = calc_dy_acumulado_12m(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_calc_dividend_per_cota(self, session):
        _setup_rows(session, [
            make_row(dividend_per_cota=Decimal("0.81")),
        ])
        result = calc_dividend_per_cota(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_calc_total_dividends(self, session):
        _setup_rows(session, [
            make_row(total_dividends=Decimal("50000000")),
        ])
        result = calc_total_dividends(session, SAMPLE_CNPJ, months=12)
        assert isinstance(result, dict)

    def test_calc_real_estate_pct(self, session):
        _setup_rows(session, [
            make_row(real_estate_pct=Decimal("60.0")),
        ])
        result = calc_real_estate_pct(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_calc_paper_pct(self, session):
        _setup_rows(session, [
            make_row(paper_pct=Decimal("0.0")),
        ])
        result = calc_paper_pct(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_calc_fof_pct(self, session):
        _setup_rows(session, [
            make_row(fof_pct=Decimal("0.0")),
        ])
        result = calc_fof_pct(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_calc_cash_pct(self, session):
        _setup_rows(session, [
            make_row(cash_pct=Decimal("2.0")),
        ])
        result = calc_cash_pct(session, SAMPLE_CNPJ)
        assert isinstance(result, dict)

    def test_calc_real_estate_pct_sql(self, session):
        _setup_rows(session, [make_row(real_estate_pct=Decimal("60.0"))])
        calc_real_estate_pct(session, SAMPLE_CNPJ)
        _assert_sql_contains(session, "imoveis_renda_acabados", "total_investido")

    def test_calc_dy_anualizado_sql(self, session):
        _setup_rows(session, [make_row(dy_anualizado=Decimal("9.6"))])
        calc_dy_anualizado(session, SAMPLE_CNPJ)
        _assert_sql_contains(session, "12")
