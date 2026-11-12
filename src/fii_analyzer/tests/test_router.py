import pytest
from datetime import date

from fii_analyzer.llm.router import (
    normalize,
    extract_cnpjs,
    extract_fund_names,
    extract_dates,
    extract_numbers,
    extract_segment,
    match_query,
    route,
    ExtractedEntities,
    RouterResult,
)

SAMPLE_CNPJ = "00.332.266/0001-31"
SAMPLE_CNPJ_2 = "01.234.567/0001-89"


# =============================================================================
# Normalization
# =============================================================================


class TestNormalize:
    def test_lowercase(self):
        assert normalize("QUAL O DY") == "qual o dy"

    def test_accents_removed(self):
        result = normalize("histórico de última análise ação")
        assert "i" in result
        assert "u" in result
        assert "a" in result
        assert "é" not in result
        assert "ú" not in result
        assert "á" not in result
        assert "ã" not in result
        assert "ç" not in result

    def test_cedilla(self):
        result = normalize("preço ação")
        assert "ç" not in result
        assert "preco" in result

    def test_whitespace_normalized(self):
        result = normalize("  qual   o   dy  ")
        assert result == "qual o dy"

    def test_special_chars_removed(self):
        result = normalize("qual o dy?! do fundo")
        assert "?" not in result
        assert "!" not in result

    def test_preserves_percent(self):
        result = normalize("acima de 0.5%")
        assert "%" in result

    def test_preserves_slash_in_cnpj(self):
        result = normalize("00.332.266/0001-31")
        assert "/" in result

    def test_preserves_dots_and_commas(self):
        result = normalize("R$ 100.000,50")
        assert "100.000" in result or "100000" in result


# =============================================================================
# CNPJ Extraction
# =============================================================================


class TestExtractCnpjs:
    def test_valid_cnpj(self):
        result = extract_cnpjs(f"qual o dy do {SAMPLE_CNPJ}")
        assert result == [SAMPLE_CNPJ]

    def test_multiple_cnpjs(self):
        result = extract_cnpjs(f"comparar {SAMPLE_CNPJ} e {SAMPLE_CNPJ_2}")
        assert len(result) == 2
        assert SAMPLE_CNPJ in result
        assert SAMPLE_CNPJ_2 in result

    def test_no_cnpj(self):
        result = extract_cnpjs("qual o dy do HGLG11")
        assert result == []

    def test_cnpj_in_sentence(self):
        text = f"o fundo com cnpj {SAMPLE_CNPJ} pagou dividendo"
        result = extract_cnpjs(text)
        assert result == [SAMPLE_CNPJ]


# =============================================================================
# Fund Name / Ticker Extraction
# =============================================================================


class TestExtractFundNames:
    def test_ticker_pattern(self):
        result = extract_fund_names("qual o dy do HGLG11")
        assert "HGLG11" in result

    def test_multiple_tickers(self):
        result = extract_fund_names("comparar HGLG11 e XPLG11")
        assert "HGLG11" in result
        assert "XPLG11" in result

    def test_ticker_with_lowercase(self):
        result = extract_fund_names("qual o dy do hglg11")
        assert len(result) >= 1
        assert result[0] == "HGLG11"

    def test_quoted_name(self):
        result = extract_fund_names('buscar fundo "via parque"')
        assert any("via parque" in name.lower() for name in result)

    def test_no_fund(self):
        result = extract_fund_names("quais segmentos existem")
        assert result == []

    def test_ticker_not_confused_with_numbers(self):
        result = extract_fund_names("top 10 fundos")
        assert result == []


# =============================================================================
# Date Extraction
# =============================================================================


