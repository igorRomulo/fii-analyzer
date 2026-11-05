# ADR-001: LLM Model Selection for Brazilian REITs RAG Application

**Status:** Accepted  
**Date:** 2026-11-07  
**Author:** Igor Santos  

## Context

This project is a RAG (Retrieval-Augmented Generation) application for Brazilian Real Estate Investment Trusts (FIIs — Fundos de Investimento Imobiliário). The application consumes structured data from CVM/B3 Monthly Reports (Informes Mensais Estruturados), stores it in a database, and uses an LLM to answer user questions about the funds.

The application runs in production on Google Cloud Platform.

The model must meet three simultaneous requirements:

1. **Brazilian Portuguese quality** — use correct Brazilian financial terminology (cotas, rendimentos, proventos, dividend yield, P/VP), without mixing in European Portuguese.
2. **Financial data competence** — interpret numerical tables, compare funds, identify trends, and not hallucinate missing data.
3. **Low operational cost** — the project is a personal portfolio running in production, so monthly cost must remain viable.

## Decision

**Chosen model: Gemini 3.5 Flash-Lite (Google)**

- Provider: Google (Vertex AI / AI Studio)
- Cost: $0.30/M input tokens, $2.50/M output tokens
- Context window: 1M tokens
- Observed average latency: 1,396ms

## Models Evaluated

| Model | Provider | Input $/M | Output $/M |
|---|---|---|---|
| Gemini 3.5 Flash-Lite | Google | $0.30 | $2.50 |
| Gemini 3.8 Flash | Google | $0.75 | $3.75 |
| Gemini 3.1 Pro Preview | Google | $2.00 | $12.00 |
| GPT-4o mini | OpenAI | $0.15 | $0.60 |
| Claude Haiku 4.5 | Anthropic | $0.80 | $4.00 |

## Evaluation Methodology

### Tool

