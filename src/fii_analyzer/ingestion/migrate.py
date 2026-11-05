"""CVM FII data migration/seed script.

Usage:
    python -m fii_analyzer.ingestion.migrate seed --data-dir /path/to/zips --env local
    python -m fii_analyzer.ingestion.migrate update --data-dir /path/to/zips --env prod
"""
import argparse
import logging
import os
import re
import sys
import tempfile
import unicodedata
import zipfile
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from sqlalchemy import BigInteger, Date, Integer, Numeric, String, Text, create_engine, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from fii_analyzer.db.model import (
    Base,
    FiiAquisicaoAnual,
    FiiBalancoMensal,
    FiiDistribuicaoCotistaAnual,
    FiiFundoAnual,
    FiiFundoMensal,
    FiiMetricaMensal,
    FiiNarrativaAnual,
    FiiProcessoAnual,
    FiiTransacaoAnual,
    FiiValorAtivoAnual,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def get_database_url(env: str) -> str:
    if env == "prod":
        url = os.environ.get("DATABASE_URL_PROD")
        if not url:
            sys.exit("Error: DATABASE_URL_PROD environment variable not set for --env prod")
        return url
    from fii_analyzer.config import settings
    return settings.database_url


def convert_value(val, sa_type):
    if pd.isna(val) or val is None:
        return None
    val = str(val).strip()
    if not val:
        return None
    if isinstance(sa_type, Date):
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            return None
    if isinstance(sa_type, (Integer, BigInteger)):
        try:
            return int(float(val))
        except (ValueError, OverflowError):
            return None
    if isinstance(sa_type, Numeric):
        try:
            return Decimal(val)
        except InvalidOperation:
            return None
    return val


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [strip_accents(c) for c in df.columns]
    renames = {}
    if "CNPJ_Fundo_Classe" in df.columns:
        renames["CNPJ_Fundo_Classe"] = "CNPJ_Fundo"
    if "Nome_Fundo_Classe" in df.columns:
        renames["Nome_Fundo_Classe"] = "Nome_Fundo"
    if renames:
        df = df.rename(columns=renames)
    return df


# ---------------------------------------------------------------------------
# Column mappings:  CSV column (after accent-strip + CNPJ rename) -> DB column
# DB column = CSV column lowercased
# ---------------------------------------------------------------------------

def _cols(*names: str) -> dict[str, str]:
    return {n: n.lower() for n in names}


FUND_ANNUAL_COLUMNS = _cols(
    "CNPJ_Fundo", "Data_Referencia", "Versao", "Data_Entrega", "Tipo_Fundo_Classe",
    "Nome_Fundo", "Codigo_ISIN", "Data_Funcionamento", "Publico_Alvo",
    "Quantidade_Cotas_Emitidas", "Fundo_Exclusivo", "Mandato", "Segmento_Atuacao",
    "Tipo_Gestao", "Prazo_Duracao", "Mercado_Negociacao_Bolsa", "Nome_Administrador",
    "CNPJ_Administrador",
)

FUND_MONTHLY_COLUMNS = _cols(
    "CNPJ_Fundo", "Data_Referencia", "Versao", "Data_Entrega", "Tipo_Fundo_Classe",
    "Nome_Fundo", "Codigo_ISIN", "Data_Funcionamento", "Publico_Alvo",
    "Quantidade_Cotas_Emitidas", "Fundo_Exclusivo", "Cotistas_Vinculo_Familiar",
    "Mandato", "Segmento_Atuacao", "Tipo_Gestao", "Prazo_Duracao",
    "Data_Prazo_Duracao", "Encerramento_Exercicio_Social",
    "Mercado_Negociacao_Bolsa", "Mercado_Negociacao_MBO", "Mercado_Negociacao_MB",
    "Entidade_Administradora_BVMF", "Entidade_Administradora_CETIP",
    "Nome_Administrador", "CNPJ_Administrador",
    "Logradouro", "Numero", "Complemento", "Bairro", "Cidade", "Estado", "CEP",
    "Telefone1", "Telefone2", "Telefone3", "Site", "Email",
)

MONTHLY_METRICS_COLUMNS = _cols(
    "CNPJ_Fundo", "Data_Referencia", "Versao",
    "Data_Informacao_Numero_Cotistas", "Total_Numero_Cotistas",
    "Numero_Cotistas_Pessoa_Fisica", "Numero_Cotistas_Pessoa_Juridica_Nao_Financeira",
    "Numero_Cotistas_Banco_Comercial", "Numero_Cotistas_Corretora_Distribuidora",
    "Numero_Cotistas_Outras_Pessoas_Juridicas_Financeira",
    "Numero_Cotistas_Investidores_Nao_Residentes",
    "Numero_Cotistas_Entidade_Aberta_Previdencia_Complementar",
    "Numero_Cotistas_Entidade_Fechada_Previdencia_Complementar",
    "Numero_Cotistas_Regime_Proprio_Previdencia_Servidores_Publicos",
    "Numero_Cotistas_Sociedade_Seguradora_Resseguradora",
    "Numero_Cotistas_Sociedade_Capitalizacao_Arrendamento_Mercantil",
    "Numero_Cotistas_FII", "Numero_Cotistas_Outros_Fundos",
    "Numero_Cotistas_Distribuidores_Fundo", "Numero_Cotistas_Outros_Tipos",
    "Valor_Ativo", "Patrimonio_Liquido", "Cotas_Emitidas", "Valor_Patrimonial_Cotas",
    "Percentual_Despesas_Taxa_Administracao", "Percentual_Despesas_Agente_Custodiante",
    "Percentual_Rentabilidade_Efetiva_Mes", "Percentual_Rentabilidade_Patrimonial_Mes",
    "Percentual_Dividend_Yield_Mes", "Percentual_Amortizacao_Cotas_Mes",
)

MONTHLY_BALANCE_COLUMNS = _cols(
    "CNPJ_Fundo", "Data_Referencia", "Versao", "Total_Necessidades_Liquidez",
    "Disponibilidades", "Titulos_Publicos", "Titulos_Privados", "Fundos_Renda_Fixa",
    "Total_Investido", "Direitos_Bens_Imoveis", "Terrenos", "Imoveis_Renda_Acabados",
    "Imoveis_Renda_Construcao", "Imoveis_Venda_Acabados", "Imoveis_Venda_Construcao",
    "Outros_Direitos_Reais",
    "Acoes", "Debentures", "Bonus_Subscricao",
    "Certificados_Deposito_Valores_Mobiliarios", "Cedulas_Debentures",
    "Fundo_Acoes", "FIP", "FII", "FDIC", "Outras_Cotas_FI",
    "Notas_Promissorias", "Acoes_Sociedades_Atividades_FII",
    "Cotas_Sociedades_Atividades_FII", "CEPAC",
    "CRI", "CRI_CRA", "Letras_Hipotecarias", "LCI", "LCI_LCA", "LIG",
    "Outros_Valores_Mobliarios",
    "Valores_Receber", "Contas_Receber_Aluguel",
    "Contas_Receber_Venda_Imoveis", "Outros_Valores_Receber",
    "Rendimentos_Distribuir", "Taxa_Administracao_Pagar", "Taxa_Performance_Pagar",
    "Obrigacoes_Aquisicao_Imoveis", "Adiantamento_Venda_Imoveis",
    "Adiantamento_Alugueis", "Obrigacoes_Securitizacao_Recebiveis",
    "Instrumentos_Financeiros_Derivativos", "Provisoes_Contigencias",
    "Outros_Valores_Pagar", "Total_Passivo",
)

ANNUAL_NARRATIVE_COLUMNS = _cols(
    "CNPJ_Fundo", "Data_Referencia", "Nome_Gestor", "Nome_Custodiante",
    "Nome_Auditor_Independente", "Conjuntura_Economica_Periodo_Findo",
    "Resultado_Exercicio_Findo", "Perspectiva_Periodo_Seguinte",
    "Programa_Investimentos_Exercicio_Seguinte", "Criterios_Avaliacao",
    "Politica_Remuneracao",
)

ANNUAL_TRANSACTION_COLUMNS = _cols(
    "CNPJ_Fundo", "Data_Referencia", "Ativo_Negociado", "Natureza_Transacao",
    "Data_Transacao", "Valor_Envolvido", "Data_Assembleia", "Contraparte",
)

ANNUAL_ASSET_VALUE_COLUMNS = _cols(
    "CNPJ_Fundo", "Data_Referencia", "Nome_Ativo", "Valor", "Valor_Justo",
    "Percentual_Valorizacao_Desvalorizacao",
)

ANNUAL_ACQUISITION_COLUMNS = _cols(
    "CNPJ_Fundo", "Data_Referencia", "Nome_Ativo", "Objetivos",
    "Montante_Investido", "Origem_Recursos",
)


def _build_shareholder_dist_columns() -> dict[str, str]:
    m: dict[str, str] = {"CNPJ_Fundo": "cnpj_fundo", "Data_Referencia": "data_referencia"}
    for sfx in ("Ate_5", "5a10", "10a15", "15a20", "20a30", "30a40", "40a50", "Acima_50"):
        for prefix in (
            f"Numero_Cotistas_Faixa_{sfx}",
            f"Numero_Cotas_Detidas_Faixa_{sfx}",
            f"Percentual_Cotas_Detidas_Faixa_{sfx}",
            f"Percentual_Detido_PF_Faixa_{sfx}",
            f"Percentual_Detido_PJ_Faixa_{sfx}",
        ):
            m[prefix] = prefix.lower()
    return m


SHAREHOLDER_DIST_COLUMNS = _build_shareholder_dist_columns()

ANNUAL_LAWSUIT_COLUMNS = _cols(
    "CNPJ_Fundo", "Data_Referencia", "Numero_Processo", "Juizo", "Instancia",
    "Data_Instauracao", "Valor_Causa", "Partes_Processo", "Chance_Perda",
    "Principais_Fatos", "Analise_Impacto_Perda",
)


# ---------------------------------------------------------------------------
# Table config registry
# ---------------------------------------------------------------------------

TABLE_CONFIGS = [
    {
        "pattern": re.compile(r"inf_mensal_fii_geral_\d{4}\.csv$"),
        "model": FiiFundoMensal,
        "column_map": FUND_MONTHLY_COLUMNS,
    },
    {
        "pattern": re.compile(r"inf_anual_fii_geral_\d{4}\.csv$"),
        "model": FiiFundoAnual,
        "column_map": FUND_ANNUAL_COLUMNS,
    },
    {
        "pattern": re.compile(r"inf_mensal_fii_complemento_\d{4}\.csv$"),
        "model": FiiMetricaMensal,
        "column_map": MONTHLY_METRICS_COLUMNS,
    },
    {
        "pattern": re.compile(r"inf_mensal_fii_ativo_passivo_\d{4}\.csv$"),
        "model": FiiBalancoMensal,
        "column_map": MONTHLY_BALANCE_COLUMNS,
    },
    {
        "pattern": re.compile(r"inf_anual_fii_complemento_\d{4}\.csv$"),
        "model": FiiNarrativaAnual,
        "column_map": ANNUAL_NARRATIVE_COLUMNS,
    },
    {
        "pattern": re.compile(r"inf_anual_fii_ativo_transacao_\d{4}\.csv$"),
        "model": FiiTransacaoAnual,
        "column_map": ANNUAL_TRANSACTION_COLUMNS,
    },
    {
        "pattern": re.compile(r"inf_anual_fii_ativo_valor_contabil_\d{4}\.csv$"),
        "model": FiiValorAtivoAnual,
        "column_map": ANNUAL_ASSET_VALUE_COLUMNS,
    },
    {
        "pattern": re.compile(r"inf_anual_fii_ativo_adquirido_\d{4}\.csv$"),
        "model": FiiAquisicaoAnual,
        "column_map": ANNUAL_ACQUISITION_COLUMNS,
    },
    {
        "pattern": re.compile(r"inf_anual_fii_distribuicao_cotistas_\d{4}\.csv$"),
        "model": FiiDistribuicaoCotistaAnual,
        "column_map": SHAREHOLDER_DIST_COLUMNS,
    },
    {
        "pattern": re.compile(r"inf_anual_fii_processo_\d{4}\.csv$"),
        "model": FiiProcessoAnual,
        "column_map": ANNUAL_LAWSUIT_COLUMNS,
    },
]


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _get_pk_columns(model) -> list[str]:
    return [col.name for col in model.__table__.primary_key.columns]


def _dedupe_batch(batch: list[dict], pk_columns: list[str]) -> list[dict]:
    seen: dict[tuple, int] = {}
    for i, row in enumerate(batch):
        key = tuple(row[pk] for pk in pk_columns)
        seen[key] = i
    return [batch[i] for i in sorted(seen.values())]


def _upsert_batch(
    engine, table, pk_columns: list[str], non_pk_cols: list[str], batch: list[dict]
) -> tuple[int, int]:
    """Upsert a batch. Returns (upserted, skipped)."""
    batch = _dedupe_batch(batch, pk_columns)
    update_cols = [c for c in non_pk_cols if c not in ("created_at", "updated_at")]
    try:
        stmt = pg_insert(table).values(batch)
        set_ = {col: stmt.excluded[col] for col in update_cols}
        set_["updated_at"] = func.now()
        stmt = stmt.on_conflict_do_update(
            index_elements=pk_columns,
            set_=set_,
        )
        with engine.begin() as conn:
            conn.execute(stmt)
        return len(batch), 0
    except Exception:
        upserted = 0
        skipped = 0
        for row in batch:
            try:
                stmt = pg_insert(table).values([row])
                set_ = {col: stmt.excluded[col] for col in update_cols}
                set_["updated_at"] = func.now()
                stmt = stmt.on_conflict_do_update(
                    index_elements=pk_columns,
                    set_=set_,
                )
                with engine.begin() as conn:
                    conn.execute(stmt)
                upserted += 1
            except Exception as e:
                pk_vals = {k: row.get(k) for k in pk_columns}
                logger.warning("Skipped row %s: %s", pk_vals, e)
                skipped += 1
        return upserted, skipped



def _lookup_nome_ativo(engine, cnpj: str, data_ref) -> str | None:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT nome_ativo FROM fii_aquisicao_anual "
                "WHERE cnpj_fundo = :c AND data_referencia = :d LIMIT 1"
            ),
            {"c": cnpj, "d": data_ref},
        ).fetchone()
    return row[0] if row else None


