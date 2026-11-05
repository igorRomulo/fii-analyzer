# CVM Data Ingestion

## Data Source

Data is sourced from CVM's open data portal:
`https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS`

ZIP files follow the pattern:
- `inf_mensal_fii_YYYY.zip` — monthly data
- `inf_anual_fii_YYYY.zip` — annual data

Coverage: 2016 to 2026.

## CSV Format

- Encoding: `latin-1`
- Delimiter: `;` (semicolon)
- Schema break in 2025: columns `CNPJ_Fundo` and `Nome_Fundo` were renamed to `CNPJ_Fundo_Classe` and `Nome_Fundo_Classe`, and new columns were added (`Tipo_Fundo_Classe`, `CRI_CRA`, `LCI_LCA`)

## CSV to Table Mapping

DB column names match the CSV column names exactly, lowercased (e.g., `Numero_Cotistas_Pessoa_Fisica` -> `numero_cotistas_pessoa_fisica`). CSV typos are preserved (e.g., `Outros_Valores_Mobliarios`, `Provisoes_Contigencias`).

### `inf_mensal_fii_geral_YYYY.csv` -> `fii_fundo_mensal`

Monthly fund registry.

| CSV Column | DB Column | Type |
|---|---|---|
| `CNPJ_Fundo` | `cnpj_fundo` | String(20) **PK** |
| `Data_Referencia` | `data_referencia` | Date **PK** |
| `Versao` | `versao` | Integer **PK** |
| `Data_Entrega` | `data_entrega` | Date |
| `Tipo_Fundo_Classe` | `tipo_fundo_classe` | String(30) |
| `Nome_Fundo` | `nome_fundo` | String(200) |
| `Codigo_ISIN` | `codigo_isin` | String(20) |
| `Data_Funcionamento` | `data_funcionamento` | Date |
| `Publico_Alvo` | `publico_alvo` | String(100) |
| `Quantidade_Cotas_Emitidas` | `quantidade_cotas_emitidas` | Numeric(25,8) |
| `Fundo_Exclusivo` | `fundo_exclusivo` | String(1) |
| `Cotistas_Vinculo_Familiar` | `cotistas_vinculo_familiar` | String(1) |
| `Mandato` | `mandato` | String(50) |
| `Segmento_Atuacao` | `segmento_atuacao` | String(50) |
| `Tipo_Gestao` | `tipo_gestao` | String(30) |
| `Prazo_Duracao` | `prazo_duracao` | String(30) |
| `Data_Prazo_Duracao` | `data_prazo_duracao` | Date |
| `Encerramento_Exercicio_Social` | `encerramento_exercicio_social` | String(50) |
| `Mercado_Negociacao_Bolsa` | `mercado_negociacao_bolsa` | String(1) |
| `Mercado_Negociacao_MBO` | `mercado_negociacao_mbo` | String(1) |
| `Mercado_Negociacao_MB` | `mercado_negociacao_mb` | String(1) |
| `Entidade_Administradora_BVMF` | `entidade_administradora_bvmf` | String(1) |
| `Entidade_Administradora_CETIP` | `entidade_administradora_cetip` | String(1) |
| `Nome_Administrador` | `nome_administrador` | String(200) |
| `CNPJ_Administrador` | `cnpj_administrador` | String(20) |
| `Logradouro` | `logradouro` | String(200) |
| `Numero` | `numero` | String(20) |
| `Complemento` | `complemento` | String(100) |
| `Bairro` | `bairro` | String(100) |
| `Cidade` | `cidade` | String(100) |
| `Estado` | `estado` | String(2) |
| `CEP` | `cep` | String(10) |
| `Telefone1` | `telefone1` | String(20) |
| `Telefone2` | `telefone2` | String(20) |
| `Telefone3` | `telefone3` | String(20) |
| `Site` | `site` | String(200) |
| `Email` | `email` | String(200) |

### `inf_anual_fii_geral_YYYY.csv` -> `fii_fundo_anual`

Annual fund registry. Subset of `fii_fundo_mensal` columns (no address, contact, or extra market/entity fields).

