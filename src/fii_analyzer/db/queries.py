from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session


def _to_dict(row) -> dict:
    return dict(row._mapping)


def _to_list(rows) -> list[dict]:
    return [dict(r._mapping) for r in rows]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_LATEST_VERSAO_GERAL = """
WITH latest_g AS (
    SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
    FROM fii_fundo_mensal
    WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
    GROUP BY cnpj_fundo, data_referencia
)
"""

_LATEST_VERSAO_METRICA = """
WITH latest_m AS (
    SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
    FROM fii_metrica_mensal
    WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_metrica_mensal))
    GROUP BY cnpj_fundo, data_referencia
)
"""

_LATEST_VERSAO_BALANCO = """
WITH latest_b AS (
    SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
    FROM fii_balanco_mensal
    WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_balanco_mensal))
    GROUP BY cnpj_fundo, data_referencia
)
"""


def _single_metric(
    session: Session,
    cnpj: str,
    ref: date | None,
    column: str,
    table: str,
) -> dict | None:
    sql = text(f"""
        SELECT t.cnpj_fundo, t.data_referencia, t.{column}
        FROM {table} t
        WHERE t.cnpj_fundo = :cnpj
          AND t.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM {table} WHERE cnpj_fundo = :cnpj))
          AND t.versao = (
              SELECT MAX(versao) FROM {table} t2
              WHERE t2.cnpj_fundo = t.cnpj_fundo
                AND t2.data_referencia = t.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def _history(
    session: Session,
    cnpj: str,
    column: str,
    table: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    sql = text(f"""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM {table}
            WHERE cnpj_fundo = :cnpj
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT t.data_referencia, t.{column}
        FROM {table} t
        JOIN latest l ON t.cnpj_fundo = l.cnpj_fundo
            AND t.data_referencia = l.data_referencia AND t.versao = l.v
        WHERE t.cnpj_fundo = :cnpj
          AND t.data_referencia >= COALESCE(:start,
              (SELECT MAX(data_referencia) FROM {table} WHERE cnpj_fundo = :cnpj)
              - MAKE_INTERVAL(months => :months))
          AND t.data_referencia <= COALESCE(:end, CURRENT_DATE)
        ORDER BY t.data_referencia
    """)
    rows = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).all()
    return _to_list(rows)


def _rank(
    session: Session,
    column: str,
    table: str,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
    order: str = "DESC",
) -> list[dict]:
    alias = "m" if table == "fii_metrica_mensal" else "b"
    cte_name = "latest_t"
    sql = text(f"""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
            GROUP BY cnpj_fundo, data_referencia
        ),
        {cte_name} AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM {table}
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM {table}))
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao, {alias}.{column}
        FROM {table} {alias}
        JOIN {cte_name} lt ON {alias}.cnpj_fundo = lt.cnpj_fundo
            AND {alias}.data_referencia = lt.data_referencia AND {alias}.versao = lt.v
        JOIN fii_fundo_mensal g ON g.cnpj_fundo = {alias}.cnpj_fundo
            AND g.data_referencia = {alias}.data_referencia
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        WHERE {alias}.{column} IS NOT NULL
          AND (:segment IS NULL OR g.segmento_atuacao ILIKE :segment)
        ORDER BY {alias}.{column} {order}
        LIMIT :n
    """)
    rows = session.execute(sql, {"ref": ref, "segment": segment, "n": n}).all()
    return _to_list(rows)


def _segment_agg(
    session: Session,
    column: str,
    table: str,
    agg: str,
    segment: str | None,
    ref: date | None,
) -> list[dict]:
    alias = "m" if table == "fii_metrica_mensal" else "b"
    cte_name = "latest_t"
    sql = text(f"""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
            GROUP BY cnpj_fundo, data_referencia
        ),
        {cte_name} AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM {table}
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM {table}))
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.segmento_atuacao, {agg}({alias}.{column}) AS value,
               COUNT(DISTINCT g.cnpj_fundo) AS fund_count
        FROM {table} {alias}
        JOIN {cte_name} lt ON {alias}.cnpj_fundo = lt.cnpj_fundo
            AND {alias}.data_referencia = lt.data_referencia AND {alias}.versao = lt.v
        JOIN fii_fundo_mensal g ON g.cnpj_fundo = {alias}.cnpj_fundo
            AND g.data_referencia = {alias}.data_referencia
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        WHERE {alias}.{column} IS NOT NULL
          AND (:segment IS NULL OR g.segmento_atuacao ILIKE :segment)
        GROUP BY g.segmento_atuacao
        ORDER BY value DESC
    """)
    rows = session.execute(sql, {"ref": ref, "segment": segment}).all()
    return _to_list(rows)


def _compare_history(
    session: Session,
    cnpjs: list[str],
    column: str,
    table: str,
    months: int = 12,
) -> list[dict]:
    sql = text(f"""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM {table}
            WHERE cnpj_fundo = ANY(:cnpjs)
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT t.cnpj_fundo, t.data_referencia, t.{column}
        FROM {table} t
        JOIN latest l ON t.cnpj_fundo = l.cnpj_fundo
            AND t.data_referencia = l.data_referencia AND t.versao = l.v
        WHERE t.cnpj_fundo = ANY(:cnpjs)
          AND t.data_referencia >= (
              SELECT MAX(data_referencia) FROM {table} WHERE cnpj_fundo = ANY(:cnpjs))
              - MAKE_INTERVAL(months => :months)
        ORDER BY t.cnpj_fundo, t.data_referencia
    """)
    rows = session.execute(sql, {"cnpjs": cnpjs, "months": months}).all()
    return _to_list(rows)


def _alert_mom(
    session: Session,
    column: str,
    table: str,
    threshold: float,
    direction: str,
    segment: str | None = None,
) -> list[dict]:
    if direction == "drop":
        condition = f"curr.{column} < prev.{column} * (1 - :threshold)"
    else:
        condition = f"curr.{column} > prev.{column} * (1 + :threshold)"

    sql = text(f"""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM {table}
            GROUP BY cnpj_fundo, data_referencia
        ),
        ranked AS (
            SELECT t.cnpj_fundo, t.data_referencia, t.{column},
                   ROW_NUMBER() OVER (PARTITION BY t.cnpj_fundo ORDER BY t.data_referencia DESC) AS rn
            FROM {table} t
            JOIN latest l ON t.cnpj_fundo = l.cnpj_fundo
                AND t.data_referencia = l.data_referencia AND t.versao = l.v
            WHERE t.{column} IS NOT NULL
        ),
        latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = (SELECT MAX(data_referencia) FROM fii_fundo_mensal)
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT curr.cnpj_fundo, g.nome_fundo, g.segmento_atuacao,
               prev.{column} AS previous_value, curr.{column} AS current_value,
               curr.data_referencia AS current_date,
               prev.data_referencia AS previous_date
        FROM ranked curr
        JOIN ranked prev ON curr.cnpj_fundo = prev.cnpj_fundo AND prev.rn = 2
        JOIN fii_fundo_mensal g ON g.cnpj_fundo = curr.cnpj_fundo
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        WHERE curr.rn = 1
          AND prev.{column} != 0
          AND {condition}
          AND (:segment IS NULL OR g.segmento_atuacao ILIKE :segment)
        ORDER BY ABS(curr.{column} - prev.{column}) / ABS(prev.{column}) DESC
    """)
    rows = session.execute(sql, {"threshold": threshold, "segment": segment}).all()
    return _to_list(rows)


# ===========================================================================
# Category 1: Fund Identification & Basic Info (11 queries)
# ===========================================================================


def find_fund_by_name(session: Session, name: str) -> list[dict]:
    sql = text("""
        SELECT DISTINCT ON (g.cnpj_fundo)
            g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao, g.tipo_gestao
        FROM fii_fundo_mensal g
        WHERE g.nome_fundo ILIKE '%' || :name || '%'
          AND g.data_referencia = (SELECT MAX(data_referencia) FROM fii_fundo_mensal)
          AND g.versao = (SELECT MAX(versao) FROM fii_fundo_mensal g2
                          WHERE g2.cnpj_fundo = g.cnpj_fundo
                            AND g2.data_referencia = g.data_referencia)
        ORDER BY g.cnpj_fundo
    """)
    return _to_list(session.execute(sql, {"name": name}).all())


def get_fund_info(session: Session, cnpj: str) -> dict | None:
    sql = text("""
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao, g.tipo_gestao,
            g.publico_alvo, g.prazo_duracao, g.fundo_exclusivo, g.data_funcionamento,
            g.nome_administrador, g.cnpj_administrador, g.estado, g.cidade,
            g.mercado_negociacao_bolsa, g.codigo_isin, g.quantidade_cotas_emitidas
        FROM fii_fundo_mensal g
        WHERE g.cnpj_fundo = :cnpj
          AND g.data_referencia = (SELECT MAX(data_referencia) FROM fii_fundo_mensal
                                   WHERE cnpj_fundo = :cnpj)
          AND g.versao = (SELECT MAX(versao) FROM fii_fundo_mensal g2
                          WHERE g2.cnpj_fundo = :cnpj
                            AND g2.data_referencia = g.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj}).first()
    return _to_dict(row) if row else None