class TestExtractDates:
    def test_month_year_portuguese(self):
        result = extract_dates("em setembro de 2026")
        assert result is not None
        assert result.get("date_ref") == date(2026, 9, 1)

    def test_year_only(self):
        result = extract_dates("em 2025")
        assert result is not None
        start = result.get("start_date")
        end = result.get("end_date")
        if start and end:
            assert start.year == 2025
            assert end.year == 2025

    def test_last_n_months(self):
        result = extract_dates("ultimos 6 meses")
        assert result is not None
        assert result.get("months") == 6

    def test_last_month(self):
        result = extract_dates("ultimo mes")
        assert result is not None
        assert result.get("months") == 1

    def test_this_year(self):
        result = extract_dates("este ano")
        assert result is not None

    def test_last_year(self):
        result = extract_dates("ano passado")
        assert result is not None
        start = result.get("start_date")
        if start:
            assert start.year == date.today().year - 1

    def test_since_year(self):
        result = extract_dates("desde 2020")
        assert result is not None
        start = result.get("start_date")
        if start:
            assert start.year == 2020

    def test_mm_yyyy(self):
        result = extract_dates("09/2026")
        assert result is not None

    def test_no_date(self):
        result = extract_dates("qual o dy do HGLG11")
        assert result is None or result == {}

    def test_janeiro(self):
        result = extract_dates("em janeiro de 2026")
        assert result is not None

    def test_dezembro(self):
        result = extract_dates("em dezembro de 2025")
        assert result is not None

    def test_ultimos_12_meses(self):
        result = extract_dates("ultimos 12 meses")
        assert result is not None
        assert result.get("months") == 12


# =============================================================================
# Number/Threshold Extraction
# =============================================================================


class TestExtractNumbers:
    def test_min_pct(self):
        result = extract_numbers("acima de 0.5%")
        assert result.get("min_pct") == pytest.approx(0.5)

    def test_max_pct(self):
        result = extract_numbers("abaixo de 1%")
        assert result.get("max_pct") == pytest.approx(1.0)

    def test_min_pct_with_mais_de(self):
        result = extract_numbers("mais de 0.8%")
        assert result.get("min_pct") == pytest.approx(0.8)

    def test_min_value(self):
        result = extract_numbers(normalize("mais de R$ 100000"))
        assert result.get("min_value") == pytest.approx(100000)

    def test_min_value_with_dots(self):
        result = extract_numbers(normalize("acima de R$ 100.000"))
        assert result.get("min_value") is not None

    def test_limit_top(self):
        result = extract_numbers("top 10")
        assert result.get("limit") == 10

    def test_limit_maiores(self):
        result = extract_numbers("5 maiores fundos")
        assert result.get("limit") == 5

    def test_limit_melhores(self):
        result = extract_numbers("10 melhores dividendos")
        assert result.get("limit") == 10

    def test_no_numbers(self):
        result = extract_numbers("qual o dy do fundo")
        assert result == {} or all(v is None for v in result.values())

    def test_max_value(self):
        result = extract_numbers(normalize("abaixo de R$ 50000"))
        assert result.get("max_value") is not None


# =============================================================================
# Segment Extraction
# =============================================================================


class TestExtractSegment:
    def test_logistica(self):
        result = extract_segment("fundos de logistica")
        assert result is not None
        assert "log" in result.lower()

    def test_shoppings(self):
        result = extract_segment("fiis de shoppings")
        assert result is not None
        assert "shopping" in result.lower()

    def test_escritorios(self):
        result = extract_segment("fundos de escritorios")
        assert result is not None

    def test_residencial(self):
        result = extract_segment(normalize("fiis residenciais"))
        assert result is not None

    def test_hospital(self):
        result = extract_segment(normalize("fundos de hospital"))
        assert result is not None

    def test_no_segment(self):
        result = extract_segment(normalize("qual o dy do HGLG11"))
        assert result is None

    def test_multicategoria(self):
        result = extract_segment(normalize("fundos multicategoria"))
        assert result is not None

    def test_case_insensitive(self):
        result = extract_segment("LOGISTICA")
        assert result is not None


# =============================================================================
# End-to-End Router Tests
# =============================================================================