| CSV Column | DB Column | Type |
|---|---|---|
| `CNPJ_Fundo` | `cnpj_fundo` | String(20) **PK** |
| `Data_Referencia` | `data_referencia` | Date **PK** |
| `Versao` | `versao` | Integer **PK** |
| `Data_Entrega` | `data_entrega` | Date |
| `Tipo_Fundo_Classe` | `tipo_fundo_classe` | String(30) |
| `Nome_Fundo` | `nome_fundo` | String(200) |
| `Codigo_ISIN` | `codigo_isin` | String(20) |
| `Data_Funcionamento` | `data_funcionamento` | Date |
| `Publico_Alvo` | `publico_alvo` | String(100) |
| `Quantidade_Cotas_Emitidas` | `quantidade_cotas_emitidas` | Numeric(25,8) |
| `Fundo_Exclusivo` | `fundo_exclusivo` | String(1) |
| `Mandato` | `mandato` | String(50) |
| `Segmento_Atuacao` | `segmento_atuacao` | String(50) |
| `Tipo_Gestao` | `tipo_gestao` | String(30) |
| `Prazo_Duracao` | `prazo_duracao` | String(30) |
| `Mercado_Negociacao_Bolsa` | `mercado_negociacao_bolsa` | String(1) |
| `Nome_Administrador` | `nome_administrador` | String(200) |
| `CNPJ_Administrador` | `cnpj_administrador` | String(20) |

### `inf_mensal_fii_complemento_YYYY.csv` -> `fii_metrica_mensal`

Monthly metrics: shareholder counts, financial indicators.

| CSV Column | DB Column | Type |
|---|---|---|
| `CNPJ_Fundo` | `cnpj_fundo` | String(20) **PK** |
| `Data_Referencia` | `data_referencia` | Date **PK** |
| `Versao` | `versao` | Integer **PK** |
| `Data_Informacao_Numero_Cotistas` | `data_informacao_numero_cotistas` | Date |
| `Total_Numero_Cotistas` | `total_numero_cotistas` | Integer |
| `Numero_Cotistas_Pessoa_Fisica` | `numero_cotistas_pessoa_fisica` | Integer |
| `Numero_Cotistas_Pessoa_Juridica_Nao_Financeira` | `numero_cotistas_pessoa_juridica_nao_financeira` | Integer |
| `Numero_Cotistas_Banco_Comercial` | `numero_cotistas_banco_comercial` | Integer |
| `Numero_Cotistas_Corretora_Distribuidora` | `numero_cotistas_corretora_distribuidora` | Integer |
| `Numero_Cotistas_Outras_Pessoas_Juridicas_Financeira` | `numero_cotistas_outras_pessoas_juridicas_financeira` | Integer |
| `Numero_Cotistas_Investidores_Nao_Residentes` | `numero_cotistas_investidores_nao_residentes` | Integer |
| `Numero_Cotistas_Entidade_Aberta_Previdencia_Complementar` | `numero_cotistas_entidade_aberta_previdencia_complementar` | Integer |
| `Numero_Cotistas_Entidade_Fechada_Previdencia_Complementar` | `numero_cotistas_entidade_fechada_previdencia_complementar` | Integer |
| `Numero_Cotistas_Regime_Proprio_Previdencia_Servidores_Publicos` | `numero_cotistas_regime_proprio_previdencia_servidores_publicos` | Integer |
| `Numero_Cotistas_Sociedade_Seguradora_Resseguradora` | `numero_cotistas_sociedade_seguradora_resseguradora` | Integer |
| `Numero_Cotistas_Sociedade_Capitalizacao_Arrendamento_Mercantil` | `numero_cotistas_sociedade_capitalizacao_arrendamento_mercantil` | Integer |
| `Numero_Cotistas_FII` | `numero_cotistas_fii` | Integer |
| `Numero_Cotistas_Outros_Fundos` | `numero_cotistas_outros_fundos` | Integer |
| `Numero_Cotistas_Distribuidores_Fundo` | `numero_cotistas_distribuidores_fundo` | Integer |
| `Numero_Cotistas_Outros_Tipos` | `numero_cotistas_outros_tipos` | Integer |
| `Valor_Ativo` | `valor_ativo` | Numeric(18,2) |
| `Patrimonio_Liquido` | `patrimonio_liquido` | Numeric(18,2) |
| `Cotas_Emitidas` | `cotas_emitidas` | Numeric(18,2) |
| `Valor_Patrimonial_Cotas` | `valor_patrimonial_cotas` | Numeric(18,8) |
| `Percentual_Despesas_Taxa_Administracao` | `percentual_despesas_taxa_administracao` | Numeric(20,8) |
| `Percentual_Despesas_Agente_Custodiante` | `percentual_despesas_agente_custodiante` | Numeric(20,8) |
| `Percentual_Rentabilidade_Efetiva_Mes` | `percentual_rentabilidade_efetiva_mes` | Numeric(20,8) |
| `Percentual_Rentabilidade_Patrimonial_Mes` | `percentual_rentabilidade_patrimonial_mes` | Numeric(20,8) |
| `Percentual_Dividend_Yield_Mes` | `percentual_dividend_yield_mes` | Numeric(20,8) |
| `Percentual_Amortizacao_Cotas_Mes` | `percentual_amortizacao_cotas_mes` | Numeric(20,8) |