def list_funds_by_segment(
    session: Session, segment: str, ref: date | None = None
) -> list[dict]:
    sql = text(
        _LATEST_VERSAO_GERAL
        + """
        SELECT g.cnpj_fundo, g.nome_fundo, g.tipo_gestao, g.segmento_atuacao
        FROM fii_fundo_mensal g
        JOIN latest_g l ON g.cnpj_fundo = l.cnpj_fundo
            AND g.data_referencia = l.data_referencia AND g.versao = l.v
        WHERE g.segmento_atuacao ILIKE :segment
        ORDER BY g.nome_fundo
    """
    )
    return _to_list(session.execute(sql, {"ref": ref, "segment": segment}).all())


def list_funds_by_administrator(
    session: Session, admin_name: str, ref: date | None = None
) -> list[dict]:
    sql = text(
        _LATEST_VERSAO_GERAL
        + """
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao, g.nome_administrador
        FROM fii_fundo_mensal g
        JOIN latest_g l ON g.cnpj_fundo = l.cnpj_fundo
            AND g.data_referencia = l.data_referencia AND g.versao = l.v
        WHERE g.nome_administrador ILIKE '%' || :admin || '%'
        ORDER BY g.nome_fundo
    """
    )
    return _to_list(session.execute(sql, {"ref": ref, "admin": admin_name}).all())


def list_funds_by_state(
    session: Session, state: str, ref: date | None = None
) -> list[dict]:
    sql = text(
        _LATEST_VERSAO_GERAL
        + """
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao, g.estado, g.cidade
        FROM fii_fundo_mensal g
        JOIN latest_g l ON g.cnpj_fundo = l.cnpj_fundo
            AND g.data_referencia = l.data_referencia AND g.versao = l.v
        WHERE g.estado = UPPER(:state)
        ORDER BY g.nome_fundo
    """
    )
    return _to_list(session.execute(sql, {"ref": ref, "state": state}).all())


def list_all_segments(session: Session, ref: date | None = None) -> list[dict]:
    sql = text(
        _LATEST_VERSAO_GERAL
        + """
        SELECT g.segmento_atuacao, COUNT(DISTINCT g.cnpj_fundo) AS num_funds
        FROM fii_fundo_mensal g
        JOIN latest_g l ON g.cnpj_fundo = l.cnpj_fundo
            AND g.data_referencia = l.data_referencia AND g.versao = l.v
        WHERE g.segmento_atuacao IS NOT NULL
        GROUP BY g.segmento_atuacao
        ORDER BY num_funds DESC
    """
    )
    return _to_list(session.execute(sql, {"ref": ref}).all())


def list_all_administrators(session: Session, ref: date | None = None) -> list[dict]:
    sql = text(
        _LATEST_VERSAO_GERAL
        + """
        SELECT g.nome_administrador, g.cnpj_administrador,
               COUNT(DISTINCT g.cnpj_fundo) AS num_funds
        FROM fii_fundo_mensal g
        JOIN latest_g l ON g.cnpj_fundo = l.cnpj_fundo
            AND g.data_referencia = l.data_referencia AND g.versao = l.v
        WHERE g.nome_administrador IS NOT NULL
        GROUP BY g.nome_administrador, g.cnpj_administrador
        ORDER BY num_funds DESC
    """
    )
    return _to_list(session.execute(sql, {"ref": ref}).all())


def count_total_funds(session: Session, ref: date | None = None) -> int:
    sql = text("""
        SELECT COUNT(DISTINCT cnpj_fundo) AS total
        FROM fii_fundo_mensal
        WHERE data_referencia = COALESCE(:ref,
            (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
    """)
    row = session.execute(sql, {"ref": ref}).first()
    return row.total if row else 0


def count_funds_by_segment(session: Session, ref: date | None = None) -> list[dict]:
    sql = text(
        _LATEST_VERSAO_GERAL
        + """
        SELECT g.segmento_atuacao, COUNT(DISTINCT g.cnpj_fundo) AS num_funds
        FROM fii_fundo_mensal g
        JOIN latest_g l ON g.cnpj_fundo = l.cnpj_fundo
            AND g.data_referencia = l.data_referencia AND g.versao = l.v
        GROUP BY g.segmento_atuacao
        ORDER BY num_funds DESC
    """
    )
    return _to_list(session.execute(sql, {"ref": ref}).all())


