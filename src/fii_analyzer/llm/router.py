from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class RouterResult:
    query_name: str
    params: dict
    confidence: float


@dataclass
class ExtractedEntities:
    cnpjs: list[str] = field(default_factory=list)
    fund_names: list[str] = field(default_factory=list)
    date_ref: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    months: int | None = None
    limit: int | None = None
    min_pct: float | None = None
    max_pct: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    segment: str | None = None
    metric: str | None = None


# ---------------------------------------------------------------------------
# Keyword synonym groups
# ---------------------------------------------------------------------------

KW_DY = ["dy", "dividend", "dividendo", "dividendos", "rendimento", "provento", "yield", "distribuicao"]
KW_PL = ["pl", "patrimonio liquido", "patrimonio", "net worth"]
KW_VPA = ["vpa", "valor patrimonial", "valor da cota", "valor cota", "book value"]
KW_COTISTAS = ["cotistas", "investidores", "shareholders", "cotista", "base de cotistas"]
KW_COTISTAS_PF = ["pessoa fisica", "pf", "pessoas fisicas"]
KW_COTISTAS_PJ = ["pessoa juridica", "pj", "pessoas juridicas"]
KW_RENTABILIDADE = ["rentabilidade", "retorno", "return", "rendimento efetivo"]
KW_RENT_PATRIMONIAL = ["rentabilidade patrimonial", "retorno patrimonial"]
KW_TAXA_ADM = ["taxa administracao", "taxa de administracao", "taxa adm", "custo administracao", "management fee"]
KW_TAXA_CUSTODIANTE = ["taxa custodiante", "custo custodia"]
KW_AMORTIZACAO = ["amortizacao", "amortizou"]
KW_ATIVOS = ["ativo", "ativos", "investido", "investimentos", "valor ativo"]
KW_IMOVEIS = ["imoveis", "imovel", "tijolo", "real estate", "patrimonio imobiliario"]
KW_CRI = ["cri", "cra", "papel", "recebiveis", "certificados"]
KW_FOF = ["fof", "fund of funds", "fundo de fundos", "cotas de fii"]
KW_PASSIVO = ["passivo", "divida", "dividas", "obrigacoes", "liabilities", "endividamento"]
KW_CAIXA = ["caixa", "disponibilidades", "liquidez", "cash"]
KW_ALUGUEL = ["aluguel", "alugueis", "receita aluguel", "rent"]
KW_COTAS_EMITIDAS = ["cotas emitidas", "emissao", "novas cotas", "diluicao"]
KW_RENDIMENTOS_DIST = ["rendimentos a distribuir", "dividendos a pagar", "proventos pendentes"]
KW_VALORES_RECEBER = ["valores a receber", "recebiveis do fundo", "contas a receber"]
KW_LIQUIDEZ = ["liquidez", "necessidade de liquidez"]
KW_SECURITIZACAO = ["securitizacao", "alavancagem", "divida securitizada"]
KW_PROVISOES = ["provisoes", "contingencias", "provisao"]
KW_SEGMENTO = ["segmento", "categoria", "classificacao", "setor"]

KW_HISTORICAL = ["historico", "evolucao", "ao longo", "serie", "temporal", "ultimos", "meses", "desde"]
KW_RANKING = ["maiores", "melhores", "top", "ranking", "mais pagam", "mais paga", "mais", "piores", "menores"]
KW_COMPARE = ["comparar", "versus", "vs", "comparativo", "comparacao"]
KW_AGGREGATION = ["acumulado", "acumulada", "media", "medio", "soma", "total", "maximo", "minimo", "variacao"]
KW_ALERT = ["queda", "caiu", "diminuiu", "cortou", "parou", "perdeu", "aumentou", "subiu", "negativo"]
KW_PROFILE = ["perfil", "completo", "tudo sobre", "resumo", "ficha", "detalhes"]
KW_COMPOSITION = ["composicao", "alocacao", "carteira", "no que investe", "distribuicao percentual"]

# Modifiers used as exclusions for factual lookups (so they don't steal from
# historical/ranking/aggregation patterns).
KW_EXCLUDE_FROM_FACTUAL = (
    KW_HISTORICAL + KW_RANKING + KW_COMPARE + KW_AGGREGATION + KW_ALERT + KW_PROFILE + KW_COMPOSITION
)

CATEGORY_PRIORITY = {
    "alert": 9,
    "calculated": 8,
    "cross_table": 7,
    "aggregation": 6,
    "comparison": 5,
    "ranking": 4,
    "historical": 3,
    "factual": 2,
    "identification": 1,
    "segment": 5,
    "data_range": 1,
}

# ---------------------------------------------------------------------------
# QUERY_PATTERNS — all 138 queries
# ---------------------------------------------------------------------------