### `inf_mensal_fii_ativo_passivo_YYYY.csv` -> `fii_balanco_mensal`

Monthly balance sheet: liquidity, real estate assets, securities, receivables, liabilities.

| CSV Column | DB Column | Type |
|---|---|---|
| `CNPJ_Fundo` | `cnpj_fundo` | String(20) **PK** |
| `Data_Referencia` | `data_referencia` | Date **PK** |
| `Versao` | `versao` | Integer **PK** |
| `Total_Necessidades_Liquidez` | `total_necessidades_liquidez` | Numeric(18,2) |
| `Disponibilidades` | `disponibilidades` | Numeric(18,2) |
| `Titulos_Publicos` | `titulos_publicos` | Numeric(18,2) |
| `Titulos_Privados` | `titulos_privados` | Numeric(18,2) |
| `Fundos_Renda_Fixa` | `fundos_renda_fixa` | Numeric(18,2) |
| `Total_Investido` | `total_investido` | Numeric(18,2) |
| `Direitos_Bens_Imoveis` | `direitos_bens_imoveis` | Numeric(18,2) |
| `Terrenos` | `terrenos` | Numeric(18,2) |
| `Imoveis_Renda_Acabados` | `imoveis_renda_acabados` | Numeric(18,2) |
| `Imoveis_Renda_Construcao` | `imoveis_renda_construcao` | Numeric(18,2) |
| `Imoveis_Venda_Acabados` | `imoveis_venda_acabados` | Numeric(18,2) |
| `Imoveis_Venda_Construcao` | `imoveis_venda_construcao` | Numeric(18,2) |
| `Outros_Direitos_Reais` | `outros_direitos_reais` | Numeric(18,2) |
| `Acoes` | `acoes` | Numeric(18,2) |
| `Debentures` | `debentures` | Numeric(18,2) |
| `Bonus_Subscricao` | `bonus_subscricao` | Numeric(18,2) |
| `Certificados_Deposito_Valores_Mobiliarios` | `certificados_deposito_valores_mobiliarios` | Numeric(18,2) |
| `Cedulas_Debentures` | `cedulas_debentures` | Numeric(18,2) |
| `Fundo_Acoes` | `fundo_acoes` | Numeric(18,2) |
| `FIP` | `fip` | Numeric(18,2) |
| `FII` | `fii` | Numeric(18,2) |
| `FDIC` | `fdic` | Numeric(18,2) |
| `Outras_Cotas_FI` | `outras_cotas_fi` | Numeric(18,2) |
| `Notas_Promissorias` | `notas_promissorias` | Numeric(18,2) |
| `Acoes_Sociedades_Atividades_FII` | `acoes_sociedades_atividades_fii` | Numeric(18,2) |
| `Cotas_Sociedades_Atividades_FII` | `cotas_sociedades_atividades_fii` | Numeric(18,2) |
| `CEPAC` | `cepac` | Numeric(18,2) |
| `CRI` | `cri` | Numeric(18,2) |
| `CRI_CRA` | `cri_cra` | Numeric(18,2) |
| `Letras_Hipotecarias` | `letras_hipotecarias` | Numeric(18,2) |
| `LCI` | `lci` | Numeric(18,2) |
| `LCI_LCA` | `lci_lca` | Numeric(18,2) |
| `LIG` | `lig` | Numeric(18,2) |
| `Outros_Valores_Mobliarios` | `outros_valores_mobliarios` | Numeric(18,2) |
| `Valores_Receber` | `valores_receber` | Numeric(18,2) |
| `Contas_Receber_Aluguel` | `contas_receber_aluguel` | Numeric(18,2) |
| `Contas_Receber_Venda_Imoveis` | `contas_receber_venda_imoveis` | Numeric(18,2) |
| `Outros_Valores_Receber` | `outros_valores_receber` | Numeric(18,2) |
| `Rendimentos_Distribuir` | `rendimentos_distribuir` | Numeric(18,2) |
| `Taxa_Administracao_Pagar` | `taxa_administracao_pagar` | Numeric(18,2) |
| `Taxa_Performance_Pagar` | `taxa_performance_pagar` | Numeric(18,2) |
| `Obrigacoes_Aquisicao_Imoveis` | `obrigacoes_aquisicao_imoveis` | Numeric(18,2) |
| `Adiantamento_Venda_Imoveis` | `adiantamento_venda_imoveis` | Numeric(18,2) |
| `Adiantamento_Alugueis` | `adiantamento_alugueis` | Numeric(18,2) |
| `Obrigacoes_Securitizacao_Recebiveis` | `obrigacoes_securitizacao_recebiveis` | Numeric(18,2) |
| `Instrumentos_Financeiros_Derivativos` | `instrumentos_financeiros_derivativos` | Numeric(18,2) |
| `Provisoes_Contigencias` | `provisoes_contigencias` | Numeric(18,2) |
| `Outros_Valores_Pagar` | `outros_valores_pagar` | Numeric(18,2) |
| `Total_Passivo` | `total_passivo` | Numeric(18,2) |