def get_fund_age(session: Session, cnpj: str) -> dict | None:
    sql = text("""
        SELECT g.cnpj_fundo, g.nome_fundo, g.data_funcionamento,
               EXTRACT(YEAR FROM AGE(CURRENT_DATE, g.data_funcionamento)) AS age_years
        FROM fii_fundo_mensal g
        WHERE g.cnpj_fundo = :cnpj
          AND g.data_referencia = (SELECT MAX(data_referencia) FROM fii_fundo_mensal
                                   WHERE cnpj_fundo = :cnpj)
          AND g.versao = (SELECT MAX(versao) FROM fii_fundo_mensal g2
                          WHERE g2.cnpj_fundo = :cnpj
                            AND g2.data_referencia = g.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj}).first()
    return _to_dict(row) if row else None


def get_available_months(session: Session, cnpj: str) -> list[date]:
    sql = text("""
        SELECT DISTINCT data_referencia
        FROM fii_fundo_mensal
        WHERE cnpj_fundo = :cnpj
        ORDER BY data_referencia
    """)
    rows = session.execute(sql, {"cnpj": cnpj}).all()
    return [r.data_referencia for r in rows]


# ===========================================================================
# Category 2: Factual Lookups — single fund, single metric (25 queries)
# ===========================================================================

# --- from fii_metrica_mensal ---


def get_patrimonio_liquido(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(session, cnpj, ref, "patrimonio_liquido", "fii_metrica_mensal")


def get_valor_ativo(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(session, cnpj, ref, "valor_ativo", "fii_metrica_mensal")


def get_valor_patrimonial_cotas(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session, cnpj, ref, "valor_patrimonial_cotas", "fii_metrica_mensal"
    )


def get_dividend_yield(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session, cnpj, ref, "percentual_dividend_yield_mes", "fii_metrica_mensal"
    )


def get_rentabilidade_efetiva(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session, cnpj, ref, "percentual_rentabilidade_efetiva_mes", "fii_metrica_mensal"
    )


def get_rentabilidade_patrimonial(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session,
        cnpj,
        ref,
        "percentual_rentabilidade_patrimonial_mes",
        "fii_metrica_mensal",
    )


def get_total_cotistas(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session, cnpj, ref, "total_numero_cotistas", "fii_metrica_mensal"
    )


def get_cotistas_pf(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session, cnpj, ref, "numero_cotistas_pessoa_fisica", "fii_metrica_mensal"
    )


def get_cotistas_pj(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session,
        cnpj,
        ref,
        "numero_cotistas_pessoa_juridica_nao_financeira",
        "fii_metrica_mensal",
    )


def get_cotas_emitidas(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(session, cnpj, ref, "cotas_emitidas", "fii_metrica_mensal")


def get_taxa_administracao(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session,
        cnpj,
        ref,
        "percentual_despesas_taxa_administracao",
        "fii_metrica_mensal",
    )


def get_taxa_custodiante(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session,
        cnpj,
        ref,
        "percentual_despesas_agente_custodiante",
        "fii_metrica_mensal",
    )


def get_amortizacao(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session, cnpj, ref, "percentual_amortizacao_cotas_mes", "fii_metrica_mensal"
    )


# --- from fii_balanco_mensal ---


def get_total_investido(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(session, cnpj, ref, "total_investido", "fii_balanco_mensal")


def get_imoveis_renda(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session, cnpj, ref, "imoveis_renda_acabados", "fii_balanco_mensal"
    )


def get_cri_cra(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(session, cnpj, ref, "cri_cra", "fii_balanco_mensal")


def get_fii_holdings(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(session, cnpj, ref, "fii", "fii_balanco_mensal")


def get_total_passivo(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(session, cnpj, ref, "total_passivo", "fii_balanco_mensal")


def get_disponibilidades(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(session, cnpj, ref, "disponibilidades", "fii_balanco_mensal")


def get_rendimentos_distribuir(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session, cnpj, ref, "rendimentos_distribuir", "fii_balanco_mensal"
    )


def get_valores_receber(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(session, cnpj, ref, "valores_receber", "fii_balanco_mensal")


def get_contas_aluguel(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session, cnpj, ref, "contas_receber_aluguel", "fii_balanco_mensal"
    )


def get_liquidez(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session, cnpj, ref, "total_necessidades_liquidez", "fii_balanco_mensal"
    )


def get_obrigacoes_securitizacao(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session, cnpj, ref, "obrigacoes_securitizacao_recebiveis", "fii_balanco_mensal"
    )


def get_provisoes(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    return _single_metric(
        session, cnpj, ref, "provisoes_contigencias", "fii_balanco_mensal"
    )


# ===========================================================================
# Category 3: Historical / Time Series (20 queries)
# ===========================================================================

# --- from fii_metrica_mensal ---


def history_patrimonio_liquido(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "patrimonio_liquido", "fii_metrica_mensal",
        months, start_date, end_date,
    )


def history_valor_ativo(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "valor_ativo", "fii_metrica_mensal",
        months, start_date, end_date,
    )


def history_valor_patrimonial(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "valor_patrimonial_cotas", "fii_metrica_mensal",
        months, start_date, end_date,
    )


def history_dividend_yield(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "percentual_dividend_yield_mes", "fii_metrica_mensal",
        months, start_date, end_date,
    )


def history_rentabilidade_efetiva(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "percentual_rentabilidade_efetiva_mes", "fii_metrica_mensal",
        months, start_date, end_date,
    )


def history_rentabilidade_patrimonial(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "percentual_rentabilidade_patrimonial_mes", "fii_metrica_mensal",
        months, start_date, end_date,
    )


def history_cotistas(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "total_numero_cotistas", "fii_metrica_mensal",
        months, start_date, end_date,
    )


def history_cotistas_pf(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "numero_cotistas_pessoa_fisica", "fii_metrica_mensal",
        months, start_date, end_date,
    )


def history_cotas_emitidas(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "cotas_emitidas", "fii_metrica_mensal",
        months, start_date, end_date,
    )


def history_taxa_administracao(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "percentual_despesas_taxa_administracao", "fii_metrica_mensal",
        months, start_date, end_date,
    )


# --- from fii_balanco_mensal ---


def history_total_investido(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "total_investido", "fii_balanco_mensal",
        months, start_date, end_date,
    )


def history_imoveis_renda(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "imoveis_renda_acabados", "fii_balanco_mensal",
        months, start_date, end_date,
    )


def history_cri_cra(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "cri_cra", "fii_balanco_mensal",
        months, start_date, end_date,
    )


def history_fii_holdings(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "fii", "fii_balanco_mensal",
        months, start_date, end_date,
    )


def history_total_passivo(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "total_passivo", "fii_balanco_mensal",
        months, start_date, end_date,
    )


def history_disponibilidades(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "disponibilidades", "fii_balanco_mensal",
        months, start_date, end_date,
    )


def history_rendimentos_distribuir(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "rendimentos_distribuir", "fii_balanco_mensal",
        months, start_date, end_date,
    )


def history_contas_aluguel(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "contas_receber_aluguel", "fii_balanco_mensal",
        months, start_date, end_date,
    )


def history_amortizacao(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "percentual_amortizacao_cotas_mes", "fii_metrica_mensal",
        months, start_date, end_date,
    )


def history_liquidez(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    return _history(
        session, cnpj, "total_necessidades_liquidez", "fii_balanco_mensal",
        months, start_date, end_date,
    )


# ===========================================================================
# Category 4: Rankings / Top-N (18 queries)
# ===========================================================================

# --- from fii_metrica_mensal ---


def rank_by_dividend_yield(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "percentual_dividend_yield_mes", "fii_metrica_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_patrimonio_liquido(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "patrimonio_liquido", "fii_metrica_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_valor_ativo(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "valor_ativo", "fii_metrica_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_cotistas(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "total_numero_cotistas", "fii_metrica_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_cotistas_pf(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "numero_cotistas_pessoa_fisica", "fii_metrica_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_vpa(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "valor_patrimonial_cotas", "fii_metrica_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_rentabilidade(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "percentual_rentabilidade_efetiva_mes", "fii_metrica_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_cotas_emitidas(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "cotas_emitidas", "fii_metrica_mensal",
        n, segment, ref, "DESC",
    )


# --- from fii_balanco_mensal ---


def rank_by_total_investido(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "total_investido", "fii_balanco_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_imoveis(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "imoveis_renda_acabados", "fii_balanco_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_cri_cra(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "cri_cra", "fii_balanco_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_fii_holdings(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "fii", "fii_balanco_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_total_passivo(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "total_passivo", "fii_balanco_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_disponibilidades(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "disponibilidades", "fii_balanco_mensal",
        n, segment, ref, "DESC",
    )


# --- special sort orders ---


def rank_by_lowest_admin_fee(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "percentual_despesas_taxa_administracao", "fii_metrica_mensal",
        n, segment, ref, "ASC",
    )


def rank_by_contas_aluguel(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "contas_receber_aluguel", "fii_balanco_mensal",
        n, segment, ref, "DESC",
    )


def rank_by_rendimentos_distribuir(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "rendimentos_distribuir", "fii_balanco_mensal",
        n, segment, ref, "DESC",
    )


def rank_smallest_funds(
    session: Session,
    n: int = 10,
    segment: str | None = None,
    ref: date | None = None,
) -> list[dict]:
    return _rank(
        session, "patrimonio_liquido", "fii_metrica_mensal",
        n, segment, ref, "ASC",
    )


# ===========================================================================
# Category 5: Comparisons (7 queries)
# ===========================================================================


_METRICA_COLUMNS = {
    "patrimonio_liquido", "valor_ativo", "valor_patrimonial_cotas",
    "percentual_dividend_yield_mes", "percentual_rentabilidade_efetiva_mes",
    "percentual_rentabilidade_patrimonial_mes", "total_numero_cotistas",
    "numero_cotistas_pessoa_fisica", "cotas_emitidas",
    "percentual_despesas_taxa_administracao",
    "percentual_despesas_agente_custodiante",
    "percentual_amortizacao_cotas_mes",
}


def compare_funds_single_metric(
    session: Session,
    cnpjs: list[str],
    metric: str,
    ref: date | None = None,
) -> list[dict]:
    table = "fii_metrica_mensal" if metric in _METRICA_COLUMNS else "fii_balanco_mensal"
    alias = "m" if table == "fii_metrica_mensal" else "b"
    sql = text(f"""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
              AND cnpj_fundo = ANY(:cnpjs)
            GROUP BY cnpj_fundo, data_referencia
        ),
        latest_t AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM {table}
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM {table}))
              AND cnpj_fundo = ANY(:cnpjs)
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao, {alias}.{metric}
        FROM {table} {alias}
        JOIN latest_t lt ON {alias}.cnpj_fundo = lt.cnpj_fundo
            AND {alias}.data_referencia = lt.data_referencia AND {alias}.versao = lt.v
        JOIN fii_fundo_mensal g ON g.cnpj_fundo = {alias}.cnpj_fundo
            AND g.data_referencia = {alias}.data_referencia
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        ORDER BY g.cnpj_fundo
    """)
    return _to_list(session.execute(sql, {"cnpjs": cnpjs, "ref": ref}).all())


def compare_funds_full(
    session: Session, cnpjs: list[str], ref: date | None = None
) -> list[dict]:
    sql = text("""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
              AND cnpj_fundo = ANY(:cnpjs)
            GROUP BY cnpj_fundo, data_referencia
        ),
        latest_m AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_metrica_mensal))
              AND cnpj_fundo = ANY(:cnpjs)
            GROUP BY cnpj_fundo, data_referencia
        ),
        latest_b AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_balanco_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_balanco_mensal))
              AND cnpj_fundo = ANY(:cnpjs)
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao,
               m.patrimonio_liquido, m.valor_patrimonial_cotas,
               m.percentual_dividend_yield_mes, m.total_numero_cotistas,
               m.percentual_rentabilidade_efetiva_mes,
               m.percentual_despesas_taxa_administracao,
               b.total_investido, b.total_passivo
        FROM fii_fundo_mensal g
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        LEFT JOIN fii_metrica_mensal m ON m.cnpj_fundo = g.cnpj_fundo
            AND m.data_referencia = g.data_referencia
        LEFT JOIN latest_m lm ON m.cnpj_fundo = lm.cnpj_fundo
            AND m.data_referencia = lm.data_referencia AND m.versao = lm.v
        LEFT JOIN fii_balanco_mensal b ON b.cnpj_fundo = g.cnpj_fundo
            AND b.data_referencia = g.data_referencia
        LEFT JOIN latest_b lb ON b.cnpj_fundo = lb.cnpj_fundo
            AND b.data_referencia = lb.data_referencia AND b.versao = lb.v
        WHERE lm.cnpj_fundo IS NOT NULL
        ORDER BY g.cnpj_fundo
    """)
    return _to_list(session.execute(sql, {"cnpjs": cnpjs, "ref": ref}).all())


def compare_funds_dy_history(
    session: Session, cnpjs: list[str], months: int = 12
) -> list[dict]:
    return _compare_history(
        session, cnpjs, "percentual_dividend_yield_mes", "fii_metrica_mensal", months
    )


def compare_funds_pl_history(
    session: Session, cnpjs: list[str], months: int = 12
) -> list[dict]:
    return _compare_history(
        session, cnpjs, "patrimonio_liquido", "fii_metrica_mensal", months
    )


def compare_funds_cotistas_history(
    session: Session, cnpjs: list[str], months: int = 12
) -> list[dict]:
    return _compare_history(
        session, cnpjs, "total_numero_cotistas", "fii_metrica_mensal", months
    )


def compare_funds_balance_sheet(
    session: Session, cnpjs: list[str], ref: date | None = None
) -> list[dict]:
    sql = text("""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
              AND cnpj_fundo = ANY(:cnpjs)
            GROUP BY cnpj_fundo, data_referencia
        ),
        latest_b AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_balanco_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_balanco_mensal))
              AND cnpj_fundo = ANY(:cnpjs)
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.cnpj_fundo, g.nome_fundo,
               b.total_investido, b.imoveis_renda_acabados, b.cri_cra,
               b.fii, b.disponibilidades, b.total_passivo,
               b.total_necessidades_liquidez
        FROM fii_fundo_mensal g
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        JOIN fii_balanco_mensal b ON b.cnpj_fundo = g.cnpj_fundo
            AND b.data_referencia = g.data_referencia
        JOIN latest_b lb ON b.cnpj_fundo = lb.cnpj_fundo
            AND b.data_referencia = lb.data_referencia AND b.versao = lb.v
        ORDER BY g.cnpj_fundo
    """)
    return _to_list(session.execute(sql, {"cnpjs": cnpjs, "ref": ref}).all())


def compare_funds_fees(
    session: Session, cnpjs: list[str], ref: date | None = None
) -> list[dict]:
    sql = text("""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
              AND cnpj_fundo = ANY(:cnpjs)
            GROUP BY cnpj_fundo, data_referencia
        ),
        latest_m AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_metrica_mensal))
              AND cnpj_fundo = ANY(:cnpjs)
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.cnpj_fundo, g.nome_fundo,
               m.percentual_despesas_taxa_administracao,
               m.percentual_despesas_agente_custodiante
        FROM fii_fundo_mensal g
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        JOIN fii_metrica_mensal m ON m.cnpj_fundo = g.cnpj_fundo
            AND m.data_referencia = g.data_referencia
        JOIN latest_m lm ON m.cnpj_fundo = lm.cnpj_fundo
            AND m.data_referencia = lm.data_referencia AND m.versao = lm.v
        ORDER BY g.cnpj_fundo
    """)
    return _to_list(session.execute(sql, {"cnpjs": cnpjs, "ref": ref}).all())


# ===========================================================================
# Category 6: Aggregations (14 queries)
# ===========================================================================


def accumulated_dy(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        )
        SELECT SUM(m.percentual_dividend_yield_mes) AS accumulated_dy,
               COUNT(*) AS num_months,
               MIN(m.data_referencia) AS start_date,
               MAX(m.data_referencia) AS end_date
        FROM fii_metrica_mensal m
        JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
            AND m.data_referencia = l.data_referencia AND m.versao = l.v
        WHERE m.cnpj_fundo = :cnpj
          AND m.data_referencia >= COALESCE(:start,
              (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
              - MAKE_INTERVAL(months => :months))
          AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def average_dy(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        )
        SELECT AVG(m.percentual_dividend_yield_mes) AS average_dy,
               COUNT(*) AS num_months
        FROM fii_metrica_mensal m
        JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
            AND m.data_referencia = l.data_referencia AND m.versao = l.v
        WHERE m.cnpj_fundo = :cnpj
          AND m.data_referencia >= COALESCE(:start,
              (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
              - MAKE_INTERVAL(months => :months))
          AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def annualized_dy(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        )
        SELECT AVG(m.percentual_dividend_yield_mes) * 12 AS annualized_dy,
               COUNT(*) AS num_months
        FROM fii_metrica_mensal m
        JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
            AND m.data_referencia = l.data_referencia AND m.versao = l.v
        WHERE m.cnpj_fundo = :cnpj
          AND m.data_referencia >= COALESCE(:start,
              (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
              - MAKE_INTERVAL(months => :months))
          AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def dy_last_12_months(session: Session, cnpj: str) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        )
        SELECT SUM(m.percentual_dividend_yield_mes) AS dy_12m,
               COUNT(*) AS num_months
        FROM fii_metrica_mensal m
        JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
            AND m.data_referencia = l.data_referencia AND m.versao = l.v
        WHERE m.cnpj_fundo = :cnpj
          AND m.data_referencia > (
              SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
              - INTERVAL '12 months'
    """)
    row = session.execute(sql, {"cnpj": cnpj}).first()
    return _to_dict(row) if row else None