QUERY_PATTERNS: list[dict] = [
    # ===================================================================
    # Category 1: Fund Identification & Basic Info (11 queries)
    # ===================================================================
    {
        "query": "find_fund_by_name",
        "required": [["buscar fundo", "encontrar fii", "qual fundo", "nome do fundo", "qual o cnpj"]],
        "excluded": [],
        "needs_fund": False,
        "category": "identification",
    },
    {
        "query": "get_fund_info",
        "required": [["informacoes do fundo", "dados do fundo", "detalhes", "perfil", "qual segmento", "quem administra"]],
        "excluded": [KW_HISTORICAL, KW_RANKING],
        "needs_fund": True,
        "category": "identification",
    },
    {
        "query": "list_funds_by_segment",
        "required": [["fundos", "fiis", "listar"], KW_SEGMENTO + ["logistica", "shoppings", "escritorios", "residencial", "hospital", "varejo", "hotel", "educacional"]],
        "excluded": [KW_RANKING, KW_AGGREGATION],
        "needs_fund": False,
        "category": "identification",
    },
    {
        "query": "list_funds_by_administrator",
        "required": [["fundos", "fiis", "listar", "administrados"], ["administrador", "administra", "gestora", "btg", "xp", "brl trust"]],
        "excluded": [],
        "needs_fund": False,
        "category": "identification",
    },
    {
        "query": "list_funds_by_state",
        "required": [["fundos", "fiis", "listar"], ["estado", "sao paulo", "rio de janeiro", "minas gerais", "parana"]],
        "excluded": [],
        "needs_fund": False,
        "category": "identification",
    },
    {
        "query": "list_all_segments",
        "required": [["quais segmentos", "listar segmentos", "tipos de fii", "categorias de fii", "segmentos existentes"]],
        "excluded": [],
        "needs_fund": False,
        "category": "identification",
    },
    {
        "query": "list_all_administrators",
        "required": [["quais administradores", "maiores administradores", "listar gestores", "administradores de fii"]],
        "excluded": [],
        "needs_fund": False,
        "category": "identification",
    },
    {
        "query": "count_total_funds",
        "required": [["quantos fiis", "total de fundos", "numero de fiis", "quantos fundos existem"]],
        "excluded": [KW_SEGMENTO],
        "needs_fund": False,
        "category": "identification",
    },
    {
        "query": "count_funds_by_segment",
        "required": [["quantos fundos", "quantidade"], KW_SEGMENTO + ["por segmento"]],
        "excluded": [],
        "needs_fund": False,
        "category": "identification",
    },
    {
        "query": "get_fund_age",
        "required": [["quando foi criado", "idade do fundo", "data de inicio", "ha quantos anos", "data funcionamento", "fundado em"]],
        "excluded": [],
        "needs_fund": True,
        "category": "identification",
    },
    {
        "query": "get_available_months",
        "required": [["quais meses", "periodo disponivel", "desde quando tem dados", "meses disponiveis"]],
        "excluded": [],
        "needs_fund": True,
        "category": "data_range",
    },

    # ===================================================================
    # Category 2: Factual Lookups (25 queries)
    # Single fund, single metric, optional date
    # ===================================================================
    # 12: get_patrimonio_liquido
    {
        "query": "get_patrimonio_liquido",
        "required": [KW_PL],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_AGGREGATION, KW_ALERT, KW_COMPOSITION],
        "needs_fund": True,
        "category": "factual",
    },
    # 13: get_valor_ativo
    {
        "query": "get_valor_ativo",
        "required": [KW_ATIVOS],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_AGGREGATION, KW_ALERT, KW_COMPOSITION, KW_IMOVEIS, KW_CRI, KW_FOF],
        "needs_fund": True,
        "category": "factual",
    },
    # 14: get_valor_patrimonial_cotas
    {
        "query": "get_valor_patrimonial_cotas",
        "required": [KW_VPA],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_AGGREGATION, KW_ALERT],
        "needs_fund": True,
        "category": "factual",
    },
    # 15: get_dividend_yield
    {
        "query": "get_dividend_yield",
        "required": [KW_DY],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_AGGREGATION, KW_ALERT],
        "needs_fund": True,
        "category": "factual",
    },
    # 16: get_rentabilidade_efetiva
    {
        "query": "get_rentabilidade_efetiva",
        "required": [KW_RENTABILIDADE],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_AGGREGATION, KW_ALERT, KW_RENT_PATRIMONIAL],
        "needs_fund": True,
        "category": "factual",
    },
    # 17: get_rentabilidade_patrimonial
    {
        "query": "get_rentabilidade_patrimonial",
        "required": [KW_RENT_PATRIMONIAL],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_AGGREGATION],
        "needs_fund": True,
        "category": "factual",
    },
    # 18: get_total_cotistas
    {
        "query": "get_total_cotistas",
        "required": [KW_COTISTAS],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_AGGREGATION, KW_ALERT, KW_COTISTAS_PF, KW_COTISTAS_PJ],
        "needs_fund": True,
        "category": "factual",
    },
    # 19: get_cotistas_pf
    {
        "query": "get_cotistas_pf",
        "required": [KW_COTISTAS, KW_COTISTAS_PF],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_AGGREGATION],
        "needs_fund": True,
        "category": "factual",
    },
    # 20: get_cotistas_pj
    {
        "query": "get_cotistas_pj",
        "required": [KW_COTISTAS, KW_COTISTAS_PJ],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_AGGREGATION],
        "needs_fund": True,
        "category": "factual",
    },
    # 21: get_cotas_emitidas
    {
        "query": "get_cotas_emitidas",
        "required": [KW_COTAS_EMITIDAS + ["numero de cotas", "quantas cotas"]],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_ALERT],
        "needs_fund": True,
        "category": "factual",
    },
    # 22: get_taxa_administracao
    {
        "query": "get_taxa_administracao",
        "required": [KW_TAXA_ADM],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_AGGREGATION],
        "needs_fund": True,
        "category": "factual",
    },
    # 23: get_taxa_custodiante
    {
        "query": "get_taxa_custodiante",
        "required": [KW_TAXA_CUSTODIANTE],
        "excluded": [KW_HISTORICAL, KW_RANKING],
        "needs_fund": True,
        "category": "factual",
    },
    # 24: get_amortizacao
    {
        "query": "get_amortizacao",
        "required": [KW_AMORTIZACAO],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_ALERT],
        "needs_fund": True,
        "category": "factual",
    },
    # 25: get_total_investido
    {
        "query": "get_total_investido",
        "required": [["total investido", "investimentos totais"]],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_COMPOSITION],
        "needs_fund": True,
        "category": "factual",
    },
    # 26: get_imoveis_renda
    {
        "query": "get_imoveis_renda",
        "required": [KW_IMOVEIS],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_COMPOSITION, ["detalhes imoveis", "patrimonio imobiliario detalhado"]],
        "needs_fund": True,
        "category": "factual",
    },
    # 27: get_cri_cra
    {
        "query": "get_cri_cra",
        "required": [KW_CRI],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_COMPOSITION],
        "needs_fund": True,
        "category": "factual",
    },
    # 28: get_fii_holdings
    {
        "query": "get_fii_holdings",
        "required": [KW_FOF],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_COMPOSITION],
        "needs_fund": True,
        "category": "factual",
    },
    # 29: get_total_passivo
    {
        "query": "get_total_passivo",
        "required": [KW_PASSIVO],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_ALERT, KW_COMPOSITION, ["detalhamento passivo"]],
        "needs_fund": True,
        "category": "factual",
    },
    # 30: get_disponibilidades
    {
        "query": "get_disponibilidades",
        "required": [KW_CAIXA],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_COMPOSITION],
        "needs_fund": True,
        "category": "factual",
    },
    # 31: get_rendimentos_distribuir
    {
        "query": "get_rendimentos_distribuir",
        "required": [KW_RENDIMENTOS_DIST],
        "excluded": [KW_HISTORICAL, KW_RANKING],
        "needs_fund": True,
        "category": "factual",
    },
    # 32: get_valores_receber
    {
        "query": "get_valores_receber",
        "required": [KW_VALORES_RECEBER],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPOSITION],
        "needs_fund": True,
        "category": "factual",
    },
    # 33: get_contas_aluguel
    {
        "query": "get_contas_aluguel",
        "required": [KW_ALUGUEL],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "factual",
    },
    # 34: get_liquidez
    {
        "query": "get_liquidez",
        "required": [KW_LIQUIDEZ],
        "excluded": [KW_HISTORICAL, KW_RANKING, KW_COMPARE, KW_COMPOSITION],
        "needs_fund": True,
        "category": "factual",
    },
    # 35: get_obrigacoes_securitizacao
    {
        "query": "get_obrigacoes_securitizacao",
        "required": [KW_SECURITIZACAO],
        "excluded": [KW_HISTORICAL, KW_RANKING],
        "needs_fund": True,
        "category": "factual",
    },
    # 36: get_provisoes
    {
        "query": "get_provisoes",
        "required": [KW_PROVISOES],
        "excluded": [KW_HISTORICAL, KW_RANKING],
        "needs_fund": True,
        "category": "factual",
    },

    # ===================================================================
    # Category 3: Historical / Time Series (20 queries)
    # ===================================================================
    # 37: history_patrimonio_liquido
    {
        "query": "history_patrimonio_liquido",
        "required": [KW_PL, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE, KW_AGGREGATION],
        "needs_fund": True,
        "category": "historical",
    },
    # 38: history_valor_ativo
    {
        "query": "history_valor_ativo",
        "required": [KW_ATIVOS, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE, KW_AGGREGATION, KW_IMOVEIS, KW_CRI, KW_FOF],
        "needs_fund": True,
        "category": "historical",
    },
    # 39: history_valor_patrimonial
    {
        "query": "history_valor_patrimonial",
        "required": [KW_VPA, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE, KW_AGGREGATION],
        "needs_fund": True,
        "category": "historical",
    },
    # 40: history_dividend_yield
    {
        "query": "history_dividend_yield",
        "required": [KW_DY, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE, KW_AGGREGATION],
        "needs_fund": True,
        "category": "historical",
    },
    # 41: history_rentabilidade_efetiva
    {
        "query": "history_rentabilidade_efetiva",
        "required": [KW_RENTABILIDADE, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE, KW_AGGREGATION, KW_RENT_PATRIMONIAL],
        "needs_fund": True,
        "category": "historical",
    },
    # 42: history_rentabilidade_patrimonial
    {
        "query": "history_rentabilidade_patrimonial",
        "required": [KW_RENT_PATRIMONIAL, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "historical",
    },
    # 43: history_cotistas
    {
        "query": "history_cotistas",
        "required": [KW_COTISTAS, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE, KW_AGGREGATION, KW_COTISTAS_PF, KW_COTISTAS_PJ],
        "needs_fund": True,
        "category": "historical",
    },
    # 44: history_cotistas_pf
    {
        "query": "history_cotistas_pf",
        "required": [KW_COTISTAS, KW_COTISTAS_PF, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "historical",
    },
    # 45: history_cotas_emitidas
    {
        "query": "history_cotas_emitidas",
        "required": [KW_COTAS_EMITIDAS + ["numero de cotas"], KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_ALERT],
        "needs_fund": True,
        "category": "historical",
    },
    # 46: history_taxa_administracao
    {
        "query": "history_taxa_administracao",
        "required": [KW_TAXA_ADM, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "historical",
    },
    # 47: history_total_investido
    {
        "query": "history_total_investido",
        "required": [["total investido", "investimentos totais", "investido"], KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE, KW_COMPOSITION],
        "needs_fund": True,
        "category": "historical",
    },
    # 48: history_imoveis_renda
    {
        "query": "history_imoveis_renda",
        "required": [KW_IMOVEIS, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE, KW_COMPOSITION],
        "needs_fund": True,
        "category": "historical",
    },
    # 49: history_cri_cra
    {
        "query": "history_cri_cra",
        "required": [KW_CRI, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE, KW_COMPOSITION],
        "needs_fund": True,
        "category": "historical",
    },
    # 50: history_fii_holdings
    {
        "query": "history_fii_holdings",
        "required": [KW_FOF, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE, KW_COMPOSITION],
        "needs_fund": True,
        "category": "historical",
    },
    # 51: history_total_passivo
    {
        "query": "history_total_passivo",
        "required": [KW_PASSIVO, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE, KW_ALERT, KW_COMPOSITION],
        "needs_fund": True,
        "category": "historical",
    },
    # 52: history_disponibilidades
    {
        "query": "history_disponibilidades",
        "required": [KW_CAIXA, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE, KW_COMPOSITION],
        "needs_fund": True,
        "category": "historical",
    },
    # 53: history_rendimentos_distribuir
    {
        "query": "history_rendimentos_distribuir",
        "required": [KW_RENDIMENTOS_DIST, KW_HISTORICAL],
        "excluded": [KW_RANKING],
        "needs_fund": True,
        "category": "historical",
    },
    # 54: history_contas_aluguel
    {
        "query": "history_contas_aluguel",
        "required": [KW_ALUGUEL, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "historical",
    },
    # 55: history_amortizacao
    {
        "query": "history_amortizacao",
        "required": [KW_AMORTIZACAO, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_ALERT],
        "needs_fund": True,
        "category": "historical",
    },
    # 56: history_liquidez
    {
        "query": "history_liquidez",
        "required": [KW_LIQUIDEZ, KW_HISTORICAL],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "historical",
    },

    # ===================================================================
    # Category 4: Rankings / Top-N (18 queries)
    # ===================================================================
    # 57: rank_by_dividend_yield
    {
        "query": "rank_by_dividend_yield",
        "required": [KW_DY, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL],
        "needs_fund": False,
        "category": "ranking",
    },
    # 58: rank_by_patrimonio_liquido
    {
        "query": "rank_by_patrimonio_liquido",
        "required": [KW_PL, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL, ["menores fundos", "menor pl"]],
        "needs_fund": False,
        "category": "ranking",
    },
    # 59: rank_by_valor_ativo
    {
        "query": "rank_by_valor_ativo",
        "required": [KW_ATIVOS, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL, KW_IMOVEIS, KW_CRI, KW_FOF],
        "needs_fund": False,
        "category": "ranking",
    },
    # 60: rank_by_cotistas
    {
        "query": "rank_by_cotistas",
        "required": [KW_COTISTAS, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL, KW_COTISTAS_PF, KW_COTISTAS_PJ],
        "needs_fund": False,
        "category": "ranking",
    },
    # 61: rank_by_cotistas_pf
    {
        "query": "rank_by_cotistas_pf",
        "required": [KW_COTISTAS, KW_COTISTAS_PF, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL],
        "needs_fund": False,
        "category": "ranking",
    },
    # 62: rank_by_vpa
    {
        "query": "rank_by_vpa",
        "required": [KW_VPA, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL],
        "needs_fund": False,
        "category": "ranking",
    },
    # 63: rank_by_rentabilidade
    {
        "query": "rank_by_rentabilidade",
        "required": [KW_RENTABILIDADE, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL],
        "needs_fund": False,
        "category": "ranking",
    },
    # 64: rank_by_cotas_emitidas
    {
        "query": "rank_by_cotas_emitidas",
        "required": [KW_COTAS_EMITIDAS + ["numero de cotas"], KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL],
        "needs_fund": False,
        "category": "ranking",
    },
    # 65: rank_by_total_investido
    {
        "query": "rank_by_total_investido",
        "required": [["total investido", "investimentos totais", "investido"], KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL, KW_COMPOSITION],
        "needs_fund": False,
        "category": "ranking",
    },
    # 66: rank_by_imoveis
    {
        "query": "rank_by_imoveis",
        "required": [KW_IMOVEIS, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL, KW_COMPOSITION],
        "needs_fund": False,
        "category": "ranking",
    },
    # 67: rank_by_cri_cra
    {
        "query": "rank_by_cri_cra",
        "required": [KW_CRI, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL, KW_COMPOSITION],
        "needs_fund": False,
        "category": "ranking",
    },
    # 68: rank_by_fii_holdings
    {
        "query": "rank_by_fii_holdings",
        "required": [KW_FOF, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL, KW_COMPOSITION],
        "needs_fund": False,
        "category": "ranking",
    },
    # 69: rank_by_total_passivo
    {
        "query": "rank_by_total_passivo",
        "required": [KW_PASSIVO, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL, KW_ALERT, KW_COMPOSITION],
        "needs_fund": False,
        "category": "ranking",
    },
    # 70: rank_by_disponibilidades
    {
        "query": "rank_by_disponibilidades",
        "required": [KW_CAIXA, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL, KW_COMPOSITION],
        "needs_fund": False,
        "category": "ranking",
    },
    # 71: rank_by_lowest_admin_fee
    {
        "query": "rank_by_lowest_admin_fee",
        "required": [KW_TAXA_ADM, ["menor", "menores", "mais baixa", "mais barato", "ranking", "top"]],
        "excluded": [KW_COMPARE, KW_HISTORICAL],
        "needs_fund": False,
        "category": "ranking",
    },
    # 72: rank_by_contas_aluguel
    {
        "query": "rank_by_contas_aluguel",
        "required": [KW_ALUGUEL, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL],
        "needs_fund": False,
        "category": "ranking",
    },
    # 73: rank_by_rendimentos_distribuir
    {
        "query": "rank_by_rendimentos_distribuir",
        "required": [KW_RENDIMENTOS_DIST, KW_RANKING],
        "excluded": [KW_COMPARE, KW_HISTORICAL],
        "needs_fund": False,
        "category": "ranking",
    },
    # 74: rank_smallest_funds
    {
        "query": "rank_smallest_funds",
        "required": [KW_PL, ["menores fundos", "menor pl", "menores patrimonios", "menores"]],
        "excluded": [KW_COMPARE, KW_HISTORICAL],
        "needs_fund": False,
        "category": "ranking",
    },

    # ===================================================================
    # Category 5: Comparisons (7 queries)
    # ===================================================================
    # 75: compare_funds_single_metric
    {
        "query": "compare_funds_single_metric",
        "required": [KW_COMPARE, KW_DY + KW_PL + KW_VPA + KW_COTISTAS + KW_RENTABILIDADE + KW_ATIVOS + KW_PASSIVO + KW_IMOVEIS + KW_CRI + KW_CAIXA],
        "excluded": [KW_HISTORICAL, KW_PROFILE, ["balanco", "todos os indicadores", "completo"]],
        "needs_fund": True,
        "category": "comparison",
    },
    # 76: compare_funds_full
    {
        "query": "compare_funds_full",
        "required": [KW_COMPARE],
        "excluded": [KW_HISTORICAL, KW_DY, KW_PL, KW_VPA, KW_COTISTAS, KW_RENTABILIDADE, KW_IMOVEIS, KW_CRI, KW_FOF, KW_PASSIVO, KW_CAIXA, KW_TAXA_ADM, ["balanco"]],
        "needs_fund": True,
        "category": "comparison",
    },
    # 77: compare_funds_dy_history
    {
        "query": "compare_funds_dy_history",
        "required": [KW_COMPARE, KW_DY, KW_HISTORICAL],
        "excluded": [],
        "needs_fund": True,
        "category": "comparison",
    },
    # 78: compare_funds_pl_history
    {
        "query": "compare_funds_pl_history",
        "required": [KW_COMPARE, KW_PL, KW_HISTORICAL],
        "excluded": [],
        "needs_fund": True,
        "category": "comparison",
    },
    # 79: compare_funds_cotistas_history
    {
        "query": "compare_funds_cotistas_history",
        "required": [KW_COMPARE, KW_COTISTAS, KW_HISTORICAL],
        "excluded": [],
        "needs_fund": True,
        "category": "comparison",
    },
    # 80: compare_funds_balance_sheet
    {
        "query": "compare_funds_balance_sheet",
        "required": [KW_COMPARE, ["balanco", "composicao de ativos", "ativos e passivos", "balanco patrimonial"]],
        "excluded": [],
        "needs_fund": True,
        "category": "comparison",
    },
    # 81: compare_funds_fees
    {
        "query": "compare_funds_fees",
        "required": [KW_COMPARE, KW_TAXA_ADM + KW_TAXA_CUSTODIANTE + ["taxas", "custos"]],
        "excluded": [],
        "needs_fund": True,
        "category": "comparison",
    },

    # ===================================================================
    # Category 6: Aggregations (14 queries)
    # ===================================================================
    # 82: accumulated_dy
    {
        "query": "accumulated_dy",
        "required": [KW_DY, ["acumulado", "acumulada", "soma", "somado"]],
        "excluded": [KW_RANKING, KW_COMPARE, ["anualizado", "anual", "12 meses", "por ano"]],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 83: average_dy
    {
        "query": "average_dy",
        "required": [KW_DY, ["media", "medio", "average"]],
        "excluded": [KW_RANKING, KW_COMPARE, ["anualizado"]],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 84: annualized_dy
    {
        "query": "annualized_dy",
        "required": [KW_DY, ["anualizado", "anualizada", "anual", "por ano"]],
        "excluded": [KW_RANKING, KW_COMPARE, ["12 meses", "ultimos 12"]],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 85: dy_last_12_months
    {
        "query": "dy_last_12_months",
        "required": [KW_DY, ["12 meses", "ultimos 12", "ultimo ano", "acumulado 12"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 86: average_rentabilidade
    {
        "query": "average_rentabilidade",
        "required": [KW_RENTABILIDADE, ["media", "medio", "average"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 87: pl_variation
    {
        "query": "pl_variation",
        "required": [KW_PL, ["variacao", "mudou", "crescimento", "cresceu", "caiu"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 88: cotistas_variation
    {
        "query": "cotistas_variation",
        "required": [KW_COTISTAS, ["variacao", "ganhou", "perdeu", "crescimento", "mudou"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 89: vpa_variation
    {
        "query": "vpa_variation",
        "required": [KW_VPA, ["variacao", "mudou", "cresceu", "caiu"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 90: dividend_per_cota_estimate
    {
        "query": "dividend_per_cota_estimate",
        "required": [KW_DY + ["dividendo", "rendimento"], ["por cota", "em reais", "valor rendimento", "quanto pagou", "quanto paga"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 91: max_dy_period
    {
        "query": "max_dy_period",
        "required": [KW_DY, ["maior", "maximo", "melhor mes", "pico"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 92: min_dy_period
    {
        "query": "min_dy_period",
        "required": [KW_DY, ["menor", "minimo", "pior mes"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 93: average_pl_period
    {
        "query": "average_pl_period",
        "required": [KW_PL, ["media", "medio", "pl medio"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 94: cotas_emitidas_change
    {
        "query": "cotas_emitidas_change",
        "required": [KW_COTAS_EMITIDAS + ["numero de cotas"], ["variacao", "mudou", "emitiu", "houve emissao"]],
        "excluded": [KW_RANKING],
        "needs_fund": True,
        "category": "aggregation",
    },
    # 95: total_return_estimate
    {
        "query": "total_return_estimate",
        "required": [KW_RENTABILIDADE, ["acumulado", "acumulada", "total", "no periodo"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "aggregation",
    },

    # ===================================================================
    # Category 7: Segment Analysis (10 queries)
    # ===================================================================
    # 96: segment_average_dy
    {
        "query": "segment_average_dy",
        "required": [KW_DY, KW_SEGMENTO + ["por segmento"]],
        "excluded": [KW_COMPARE],
        "needs_fund": False,
        "category": "segment",
    },
    # 97: segment_average_pl
    {
        "query": "segment_average_pl",
        "required": [KW_PL, KW_SEGMENTO + ["por segmento"]],
        "excluded": [KW_COMPARE],
        "needs_fund": False,
        "category": "segment",
    },
    # 98: segment_total_pl
    {
        "query": "segment_total_pl",
        "required": [KW_PL, ["total", "soma"], KW_SEGMENTO + ["por segmento"]],
        "excluded": [KW_COMPARE],
        "needs_fund": False,
        "category": "segment",
    },
    # 99: segment_fund_count
    {
        "query": "segment_fund_count",
        "required": [["quantos", "quantidade", "numero"], KW_SEGMENTO + ["por segmento"]],
        "excluded": [],
        "needs_fund": False,
        "category": "segment",
    },
    # 100: segment_average_cotistas
    {
        "query": "segment_average_cotistas",
        "required": [KW_COTISTAS, KW_SEGMENTO + ["por segmento"]],
        "excluded": [KW_COMPARE],
        "needs_fund": False,
        "category": "segment",
    },
    # 101: segment_average_vpa
    {
        "query": "segment_average_vpa",
        "required": [KW_VPA, KW_SEGMENTO + ["por segmento"]],
        "excluded": [KW_COMPARE],
        "needs_fund": False,
        "category": "segment",
    },
    # 102: segment_average_rentabilidade
    {
        "query": "segment_average_rentabilidade",
        "required": [KW_RENTABILIDADE, KW_SEGMENTO + ["por segmento"]],
        "excluded": [KW_COMPARE],
        "needs_fund": False,
        "category": "segment",
    },
    # 103: segment_average_fee
    {
        "query": "segment_average_fee",
        "required": [KW_TAXA_ADM, KW_SEGMENTO + ["por segmento"]],
        "excluded": [KW_COMPARE],
        "needs_fund": False,
        "category": "segment",
    },
    # 104: segment_total_investido
    {
        "query": "segment_total_investido",
        "required": [["total investido", "investimentos", "investido"], KW_SEGMENTO + ["por segmento"]],
        "excluded": [KW_COMPARE],
        "needs_fund": False,
        "category": "segment",
    },
    # 105: segment_comparison
    {
        "query": "segment_comparison",
        "required": [KW_COMPARE + ["comparar segmentos"], KW_SEGMENTO + ["logistica", "shoppings", "escritorios", "residencial"]],
        "excluded": [],
        "needs_fund": False,
        "category": "segment",
    },

    # ===================================================================
    # Category 8: Cross-Table Queries (12 queries)
    # ===================================================================
    # 106: fund_complete_profile
    {
        "query": "fund_complete_profile",
        "required": [KW_PROFILE],
        "excluded": [],
        "needs_fund": True,
        "category": "cross_table",
    },
    # 107: fund_asset_composition
    {
        "query": "fund_asset_composition",
        "required": [KW_COMPOSITION + ["no que investe"]],
        "excluded": [["percentual", "porcentagem", "%"]],
        "needs_fund": True,
        "category": "cross_table",
    },
    # 108: fund_asset_composition_pct
    {
        "query": "fund_asset_composition_pct",
        "required": [KW_COMPOSITION + ["no que investe"], ["percentual", "porcentagem", "%", "distribuicao percentual"]],
        "excluded": [],
        "needs_fund": True,
        "category": "cross_table",
    },
    # 109: fund_liquidity_analysis
    {
        "query": "fund_liquidity_analysis",
        "required": [["posicao de caixa", "liquidez do fundo", "quanto em caixa", "analise de liquidez"]],
        "excluded": [KW_HISTORICAL],
        "needs_fund": True,
        "category": "cross_table",
    },
    # 110: fund_liability_breakdown
    {
        "query": "fund_liability_breakdown",
        "required": [KW_PASSIVO, ["detalhamento", "detalhado", "breakdown", "composicao"]],
        "excluded": [KW_HISTORICAL],
        "needs_fund": True,
        "category": "cross_table",
    },
    # 111: fund_real_estate_detail
    {
        "query": "fund_real_estate_detail",
        "required": [KW_IMOVEIS, ["detalhes", "detalhado", "detalhamento", "patrimonio imobiliario"]],
        "excluded": [KW_HISTORICAL],
        "needs_fund": True,
        "category": "cross_table",
    },
    # 112: fund_securities_detail
    {
        "query": "fund_securities_detail",
        "required": [["detalhes titulos", "carteira de papeis", "investimentos mobiliarios", "titulos do fundo"]],
        "excluded": [KW_HISTORICAL],
        "needs_fund": True,
        "category": "cross_table",
    },
    # 113: fund_receivables_detail
    {
        "query": "fund_receivables_detail",
        "required": [KW_VALORES_RECEBER + ["recebiveis"], ["detalhes", "detalhado", "breakdown", "composicao"]],
        "excluded": [KW_HISTORICAL],
        "needs_fund": True,
        "category": "cross_table",
    },
    # 114: fund_metrics_with_segment
    {
        "query": "fund_metrics_with_segment",
        "required": [["metricas", "indicadores"], KW_SEGMENTO + ["classificacao"]],
        "excluded": [KW_HISTORICAL, KW_RANKING],
        "needs_fund": True,
        "category": "cross_table",
    },
    # 115: funds_filtered_dy_and_pl
    {
        "query": "funds_filtered_dy_and_pl",
        "required": [KW_DY, KW_PL, ["acima", "maior que", "filtrar", "mais de"]],
        "excluded": [],
        "needs_fund": False,
        "category": "cross_table",
    },
    # 116: funds_filtered_multi
    {
        "query": "funds_filtered_multi",
        "required": [["filtrar fundos", "buscar com criterios", "encontrar fiis que", "filtrar fiis"]],
        "excluded": [KW_ALERT],
        "needs_fund": False,
        "category": "cross_table",
    },
    # 117: fund_dy_with_balance_summary
    {
        "query": "fund_dy_with_balance_summary",
        "required": [KW_DY, ["balanco", "ativos", "passivo"]],
        "excluded": [KW_HISTORICAL, KW_COMPARE],
        "needs_fund": True,
        "category": "cross_table",
    },

    # ===================================================================
    # Category 9: Alerts & Anomalies (13 queries)
    # ===================================================================
    # 118: dy_drop_mom
    {
        "query": "dy_drop_mom",
        "required": [KW_DY, ["queda", "caiu", "diminuiu", "cortou", "reduziu"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": False,
        "category": "alert",
    },
    # 119: dy_increase_mom
    {
        "query": "dy_increase_mom",
        "required": [KW_DY, ["aumento", "aumentou", "subiu", "cresceu"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": False,
        "category": "alert",
    },
    # 120: cotistas_drop
    {
        "query": "cotistas_drop",
        "required": [KW_COTISTAS, ["perdeu", "queda", "fuga", "saida", "diminuiu"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": False,
        "category": "alert",
    },
    # 121: cotistas_increase
    {
        "query": "cotistas_increase",
        "required": [KW_COTISTAS, ["ganhou", "atraiu", "novos", "aumentou", "cresceu"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": False,
        "category": "alert",
    },
    # 122: pl_drop
    {
        "query": "pl_drop",
        "required": [KW_PL, ["queda", "caiu", "diminuiu", "reduziu"]],
        "excluded": [KW_RANKING, KW_COMPARE, KW_AGGREGATION],
        "needs_fund": False,
        "category": "alert",
    },
    # 123: pl_increase
    {
        "query": "pl_increase",
        "required": [KW_PL, ["crescimento", "aumentou", "subiu", "cresceu"]],
        "excluded": [KW_RANKING, KW_COMPARE, KW_AGGREGATION],
        "needs_fund": False,
        "category": "alert",
    },
    # 124: vpa_drop
    {
        "query": "vpa_drop",
        "required": [KW_VPA, ["queda", "caiu", "desvalorizou", "diminuiu"]],
        "excluded": [KW_RANKING, KW_COMPARE, KW_AGGREGATION],
        "needs_fund": False,
        "category": "alert",
    },
    # 125: funds_with_negative_dy
    {
        "query": "funds_with_negative_dy",
        "required": [KW_DY, ["negativo", "negativos"]],
        "excluded": [KW_RANKING],
        "needs_fund": False,
        "category": "alert",
    },
    # 126: funds_with_negative_pl
    {
        "query": "funds_with_negative_pl",
        "required": [KW_PL, ["negativo", "negativos"]],
        "excluded": [KW_RANKING],
        "needs_fund": False,
        "category": "alert",
    },
    # 127: funds_stopped_distributing
    {
        "query": "funds_stopped_distributing",
        "required": [["parou de pagar", "pararam de pagar", "suspendeu dividendo", "sem rendimento", "parou de distribuir", "pararam de distribuir", "nao pagou", "nao pagaram"]],
        "excluded": [],
        "needs_fund": False,
        "category": "alert",
    },
    # 128: share_dilution
    {
        "query": "share_dilution",
        "required": [KW_COTAS_EMITIDAS + ["novas cotas"], ["emissao", "diluicao", "emitiu", "emitiram", "emitidas"]],
        "excluded": [KW_HISTORICAL],
        "needs_fund": False,
        "category": "alert",
    },
    # 129: new_funds
    {
        "query": "new_funds",
        "required": [["novos fundos", "fiis novos", "lancamentos", "fundos recentes", "novos fiis"]],
        "excluded": [],
        "needs_fund": False,
        "category": "alert",
    },
    # 130: passivo_increase
    {
        "query": "passivo_increase",
        "required": [KW_PASSIVO, ["aumento", "aumentou", "cresceu", "subiu"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": False,
        "category": "alert",
    },

    # ===================================================================
    # Category 10: Calculated Metrics (8 queries)
    # ===================================================================
    # 131: calc_dy_anualizado
    {
        "query": "calc_dy_anualizado",
        "required": [KW_DY, ["anualizado", "anualizada", "anual", "por ano", "quanto rende por ano"]],
        "excluded": [KW_RANKING, KW_COMPARE, KW_HISTORICAL],
        "needs_fund": True,
        "category": "calculated",
    },
    # 132: calc_dy_acumulado_12m
    {
        "query": "calc_dy_acumulado_12m",
        "required": [KW_DY, ["12 meses", "ultimos 12", "ultimo ano", "acumulado 12"]],
        "excluded": [KW_RANKING, KW_COMPARE, KW_HISTORICAL],
        "needs_fund": True,
        "category": "calculated",
    },
    # 133: calc_dividend_per_cota
    {
        "query": "calc_dividend_per_cota",
        "required": [["dividendo por cota", "quanto paga por cota", "rendimento em reais", "valor por cota"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "calculated",
    },
    # 134: calc_total_dividends
    {
        "query": "calc_total_dividends",
        "required": [["total distribuido", "quanto pagou no total", "total pago", "soma dos dividendos"]],
        "excluded": [KW_RANKING, KW_COMPARE],
        "needs_fund": True,
        "category": "calculated",
    },
    # 135: calc_real_estate_pct
    {
        "query": "calc_real_estate_pct",
        "required": [KW_IMOVEIS, ["percentual", "porcentagem", "%", "quanto em"]],
        "excluded": [KW_RANKING, KW_COMPARE, KW_HISTORICAL, KW_COMPOSITION],
        "needs_fund": True,
        "category": "calculated",
    },
    # 136: calc_paper_pct
    {
        "query": "calc_paper_pct",
        "required": [KW_CRI, ["percentual", "porcentagem", "%", "quanto em"]],
        "excluded": [KW_RANKING, KW_COMPARE, KW_HISTORICAL, KW_COMPOSITION],
        "needs_fund": True,
        "category": "calculated",
    },
    # 137: calc_fof_pct
    {
        "query": "calc_fof_pct",
        "required": [KW_FOF, ["percentual", "porcentagem", "%", "quanto em"]],
        "excluded": [KW_RANKING, KW_COMPARE, KW_HISTORICAL, KW_COMPOSITION],
        "needs_fund": True,
        "category": "calculated",
    },
    # 138: calc_cash_pct
    {
        "query": "calc_cash_pct",
        "required": [KW_CAIXA, ["percentual", "porcentagem", "%", "quanto em"]],
        "excluded": [KW_RANKING, KW_COMPARE, KW_HISTORICAL, KW_COMPOSITION],
        "needs_fund": True,
        "category": "calculated",
    },
]


# ---------------------------------------------------------------------------
# Segments canonical map (normalized → display)
# ---------------------------------------------------------------------------

SEGMENT_MAP = {
    "logistica": "Logística",
    "shoppings": "Shoppings",
    "shopping": "Shoppings",
    "escritorios": "Escritórios",
    "escritorio": "Escritórios",
    "lajes corporativas": "Lajes Corporativas",
    "lajes": "Lajes Corporativas",
    "residencial": "Residencial",
    "residenciais": "Residencial",
    "hospital": "Hospital",
    "varejo": "Varejo",
    "hotel": "Hotel",
    "educacional": "Educacional",
    "hibrido": "Híbrido",
    "multicategoria": "Multicategoria",
    "outros": "Outros",
}

MONTH_MAP = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s%/.,]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

_CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
_TICKER_RE = re.compile(r"\b[A-Za-z]{4}\d{2}\b")
_QUOTED_RE = re.compile(r'"([^"]+)"')


def extract_cnpjs(text: str) -> list[str]:
    return _CNPJ_RE.findall(text)


def extract_fund_names(text: str) -> list[str]:
    names: list[str] = []
    names.extend(t.upper() for t in _TICKER_RE.findall(text))
    names.extend(_QUOTED_RE.findall(text))
    return names


_MONTH_NAMES = "|".join(MONTH_MAP.keys())
_RE_MONTH_YEAR = re.compile(
    rf"em\s+({_MONTH_NAMES})\s+(?:de\s+)?(\d{{4}})"
)
_RE_YEAR_ONLY = re.compile(r"\bem\s+(\d{4})\b")
_RE_LAST_N_MONTHS = re.compile(r"ultimos?\s+(\d+)\s+mes(?:es)?")
_RE_LAST_MONTH = re.compile(r"ultimo\s+mes")
_RE_THIS_YEAR = re.compile(r"(?:este\s+ano|ano\s+atual)")
_RE_LAST_YEAR = re.compile(r"ano\s+passado")
_RE_SINCE_YEAR = re.compile(r"desde\s+(\d{4})")
_RE_MM_YYYY = re.compile(r"\b(\d{2})/(\d{4})\b")


def extract_dates(normalized: str) -> dict:
    result: dict = {}
    today = date.today()

    m = _RE_MONTH_YEAR.search(normalized)
    if m:
        month_num = MONTH_MAP[m.group(1)]
        year = int(m.group(2))
        result["date_ref"] = date(year, month_num, 1)
        return result

    m = _RE_MM_YYYY.search(normalized)
    if m:
        month_num = int(m.group(1))
        year = int(m.group(2))
        if 1 <= month_num <= 12:
            result["date_ref"] = date(year, month_num, 1)
            return result

    m = _RE_LAST_N_MONTHS.search(normalized)
    if m:
        result["months"] = int(m.group(1))
        return result

    if _RE_LAST_MONTH.search(normalized):
        result["months"] = 1
        return result

    if _RE_THIS_YEAR.search(normalized):
        result["start_date"] = date(today.year, 1, 1)
        return result

    if _RE_LAST_YEAR.search(normalized):
        result["start_date"] = date(today.year - 1, 1, 1)
        result["end_date"] = date(today.year - 1, 12, 1)
        return result

    m = _RE_SINCE_YEAR.search(normalized)
    if m:
        result["start_date"] = date(int(m.group(1)), 1, 1)
        return result

    m = _RE_YEAR_ONLY.search(normalized)
    if m:
        year = int(m.group(1))
        result["start_date"] = date(year, 1, 1)
        result["end_date"] = date(year, 12, 1)
        return result

    return result


_THRESHOLD_PATTERNS = [
    (re.compile(r"(?:acima|mais|maior|superior)\s+(?:de|que)\s+(\d+[.,]?\d*)\s*%"), "min_pct"),
    (re.compile(r"(?:abaixo|menos|menor|inferior)\s+(?:de|que)\s+(\d+[.,]?\d*)\s*%"), "max_pct"),
    (re.compile(r"(?:acima|mais|maior|superior)\s+(?:de|que)\s+r?\$?\s*(\d+[.,]?\d*)"), "min_value"),
    (re.compile(r"(?:abaixo|menos|menor|inferior)\s+(?:de|que)\s+r?\$?\s*(\d+[.,]?\d*)"), "max_value"),
    (re.compile(r"top\s+(\d+)"), "limit"),
    (re.compile(r"(\d+)\s+(?:maiores|melhores|piores|menores)"), "limit"),
]


def extract_numbers(normalized: str) -> dict:
    result: dict = {}
    for pattern, key in _THRESHOLD_PATTERNS:
        m = pattern.search(normalized)
        if m:
            val_str = m.group(1).replace(",", ".")
            val = float(val_str)
            if key == "limit":
                result[key] = int(val)
            else:
                result[key] = val
    return result


def extract_segment(normalized: str) -> str | None:
    text = normalized.lower()
    for key, canonical in SEGMENT_MAP.items():
        if key in text:
            return canonical
    return None


# ---------------------------------------------------------------------------
# Matching engine
# ---------------------------------------------------------------------------

def _keyword_in_text(keyword: str, text: str) -> bool:
    if " " in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def _group_matches(group: list[str], text: str) -> bool:
    return any(_keyword_in_text(kw, text) for kw in group)


def match_query(normalized: str, entities: ExtractedEntities) -> RouterResult | None:
    has_fund = bool(entities.cnpjs or entities.fund_names)
    scores: list[tuple[float, str]] = []

    for pattern in QUERY_PATTERNS:
        if pattern["needs_fund"] and not has_fund:
            continue

        required: list[list[str]] = pattern["required"]
        all_required = True
        match_count = 0
        for group in required:
            if _group_matches(group, normalized):
                match_count += 1
            else:
                all_required = False
                break

        if not all_required:
            continue

        excluded: list[list[str]] = pattern.get("excluded", [])
        if any(_group_matches(group, normalized) for group in excluded):
            continue

        cat_priority = CATEGORY_PRIORITY.get(pattern["category"], 0)
        score = match_count + cat_priority * 0.1
        scores.append((score, pattern["query"]))

    if not scores:
        return None

    scores.sort(key=lambda x: x[0], reverse=True)
    best_score, best_query = scores[0]

    max_possible = max(
        (len(p["required"]) + CATEGORY_PRIORITY.get(p["category"], 0) * 0.1)
        for p in QUERY_PATTERNS
    )
    confidence = min(best_score / max_possible, 1.0) if max_possible > 0 else 0.5

    params = _build_params(best_query, entities)
    return RouterResult(query_name=best_query, params=params, confidence=confidence)


def _build_params(query_name: str, entities: ExtractedEntities) -> dict:
    params: dict = {}

    if entities.cnpjs:
        if len(entities.cnpjs) == 1:
            params["cnpj"] = entities.cnpjs[0]
        else:
            params["cnpjs"] = entities.cnpjs

    if entities.fund_names:
        if not entities.cnpjs:
            if len(entities.fund_names) == 1:
                params["fund_identifier"] = entities.fund_names[0]
            else:
                params["fund_identifiers"] = entities.fund_names

    if entities.date_ref is not None:
        params["date"] = entities.date_ref
    if entities.start_date is not None:
        params["start_date"] = entities.start_date
    if entities.end_date is not None:
        params["end_date"] = entities.end_date
    if entities.months is not None:
        params["months"] = entities.months
    if entities.limit is not None:
        params["n"] = entities.limit
    if entities.segment is not None:
        params["segment"] = entities.segment
    if entities.min_pct is not None:
        params["min_pct"] = entities.min_pct
    if entities.max_pct is not None:
        params["max_pct"] = entities.max_pct
    if entities.min_value is not None:
        params["min_value"] = entities.min_value
    if entities.max_value is not None:
        params["max_value"] = entities.max_value

    return params


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def route(question: str) -> RouterResult | None:
    original = question
    normalized = normalize(question)

    cnpjs = extract_cnpjs(original)
    fund_names = extract_fund_names(original)
    date_info = extract_dates(normalized)
    numbers = extract_numbers(normalized)
    segment = extract_segment(normalized)

    entities = ExtractedEntities(
        cnpjs=cnpjs,
        fund_names=fund_names,
        date_ref=date_info.get("date_ref"),
        start_date=date_info.get("start_date"),
        end_date=date_info.get("end_date"),
        months=date_info.get("months"),
        limit=numbers.get("limit"),
        min_pct=numbers.get("min_pct"),
        max_pct=numbers.get("max_pct"),
        min_value=numbers.get("min_value"),
        max_value=numbers.get("max_value"),
        segment=segment,
    )

    return match_query(normalized, entities)
