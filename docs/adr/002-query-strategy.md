# ADR-002: Query Strategy — Pre-built Queries with LLM Fallback

**Status:** Accepted  
**Date:** 2026-11-07  
**Author:** Igor Santos  

## Context

The FII Analyzer chatbot receives user questions in Brazilian Portuguese about fund data stored in PostgreSQL. The system must translate natural language into database queries, retrieve the results, and explain them to the user.

The LLM (Gemini 3.5 Flash-Lite, selected in ADR-001) can generate SQL from natural language (Text-to-SQL), but every LLM call has a cost ($0.30/M input, $2.50/M output) and adds latency (~1.4s). The primary strategy is to pre-build the maximum number of queries to cover every question the data can answer, minimizing LLM usage for SQL generation.

## Decision

**Pre-built queries as the primary path, with exhaustive coverage. LLM-generated SQL exists only as a safety net for edge cases the pre-built set hasn't anticipated yet.**

The system maintains an exhaustive set of pre-built, parameterized SQL queries covering every metric, every combination of filters, every time range, and every cross-table join the schema supports. User questions are matched against these queries using keyword/pattern matching. The LLM is used only to explain the results in Portuguese — not to generate SQL in the normal flow.

```
User question (Portuguese)
      |
[Pattern matching — route to pre-built query]
      |
[Run pre-built SQL with extracted parameters]
      |
[LLM explains results in Portuguese]
      (1 LLM call)
```

When a question doesn't match any pre-built query (an edge case), the system falls back to LLM-generated SQL as a safety net — but the goal is to minimize this by continuously expanding the pre-built query set.

## Options Evaluated

### Option 1: Text-to-SQL for all queries

Every question goes to the LLM to generate SQL, then a second call explains the results.

| Dimension | Assessment |
|---|---|
| Cost | 2 LLM calls per question (~$0.002/question) |
| Latency | ~2.8s (2 × 1.4s LLM calls) + query time |
| Flexibility | High — handles any question the schema can answer |
| Predictability | Low — LLM may generate incorrect SQL |
| Complexity | Low — one code path for all questions |

### Option 2: Exhaustive pre-built queries (chosen)

Maximum coverage with pre-built queries. LLM generates SQL only as a safety net for unpredicted edge cases.

| Dimension | Assessment |
|---|---|
| Cost | 1 LLM call per question (explanation only, ~$0.001/question) |
| Latency | ~1.4s (1 LLM call) + query time |
| Flexibility | High — exhaustive query set covers every metric and combination |
| Predictability | High — SQL is hand-written and tested |
| Complexity | Higher upfront — large query set to build and maintain |

## Why Exhaustive Pre-built

1. **Cost**: every question that hits a pre-built query saves one LLM call. At scale, this is the difference between $5/month and $10/month — significant for a portfolio project.

2. **Speed**: pre-built queries eliminate one LLM round-trip. Every question responds in ~1.4s instead of ~2.8s.

3. **Reliability**: hand-written SQL is tested and deterministic. LLM-generated SQL can be syntactically valid but semantically wrong (wrong JOIN, wrong aggregation). Pre-built queries eliminate this risk entirely for covered questions.

4. **Continuous improvement**: the LLM fallback catches questions the pre-built set hasn't covered yet. Logs reveal these gaps, and new pre-built queries are added to close them. Over time, the fallback is used less and less.

## Classification Method: Pattern Matching

The system uses keyword and pattern matching to route questions to pre-built queries — not LLM-based classification.

**Rationale:**
- Zero cost per classification
- Deterministic — same question always routes the same way
- Simpler to debug and test

**Pattern matching extracts:**
- Tickers (regex: HGLG11, XPML11, MXRF11)
- Dates and periods (último mês, últimos 6 meses, em setembro, em 2025)
- Numbers and thresholds (mais de 0.80%, acima de R$10.000)
- Metric keywords with synonym support (dividendo = rendimento = provento)

**Future option:** if logs show that pattern matching misses too many classifiable questions, the classification step can be upgraded to an LLM call. This change would be isolated to the router module.

## Pre-built Query Categories

The pre-built query set is exhaustive, covering:

| Category | Scope |
|---|---|
| **Factual lookups** | Every metric for a specific fund + date |
| **Historical / time series** | Every metric's evolution over time |
| **Rankings / top-N** | Every metric ranked, with optional segment and time filters |
| **Comparisons** | Side-by-side funds on any or all metrics |
| **Aggregations** | Accumulated, averaged, summed metrics over periods |
| **Segment analysis** | All queries filterable by segment |
| **Cross-table queries** | Joins across geral + ativo_passivo + complemento |
| **Alerts / anomalies** | Metric changes above thresholds (drops, spikes) |
| **Calculated metrics** | Derived values: P/VP, dividend yield, payout ratio |

The full query list and pattern table are maintained in `db/queries.py` and `llm/router.py`.

## Codebase Impact

| Module | Responsibility |
|---|---|
| `db/queries.py` | All pre-built parameterized queries — exhaustive set |
| `llm/router.py` | Pattern matching: question → pre-built query + parameters |
| `llm/text_to_sql.py` | Safety net: LLM generates SQL for unmatched edge cases |
| `llm/client.py` | Gemini wrapper (used for result explanation and fallback SQL generation) |
| `llm/prompts.py` | System prompt with table schemas (English) and explanation prompt |

## Safety Rules for LLM-Generated SQL (fallback only)

When the LLM generates SQL in the fallback path, the following validations apply before execution:

1. **SELECT only** — reject any statement that is not a SELECT query
2. **Allowed tables** — reject queries referencing tables not in the application schema
3. **Read-only user** — execute with a PostgreSQL role that has SELECT permission only
4. **Timeout** — 5-second query timeout to prevent runaway queries
5. **Row limit** — append LIMIT 100 if no LIMIT clause is present

## Consequences

- `db/queries.py` is the largest module in the system — by design. It contains every query the data can answer.
- Nearly all user questions resolve with 1 LLM call (explanation only), keeping cost minimal
- The LLM fallback exists as a safety net, not a primary path
- Usage logs reveal which fallback queries should be promoted to pre-built — the goal is zero fallback usage over time
- The router is the single module to change if upgrading from pattern matching to LLM classification
- All LLM-generated SQL passes through validation before execution — no raw SQL reaches the database

## References

- [ADR-001: LLM Model Selection](./001-llm-model-selection.md)
- [CVM Open Data — FII Monthly Reports](https://dados.cvm.gov.br/dataset/fii-doc-inf_mensal)