def process_csv(csv_path: Path, config: dict, engine) -> tuple[int, int]:
    model = config["model"]
    column_map = config["column_map"]
    pk_columns = _get_pk_columns(model)
    all_db_cols = set(column_map.values())
    non_pk_cols = [c for c in all_db_cols if c not in pk_columns]

    table_obj = model.__table__
    col_types = {db_col: table_obj.columns[db_col].type for db_col in all_db_cols}
    required_cols = {
        c.name for c in table_obj.columns if not c.nullable and c.name in all_db_cols
    }

    df = pd.read_csv(csv_path, sep=";", encoding="latin-1", dtype=str, keep_default_na=False)
    df = normalize_df(df)

    available_csv_cols = [c for c in column_map if c in df.columns]
    active_map = {c: column_map[c] for c in available_csv_cols}

    rows_upserted = 0
    rows_skipped = 0
    batch: list[dict] = []

    for _, raw_row in df.iterrows():
        row: dict = {}
        for csv_col, db_col in active_map.items():
            row[db_col] = convert_value(raw_row.get(csv_col), col_types[db_col])
        for db_col in all_db_cols:
            if db_col not in row:
                row[db_col] = None

        missing = [c for c in required_cols if row.get(c) is None]
        if missing:
            resolved = False
            if model is FiiValorAtivoAnual and missing == ["nome_ativo"] and row.get("cnpj_fundo"):
                nome = _lookup_nome_ativo(engine, row["cnpj_fundo"], row.get("data_referencia"))
                if nome:
                    row["nome_ativo"] = nome
                    resolved = True
            if not resolved:
                rows_skipped += 1
                continue

        batch.append(row)

        if len(batch) >= BATCH_SIZE:
            u, s = _upsert_batch(engine, table_obj, pk_columns, non_pk_cols, batch)
            rows_upserted += u
            rows_skipped += s
            batch = []

    if batch:
        u, s = _upsert_batch(engine, table_obj, pk_columns, non_pk_cols, batch)
        rows_upserted += u
        rows_skipped += s

    return rows_upserted, rows_skipped


