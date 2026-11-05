from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Numeric, BigInteger, Integer, Date, DateTime, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from fii_analyzer.config import settings

class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

class FiiMarketPrice(TimestampMixin, Base):
    __tablename__ = 'fii_preco_mercado'

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    data_pregao: Mapped[date] = mapped_column(Date, primary_key=True)
    preco_abertura: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    preco_maximo: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    preco_minimo: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    preco_fechamento: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

class FiiFundoMensal(TimestampMixin, Base):
    __tablename__ = 'fii_fundo_mensal'

    cnpj_fundo: Mapped[str] = mapped_column(String(20), primary_key=True)
    data_referencia: Mapped[date] = mapped_column(Date, primary_key=True)
    versao: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_entrega: Mapped[date | None] = mapped_column(Date, nullable=True)
    tipo_fundo_classe: Mapped[str | None] = mapped_column(String(30), nullable=True)
    nome_fundo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    codigo_isin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    data_funcionamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    publico_alvo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantidade_cotas_emitidas: Mapped[Decimal | None] = mapped_column(Numeric(25, 8), nullable=True)
    fundo_exclusivo: Mapped[str | None] = mapped_column(String(1), nullable=True)
    cotistas_vinculo_familiar: Mapped[str | None] = mapped_column(String(1), nullable=True)
    mandato: Mapped[str | None] = mapped_column(String(50), nullable=True)
    segmento_atuacao: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tipo_gestao: Mapped[str | None] = mapped_column(String(30), nullable=True)
    prazo_duracao: Mapped[str | None] = mapped_column(String(30), nullable=True)
    data_prazo_duracao: Mapped[date | None] = mapped_column(Date, nullable=True)
    encerramento_exercicio_social: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mercado_negociacao_bolsa: Mapped[str | None] = mapped_column(String(1), nullable=True)
    mercado_negociacao_mbo: Mapped[str | None] = mapped_column(String(1), nullable=True)
    mercado_negociacao_mb: Mapped[str | None] = mapped_column(String(1), nullable=True)
    entidade_administradora_bvmf: Mapped[str | None] = mapped_column(String(1), nullable=True)
    entidade_administradora_cetip: Mapped[str | None] = mapped_column(String(1), nullable=True)
    nome_administrador: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cnpj_administrador: Mapped[str | None] = mapped_column(String(20), nullable=True)
    logradouro: Mapped[str | None] = mapped_column(String(200), nullable=True)
    numero: Mapped[str | None] = mapped_column(String(20), nullable=True)
    complemento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bairro: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[str | None] = mapped_column(String(2), nullable=True)
    cep: Mapped[str | None] = mapped_column(String(10), nullable=True)
    telefone1: Mapped[str | None] = mapped_column(String(20), nullable=True)
    telefone2: Mapped[str | None] = mapped_column(String(20), nullable=True)
    telefone3: Mapped[str | None] = mapped_column(String(20), nullable=True)
    site: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)


class FiiFundoAnual(TimestampMixin, Base):
    __tablename__ = 'fii_fundo_anual'

    cnpj_fundo: Mapped[str] = mapped_column(String(20), primary_key=True)
    data_referencia: Mapped[date] = mapped_column(Date, primary_key=True)
    versao: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_entrega: Mapped[date | None] = mapped_column(Date, nullable=True)
    tipo_fundo_classe: Mapped[str | None] = mapped_column(String(30), nullable=True)
    nome_fundo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    codigo_isin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    data_funcionamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    publico_alvo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantidade_cotas_emitidas: Mapped[Decimal | None] = mapped_column(Numeric(25, 8), nullable=True)
    fundo_exclusivo: Mapped[str | None] = mapped_column(String(1), nullable=True)
    mandato: Mapped[str | None] = mapped_column(String(50), nullable=True)
    segmento_atuacao: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tipo_gestao: Mapped[str | None] = mapped_column(String(30), nullable=True)
    prazo_duracao: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mercado_negociacao_bolsa: Mapped[str | None] = mapped_column(String(1), nullable=True)
    nome_administrador: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cnpj_administrador: Mapped[str | None] = mapped_column(String(20), nullable=True)