We used [Promptfoo](https://promptfoo.dev/) (v0.125.1) — an open-source LLM evaluation tool that enables side-by-side comparison with automated assertions.

### Test Data

All tests use **real data** extracted from CVM (Brazilian Securities Commission) Structured Monthly Reports, available at [dados.cvm.gov.br](https://dados.cvm.gov.br/dataset/fii-doc-inf_mensal).

Data from 12 representative FIIs across different segments was used:

| Ticker | Fund | Segment |
|---|---|---|
| HGLG11 | Pátria Log FII | Logistics |
| BTLG11 | BTGP Logística FII | Logistics |
| XPLG11 | XP Log FII | Logistics |
| VILG11 | Vinci Logística FII | Logistics |
| BRCO11 | Bresco Logística FII | Logistics |
| XPML11 | XP Malls FII | Shopping Centers |
| VISC11 | Vinci Shopping Centers FII | Shopping Centers |
| HSML11 | HSI Malls FII | Shopping Centers |
| KNRI11 | Kinea Renda Imobiliária FII | Hybrid (Office + Logistics) |
| PVBI11 | VBI Prime FII | Office |
| MXRF11 | FII Maxi Renda | Paper (CRI — Real Estate Credit Instruments) |
| KNCR11 | Kinea Rendimentos Imobiliários FII | Paper (Post-fixed CRI) |

Data period: January 2025 through September 2026 (21 months).

### Test Cases

55 tests divided into 6 categories:

| Category | Count | What it tests |
|---|---|---|
| **Factual** | 15 | Extract specific data points: net assets, NAV/share, dividend yield, number of shareholders |
| **Comparative** | 12 | Compare funds by DY, net assets, segment, year-over-year |
| **Analytical** | 13 | Interpret trends, NAV drops, share issuances, accumulated DY |
| **Calculation** | 5 | Annualized DY, income in BRL, number of shares purchasable with R$X |
| **PT-BR Quality** | 7 | Portuguese quality, not hallucinating data, correct terminology |
| **Edge Cases** | 3 | Vague questions, out-of-scope questions, multiple questions in one |

### Metrics

- **Pass rate**: percentage of tests that passed all assertions (contains + llm-rubric)
- **Average score**: weighted average of assertion scores (0 to 1)
- **Average latency**: response time in milliseconds
- **Total cost**: actual cost in USD to run all 55 tests

### Assertions

Each test includes:
- **Content assertion** (`contains` / `contains-any`): verifies the response contains correct data
- **Quality assertion** (`llm-rubric`): a judge LLM evaluates whether the response meets qualitative criteria
- **Language assertion** (default on all tests): verifies the response is in Brazilian Portuguese

## Results

### Overall Results

| Model | Pass Rate | Score | Latency | Cost (55 tests) |
|---|---|---|---|---|
| **Gemini 3.5 Flash-Lite** | **87.3%** (48/55) | **0.942** | **1,396ms** | **$0.06** |
| Claude Haiku 4.5 | 83.6% (46/55) | 0.929 | 3,544ms | $0.15 |
| GPT-4o mini | 69.1% (38/55) | 0.862 | 4,326ms | ~$0.00* |
| Gemini 3.8 Flash | 54.5% (30/55) | 0.771 | 6,742ms | $0.21 |
| Gemini 3.1 Pro Preview | 38.2% (21/55) | 0.639 | 7,812ms | $0.72 |

*GPT-4o mini reported zero cost, likely due to promotional credits.

### Results by Category

| Category | Flash-Lite | Haiku 4.5 | GPT-4o mini | Gemini Flash | Gemini Pro |
|---|---|---|---|---|---|
| **Factual** (15) | **100%** | 93% | 93% | 93% | 73% |
| **Comparative** (12) | **83%** | 67% | 67% | 58% | 33% |
| **Analytical** (13) | **77%** | 69% | 54% | 15% | 8% |
| **Calculation** (5) | 80% | **100%** | 40% | 20% | 0% |
| **PT-BR** (7) | 86% | **100%** | 57% | 57% | 43% |
| **Edge Cases** (3) | **100%** | **100%** | **100%** | 67% | 67% |

### Error Analysis

**Gemini 3.1 Pro Preview**: despite being the most expensive model ($0.72 total, 12x more than Flash-Lite), it had the worst performance (38.2%). Many responses were truncated, and in some tests the model partially responded in English. Not recommended for this use case.

**Gemini 3.8 Flash**: intermediate performance but 5x slower than Flash-Lite and 3.5x more expensive, with no proportional quality gain.

**Claude Haiku 4.5**: second best overall, with standout performance in calculations (100%) and PT-BR quality (100%). However, it costs 2.5x more than Flash-Lite and is 2.5x slower.

**GPT-4o mini**: good at edge cases and factual tests, but weak in analytical and calculation tests.

## Accepted Trade-offs

1. **Calculations**: Flash-Lite passed 80% of calculation tests (4/5), versus 100% for Haiku. This is acceptable because heavy calculations (annualized DY, projections, sums) are performed in the application backend, not delegated to the LLM. The LLM interprets and explains the results.

2. **PT-BR quality**: Flash-Lite passed 86% of Portuguese tests (6/7), versus 100% for Haiku. The single failure was not using specific terms like "proventos" and "cotistas" in one response — an edge case that does not impact user experience in most scenarios.

3. **Cost vs. quality**: paying 2.5x more (Haiku) for 3.7 percentage points less error (87.3% vs 83.6%) does not justify the cost for a portfolio project. In production with high volume, this cost difference scales significantly.

## Tokenization Considerations

Brazilian Portuguese consumes approximately 35% more tokens than English on modern tokenizers. Gemini has the largest vocabulary among providers (256k tokens on SentencePiece), resulting in better tokenization efficiency for Portuguese — meaning the real cost per PT-BR text is proportionally lower on Gemini than on competitors.

To mitigate the extra tokenization cost, the application's system prompt is written in English (fixed part, sent on every request), while B3 data and the user's question remain in Portuguese.

## Considered Alternative: Two-Tier Architecture

An alternative evaluated was using two models: Flash-Lite for simple queries (80% of traffic) and a stronger model (Haiku or Gemini Pro) for complex analysis (20%). The results did not justify this complexity:

- Flash-Lite already passes 87% of tests without complexity distinction
- Gemini Pro, which would be the "premium tier" candidate on the same provider, had the worst overall performance
- The complexity of maintaining a model router does not compensate for the marginal gain

## Consequences

- The application exclusively uses Gemini 3.5 Flash-Lite via Vertex AI
- Estimated production cost: < $5/month for typical portfolio volumes
- Average latency of 1.4s, suitable for an interactive experience
- Calculations and aggregations are performed in the backend (Python/SQL), not delegated to the LLM
- The system prompt is maintained in English for token economy
- If volume grows significantly or the use case demands higher precision in calculations, this decision can be revisited with new tests

## How to Reproduce

```bash
# Install Promptfoo
npm install -g promptfoo

# Set API keys
export GOOGLE_API_KEY=your_key
export OPENAI_API_KEY=your_key
export ANTHROPIC_API_KEY=your_key

# Run evaluation
promptfoo eval

# View results
promptfoo view

# Export results
promptfoo eval -o results.json
```

Configuration files:
- `promptfooconfig.yaml` — model configuration and 55 test cases
- `docs/adr/001-llm-model-selection.md` — this document

## References

- [CVM Open Data — FII Monthly Reports](https://dados.cvm.gov.br/dataset/fii-doc-inf_mensal)
- [Promptfoo — LLM Evaluation Framework](https://promptfoo.dev/)
- [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Artificial Analysis — Multilingual Benchmark](https://artificialanalysis.ai/models/multilingual/portuguese)