def average_rentabilidade(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        )
        SELECT AVG(m.percentual_rentabilidade_efetiva_mes) AS average_rentabilidade,
               COUNT(*) AS num_months
        FROM fii_metrica_mensal m
        JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
            AND m.data_referencia = l.data_referencia AND m.versao = l.v
        WHERE m.cnpj_fundo = :cnpj
          AND m.data_referencia >= COALESCE(:start,
              (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
              - MAKE_INTERVAL(months => :months))
          AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def pl_variation(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        ),
        ordered AS (
            SELECT m.data_referencia, m.patrimonio_liquido,
                   ROW_NUMBER() OVER (ORDER BY m.data_referencia ASC) AS rn_asc,
                   ROW_NUMBER() OVER (ORDER BY m.data_referencia DESC) AS rn_desc
            FROM fii_metrica_mensal m
            JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
                AND m.data_referencia = l.data_referencia AND m.versao = l.v
            WHERE m.cnpj_fundo = :cnpj
              AND m.data_referencia >= COALESCE(:start,
                  (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
                  - MAKE_INTERVAL(months => :months))
              AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
        )
        SELECT
            s.data_referencia AS start_date, s.patrimonio_liquido AS start_pl,
            e.data_referencia AS end_date, e.patrimonio_liquido AS end_pl,
            e.patrimonio_liquido - s.patrimonio_liquido AS absolute_change,
            CASE WHEN s.patrimonio_liquido != 0
                THEN (e.patrimonio_liquido - s.patrimonio_liquido) / s.patrimonio_liquido
                ELSE NULL END AS pct_change
        FROM ordered s, ordered e
        WHERE s.rn_asc = 1 AND e.rn_desc = 1
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def cotistas_variation(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        ),
        ordered AS (
            SELECT m.data_referencia, m.total_numero_cotistas,
                   ROW_NUMBER() OVER (ORDER BY m.data_referencia ASC) AS rn_asc,
                   ROW_NUMBER() OVER (ORDER BY m.data_referencia DESC) AS rn_desc
            FROM fii_metrica_mensal m
            JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
                AND m.data_referencia = l.data_referencia AND m.versao = l.v
            WHERE m.cnpj_fundo = :cnpj
              AND m.data_referencia >= COALESCE(:start,
                  (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
                  - MAKE_INTERVAL(months => :months))
              AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
        )
        SELECT
            s.data_referencia AS start_date, s.total_numero_cotistas AS start_cotistas,
            e.data_referencia AS end_date, e.total_numero_cotistas AS end_cotistas,
            e.total_numero_cotistas - s.total_numero_cotistas AS absolute_change,
            CASE WHEN s.total_numero_cotistas != 0
                THEN (e.total_numero_cotistas - s.total_numero_cotistas)::numeric
                     / s.total_numero_cotistas
                ELSE NULL END AS pct_change
        FROM ordered s, ordered e
        WHERE s.rn_asc = 1 AND e.rn_desc = 1
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def vpa_variation(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        ),
        ordered AS (
            SELECT m.data_referencia, m.valor_patrimonial_cotas,
                   ROW_NUMBER() OVER (ORDER BY m.data_referencia ASC) AS rn_asc,
                   ROW_NUMBER() OVER (ORDER BY m.data_referencia DESC) AS rn_desc
            FROM fii_metrica_mensal m
            JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
                AND m.data_referencia = l.data_referencia AND m.versao = l.v
            WHERE m.cnpj_fundo = :cnpj
              AND m.data_referencia >= COALESCE(:start,
                  (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
                  - MAKE_INTERVAL(months => :months))
              AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
        )
        SELECT
            s.data_referencia AS start_date, s.valor_patrimonial_cotas AS start_vpa,
            e.data_referencia AS end_date, e.valor_patrimonial_cotas AS end_vpa,
            e.valor_patrimonial_cotas - s.valor_patrimonial_cotas AS absolute_change,
            CASE WHEN s.valor_patrimonial_cotas != 0
                THEN (e.valor_patrimonial_cotas - s.valor_patrimonial_cotas)
                     / s.valor_patrimonial_cotas
                ELSE NULL END AS pct_change
        FROM ordered s, ordered e
        WHERE s.rn_asc = 1 AND e.rn_desc = 1
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def dividend_per_cota_estimate(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        )
        SELECT SUM(m.percentual_dividend_yield_mes * m.valor_patrimonial_cotas)
                   AS total_dividend_per_cota,
               COUNT(*) AS num_months
        FROM fii_metrica_mensal m
        JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
            AND m.data_referencia = l.data_referencia AND m.versao = l.v
        WHERE m.cnpj_fundo = :cnpj
          AND m.percentual_dividend_yield_mes IS NOT NULL
          AND m.valor_patrimonial_cotas IS NOT NULL
          AND m.data_referencia >= COALESCE(:start,
              (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
              - MAKE_INTERVAL(months => :months))
          AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def max_dy_period(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        )
        SELECT m.data_referencia, m.percentual_dividend_yield_mes
        FROM fii_metrica_mensal m
        JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
            AND m.data_referencia = l.data_referencia AND m.versao = l.v
        WHERE m.cnpj_fundo = :cnpj
          AND m.percentual_dividend_yield_mes IS NOT NULL
          AND m.data_referencia >= COALESCE(:start,
              (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
              - MAKE_INTERVAL(months => :months))
          AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
        ORDER BY m.percentual_dividend_yield_mes DESC
        LIMIT 1
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def min_dy_period(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        )
        SELECT m.data_referencia, m.percentual_dividend_yield_mes
        FROM fii_metrica_mensal m
        JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
            AND m.data_referencia = l.data_referencia AND m.versao = l.v
        WHERE m.cnpj_fundo = :cnpj
          AND m.percentual_dividend_yield_mes IS NOT NULL
          AND m.data_referencia >= COALESCE(:start,
              (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
              - MAKE_INTERVAL(months => :months))
          AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
        ORDER BY m.percentual_dividend_yield_mes ASC
        LIMIT 1
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def average_pl_period(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        )
        SELECT AVG(m.patrimonio_liquido) AS average_pl, COUNT(*) AS num_months
        FROM fii_metrica_mensal m
        JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
            AND m.data_referencia = l.data_referencia AND m.versao = l.v
        WHERE m.cnpj_fundo = :cnpj
          AND m.data_referencia >= COALESCE(:start,
              (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
              - MAKE_INTERVAL(months => :months))
          AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def cotas_emitidas_change(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        ),
        ordered AS (
            SELECT m.data_referencia, m.cotas_emitidas,
                   ROW_NUMBER() OVER (ORDER BY m.data_referencia ASC) AS rn_asc,
                   ROW_NUMBER() OVER (ORDER BY m.data_referencia DESC) AS rn_desc
            FROM fii_metrica_mensal m
            JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
                AND m.data_referencia = l.data_referencia AND m.versao = l.v
            WHERE m.cnpj_fundo = :cnpj
              AND m.data_referencia >= COALESCE(:start,
                  (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
                  - MAKE_INTERVAL(months => :months))
              AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
        )
        SELECT
            s.data_referencia AS start_date, s.cotas_emitidas AS start_cotas,
            e.data_referencia AS end_date, e.cotas_emitidas AS end_cotas,
            e.cotas_emitidas - s.cotas_emitidas AS absolute_change,
            CASE WHEN s.cotas_emitidas != 0
                THEN (e.cotas_emitidas - s.cotas_emitidas) / s.cotas_emitidas
                ELSE NULL END AS pct_change
        FROM ordered s, ordered e
        WHERE s.rn_asc = 1 AND e.rn_desc = 1
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def total_return_estimate(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        )
        SELECT SUM(m.percentual_rentabilidade_efetiva_mes) AS total_return,
               COUNT(*) AS num_months
        FROM fii_metrica_mensal m
        JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
            AND m.data_referencia = l.data_referencia AND m.versao = l.v
        WHERE m.cnpj_fundo = :cnpj
          AND m.data_referencia >= COALESCE(:start,
              (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
              - MAKE_INTERVAL(months => :months))
          AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


# ===========================================================================
# Category 7: Segment Analysis (10 queries)
# ===========================================================================


def segment_average_dy(
    session: Session, segment: str | None = None, ref: date | None = None
) -> list[dict]:
    return _segment_agg(
        session, "percentual_dividend_yield_mes", "fii_metrica_mensal",
        "AVG", segment, ref,
    )


def segment_average_pl(
    session: Session, segment: str | None = None, ref: date | None = None
) -> list[dict]:
    return _segment_agg(
        session, "patrimonio_liquido", "fii_metrica_mensal",
        "AVG", segment, ref,
    )


def segment_total_pl(
    session: Session, segment: str | None = None, ref: date | None = None
) -> list[dict]:
    return _segment_agg(
        session, "patrimonio_liquido", "fii_metrica_mensal",
        "SUM", segment, ref,
    )


def segment_fund_count(
    session: Session, segment: str | None = None, ref: date | None = None
) -> list[dict]:
    sql = text("""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.segmento_atuacao, COUNT(DISTINCT g.cnpj_fundo) AS fund_count
        FROM fii_fundo_mensal g
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        WHERE (:segment IS NULL OR g.segmento_atuacao ILIKE :segment)
        GROUP BY g.segmento_atuacao
        ORDER BY fund_count DESC
    """)
    return _to_list(session.execute(sql, {"ref": ref, "segment": segment}).all())


def segment_average_cotistas(
    session: Session, segment: str | None = None, ref: date | None = None
) -> list[dict]:
    return _segment_agg(
        session, "total_numero_cotistas", "fii_metrica_mensal",
        "AVG", segment, ref,
    )


def segment_average_vpa(
    session: Session, segment: str | None = None, ref: date | None = None
) -> list[dict]:
    return _segment_agg(
        session, "valor_patrimonial_cotas", "fii_metrica_mensal",
        "AVG", segment, ref,
    )


def segment_average_rentabilidade(
    session: Session, segment: str | None = None, ref: date | None = None
) -> list[dict]:
    return _segment_agg(
        session, "percentual_rentabilidade_efetiva_mes", "fii_metrica_mensal",
        "AVG", segment, ref,
    )


def segment_average_fee(
    session: Session, segment: str | None = None, ref: date | None = None
) -> list[dict]:
    return _segment_agg(
        session, "percentual_despesas_taxa_administracao", "fii_metrica_mensal",
        "AVG", segment, ref,
    )


def segment_total_investido(
    session: Session, segment: str | None = None, ref: date | None = None
) -> list[dict]:
    return _segment_agg(
        session, "total_investido", "fii_balanco_mensal",
        "SUM", segment, ref,
    )


def segment_comparison(
    session: Session, segments: list[str], ref: date | None = None
) -> list[dict]:
    sql = text("""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
            GROUP BY cnpj_fundo, data_referencia
        ),
        latest_m AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_metrica_mensal))
            GROUP BY cnpj_fundo, data_referencia
        ),
        latest_b AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_balanco_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_balanco_mensal))
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.segmento_atuacao,
               COUNT(DISTINCT g.cnpj_fundo) AS fund_count,
               AVG(m.percentual_dividend_yield_mes) AS avg_dy,
               AVG(m.patrimonio_liquido) AS avg_pl,
               SUM(m.patrimonio_liquido) AS total_pl,
               AVG(m.valor_patrimonial_cotas) AS avg_vpa,
               AVG(m.total_numero_cotistas) AS avg_cotistas,
               AVG(m.percentual_rentabilidade_efetiva_mes) AS avg_rentabilidade,
               AVG(m.percentual_despesas_taxa_administracao) AS avg_taxa_adm,
               SUM(b.total_investido) AS total_investido
        FROM fii_fundo_mensal g
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        LEFT JOIN fii_metrica_mensal m ON m.cnpj_fundo = g.cnpj_fundo
            AND m.data_referencia = g.data_referencia
        LEFT JOIN latest_m lm ON m.cnpj_fundo = lm.cnpj_fundo
            AND m.data_referencia = lm.data_referencia AND m.versao = lm.v
        LEFT JOIN fii_balanco_mensal b ON b.cnpj_fundo = g.cnpj_fundo
            AND b.data_referencia = g.data_referencia
        LEFT JOIN latest_b lb ON b.cnpj_fundo = lb.cnpj_fundo
            AND b.data_referencia = lb.data_referencia AND b.versao = lb.v
        WHERE g.segmento_atuacao = ANY(:segments) AND lm.cnpj_fundo IS NOT NULL
        GROUP BY g.segmento_atuacao
        ORDER BY total_pl DESC
    """)
    return _to_list(session.execute(sql, {"ref": ref, "segments": segments}).all())


# ===========================================================================
# Category 8: Cross-Table Queries (12 queries)
# ===========================================================================


def fund_complete_profile(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        WITH latest_g AS (
            SELECT MAX(versao) AS v, data_referencia
            FROM fii_fundo_mensal
            WHERE cnpj_fundo = :cnpj
              AND data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal WHERE cnpj_fundo = :cnpj))
            GROUP BY data_referencia
        ),
        latest_m AS (
            SELECT MAX(versao) AS v, data_referencia
            FROM fii_metrica_mensal
            WHERE cnpj_fundo = :cnpj
              AND data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj))
            GROUP BY data_referencia
        ),
        latest_b AS (
            SELECT MAX(versao) AS v, data_referencia
            FROM fii_balanco_mensal
            WHERE cnpj_fundo = :cnpj
              AND data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
            GROUP BY data_referencia
        )
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao, g.tipo_gestao,
               g.publico_alvo, g.prazo_duracao, g.fundo_exclusivo,
               g.data_funcionamento, g.nome_administrador, g.estado, g.cidade,
               g.mercado_negociacao_bolsa, g.codigo_isin,
               m.patrimonio_liquido, m.valor_ativo, m.valor_patrimonial_cotas,
               m.percentual_dividend_yield_mes, m.total_numero_cotistas,
               m.percentual_rentabilidade_efetiva_mes,
               m.percentual_despesas_taxa_administracao,
               m.cotas_emitidas,
               b.total_investido, b.imoveis_renda_acabados, b.cri_cra, b.fii,
               b.disponibilidades, b.total_passivo, b.total_necessidades_liquidez
        FROM fii_fundo_mensal g
        JOIN latest_g lg ON g.data_referencia = lg.data_referencia AND g.versao = lg.v
        LEFT JOIN fii_metrica_mensal m ON m.cnpj_fundo = g.cnpj_fundo
            AND m.data_referencia = g.data_referencia
        LEFT JOIN latest_m lm ON m.data_referencia = lm.data_referencia AND m.versao = lm.v
        LEFT JOIN fii_balanco_mensal b ON b.cnpj_fundo = g.cnpj_fundo
            AND b.data_referencia = g.data_referencia
        LEFT JOIN latest_b lb ON b.data_referencia = lb.data_referencia AND b.versao = lb.v
        WHERE g.cnpj_fundo = :cnpj
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def fund_asset_composition(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT b.cnpj_fundo, b.data_referencia, b.total_investido,
               b.imoveis_renda_acabados, b.imoveis_renda_construcao,
               b.imoveis_venda_acabados, b.terrenos, b.direitos_bens_imoveis,
               b.cri_cra, b.lci_lca, b.fii, b.acoes,
               b.acoes_sociedades_atividades_fii, b.fip, b.fdic,
               b.disponibilidades, b.titulos_publicos, b.titulos_privados,
               b.fundos_renda_fixa, b.total_necessidades_liquidez
        FROM fii_balanco_mensal b
        WHERE b.cnpj_fundo = :cnpj
          AND b.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
          AND b.versao = (SELECT MAX(versao) FROM fii_balanco_mensal b2
                          WHERE b2.cnpj_fundo = :cnpj AND b2.data_referencia = b.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def fund_asset_composition_pct(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT b.cnpj_fundo, b.data_referencia, b.total_investido,
               CASE WHEN b.total_investido != 0
                   THEN b.imoveis_renda_acabados / b.total_investido ELSE NULL END AS pct_imoveis_renda,
               CASE WHEN b.total_investido != 0
                   THEN b.cri_cra / b.total_investido ELSE NULL END AS pct_cri_cra,
               CASE WHEN b.total_investido != 0
                   THEN b.fii / b.total_investido ELSE NULL END AS pct_fii,
               CASE WHEN b.total_investido != 0
                   THEN b.acoes / b.total_investido ELSE NULL END AS pct_acoes,
               CASE WHEN b.total_investido != 0
                   THEN b.lci_lca / b.total_investido ELSE NULL END AS pct_lci_lca,
               CASE WHEN b.total_investido != 0
                   THEN b.disponibilidades / b.total_investido ELSE NULL END AS pct_disponibilidades,
               CASE WHEN b.total_investido != 0
                   THEN b.fundos_renda_fixa / b.total_investido ELSE NULL END AS pct_renda_fixa,
               CASE WHEN b.total_investido != 0
                   THEN b.terrenos / b.total_investido ELSE NULL END AS pct_terrenos
        FROM fii_balanco_mensal b
        WHERE b.cnpj_fundo = :cnpj
          AND b.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
          AND b.versao = (SELECT MAX(versao) FROM fii_balanco_mensal b2
                          WHERE b2.cnpj_fundo = :cnpj AND b2.data_referencia = b.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def fund_liquidity_analysis(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT b.cnpj_fundo, b.data_referencia,
               b.disponibilidades, b.titulos_publicos, b.fundos_renda_fixa,
               b.total_necessidades_liquidez,
               COALESCE(b.disponibilidades, 0) + COALESCE(b.titulos_publicos, 0)
                   + COALESCE(b.fundos_renda_fixa, 0) AS liquid_assets,
               b.total_investido,
               CASE WHEN b.total_investido != 0
                   THEN (COALESCE(b.disponibilidades, 0) + COALESCE(b.titulos_publicos, 0)
                         + COALESCE(b.fundos_renda_fixa, 0)) / b.total_investido
                   ELSE NULL END AS liquidity_ratio
        FROM fii_balanco_mensal b
        WHERE b.cnpj_fundo = :cnpj
          AND b.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
          AND b.versao = (SELECT MAX(versao) FROM fii_balanco_mensal b2
                          WHERE b2.cnpj_fundo = :cnpj AND b2.data_referencia = b.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def fund_liability_breakdown(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT b.cnpj_fundo, b.data_referencia, b.total_passivo,
               b.rendimentos_distribuir, b.taxa_administracao_pagar,
               b.taxa_performance_pagar, b.obrigacoes_aquisicao_imoveis,
               b.adiantamento_venda_imoveis, b.adiantamento_alugueis,
               b.obrigacoes_securitizacao_recebiveis,
               b.instrumentos_financeiros_derivativos,
               b.provisoes_contigencias, b.outros_valores_pagar
        FROM fii_balanco_mensal b
        WHERE b.cnpj_fundo = :cnpj
          AND b.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
          AND b.versao = (SELECT MAX(versao) FROM fii_balanco_mensal b2
                          WHERE b2.cnpj_fundo = :cnpj AND b2.data_referencia = b.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def fund_real_estate_detail(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT b.cnpj_fundo, b.data_referencia,
               b.direitos_bens_imoveis, b.imoveis_renda_acabados,
               b.imoveis_renda_construcao, b.imoveis_venda_acabados,
               b.imoveis_venda_construcao, b.terrenos, b.outros_direitos_reais
        FROM fii_balanco_mensal b
        WHERE b.cnpj_fundo = :cnpj
          AND b.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
          AND b.versao = (SELECT MAX(versao) FROM fii_balanco_mensal b2
                          WHERE b2.cnpj_fundo = :cnpj AND b2.data_referencia = b.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def fund_securities_detail(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT b.cnpj_fundo, b.data_referencia,
               b.cri_cra, b.lci_lca, b.acoes, b.debentures,
               b.fii, b.fip, b.fdic, b.fundo_acoes,
               b.acoes_sociedades_atividades_fii,
               b.cotas_sociedades_atividades_fii,
               b.outras_cotas_fi, b.outros_valores_mobliarios
        FROM fii_balanco_mensal b
        WHERE b.cnpj_fundo = :cnpj
          AND b.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
          AND b.versao = (SELECT MAX(versao) FROM fii_balanco_mensal b2
                          WHERE b2.cnpj_fundo = :cnpj AND b2.data_referencia = b.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def fund_receivables_detail(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT b.cnpj_fundo, b.data_referencia,
               b.valores_receber, b.contas_receber_aluguel,
               b.contas_receber_venda_imoveis, b.outros_valores_receber
        FROM fii_balanco_mensal b
        WHERE b.cnpj_fundo = :cnpj
          AND b.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
          AND b.versao = (SELECT MAX(versao) FROM fii_balanco_mensal b2
                          WHERE b2.cnpj_fundo = :cnpj AND b2.data_referencia = b.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def fund_metrics_with_segment(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        WITH latest_g AS (
            SELECT MAX(versao) AS v, data_referencia
            FROM fii_fundo_mensal
            WHERE cnpj_fundo = :cnpj
              AND data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal WHERE cnpj_fundo = :cnpj))
            GROUP BY data_referencia
        ),
        latest_m AS (
            SELECT MAX(versao) AS v, data_referencia
            FROM fii_metrica_mensal
            WHERE cnpj_fundo = :cnpj
              AND data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj))
            GROUP BY data_referencia
        )
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao, g.tipo_gestao,
               m.patrimonio_liquido, m.valor_patrimonial_cotas,
               m.percentual_dividend_yield_mes, m.total_numero_cotistas,
               m.percentual_rentabilidade_efetiva_mes,
               m.percentual_despesas_taxa_administracao
        FROM fii_fundo_mensal g
        JOIN latest_g lg ON g.data_referencia = lg.data_referencia AND g.versao = lg.v
        LEFT JOIN fii_metrica_mensal m ON m.cnpj_fundo = g.cnpj_fundo
            AND m.data_referencia = g.data_referencia
        LEFT JOIN latest_m lm ON m.data_referencia = lm.data_referencia AND m.versao = lm.v
        WHERE g.cnpj_fundo = :cnpj
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def funds_filtered_dy_and_pl(
    session: Session,
    min_dy: float | None = None,
    min_pl: float | None = None,
    segment: str | None = None,
    ref: date | None = None,
    limit: int = 50,
) -> list[dict]:
    sql = text("""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
            GROUP BY cnpj_fundo, data_referencia
        ),
        latest_m AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_metrica_mensal))
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao,
               m.percentual_dividend_yield_mes, m.patrimonio_liquido
        FROM fii_fundo_mensal g
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        JOIN fii_metrica_mensal m ON m.cnpj_fundo = g.cnpj_fundo
            AND m.data_referencia = g.data_referencia
        JOIN latest_m lm ON m.cnpj_fundo = lm.cnpj_fundo
            AND m.data_referencia = lm.data_referencia AND m.versao = lm.v
        WHERE (:min_dy IS NULL OR m.percentual_dividend_yield_mes >= :min_dy)
          AND (:min_pl IS NULL OR m.patrimonio_liquido >= :min_pl)
          AND (:segment IS NULL OR g.segmento_atuacao ILIKE :segment)
        ORDER BY m.percentual_dividend_yield_mes DESC
        LIMIT :limit
    """)
    return _to_list(
        session.execute(
            sql,
            {"ref": ref, "min_dy": min_dy, "min_pl": min_pl, "segment": segment, "limit": limit},
        ).all()
    )


def funds_filtered_multi(
    session: Session,
    segment: str | None = None,
    min_dy: float | None = None,
    min_pl: float | None = None,
    min_cotistas: int | None = None,
    listed_only: bool = False,
    ref: date | None = None,
    limit: int = 50,
) -> list[dict]:
    listed_clause = "AND g.mercado_negociacao_bolsa = 'S'" if listed_only else ""
    sql = text(f"""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
            GROUP BY cnpj_fundo, data_referencia
        ),
        latest_m AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_metrica_mensal))
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao,
               g.mercado_negociacao_bolsa,
               m.percentual_dividend_yield_mes, m.patrimonio_liquido,
               m.total_numero_cotistas, m.valor_patrimonial_cotas
        FROM fii_fundo_mensal g
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        JOIN fii_metrica_mensal m ON m.cnpj_fundo = g.cnpj_fundo
            AND m.data_referencia = g.data_referencia
        JOIN latest_m lm ON m.cnpj_fundo = lm.cnpj_fundo
            AND m.data_referencia = lm.data_referencia AND m.versao = lm.v
        WHERE (:segment IS NULL OR g.segmento_atuacao ILIKE :segment)
          AND (:min_dy IS NULL OR m.percentual_dividend_yield_mes >= :min_dy)
          AND (:min_pl IS NULL OR m.patrimonio_liquido >= :min_pl)
          AND (:min_cotistas IS NULL OR m.total_numero_cotistas >= :min_cotistas)
          {listed_clause}
        ORDER BY m.percentual_dividend_yield_mes DESC
        LIMIT :limit
    """)
    return _to_list(
        session.execute(
            sql,
            {
                "ref": ref,
                "segment": segment,
                "min_dy": min_dy,
                "min_pl": min_pl,
                "min_cotistas": min_cotistas,
                "limit": limit,
            },
        ).all()
    )


def fund_dy_with_balance_summary(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        WITH latest_m AS (
            SELECT MAX(versao) AS v, data_referencia
            FROM fii_metrica_mensal
            WHERE cnpj_fundo = :cnpj
              AND data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj))
            GROUP BY data_referencia
        ),
        latest_b AS (
            SELECT MAX(versao) AS v, data_referencia
            FROM fii_balanco_mensal
            WHERE cnpj_fundo = :cnpj
              AND data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
            GROUP BY data_referencia
        )
        SELECT m.cnpj_fundo, m.data_referencia,
               m.percentual_dividend_yield_mes, m.patrimonio_liquido,
               m.valor_patrimonial_cotas,
               b.total_investido, b.total_passivo, b.disponibilidades,
               b.total_necessidades_liquidez
        FROM fii_metrica_mensal m
        JOIN latest_m lm ON m.data_referencia = lm.data_referencia AND m.versao = lm.v
        LEFT JOIN fii_balanco_mensal b ON b.cnpj_fundo = m.cnpj_fundo
            AND b.data_referencia = m.data_referencia
        LEFT JOIN latest_b lb ON b.data_referencia = lb.data_referencia AND b.versao = lb.v
        WHERE m.cnpj_fundo = :cnpj
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


# ===========================================================================
# Category 9: Alerts & Anomalies (13 queries)
# ===========================================================================


def dy_drop_mom(
    session: Session, threshold: float = 0.2, segment: str | None = None
) -> list[dict]:
    return _alert_mom(
        session, "percentual_dividend_yield_mes", "fii_metrica_mensal",
        threshold, "drop", segment,
    )


def dy_increase_mom(
    session: Session, threshold: float = 0.2, segment: str | None = None
) -> list[dict]:
    return _alert_mom(
        session, "percentual_dividend_yield_mes", "fii_metrica_mensal",
        threshold, "increase", segment,
    )


def cotistas_drop(
    session: Session, threshold: float = 0.1, segment: str | None = None
) -> list[dict]:
    return _alert_mom(
        session, "total_numero_cotistas", "fii_metrica_mensal",
        threshold, "drop", segment,
    )


def cotistas_increase(
    session: Session, threshold: float = 0.1, segment: str | None = None
) -> list[dict]:
    return _alert_mom(
        session, "total_numero_cotistas", "fii_metrica_mensal",
        threshold, "increase", segment,
    )


def pl_drop(
    session: Session, threshold: float = 0.1, segment: str | None = None
) -> list[dict]:
    return _alert_mom(
        session, "patrimonio_liquido", "fii_metrica_mensal",
        threshold, "drop", segment,
    )


def pl_increase(
    session: Session, threshold: float = 0.1, segment: str | None = None
) -> list[dict]:
    return _alert_mom(
        session, "patrimonio_liquido", "fii_metrica_mensal",
        threshold, "increase", segment,
    )


def vpa_drop(
    session: Session, threshold: float = 0.1, segment: str | None = None
) -> list[dict]:
    return _alert_mom(
        session, "valor_patrimonial_cotas", "fii_metrica_mensal",
        threshold, "drop", segment,
    )


def funds_with_negative_dy(
    session: Session, ref: date | None = None
) -> list[dict]:
    sql = text("""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
            GROUP BY cnpj_fundo, data_referencia
        ),
        latest_m AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_metrica_mensal))
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao,
               m.percentual_dividend_yield_mes
        FROM fii_metrica_mensal m
        JOIN latest_m lm ON m.cnpj_fundo = lm.cnpj_fundo
            AND m.data_referencia = lm.data_referencia AND m.versao = lm.v
        JOIN fii_fundo_mensal g ON g.cnpj_fundo = m.cnpj_fundo
            AND g.data_referencia = m.data_referencia
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        WHERE m.percentual_dividend_yield_mes < 0
        ORDER BY m.percentual_dividend_yield_mes ASC
    """)
    return _to_list(session.execute(sql, {"ref": ref}).all())


def funds_with_negative_pl(
    session: Session, ref: date | None = None
) -> list[dict]:
    sql = text("""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_fundo_mensal))
            GROUP BY cnpj_fundo, data_referencia
        ),
        latest_m AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal
            WHERE data_referencia = COALESCE(:ref, (SELECT MAX(data_referencia) FROM fii_metrica_mensal))
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao,
               m.patrimonio_liquido
        FROM fii_metrica_mensal m
        JOIN latest_m lm ON m.cnpj_fundo = lm.cnpj_fundo
            AND m.data_referencia = lm.data_referencia AND m.versao = lm.v
        JOIN fii_fundo_mensal g ON g.cnpj_fundo = m.cnpj_fundo
            AND g.data_referencia = m.data_referencia
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        WHERE m.patrimonio_liquido < 0
        ORDER BY m.patrimonio_liquido ASC
    """)
    return _to_list(session.execute(sql, {"ref": ref}).all())


def funds_stopped_distributing(
    session: Session, months_back: int = 3
) -> list[dict]:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal GROUP BY 1, 2
        ),
        ranked AS (
            SELECT m.cnpj_fundo, m.data_referencia, m.percentual_dividend_yield_mes,
                   ROW_NUMBER() OVER (PARTITION BY m.cnpj_fundo ORDER BY m.data_referencia DESC) AS rn
            FROM fii_metrica_mensal m
            JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
                AND m.data_referencia = l.data_referencia AND m.versao = l.v
        ),
        latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = (SELECT MAX(data_referencia) FROM fii_fundo_mensal)
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT r1.cnpj_fundo, g.nome_fundo, g.segmento_atuacao,
               r1.data_referencia AS current_month,
               r1.percentual_dividend_yield_mes AS current_dy
        FROM ranked r1
        JOIN fii_fundo_mensal g ON g.cnpj_fundo = r1.cnpj_fundo
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        WHERE r1.rn = 1
          AND (r1.percentual_dividend_yield_mes IS NULL OR r1.percentual_dividend_yield_mes = 0)
          AND EXISTS (
              SELECT 1 FROM ranked r2
              WHERE r2.cnpj_fundo = r1.cnpj_fundo
                AND r2.rn BETWEEN 2 AND :months_back + 1
                AND r2.percentual_dividend_yield_mes > 0
          )
        ORDER BY g.nome_fundo
    """)
    return _to_list(session.execute(sql, {"months_back": months_back}).all())


def share_dilution(
    session: Session, threshold: float = 0.05, segment: str | None = None
) -> list[dict]:
    return _alert_mom(
        session, "cotas_emitidas", "fii_metrica_mensal",
        threshold, "increase", segment,
    )


def new_funds(session: Session, months_back: int = 1) -> list[dict]:
    sql = text("""
        WITH latest_g AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_fundo_mensal
            WHERE data_referencia = (SELECT MAX(data_referencia) FROM fii_fundo_mensal)
            GROUP BY cnpj_fundo, data_referencia
        )
        SELECT g.cnpj_fundo, g.nome_fundo, g.segmento_atuacao,
               g.data_funcionamento, g.data_referencia
        FROM fii_fundo_mensal g
        JOIN latest_g lg ON g.cnpj_fundo = lg.cnpj_fundo
            AND g.data_referencia = lg.data_referencia AND g.versao = lg.v
        WHERE g.cnpj_fundo NOT IN (
            SELECT DISTINCT cnpj_fundo FROM fii_fundo_mensal
            WHERE data_referencia < (SELECT MAX(data_referencia) FROM fii_fundo_mensal)
                  - MAKE_INTERVAL(months => :months_back)
        )
        ORDER BY g.nome_fundo
    """)
    return _to_list(session.execute(sql, {"months_back": months_back}).all())


def passivo_increase(
    session: Session, threshold: float = 0.2, segment: str | None = None
) -> list[dict]:
    return _alert_mom(
        session, "total_passivo", "fii_balanco_mensal",
        threshold, "increase", segment,
    )


# ===========================================================================
# Category 10: Calculated Metrics (8 queries)
# ===========================================================================


def calc_dy_anualizado(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT m.cnpj_fundo, m.data_referencia,
               m.percentual_dividend_yield_mes * 12 AS dy_anualizado
        FROM fii_metrica_mensal m
        WHERE m.cnpj_fundo = :cnpj
          AND m.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj))
          AND m.versao = (SELECT MAX(versao) FROM fii_metrica_mensal m2
                          WHERE m2.cnpj_fundo = :cnpj AND m2.data_referencia = m.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def calc_dy_acumulado_12m(session: Session, cnpj: str) -> dict | None:
    return dy_last_12_months(session, cnpj)


def calc_dividend_per_cota(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT m.cnpj_fundo, m.data_referencia,
               m.percentual_dividend_yield_mes * m.valor_patrimonial_cotas
                   AS dividend_per_cota
        FROM fii_metrica_mensal m
        WHERE m.cnpj_fundo = :cnpj
          AND m.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj))
          AND m.versao = (SELECT MAX(versao) FROM fii_metrica_mensal m2
                          WHERE m2.cnpj_fundo = :cnpj AND m2.data_referencia = m.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def calc_total_dividends(
    session: Session,
    cnpj: str,
    months: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict | None:
    sql = text("""
        WITH latest AS (
            SELECT cnpj_fundo, data_referencia, MAX(versao) AS v
            FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj GROUP BY 1, 2
        )
        SELECT SUM(m.percentual_dividend_yield_mes * m.valor_patrimonial_cotas
                    * m.cotas_emitidas) AS total_dividends,
               COUNT(*) AS num_months
        FROM fii_metrica_mensal m
        JOIN latest l ON m.cnpj_fundo = l.cnpj_fundo
            AND m.data_referencia = l.data_referencia AND m.versao = l.v
        WHERE m.cnpj_fundo = :cnpj
          AND m.percentual_dividend_yield_mes IS NOT NULL
          AND m.valor_patrimonial_cotas IS NOT NULL
          AND m.cotas_emitidas IS NOT NULL
          AND m.data_referencia >= COALESCE(:start,
              (SELECT MAX(data_referencia) FROM fii_metrica_mensal WHERE cnpj_fundo = :cnpj)
              - MAKE_INTERVAL(months => :months))
          AND m.data_referencia <= COALESCE(:end, CURRENT_DATE)
    """)
    row = session.execute(
        sql, {"cnpj": cnpj, "months": months, "start": start_date, "end": end_date}
    ).first()
    return _to_dict(row) if row else None


def calc_real_estate_pct(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT b.cnpj_fundo, b.data_referencia,
               CASE WHEN b.total_investido != 0
                   THEN b.imoveis_renda_acabados / b.total_investido
                   ELSE NULL END AS real_estate_pct
        FROM fii_balanco_mensal b
        WHERE b.cnpj_fundo = :cnpj
          AND b.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
          AND b.versao = (SELECT MAX(versao) FROM fii_balanco_mensal b2
                          WHERE b2.cnpj_fundo = :cnpj AND b2.data_referencia = b.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def calc_paper_pct(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT b.cnpj_fundo, b.data_referencia,
               CASE WHEN b.total_investido != 0
                   THEN b.cri_cra / b.total_investido
                   ELSE NULL END AS paper_pct
        FROM fii_balanco_mensal b
        WHERE b.cnpj_fundo = :cnpj
          AND b.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
          AND b.versao = (SELECT MAX(versao) FROM fii_balanco_mensal b2
                          WHERE b2.cnpj_fundo = :cnpj AND b2.data_referencia = b.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def calc_fof_pct(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT b.cnpj_fundo, b.data_referencia,
               CASE WHEN b.total_investido != 0
                   THEN b.fii / b.total_investido
                   ELSE NULL END AS fof_pct
        FROM fii_balanco_mensal b
        WHERE b.cnpj_fundo = :cnpj
          AND b.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
          AND b.versao = (SELECT MAX(versao) FROM fii_balanco_mensal b2
                          WHERE b2.cnpj_fundo = :cnpj AND b2.data_referencia = b.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None


def calc_cash_pct(
    session: Session, cnpj: str, ref: date | None = None
) -> dict | None:
    sql = text("""
        SELECT b.cnpj_fundo, b.data_referencia,
               CASE WHEN m.valor_ativo != 0
                   THEN b.total_necessidades_liquidez / m.valor_ativo
                   ELSE NULL END AS cash_pct
        FROM fii_balanco_mensal b
        JOIN fii_metrica_mensal m ON m.cnpj_fundo = b.cnpj_fundo
            AND m.data_referencia = b.data_referencia
        WHERE b.cnpj_fundo = :cnpj
          AND b.data_referencia = COALESCE(:ref,
              (SELECT MAX(data_referencia) FROM fii_balanco_mensal WHERE cnpj_fundo = :cnpj))
          AND b.versao = (SELECT MAX(versao) FROM fii_balanco_mensal b2
                          WHERE b2.cnpj_fundo = :cnpj AND b2.data_referencia = b.data_referencia)
          AND m.versao = (SELECT MAX(versao) FROM fii_metrica_mensal m2
                          WHERE m2.cnpj_fundo = :cnpj AND m2.data_referencia = m.data_referencia)
    """)
    row = session.execute(sql, {"cnpj": cnpj, "ref": ref}).first()
    return _to_dict(row) if row else None