class TestRouteEndToEnd:
    def test_simple_dy(self):
        result = route(f"qual o dy do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_dividend_yield"
        assert result.params.get("cnpj") == SAMPLE_CNPJ

    def test_simple_pl(self):
        result = route(f"patrimonio liquido do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_patrimonio_liquido"

    def test_simple_vpa(self):
        result = route(f"valor patrimonial do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_valor_patrimonial_cotas"

    def test_simple_cotistas(self):
        result = route(f"quantos cotistas tem o {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_total_cotistas"

    def test_simple_cash(self):
        result = route(f"quanto tem em caixa o {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_disponibilidades"

    def test_history_dy(self):
        result = route(f"historico de dy do {SAMPLE_CNPJ} nos ultimos 6 meses")
        assert result is not None
        assert result.query_name == "history_dividend_yield"

    def test_history_pl(self):
        result = route(f"evolucao do patrimonio liquido do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "history_patrimonio_liquido"

    def test_ranking_dy(self):
        result = route("top 10 fiis com maior dy")
        assert result is not None
        assert result.query_name == "rank_by_dividend_yield"

    def test_ranking_pl(self):
        result = route("maiores fundos por patrimonio liquido")
        assert result is not None
        assert result.query_name == "rank_by_patrimonio_liquido"

    def test_ranking_segment(self):
        result = route("maiores fundos de logistica por patrimonio")
        assert result is not None
        assert result.query_name == "rank_by_patrimonio_liquido"
        assert result.params.get("segment") is not None

    def test_compare_full(self):
        result = route(f"comparar {SAMPLE_CNPJ} e {SAMPLE_CNPJ_2}")
        assert result is not None
        assert result.query_name == "compare_funds_full"
        assert len(result.params.get("cnpjs", [])) == 2

    def test_accumulated_dy(self):
        result = route(f"dy acumulado do {SAMPLE_CNPJ} em 2025")
        assert result is not None
        assert result.query_name == "accumulated_dy"

    def test_annualized_dy(self):
        result = route(f"dy anualizado do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name in ("annualized_dy", "calc_dy_anualizado")

    def test_segment_avg_dy(self):
        result = route("dy medio por segmento")
        assert result is not None
        assert result.query_name == "segment_average_dy"

    def test_profile(self):
        result = route(f"perfil completo do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "fund_complete_profile"

    def test_composition(self):
        result = route(f"composicao dos ativos do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "fund_asset_composition"

    def test_alert_dy_drop(self):
        result = route("quais fundos tiveram queda de dy")
        assert result is not None
        assert result.query_name == "dy_drop_mom"

    def test_negative_pl(self):
        result = route("fundos com patrimonio negativo")
        assert result is not None
        assert result.query_name == "funds_with_negative_pl"

    def test_new_funds(self):
        result = route("novos fundos")
        assert result is not None
        assert result.query_name == "new_funds"

    def test_filter_dy_and_pl(self):
        result = route("fundos com dy acima de 0.8% e pl acima de 100000000")
        assert result is not None
        assert result.query_name in ("funds_filtered_dy_and_pl", "funds_filtered_multi")

    def test_no_match(self):
        result = route("como esta o tempo hoje")
        assert result is None

    def test_fund_search(self):
        result = route("qual o cnpj do via parque")
        assert result is not None
        assert result.query_name == "find_fund_by_name"

    def test_list_segments(self):
        result = route("quais segmentos existem")
        assert result is not None
        assert result.query_name == "list_all_segments"

    def test_lowest_fee(self):
        result = route("fiis com menor taxa de administracao")
        assert result is not None
        assert result.query_name == "rank_by_lowest_admin_fee"

    def test_with_ticker(self):
        result = route("dy do HGLG11")
        assert result is not None
        assert result.query_name == "get_dividend_yield"
        assert result.params.get("fund_identifier") == "HGLG11"

    def test_cotistas_pf(self):
        result = route(f"cotistas pessoa fisica do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_cotistas_pf"

    def test_taxa_adm(self):
        result = route(f"taxa de administracao do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_taxa_administracao"

    def test_rentabilidade(self):
        result = route(f"rentabilidade do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_rentabilidade_efetiva"

    def test_passivo(self):
        result = route(f"total passivo do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_total_passivo"

    def test_count_funds(self):
        result = route("quantos fiis existem")
        assert result is not None
        assert result.query_name == "count_total_funds"

    def test_fund_age(self):
        result = route(f"quando foi criado o {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_fund_age"

    def test_compare_fees(self):
        result = route(f"comparar taxas do {SAMPLE_CNPJ} e {SAMPLE_CNPJ_2}")
        assert result is not None
        assert result.query_name == "compare_funds_fees"

    def test_segment_comparison(self):
        result = route("comparar segmentos logistica e shoppings")
        assert result is not None
        assert result.query_name == "segment_comparison"

    def test_funds_stopped_distributing(self):
        result = route("fundos que pararam de pagar dividendo")
        assert result is not None
        assert result.query_name == "funds_stopped_distributing"

    def test_share_dilution(self):
        result = route("fundos que emitiram novas cotas")
        assert result is not None
        assert result.query_name == "share_dilution"

    def test_imoveis(self):
        result = route(f"valor dos imoveis do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_imoveis_renda"

    def test_cri_cra(self):
        result = route(f"cri cra do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_cri_cra"

    def test_fii_holdings(self):
        result = route(f"cotas de fii do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_fii_holdings"

    def test_real_estate_pct(self):
        result = route(f"percentual em imoveis do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "calc_real_estate_pct"

    def test_paper_pct(self):
        result = route(f"percentual em papel do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "calc_paper_pct"

    def test_history_cotistas(self):
        result = route(f"evolucao de cotistas do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "history_cotistas"

    def test_rank_by_cotistas(self):
        result = route("fiis com mais cotistas")
        assert result is not None
        assert result.query_name == "rank_by_cotistas"

    def test_available_months(self):
        result = route(f"quais meses tem dados do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_available_months"

    def test_administrators(self):
        result = route("quais administradores")
        assert result is not None
        assert result.query_name == "list_all_administrators"

    def test_funds_by_admin(self):
        result = route("fundos da btg")
        assert result is not None
        assert result.query_name == "list_funds_by_administrator"

    def test_funds_by_state(self):
        result = route("fundos de sao paulo")
        assert result is not None
        assert result.query_name in ("list_funds_by_state", "list_funds_by_segment")


class TestRouterResult:
    def test_result_has_query_name(self):
        result = route(f"qual o dy do {SAMPLE_CNPJ}")
        assert hasattr(result, "query_name")

    def test_result_has_params(self):
        result = route(f"qual o dy do {SAMPLE_CNPJ}")
        assert hasattr(result, "params")
        assert isinstance(result.params, dict)

    def test_params_has_cnpj(self):
        result = route(f"qual o dy do {SAMPLE_CNPJ}")
        assert "cnpj" in result.params
        assert result.params["cnpj"] == SAMPLE_CNPJ

    def test_params_has_fund_identifier(self):
        result = route("dy do HGLG11")
        assert "fund_identifier" in result.params
        assert result.params["fund_identifier"] == "HGLG11"

    def test_params_has_date(self):
        result = route(f"dy do {SAMPLE_CNPJ} em setembro de 2026")
        assert result.params.get("date") is not None

    def test_params_has_min_pct(self):
        result = route("filtrar fundos com dy acima de 0.8%")
        assert result is not None
        assert result.params.get("min_pct") is not None

    def test_params_has_segment(self):
        result = route("maiores fundos de logistica por patrimonio")
        assert result.params.get("segment") is not None


class TestEdgeCases:
    def test_empty_string(self):
        result = route("")
        assert result is None

    def test_only_whitespace(self):
        result = route("   ")
        assert result is None

    def test_only_special_chars(self):
        result = route("???!!!")
        assert result is None

    def test_very_long_input(self):
        result = route("a " * 1000)
        assert result is None

    def test_mixed_case_keywords(self):
        result = route(f"Qual O DY do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_dividend_yield"

    def test_accented_keywords(self):
        result = route(f"histórico de dividendos do {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "history_dividend_yield"

    def test_multiple_spaces(self):
        result = route(f"qual   o   dy   do   {SAMPLE_CNPJ}")
        assert result is not None
        assert result.query_name == "get_dividend_yield"
