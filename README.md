# FII Analyzer

A Python data pipeline and NLU-powered query engine for Brazilian Real Estate Investment Funds (FIIs), built on top of public data from CVM (Comissão de Valores Mobiliários). Deployed on Google Cloud Platform.

Ask questions in natural Portuguese like:

- *"Top 10 fundos com maior DY"*
- *"Histórico de DY do HGLG11 nos últimos 6 meses"*
- *"Comparar HGLG11 e XPLG11"*
- *"Fundos de logística com DY acima de 0.8%"*

The system parses your question, extracts entities (fund tickers, dates, thresholds, segments), routes it to the right SQL query, and returns structured results — no LLM required for query understanding.

### Example

```
> Qual o DY do HGLG11?

Query:  get_dividend_yield
Params: {fund_identifier: "HGLG11"}
Result: {cnpj_fundo: "11.728.688/0001-47", data_referencia: "2026-09-01", percentual_dividend_yield_mes: 0.72}

→ Gemini explains: "O HGLG11 apresentou um dividend yield de 0,72% no mês de setembro de 2026."
```

## Design Decisions

Key technical choices behind this project — full details in the [ADRs](docs/adr/).

- **Gemini 3.5 Flash-Lite over 4 other models** — Evaluated 5 LLMs with [Promptfoo](https://promptfoo.dev/) across 55 automated tests on real CVM data. Flash-Lite scored 87.3% pass rate at $0.06 total, 2.5x cheaper and faster than the runner-up. See [ADR-001](docs/adr/001-llm-model-selection.md).

- **Pre-built SQL over text-to-SQL** — 146 hand-written, tested queries cover every metric the schema supports. The LLM only explains results (1 call), never generates SQL in the normal path. Half the latency, half the cost, fully deterministic. See [ADR-002](docs/adr/002-query-strategy.md).

- **Rule-based NLU over LLM classification** — Pattern matching routes questions at zero cost with deterministic behavior. If logs show too many misses, the router can be swapped for an LLM classifier without touching other modules.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────┐
│  CVM Open   │────▸│  Ingestion   │────▸│  PostgreSQL  │────▸│   NLU      │
│  Data (ZIP) │     │  Pipeline    │     │  (Cloud SQL) │     │   Router   │
└─────────────┘     └──────────────┘     └──────────────┘     └────────────┘
                     download ─▸                                normalize ─▸
                     parse CSV ─▸                               extract entities ─▸
                     upsert rows                                match query ─▸
                                                                build params ─▸
                                                                execute SQL
```

## Tech Stack

- **Python 3.12**
- **PostgreSQL** (Cloud SQL on GCP)
- **SQLAlchemy 2.x** — ORM with mapped columns and type hints
- **Pydantic Settings** — environment-based configuration with `.env` support
- **httpx** — async-ready HTTP client for CVM data downloads
- **Tenacity + PyBreaker** — retry logic with circuit breaker pattern for resilience
- **pandas** — CSV parsing and data transformation
- **pytest** — 240+ unit tests with mocked database sessions
- **Google Cloud Platform** — production deployment

## NLU Router

The query router is a rule-based Natural Language Understanding (NLU) pipeline — no external LLM calls needed for query classification.

### Pipeline

```
User question
  │
  ├─▸ normalize()          — lowercase, remove accents, clean punctuation
  ├─▸ extract_fund_names() — ticker codes (HGLG11) and quoted names
  ├─▸ extract_cnpjs()      — Brazilian CNPJ patterns
  ├─▸ extract_dates()      — "janeiro 2024", "últimos 6 meses", "ano passado"
  ├─▸ extract_numbers()    — "acima de 5%", "top 10", "R$ 100.000"
  ├─▸ extract_segment()    — "logística", "shoppings", "escritórios"
  │
  ▼
ExtractedEntities
  │
  ├─▸ match_query()        — score patterns, pick best match
  ├─▸ _build_params()      — map entities to SQL parameters
  │
  ▼
RouterResult(query_name, params, confidence)
```

### Query Categories

| Category | Examples | Count |
|---|---|---|
| Identification | Fund info, search by name, list segments | 10 |
| Factual | DY, patrimônio líquido, VPA, cotistas | 25 |
| Historical | Time series for any metric | 19 |
| Ranking | Top N funds by any metric | 20 |
| Comparison | Side-by-side fund comparison | 7 |
| Aggregation | Accumulated DY, variations, averages | 15 |
| Segment Analysis | Average DY by segment, segment comparison | 11 |
| Cross-Table | Complete profile, asset composition, filters | 13 |
| Alerts | DY drops, negative PL, share dilution | 14 |
| Calculated | Annualized DY, real estate %, paper % | 8 |

## Data Source

All data comes from [CVM Open Data](https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/) — monthly FII reports that include:

- Fund identification (CNPJ, name, segment, administrator)
- Financial metrics (patrimônio líquido, DY, VPA, rentabilidade)
- Investor data (number of shareholders by type)
- Balance sheet (assets, liabilities, real estate, CRI/CRA)
- Fee structure (administration, custody)

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL
- [uv](https://docs.astral.sh/uv/) (package manager)

### Setup

```bash
# Clone the repository
git clone https://github.com/igorRomulo/fii-analyzer.git
cd fii-analyzer

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Create database tables and run ingestion
uv run python -m fii_analyzer.cli

# Run tests
uv run pytest
```

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg2://fii:fii123@localhost:5432/fii_analyzer` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `GOOGLE_API_KEY` | Google API key (for LLM response generation via Gemini) | — |
| `GEMINI_MODEL` | Gemini model ID | `gemini-3.5-flash-lite` |

## Roadmap

- [x] Data ingestion pipeline with retry and circuit breaker
- [x] PostgreSQL schema and ORM models
- [x] 146 SQL query functions across 10 categories
- [x] Rule-based NLU router with entity extraction
- [x] Test suite (240+ tests)
- [ ] LLM-powered response generation using Gemini API (see [ADR-001](docs/adr/001-llm-model-selection.md))
- [ ] Conversational interface (CLI chat)
- [ ] REST API layer
- [ ] GCP production deployment (Cloud Run + Cloud SQL)
- [ ] Scheduled ingestion (Cloud Scheduler)
- [ ] Market price data ingestion (B3)

## Project Structure

```
src/fii_analyzer/
├── cli.py                  # Entry point
├── config.py               # Pydantic settings
├── db/
│   ├── model.py            # SQLAlchemy ORM models
│   ├── queries.py          # 146 query functions
│   ├── insert.py           # Batch insert logic
│   └── ...
├── ingestion/
│   ├── pipeline.py         # Orchestrates download → parse → upsert
│   ├── downloader.py       # CVM data fetcher with retry + circuit breaker
│   ├── ingest.py           # ZIP extraction and CSV parsing
│   ├── upsert.py           # Idempotent database writes
│   └── migrate.py          # Schema migrations
├── llm/
│   └── router.py           # NLU router: normalization, extraction, intent matching
└── tests/
    ├── test_router.py      # Router tests (70+)
    ├── test_queries.py     # Query tests (170+)
    └── ...                 # Pipeline, ingestion, config tests
```