class FiiMetricaMensal(TimestampMixin, Base):
    __tablename__ = 'fii_metrica_mensal'

    cnpj_fundo: Mapped[str] = mapped_column(String(20), primary_key=True)
    data_referencia: Mapped[date] = mapped_column(Date, primary_key=True)
    versao: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_informacao_numero_cotistas: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_numero_cotistas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_pessoa_fisica: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_pessoa_juridica_nao_financeira: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_banco_comercial: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_corretora_distribuidora: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_outras_pessoas_juridicas_financeira: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_investidores_nao_residentes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_entidade_aberta_previdencia_complementar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_entidade_fechada_previdencia_complementar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_regime_proprio_previdencia_servidores_publicos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_sociedade_seguradora_resseguradora: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_sociedade_capitalizacao_arrendamento_mercantil: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_fii: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_outros_fundos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_distribuidores_fundo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotistas_outros_tipos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valor_ativo: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    patrimonio_liquido: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cotas_emitidas: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    valor_patrimonial_cotas: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    percentual_despesas_taxa_administracao: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    percentual_despesas_agente_custodiante: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    percentual_rentabilidade_efetiva_mes: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    percentual_rentabilidade_patrimonial_mes: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    percentual_dividend_yield_mes: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    percentual_amortizacao_cotas_mes: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)


class FiiBalancoMensal(TimestampMixin, Base):
    __tablename__ = 'fii_balanco_mensal'

    cnpj_fundo: Mapped[str] = mapped_column(String(20), primary_key=True)
    data_referencia: Mapped[date] = mapped_column(Date, primary_key=True)
    versao: Mapped[int] = mapped_column(Integer, primary_key=True)
    total_necessidades_liquidez: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    disponibilidades: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    titulos_publicos: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    titulos_privados: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    fundos_renda_fixa: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    total_investido: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    direitos_bens_imoveis: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    terrenos: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    imoveis_renda_acabados: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    imoveis_renda_construcao: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    imoveis_venda_acabados: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    imoveis_venda_construcao: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    outros_direitos_reais: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    acoes: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    debentures: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    bonus_subscricao: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    certificados_deposito_valores_mobiliarios: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cedulas_debentures: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    fundo_acoes: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    fip: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    fii: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    fdic: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    outras_cotas_fi: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    notas_promissorias: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    acoes_sociedades_atividades_fii: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cotas_sociedades_atividades_fii: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cepac: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cri: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cri_cra: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    letras_hipotecarias: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    lci: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    lci_lca: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    lig: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    outros_valores_mobliarios: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    valores_receber: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    contas_receber_aluguel: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    contas_receber_venda_imoveis: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    outros_valores_receber: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    rendimentos_distribuir: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    taxa_administracao_pagar: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    taxa_performance_pagar: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    obrigacoes_aquisicao_imoveis: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    adiantamento_venda_imoveis: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    adiantamento_alugueis: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    obrigacoes_securitizacao_recebiveis: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    instrumentos_financeiros_derivativos: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    provisoes_contigencias: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    outros_valores_pagar: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    total_passivo: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)


class FiiNarrativaAnual(TimestampMixin, Base):
    __tablename__ = 'fii_narrativa_anual'

    cnpj_fundo: Mapped[str] = mapped_column(String(20), primary_key=True)
    data_referencia: Mapped[date] = mapped_column(Date, primary_key=True)
    nome_gestor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nome_custodiante: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nome_auditor_independente: Mapped[str | None] = mapped_column(String(200), nullable=True)
    conjuntura_economica_periodo_findo: Mapped[str | None] = mapped_column(Text, nullable=True)
    resultado_exercicio_findo: Mapped[str | None] = mapped_column(Text, nullable=True)
    perspectiva_periodo_seguinte: Mapped[str | None] = mapped_column(Text, nullable=True)
    programa_investimentos_exercicio_seguinte: Mapped[str | None] = mapped_column(Text, nullable=True)
    criterios_avaliacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    politica_remuneracao: Mapped[str | None] = mapped_column(Text, nullable=True)


class FiiTransacaoAnual(TimestampMixin, Base):
    __tablename__ = 'fii_transacao_anual'

    cnpj_fundo: Mapped[str] = mapped_column(String(20), primary_key=True)
    data_referencia: Mapped[date] = mapped_column(Date, primary_key=True)
    ativo_negociado: Mapped[str] = mapped_column(String(300), primary_key=True)
    natureza_transacao: Mapped[str] = mapped_column(String(50), primary_key=True)
    data_transacao: Mapped[date] = mapped_column(Date, primary_key=True)
    valor_envolvido: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    data_assembleia: Mapped[date | None] = mapped_column(Date, nullable=True)
    contraparte: Mapped[str | None] = mapped_column(String(300), nullable=True)