### `inf_anual_fii_complemento_YYYY.csv` -> `fii_narrativa_anual`

Manager narratives: economic outlook, results, strategy, investment program.

| CSV Column | DB Column | Type |
|---|---|---|
| `CNPJ_Fundo` | `cnpj_fundo` | String(20) **PK** |
| `Data_Referencia` | `data_referencia` | Date **PK** |
| `Nome_Gestor` | `nome_gestor` | String(200) |
| `Nome_Custodiante` | `nome_custodiante` | String(200) |
| `Nome_Auditor_Independente` | `nome_auditor_independente` | String(200) |
| `Conjuntura_Economica_Periodo_Findo` | `conjuntura_economica_periodo_findo` | Text |
| `Resultado_Exercicio_Findo` | `resultado_exercicio_findo` | Text |
| `Perspectiva_Periodo_Seguinte` | `perspectiva_periodo_seguinte` | Text |
| `Programa_Investimentos_Exercicio_Seguinte` | `programa_investimentos_exercicio_seguinte` | Text |
| `Criterios_Avaliacao` | `criterios_avaliacao` | Text |
| `Politica_Remuneracao` | `politica_remuneracao` | Text |

### `inf_anual_fii_ativo_transacao_YYYY.csv` -> `fii_transacao_anual`

Asset transactions during the period.

| CSV Column | DB Column | Type |
|---|---|---|
| `CNPJ_Fundo` | `cnpj_fundo` | String(20) **PK** |
| `Data_Referencia` | `data_referencia` | Date **PK** |
| `Ativo_Negociado` | `ativo_negociado` | String(300) **PK** |
| `Natureza_Transacao` | `natureza_transacao` | String(50) **PK** |
| `Data_Transacao` | `data_transacao` | Date **PK** |
| `Valor_Envolvido` | `valor_envolvido` | Numeric(18,2) |
| `Data_Assembleia` | `data_assembleia` | Date |
| `Contraparte` | `contraparte` | String(300) |

### `inf_anual_fii_ativo_valor_contabil_YYYY.csv` -> `fii_valor_ativo_anual`

Asset book values.

| CSV Column | DB Column | Type |
|---|---|---|
| `CNPJ_Fundo` | `cnpj_fundo` | String(20) **PK** |
| `Data_Referencia` | `data_referencia` | Date **PK** |
| `Nome_Ativo` | `nome_ativo` | String(300) **PK** |
| `Valor` | `valor` | Numeric(18,2) |
| `Valor_Justo` | `valor_justo` | String(10) |
| `Percentual_Valorizacao_Desvalorizacao` | `percentual_valorizacao_desvalorizacao` | Numeric(20,8) |

### `inf_anual_fii_ativo_adquirido_YYYY.csv` -> `fii_aquisicao_anual`

Assets acquired during the period.