def find_config(csv_filename: str) -> dict | None:
    for cfg in TABLE_CONFIGS:
        if cfg["pattern"].search(csv_filename):
            return cfg
    return None


def extract_zip(zip_path: Path, dest_dir: Path) -> list[Path]:
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    return sorted(dest_dir.glob("*.csv"))


def _zip_sort_key(p: Path) -> tuple[int, str]:
    """Sort ZIPs chronologically: by year, then mensal before anual."""
    m = re.search(r"(\d{4})", p.name)
    year = int(m.group(1)) if m else 0
    kind = 0 if "mensal" in p.name else 1
    return (year, kind)


def discover_zips(data_dir: Path, mode: str) -> list[Path]:
    zips = sorted(data_dir.glob("inf_*_fii_*.zip"), key=_zip_sort_key)
    if not zips:
        sys.exit(f"No CVM ZIP files found in {data_dir}")
    if mode == "update":
        mensal = [z for z in zips if "mensal" in z.name]
        anual = [z for z in zips if "anual" in z.name]
        latest: list[Path] = []
        if mensal:
            latest.append(mensal[-1])
        if anual:
            latest.append(anual[-1])
        return latest
    return zips


def _ensure_timestamp_columns(engine):
    table_names = [m.__tablename__ for m in (
        FiiFundoMensal, FiiFundoAnual, FiiMetricaMensal, FiiBalancoMensal,
        FiiNarrativaAnual, FiiTransacaoAnual, FiiValorAtivoAnual,
        FiiAquisicaoAnual, FiiDistribuicaoCotistaAnual, FiiProcessoAnual,
    )]
    with engine.begin() as conn:
        for t in table_names:
            conn.execute(text(
                f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            ))
            conn.execute(text(
                f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS "
                "updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            ))
    logger.info("Ensured created_at/updated_at on %d tables", len(table_names))


def run(args: argparse.Namespace):
    engine = create_engine(get_database_url(args.env))
    Base.metadata.create_all(engine)
    _ensure_timestamp_columns(engine)

    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        sys.exit(f"Data directory not found: {data_dir}")

    zips = discover_zips(data_dir, args.command)
    logger.info("Found %d ZIP file(s) to process", len(zips))

    total_upserted = 0
    total_skipped = 0

    for zip_path in zips:
        logger.info("Processing %s", zip_path.name)
        with tempfile.TemporaryDirectory() as tmp:
            csv_files = extract_zip(zip_path, Path(tmp))
            for csv_path in csv_files:
                config = find_config(csv_path.name)
                if config is None:
                    logger.debug("Skipping unmapped CSV: %s", csv_path.name)
                    continue

                table_name = config["model"].__tablename__
                logger.info("  %s -> %s", csv_path.name, table_name)
                upserted, skipped = process_csv(csv_path, config, engine)
                total_upserted += upserted
                total_skipped += skipped
                logger.info("    %d upserted, %d skipped", upserted, skipped)

    logger.info("Done. Total: %d upserted, %d skipped", total_upserted, total_skipped)


def main():
    parser = argparse.ArgumentParser(description="CVM FII data migration")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("seed", "update"):
        p = sub.add_parser(name)
        p.add_argument("--data-dir", required=True, help="Directory with CVM ZIP files")
        p.add_argument("--env", choices=["local", "prod"], default="local")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