class FiiValorAtivoAnual(TimestampMixin, Base):
    __tablename__ = 'fii_valor_ativo_anual'

    cnpj_fundo: Mapped[str] = mapped_column(String(20), primary_key=True)
    data_referencia: Mapped[date] = mapped_column(Date, primary_key=True)
    nome_ativo: Mapped[str] = mapped_column(String(300), primary_key=True)
    valor: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    valor_justo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    percentual_valorizacao_desvalorizacao: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)


class FiiAquisicaoAnual(TimestampMixin, Base):
    __tablename__ = 'fii_aquisicao_anual'

    cnpj_fundo: Mapped[str] = mapped_column(String(20), primary_key=True)
    data_referencia: Mapped[date] = mapped_column(Date, primary_key=True)
    nome_ativo: Mapped[str] = mapped_column(String(1500), primary_key=True)
    objetivos: Mapped[str | None] = mapped_column(String(200), nullable=True)
    montante_investido: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    origem_recursos: Mapped[str | None] = mapped_column(String(150), nullable=True)


class FiiDistribuicaoCotistaAnual(TimestampMixin, Base):
    __tablename__ = 'fii_distribuicao_cotista_anual'

    cnpj_fundo: Mapped[str] = mapped_column(String(20), primary_key=True)
    data_referencia: Mapped[date] = mapped_column(Date, primary_key=True)
    numero_cotistas_faixa_ate_5: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotas_detidas_faixa_ate_5: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    percentual_cotas_detidas_faixa_ate_5: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pf_faixa_ate_5: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pj_faixa_ate_5: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    numero_cotistas_faixa_5a10: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotas_detidas_faixa_5a10: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    percentual_cotas_detidas_faixa_5a10: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pf_faixa_5a10: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pj_faixa_5a10: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    numero_cotistas_faixa_10a15: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotas_detidas_faixa_10a15: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    percentual_cotas_detidas_faixa_10a15: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pf_faixa_10a15: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pj_faixa_10a15: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    numero_cotistas_faixa_15a20: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotas_detidas_faixa_15a20: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    percentual_cotas_detidas_faixa_15a20: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pf_faixa_15a20: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pj_faixa_15a20: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    numero_cotistas_faixa_20a30: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotas_detidas_faixa_20a30: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    percentual_cotas_detidas_faixa_20a30: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pf_faixa_20a30: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pj_faixa_20a30: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    numero_cotistas_faixa_30a40: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotas_detidas_faixa_30a40: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    percentual_cotas_detidas_faixa_30a40: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pf_faixa_30a40: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pj_faixa_30a40: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    numero_cotistas_faixa_40a50: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotas_detidas_faixa_40a50: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    percentual_cotas_detidas_faixa_40a50: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pf_faixa_40a50: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pj_faixa_40a50: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    numero_cotistas_faixa_acima_50: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_cotas_detidas_faixa_acima_50: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    percentual_cotas_detidas_faixa_acima_50: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pf_faixa_acima_50: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    percentual_detido_pj_faixa_acima_50: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)


class FiiProcessoAnual(TimestampMixin, Base):
    __tablename__ = 'fii_processo_anual'

    cnpj_fundo: Mapped[str] = mapped_column(String(20), primary_key=True)
    data_referencia: Mapped[date] = mapped_column(Date, primary_key=True)
    numero_processo: Mapped[str] = mapped_column(String(100), primary_key=True)
    juizo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    instancia: Mapped[str | None] = mapped_column(String(150), nullable=True)
    data_instauracao: Mapped[date | None] = mapped_column(Date, nullable=True)
    valor_causa: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    partes_processo: Mapped[str | None] = mapped_column(Text, nullable=True)
    chance_perda: Mapped[str | None] = mapped_column(String(20), nullable=True)
    principais_fatos: Mapped[str | None] = mapped_column(Text, nullable=True)
    analise_impacto_perda: Mapped[str | None] = mapped_column(Text, nullable=True)

engine = create_engine(settings.database_url)

def create_tables():
    Base.metadata.create_all(engine)