| CSV Column | DB Column | Type |
|---|---|---|
| `CNPJ_Fundo` | `cnpj_fundo` | String(20) **PK** |
| `Data_Referencia` | `data_referencia` | Date **PK** |
| `Nome_Ativo` | `nome_ativo` | String(1500) **PK** |
| `Objetivos` | `objetivos` | String(200) |
| `Montante_Investido` | `montante_investido` | Numeric(18,2) |
| `Origem_Recursos` | `origem_recursos` | String(150) |

### `inf_anual_fii_distribuicao_cotistas_YYYY.csv` -> `fii_distribuicao_cotista_anual`

Shareholder distribution by ownership bracket. Each bracket (0-5%, 5-10%, ..., >50%) has 5 columns.

| CSV Column | DB Column | Type |
|---|---|---|
| `CNPJ_Fundo` | `cnpj_fundo` | String(20) **PK** |
| `Data_Referencia` | `data_referencia` | Date **PK** |
| `Numero_Cotistas_Faixa_{bracket}` | `numero_cotistas_faixa_{bracket}` | Integer |
| `Numero_Cotas_Detidas_Faixa_{bracket}` | `numero_cotas_detidas_faixa_{bracket}` | BigInteger |
| `Percentual_Cotas_Detidas_Faixa_{bracket}` | `percentual_cotas_detidas_faixa_{bracket}` | Numeric(16,6) |
| `Percentual_Detido_PF_Faixa_{bracket}` | `percentual_detido_pf_faixa_{bracket}` | Numeric(16,6) |
| `Percentual_Detido_PJ_Faixa_{bracket}` | `percentual_detido_pj_faixa_{bracket}` | Numeric(16,6) |

Brackets: `Ate_5` (0-5%), `5a10`, `10a15`, `15a20`, `20a30`, `30a40`, `40a50`, `Acima_50` (>50%)

### `inf_anual_fii_processo_YYYY.csv` -> `fii_processo_anual`

Fund lawsuits.

| CSV Column | DB Column | Type |
|---|---|---|
| `CNPJ_Fundo` | `cnpj_fundo` | String(20) **PK** |
| `Data_Referencia` | `data_referencia` | Date **PK** |
| `Numero_Processo` | `numero_processo` | String(100) **PK** |
| `Juizo` | `juizo` | String(200) |
| `Instancia` | `instancia` | String(150) |
| `Data_Instauracao` | `data_instauracao` | Date |
| `Valor_Causa` | `valor_causa` | Numeric(18,2) |
| `Partes_Processo` | `partes_processo` | Text |
| `Chance_Perda` | `chance_perda` | String(20) |
| `Principais_Fatos` | `principais_fatos` | Text |
| `Analise_Impacto_Perda` | `analise_impacto_perda` | Text |

### `fii_preco_mercado` (no CSV mapping)

Market prices from B3. Not populated by CVM ZIPs.

| DB Column | Type |
|---|---|
| `ticker` | String(10) **PK** |
| `data_pregao` | Date **PK** |
| `preco_abertura` | Numeric(12,2) |
| `preco_maximo` | Numeric(12,2) |
| `preco_minimo` | Numeric(12,2) |
| `preco_fechamento` | Numeric(12,2) |
| `volume` | BigInteger |

## Audit Columns

All tables include:
- `created_at` (TIMESTAMPTZ) — timestamp of the first insert
- `updated_at` (TIMESTAMPTZ) — timestamp of the last update

## Load Strategy

- **Upsert** via `INSERT ... ON CONFLICT DO UPDATE`: new records are inserted, existing ones are updated
- **Batch** of 1000 rows with row-by-row fallback on error
- **Deduplication** within batch: when duplicate PK rows exist in the same batch, only the last occurrence is kept
- **Required field lookup**: empty `nome_fundo` and `nome_ativo` are resolved by querying other records with the same CNPJ

## Commands

```bash
# Full seed (all years)
python -m fii_analyzer.ingestion.migrate seed --data-dir /path/to/zips --env local

# Incremental update (latest monthly + annual ZIP only)
python -m fii_analyzer.ingestion.migrate update --data-dir /path/to/zips --env prod
```

## Processing Order

ZIPs are processed chronologically (by year), with monthly before annual. This ensures `fii_fundo_mensal` data already exists when annual files attempt to resolve `nome_fundo` via lookup.
