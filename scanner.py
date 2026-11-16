"""
Módulo de Valuation Fundamentalista Segmentado, Setores Seguros (BESST), FIIs, ETFs e Scanner Técnico:
- Valuation Segmentado: Modelo de Gordon Dinâmico com trava de Payout (Bancos/Seguradoras), Banda P/VP Papel vs Tijolo (FIIs), MM200/RSI/Tendência (ETFs) e Graham (BESST Tradicional)
- Preço Teto de Bazin via Mediana (3 a 5 anos) com Haircut Seletivo de JCP (10% Bancos / 0% Seguradoras)
- Score de Segurança específico por classe (Ações Não-Financeiras, Bancos/Seguradoras, FIIs, ETFs)
- RSI / IFR de 14 Períodos com qualificação de Risco (Sobrevenda de Elite vs Alto Risco)
- Integração com SanityGate (validar_dados_yfinance)
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Sequence

from config import (
    UNIVERSO_BESST,
    UNIVERSO_FIIS,
    UNIVERSO_ETFS,
    UNIVERSO_BDRS,
    UNIVERSO_CRESCIMENTO,
    BANCOS_JCP,
    SEGURADORAS_ISENTAS,
    FIIS_PAPEL,
    FIIS_TIJOLO,
)
from data_engine import (
    obter_info_ativo, obter_infos_multiplos, obter_dados_macro, baixar_historico_multiplo, validar_dados_yfinance
)


def _precarregar_infos_paralelo(tickers: Sequence[str]) -> None:
    """Pré-carrega informações fundamentalistas e cotações em paralelo (ThreadPoolExecutor) quando não estiver em mock."""
    if getattr(obter_info_ativo, "__module__", "") == "data_engine":
        obter_infos_multiplos(list(tickers), max_workers=8)

BANCOS_E_SEGURADORAS_TICKERS = set(BANCOS_JCP) | set(SEGURADORAS_ISENTAS) | {"ITUB3", "BBDC3", "PSSA3", "IRBR3"}
SET_BANCOS_JCP = set(BANCOS_JCP) | {"ITUB3", "BBDC3"}
SET_SEGURADORAS_ISENTAS = set(SEGURADORAS_ISENTAS) | {"PSSA3"}
SET_FIIS_PAPEL = set(FIIS_PAPEL) | {"MXRF11"}
SET_FIIS_TIJOLO = set(FIIS_TIJOLO) | {"VISC11", "XPLG11"}
SET_ETFS = {str(t).replace(".SA", "").strip().upper() for t in UNIVERSO_ETFS}
SET_BDRS = {str(t).replace(".SA", "").strip().upper() for t in UNIVERSO_BDRS}

MAPA_SAZONALIDADE_PROVENTOS = {
    # FIIs (Pagamento Mensal Recorrente - Todos os 12 meses)
    "HGLG11": {"meses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "freq": "Mensal", "tipo": "FII Logística"},
    "KNCR11": {"meses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "freq": "Mensal", "tipo": "FII Papel / CDI"},
    "BTLG11": {"meses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "freq": "Mensal", "tipo": "FII Logística"},
    "XPML11": {"meses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "freq": "Mensal", "tipo": "FII Shoppings"},
    "KNIP11": {"meses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "freq": "Mensal", "tipo": "FII Papel / IPCA"},
    "MXRF11": {"meses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "freq": "Mensal", "tipo": "FII Híbrido / Papel"},
    "VISC11": {"meses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "freq": "Mensal", "tipo": "FII Shoppings"},
    "XPLG11": {"meses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "freq": "Mensal", "tipo": "FII Logística"},
    # Bancos (Pagamento Mensal de JCP / Recorrente)
    "ITUB4": {"meses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "freq": "Mensal + Trimestral", "tipo": "Banco Privado"},
    "ITUB3": {"meses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "freq": "Mensal + Trimestral", "tipo": "Banco Privado"},
    "BBDC4": {"meses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "freq": "Mensal + Semestral", "tipo": "Banco Privado"},
    "BBDC3": {"meses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "freq": "Mensal + Semestral", "tipo": "Banco Privado"},
    "BBAS3": {"meses": [2, 3, 5, 6, 8, 9, 11, 12], "freq": "8x ao ano (Estatutário)", "tipo": "Banco Público"},
    "SANB11": {"meses": [2, 5, 8, 11], "freq": "Trimestral", "tipo": "Banco Privado"},
    # Elétricas, Saneamento, Seguros e Telecom (Sazonalidade Histórica B3)
    "TAEE11": {"meses": [5, 8, 11], "freq": "Trimestral (Mai/Ago/Nov)", "tipo": "Transmissão"},
    "TAEE4": {"meses": [5, 8, 11], "freq": "Trimestral (Mai/Ago/Nov)", "tipo": "Transmissão"},
    "TAEE3": {"meses": [5, 8, 11], "freq": "Trimestral (Mai/Ago/Nov)", "tipo": "Transmissão"},
    "EGIE3": {"meses": [5, 8, 12], "freq": "Quadrimestral", "tipo": "Geração"},
    "ISAE4": {"meses": [5, 9, 12], "freq": "Sazonal", "tipo": "Transmissão"},
    "CPFE3": {"meses": [5, 10, 12], "freq": "Semestral / Anual", "tipo": "Distribuição/Geração"},
    "CMIG4": {"meses": [6, 12], "freq": "Semestral", "tipo": "Integrada"},
    "SBSP3": {"meses": [6, 12], "freq": "Semestral", "tipo": "Saneamento"},
    "SAPR11": {"meses": [6, 12], "freq": "Semestral", "tipo": "Saneamento"},
    "CSMG3": {"meses": [3, 6, 9, 12], "freq": "Trimestral", "tipo": "Saneamento"},
    "BBSE3": {"meses": [2, 8], "freq": "Semestral (Fev/Ago)", "tipo": "Seguros"},
    "CXSE3": {"meses": [5, 8, 11], "freq": "Trimestral (Mai/Ago/Nov)", "tipo": "Seguros"},
    "VIVT3": {"meses": [4, 7, 10, 12], "freq": "Trimestral", "tipo": "Telecomunicações"},
    "WEGE3": {"meses": [3, 8], "freq": "Semestral (Mar/Ago)", "tipo": "Bens de Capital"},
    "VALE3": {"meses": [3, 9], "freq": "Semestral (Mar/Set)", "tipo": "Mineração"},
    "PETR4": {"meses": [3, 6, 8, 11, 12], "freq": "Trimestral", "tipo": "Petróleo & Gás"},
    "GGBR4": {"meses": [3, 5, 8, 11], "freq": "Trimestral", "tipo": "Siderurgia"},
    "RADL3": {"meses": [4, 7, 10, 12], "freq": "Trimestral", "tipo": "Varejo Farmacêutico"},
    "RENT3": {"meses": [3, 6, 9, 12], "freq": "Trimestral", "tipo": "Locação de Frotas"},
    "TOTS3": {"meses": [4, 10], "freq": "Semestral", "tipo": "Tecnologia / Software"},
    "SUZB3": {"meses": [12], "freq": "Anual", "tipo": "Papel & Celulose"},
    "SLCE3": {"meses": [5, 12], "freq": "Semestral", "tipo": "Agronegócio"},
    "PRIO3": {"meses": [], "freq": "Sem Proventos (100% Crescimento)", "tipo": "Petróleo & Gás"},
    "DIVO11": {"meses": [], "freq": "Reinveste (Acumulação B3)", "tipo": "ETF Dividendos (Acumulação)"},
    "BOVA11": {"meses": [], "freq": "Reinveste (não distribui)", "tipo": "ETF Ibovespa"},
    "IVVB11": {"meses": [], "freq": "Reinveste (não distribui)", "tipo": "ETF S&P 500"},
    "NASD11": {"meses": [], "freq": "Reinveste (não distribui)", "tipo": "ETF Nasdaq 100"},
    "WRLD11": {"meses": [], "freq": "Reinveste (não distribui)", "tipo": "ETF Global"},
    "SMAL11": {"meses": [], "freq": "Reinveste (não distribui)", "tipo": "ETF Small Caps B3"},
    "GOLD11": {"meses": [], "freq": "Reinveste (não distribui)", "tipo": "ETF Ouro"},
}

ETFS_SEM_PROVENTOS = {"BOVA11", "DIVO11", "IVVB11", "SMAL11", "HASH11", "NASD11", "WRLD11", "XINA11", "GOLD11", "SPXI11", "ACWI11", "BOVV11"} | SET_ETFS
ETFS_COM_PROVENTOS = set()
UNITS_ACOES_B3 = {"TAEE11", "SAPR11", "SANB11", "KLBN11", "ALUP11", "ENGI11", "BPAC11"}

NOMES_MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]


def _eh_seguradora(ticker: str, setor: str = "") -> bool:
    """Identifica seguradoras isentas de JCP pesado (praticamente 100% dividendos isentos)."""
    t_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    if t_limpo in SET_SEGURADORAS_ISENTAS:
        return True
    s_limpo = str(setor or "").strip().lower()
    return "segur" in s_limpo or "insur" in s_limpo


def _eh_banco(ticker: str, setor: str = "") -> bool:
    """Identifica bancos que mesclam dividendos isentos e JCP."""
    t_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    if t_limpo in SET_BANCOS_JCP:
        return True
    if _eh_seguradora(t_limpo, setor):
        return False
    s_limpo = str(setor or "").strip().lower()
    return any(t in s_limpo for t in ("banco", "bank", "financial", "financeir"))


def _eh_banco_ou_seguradora(ticker: str, setor: str = "") -> bool:
    """Identifica se o ativo pertence ao segmento de Bancos ou Seguradoras."""
    t_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    if t_limpo in BANCOS_E_SEGURADORAS_TICKERS:
        return True
    return _eh_banco(t_limpo, setor) or _eh_seguradora(t_limpo, setor)


def obter_fator_haircut_jcp(ticker: str = "", setor: str = "", aplicar_haircut_jcp: bool = False) -> float:
    """
    Haircut Seletivo de JCP no Modelo de Bazin:
    - Seguradoras (BBSE3, CXSE3): 0% de haircut -> fator 1.00 (100% dividendos isentos).
    - Bancos (ITUB4, BBDC4, BBAS3, SANB11): 10% de haircut médio ponderado -> fator 0.90.
    - Demais empresas sem flag: 1.00 (ou 0.90 se flag explícita e não for seguradora).
    """
    t_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    if _eh_seguradora(t_limpo, setor):
        return 1.00
    if _eh_banco(t_limpo, setor):
        return 0.90
    if aplicar_haircut_jcp:
        return 0.90
    return 1.00


def _eh_etf(ticker: str, setor: str = "") -> bool:
    """Identifica se o ativo é um ETF de acumulação na B3."""
    t_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    s_limpo = str(setor or "").strip().lower()
    if t_limpo in ETFS_SEM_PROVENTOS or t_limpo in SET_ETFS:
        return True
    return "etf" in s_limpo or "índice" in s_limpo or "indice" in s_limpo


def _eh_fii(ticker: str, setor: str = "") -> bool:
    """Identifica se o ativo é um Fundo Imobiliário (FII)."""
    t_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    if _eh_etf(t_limpo, setor):
        return False
    s_limpo = str(setor or "").strip().lower()
    if "fii" in s_limpo or "imobili" in s_limpo or "real estate" in s_limpo:
        if t_limpo not in UNITS_ACOES_B3:
            return True
    if t_limpo.endswith("11") and t_limpo not in UNITS_ACOES_B3 and t_limpo not in ETFS_SEM_PROVENTOS and t_limpo not in ETFS_COM_PROVENTOS:
        return True
    return False


def _eh_bdr(ticker: str, setor: str = "") -> bool:
    """Identifica se o ativo é um BDR negociado na B3 (final 34, 35, 32, 33 ou presente em UNIVERSO_BDRS)."""
    t_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    if t_limpo in SET_BDRS:
        return True
    if len(t_limpo) >= 6 and t_limpo[-2:] in {"32", "33", "34", "35"} and t_limpo[:-2].isalpha():
        return True
    s_limpo = str(setor or "").strip().lower()
    return "bdr" in s_limpo


def _tipo_fii(ticker: str, segmento: str = "") -> str:
    """Classifica o FII em 'Papel' (CRIs/recebíveis) ou 'Tijolo' (imóveis físicos)."""
    t_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    if t_limpo in SET_FIIS_PAPEL:
        return "Papel"
    if t_limpo in SET_FIIS_TIJOLO:
        return "Tijolo"
    seg = str(segmento or "").strip().lower()
    if any(k in seg for k in ("papel", "cri", "receb", "título", "titulo")):
        return "Papel"
    return "Tijolo"


def calcular_graham(lpa: Optional[float], vpa: Optional[float]) -> Optional[float]:
    """
    Fórmula de Benjamin Graham: Preço_Justo = sqrt(22.5 * LPA * VPA).
    TRAVA MATEMÁTICA: Se LPA <= 0 ou VPA <= 0, retorna None (não calcula).
    """
    try:
        if lpa is None or vpa is None:
            return None
        lpa_f = float(lpa)
        vpa_f = float(vpa)
        if lpa_f <= 0.0 or vpa_f <= 0.0:
            return None
        vi = float(np.sqrt(22.5 * lpa_f * vpa_f))
        if np.isnan(vi) or np.isinf(vi):
            return None
        return round(vi, 2)
    except (ValueError, TypeError):
        return None


def calcular_bazin(
    cotacao: float,
    dy_pct: float,
    yield_desejado: float = 6.0,
    historico_dividendos: Optional[Sequence[float]] = None,
    aplicar_haircut_jcp: bool = False,
    fator_haircut_jcp: Optional[float] = None,
    ticker: Optional[str] = None,
    setor: str = "",
) -> Optional[float]:
    """
    Método Décio Bazin Refatorado:
    - Utiliza a MEDIANA dos dividendos pagos nos últimos 3 a 5 anos (quando disponível)
      para isolar distribuições extraordinárias não recorrentes.
    - Aplica 'haircut' seletivo de JCP:
      * Seguradoras isentas (BBSE3, CXSE3): 0% de haircut (fator 1.00).
      * Bancos (ITUB4, BBDC4, BBAS3, SANB11): 10% de haircut médio ponderado (fator 0.90).
      * Demais ativos com flag explícita: 10% (fator 0.90), ou fator customizado.
    """
    try:
        taxa_alvo = float(yield_desejado) / 100.0 if float(yield_desejado) > 1.0 else float(yield_desejado)
        if taxa_alvo <= 0.0:
            return None

        dividendo_base = 0.0
        if historico_dividendos:
            divs_validos = [float(d) for d in historico_dividendos if d is not None and float(d) > 0.0]
            if divs_validos:
                dividendo_base = float(np.median(divs_validos))

        if dividendo_base <= 0.0:
            cot_f = float(cotacao or 0.0)
            dy_f = float(dy_pct or 0.0)
            if cot_f <= 0.0 or dy_f <= 0.0:
                return None
            # Suporta dy_pct em percentual (ex: 7.5) ou decimal (ex: 0.075)
            dy_dec = (dy_f / 100.0) if dy_f > 1.0 else dy_f
            dividendo_base = cot_f * dy_dec

        if fator_haircut_jcp is not None:
            fator = max(0.0, min(1.0, float(fator_haircut_jcp)))
        elif ticker is not None:
            fator = obter_fator_haircut_jcp(ticker, setor=setor, aplicar_haircut_jcp=aplicar_haircut_jcp)
        elif aplicar_haircut_jcp:
            fator = 0.90
        else:
            fator = 1.00

        dividendo_base *= fator

        preco_teto = dividendo_base / taxa_alvo
        if np.isnan(preco_teto) or np.isinf(preco_teto) or preco_teto <= 0.0:
            return None
        return round(float(preco_teto), 2)
    except (ValueError, TypeError):
        return None


def calcular_valuation(
    ticker: str,
    setor: str,
    lpa: Optional[float],
    vpa: Optional[float],
    roe: Optional[float],
    dy_projetado: Optional[float],
    preco_atual: float,
    ke: Optional[float] = None,
    g: float = 0.04,
    pvp_override: Optional[float] = None,
    cdi_anual: Optional[float] = None,
    payout_conservador: Optional[float] = None,
    payout_historico: Optional[float] = None,
    historico_dividendos: Optional[Sequence[float]] = None,
    mm200: Optional[float] = None,
    rsi_14: Optional[float] = None,
    retorno_12m_pct: Optional[float] = None,
    crescimento_lucro_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Score Triplo Segmentado por Classe/Setor:
    1) FIIs: segmentados em 'Papel' (banda 0.90-1.00, penalidade severa >1.00, alerta CRI <0.85)
       vs 'Tijolo' (banda 0.85-1.05, interpolação linear 50->100 entre 0.80 e 0.85).
    2) Bancos/Seguradoras: Modelo de Gordon Dinâmico com Ke = max(12%, CDI + 4%) e
       trava conservadora de Payout <= 60%: Preco_Justo = VPA * ((ROE * Payout_Conservador) / (Ke - g)).
       Bazin auxiliar aplica haircut seletivo (10% Bancos / 0% Seguradoras).
    3) ETFs de Acumulação (BOVA11, DIVO11, IVVB11): avalia desvio vs MM200, RSI(14) e tendência secular
       em vez de DY/Bazin.
    4) BDRs Internacionais (NVDC34, AAPL34, MSFT34, etc.): isentos da trava de Preço Teto de Bazin;
       Score de Preço e Projeção combinando Tendência Secular (Cotação vs MM200), RSI 14 (pullback)
       e Rentabilidade Operacional (ROE / Crescimento de Lucro).
    5) Ações Não-Financeiras BESST: Benjamin Graham + Bazin sem haircut JCP.
    """
    t_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    preco_f = float(preco_atual or 0.0)
    lpa_f = float(lpa) if lpa is not None and not pd.isna(lpa) else 0.0
    vpa_f = float(vpa) if vpa is not None and not pd.isna(vpa) else 0.0
    roe_raw = float(roe) if roe is not None and not pd.isna(roe) else 0.0
    dy_raw = float(dy_projetado) if dy_projetado is not None and not pd.isna(dy_projetado) else 0.0

    # Normaliza ROE e DY para fração decimal e percentual
    roe_dec = (roe_raw / 100.0) if abs(roe_raw) > 1.0 else roe_raw
    dy_pct = dy_raw if dy_raw > 1.0 else (dy_raw * 100.0)

    is_etf = _eh_etf(t_limpo, setor)
    is_fii = (not is_etf) and _eh_fii(t_limpo, setor)
    is_bdr = (not is_etf) and (not is_fii) and _eh_bdr(t_limpo, setor)
    is_banco_seg = (not is_etf) and (not is_fii) and (not is_bdr) and _eh_banco_ou_seguradora(t_limpo, setor)
    tipo_fii = _tipo_fii(t_limpo, setor) if is_fii else None

    preco_justo: Optional[float] = None
    preco_teto: Optional[float] = None
    margem_seguranca_pct: Optional[float] = None
    modelo_utilizado = "Graham (BESST Tradicional)"
    alerta_risco_critico = False
    alerta_credito_cri = False
    ke_utilizado: Optional[float] = None
    payout_utilizado: Optional[float] = None
    desvio_mm200_pct: Optional[float] = None

    # Cálculo do P/VP (preserva precisão completa nos cálculos; arredondado apenas na exibição)
    if pvp_override is not None and float(pvp_override) > 0:
        pvp_calc = float(pvp_override)
    elif vpa_f > 0 and preco_f > 0:
        pvp_calc = preco_f / vpa_f
    else:
        pvp_calc = 1.0

    # -------------------------------------------------------------------------
    # CASO 0: ETF DE ACUMULAÇÃO (MM200 + RSI + TENDÊNCIA SECULAR)
    # -------------------------------------------------------------------------
    if is_etf:
        modelo_utilizado = "Tendência & MM200 (ETF)"
        mm200_f = float(mm200) if mm200 is not None and float(mm200) > 0 else 0.0
        rsi_f = float(rsi_14) if rsi_14 is not None else 50.0
        ret12_f = float(retorno_12m_pct) if retorno_12m_pct is not None else None

        if mm200_f > 0 and preco_f > 0:
            desvio_mm200_pct = round(((preco_f / mm200_f) - 1.0) * 100.0, 2)
            preco_justo = round(mm200_f, 2)
            preco_teto = round(mm200_f * 1.15, 2)
            margem_seguranca_pct = round(((preco_teto / preco_f) - 1.0) * 100.0, 2)
        elif preco_f > 0:
            desvio_mm200_pct = 0.0
            preco_justo = round(preco_f, 2)
            preco_teto = round(preco_f * 1.10, 2)
            margem_seguranca_pct = 10.0

        # Score de Preço ETF: melhor quando perto/abaixo da MM200 e RSI não esticado
        score_preco = 70.0
        if desvio_mm200_pct is not None:
            if desvio_mm200_pct <= -5.0:
                score_preco += 18.0
            elif desvio_mm200_pct <= 4.0:
                score_preco += 12.0
            elif desvio_mm200_pct <= 10.0:
                score_preco += 2.0
            else:
                score_preco -= min(35.0, (desvio_mm200_pct - 10.0) * 2.2)

        if rsi_f <= 35.0:
            score_preco += 14.0
        elif rsi_f <= 50.0:
            score_preco += 6.0
        elif rsi_f >= 72.0:
            score_preco -= 15.0

        score_preco = min(100.0, max(20.0, score_preco))

        # Score de Projeção ETF: tendência secular em vez de DY inexistente
        score_projecao = 65.0
        if desvio_mm200_pct is not None and desvio_mm200_pct >= 0.0:
            score_projecao += 12.0
        if ret12_f is not None:
            if ret12_f >= 18.0:
                score_projecao += 20.0
            elif ret12_f >= 8.0:
                score_projecao += 14.0
            elif ret12_f >= 0.0:
                score_projecao += 6.0
            elif ret12_f < -12.0:
                score_projecao -= 12.0
        score_projecao = min(100.0, max(30.0, score_projecao))
        score_seguranca = 88.0

    # -------------------------------------------------------------------------
    # CASO 0.5: BDR INTERNACIONAL (ISENTO DE BAZIN • MM200 + RSI 14 + ROE/CRESCIMENTO)
    # -------------------------------------------------------------------------
    elif is_bdr:
        modelo_utilizado = "Crescimento Global & Tendência (BDR)"
        mm200_f = float(mm200) if mm200 is not None and float(mm200) > 0 else 0.0
        rsi_f = float(rsi_14) if rsi_14 is not None else 50.0
        ret12_f = float(retorno_12m_pct) if retorno_12m_pct is not None else None
        cresc_f = float(crescimento_lucro_pct) if crescimento_lucro_pct is not None else None
        roe_pct_bdr = roe_dec * 100.0

        # BDRs são isentos da trava de Preço Teto de Bazin (preco_teto = None)
        preco_teto = None
        if mm200_f > 0 and preco_f > 0:
            desvio_mm200_pct = round(((preco_f / mm200_f) - 1.0) * 100.0, 2)
            preco_justo = round(mm200_f * 1.05, 2)
            margem_seguranca_pct = round(((preco_justo / preco_f) - 1.0) * 100.0, 2)
        elif preco_f > 0:
            desvio_mm200_pct = 0.0
            preco_justo = round(preco_f, 2)
            margem_seguranca_pct = 0.0

        # Score de Preço BDR: Tendência Secular (Cotação vs MM200) + RSI 14 (pontos de pullback)
        score_preco = 68.0
        if desvio_mm200_pct is not None:
            if desvio_mm200_pct <= -5.0:
                score_preco += 18.0
            elif desvio_mm200_pct <= 5.0:
                score_preco += 12.0
            elif desvio_mm200_pct <= 15.0:
                score_preco += 4.0
            else:
                score_preco -= min(30.0, (desvio_mm200_pct - 15.0) * 1.5)

        if rsi_f <= 35.0:
            score_preco += 18.0
        elif rsi_f <= 48.0:
            score_preco += 10.0
        elif rsi_f <= 60.0:
            score_preco += 4.0
        elif rsi_f >= 72.0:
            score_preco -= 15.0

        score_preco = min(100.0, max(25.0, score_preco))

        # Score de Projeção BDR: Rentabilidade Operacional (ROE / Crescimento) + Tendência Secular
        score_projecao = 62.0
        if roe_pct_bdr >= 25.0:
            score_projecao += 20.0
        elif roe_pct_bdr >= 15.0:
            score_projecao += 14.0
        elif roe_pct_bdr >= 8.0:
            score_projecao += 8.0
        elif roe_pct_bdr < 0.0:
            score_projecao -= 20.0

        if cresc_f is not None:
            if cresc_f >= 15.0:
                score_projecao += 12.0
            elif cresc_f >= 5.0:
                score_projecao += 7.0
            elif cresc_f < -10.0:
                score_projecao -= 10.0

        if desvio_mm200_pct is not None and desvio_mm200_pct >= -5.0:
            score_projecao += 6.0
        if ret12_f is not None:
            if ret12_f >= 15.0:
                score_projecao += 8.0
            elif ret12_f < -15.0:
                score_projecao -= 8.0

        score_projecao = min(100.0, max(25.0, score_projecao))
        score_seguranca = 88.0 if roe_pct_bdr >= 18.0 else (80.0 if (roe_pct_bdr >= 0.0 and lpa_f >= 0.0) else 45.0)
        if lpa_f < 0 and roe_pct_bdr < -10.0:
            alerta_risco_critico = True
            score_seguranca = 25.0

    # -------------------------------------------------------------------------
    # CASO 1: FII (Banda P/VP Segmentada: Papel vs Tijolo)
    # -------------------------------------------------------------------------
    elif is_fii:
        modelo_utilizado = f"Banda P/VP (FII {tipo_fii})"
        vpa_efetivo = vpa_f if vpa_f > 0 else (round(preco_f / pvp_calc, 4) if (preco_f > 0 and pvp_calc > 0) else 0.0)
        preco_justo = round(vpa_efetivo, 2) if vpa_efetivo > 0 else None

        if tipo_fii == "Papel":
            preco_teto = round(vpa_efetivo * 1.00, 2) if vpa_efetivo > 0 else None
            if pvp_calc < 0.85:
                alerta_risco_critico = True
                alerta_credito_cri = True
                score_seguranca = 20.0
                score_preco = 20.0
            elif 0.85 <= pvp_calc < 0.90:
                # Transição suave de 75 a 100 pts entre 0.85 e 0.90
                score_preco = round(75.0 + ((pvp_calc - 0.85) / 0.05) * 25.0, 1)
                score_seguranca = 70.0
            elif 0.90 <= pvp_calc <= 1.00:
                score_preco = 100.0
                score_seguranca = 90.0
            else:
                # FII de Papel com ágio > 1.00 corrói TIR: penalidade linear severa
                penalidade = (pvp_calc - 1.00) * 600.0
                score_preco = max(10.0, round(100.0 - penalidade, 1))
                score_seguranca = 75.0
        else:
            # FII de Tijolo
            preco_teto = round(vpa_efetivo * 1.05, 2) if vpa_efetivo > 0 else None
            if pvp_calc < 0.80:
                score_seguranca = 0.0
                score_preco = 25.0
                alerta_risco_critico = True
            elif 0.80 <= pvp_calc < 0.85:
                # Elimina limbo matemático: interpolação linear 50 -> 100 pts
                fator_interp = (pvp_calc - 0.80) / 0.05
                score_preco = round(50.0 + fator_interp * 50.0, 1)
                score_seguranca = round(50.0 + fator_interp * 35.0, 1)
            elif 0.85 <= pvp_calc <= 1.05:
                score_preco = 100.0
                score_seguranca = 85.0
            else:
                desconto_agio = min(80.0, (pvp_calc - 1.05) * 300.0)
                score_preco = max(15.0, round(100.0 - desconto_agio, 1))
                score_seguranca = 80.0

        if preco_teto and preco_f > 0:
            margem_seguranca_pct = round(((preco_teto / preco_f) - 1.0) * 100.0, 2)
        elif preco_justo and preco_f > 0:
            margem_seguranca_pct = round(((preco_justo / preco_f) - 1.0) * 100.0, 2)
        elif pvp_calc > 0:
            margem_seguranca_pct = round(((1.0 / pvp_calc) - 1.0) * 100.0, 2)

    # -------------------------------------------------------------------------
    # CASO 2: BANCO OU SEGURADORA (Gordon Dinâmico + Trava de Payout)
    # -------------------------------------------------------------------------
    elif is_banco_seg:
        modelo_utilizado = "Gordon Dinâmico (Bancos/Seguradoras)"
        if ke is not None:
            ke_efetivo = float(ke)
        else:
            if cdi_anual is None:
                try:
                    cdi_ref = float(obter_dados_macro().get("cdi", 10.65))
                except Exception:
                    cdi_ref = 10.65
            else:
                cdi_ref = float(cdi_anual)
            ke_efetivo = max(0.12, (cdi_ref / 100.0) + 0.04)

        ke_utilizado = round(ke_efetivo, 4)

        # Calibração do Payout Conservador (limitado a 60% para retenção de Basileia/solvência)
        if payout_conservador is not None:
            p_raw = float(payout_conservador)
            p_dec = (p_raw / 100.0) if p_raw > 1.0 else p_raw
            payout_eff = min(0.60, max(0.20, p_dec))
        elif payout_historico is not None and float(payout_historico) > 0:
            p_raw = float(payout_historico)
            p_dec = (p_raw / 100.0) if p_raw > 1.0 else p_raw
            payout_eff = min(0.60, max(0.20, p_dec))
        elif lpa_f > 0.0 and historico_dividendos:
            divs_validos = [float(d) for d in historico_dividendos if d is not None and float(d) > 0.0]
            if divs_validos:
                payout_eff = min(0.60, max(0.20, float(np.median(divs_validos)) / lpa_f))
            else:
                payout_eff = 0.60
        elif lpa_f > 0.0 and dy_pct > 0.0 and preco_f > 0.0:
            div_anual_est = preco_f * (dy_pct / 100.0)
            payout_eff = min(0.60, max(0.25, div_anual_est / lpa_f))
        else:
            payout_eff = 0.60

        payout_utilizado = round(payout_eff, 4)
        denominador = ke_efetivo - float(g)
        if vpa_f > 0.0 and denominador > 0.0 and roe_dec > 0.0:
            pj_gordon = vpa_f * ((roe_dec * payout_eff) / denominador)
            if not np.isnan(pj_gordon) and not np.isinf(pj_gordon) and pj_gordon > 0:
                preco_justo = round(float(pj_gordon), 2)

        if preco_justo and preco_f > 0:
            margem_seguranca_pct = round(((preco_justo / preco_f) - 1.0) * 100.0, 2)

        # Bazin auxiliar com Haircut Seletivo (10% Bancos / 0% Seguradoras)
        preco_teto_bazin = calcular_bazin(
            preco_f,
            dy_pct,
            yield_desejado=6.0,
            historico_dividendos=historico_dividendos,
            aplicar_haircut_jcp=True,
            ticker=t_limpo,
            setor=setor,
        )
        if preco_teto_bazin and preco_justo:
            preco_teto = round(min(preco_teto_bazin, preco_justo), 2)
        else:
            preco_teto = preco_teto_bazin or preco_justo

        margem_bazin = ((preco_teto_bazin / preco_f) - 1.0) * 100.0 if (preco_teto_bazin and preco_f > 0) else 0.0

        score_preco = 45.0
        if margem_seguranca_pct is not None:
            if margem_seguranca_pct >= 25.0:
                score_preco += 35.0
            elif margem_seguranca_pct >= 10.0:
                score_preco += 25.0
            elif margem_seguranca_pct > 0.0:
                score_preco += 15.0
            else:
                score_preco -= 10.0

        if margem_bazin >= 15.0:
            score_preco += 20.0
        elif margem_bazin > 0.0:
            score_preco += 10.0

        score_preco = min(100.0, max(15.0, score_preco))
        score_seguranca = 85.0 if roe_dec >= 0.14 else (70.0 if roe_dec > 0 else 20.0)
        if lpa_f < 0 or roe_dec < 0:
            alerta_risco_critico = True
            score_seguranca = 10.0

    # -------------------------------------------------------------------------
    # CASO 3: AÇÃO BESST TRADICIONAL (Benjamin Graham)
    # -------------------------------------------------------------------------
    else:
        modelo_utilizado = "Graham (BESST Tradicional)"
        preco_justo = calcular_graham(lpa_f, vpa_f)
        if preco_justo is not None and preco_f > 0:
            margem_seguranca_pct = round(((preco_justo / preco_f) - 1.0) * 100.0, 2)

        preco_teto_bazin = calcular_bazin(
            preco_f,
            dy_pct,
            yield_desejado=6.0,
            historico_dividendos=historico_dividendos,
            aplicar_haircut_jcp=False,
            ticker=t_limpo,
            setor=setor,
        )
        if preco_teto_bazin and preco_justo:
            # Para conservador BESST: respeita teto mais restritivo entre Graham e Bazin quando ambos existem
            preco_teto = round(min(preco_justo, preco_teto_bazin), 2)
        else:
            preco_teto = preco_teto_bazin or preco_justo

        margem_bazin = ((preco_teto_bazin / preco_f) - 1.0) * 100.0 if (preco_teto_bazin and preco_f > 0) else 0.0

        if preco_justo is None:
            # Prejuízo contábil (LPA <= 0) ou Passivo a Descoberto (VPA <= 0)
            score_preco = 20.0
            score_seguranca = 15.0
            alerta_risco_critico = True
        else:
            score_preco = 40.0
            if margem_seguranca_pct is not None:
                if margem_seguranca_pct >= 30.0:
                    score_preco += 35.0
                elif margem_seguranca_pct >= 10.0:
                    score_preco += 20.0
                elif margem_seguranca_pct > 0.0:
                    score_preco += 10.0

            if margem_bazin >= 20.0:
                score_preco += 25.0
            elif margem_bazin > 0.0:
                score_preco += 15.0

            score_preco = min(100.0, max(20.0, score_preco))
            score_seguranca = 80.0

    # Pilar Projeção (Baseado no DY projetado; ETFs e BDRs já calcularam via tendência e rentabilidade)
    if not is_etf and not is_bdr:
        score_projecao = 35.0
        if dy_pct >= 11.0:
            score_projecao = 95.0
        elif dy_pct >= 8.5:
            score_projecao = 80.0
        elif dy_pct >= 6.0:
            score_projecao = 65.0
        elif dy_pct > 0.0:
            score_projecao = 45.0
        else:
            score_projecao = 20.0

    score_triplo = round((score_preco * 0.35) + (score_projecao * 0.35) + (score_seguranca * 0.30), 1)

    return {
        "ticker": t_limpo,
        "setor": setor,
        "modelo_utilizado": modelo_utilizado,
        "tipo_fii": tipo_fii,
        "eh_etf": is_etf,
        "eh_bdr": is_bdr,
        "isento_teto_bazin": bool(is_bdr or is_etf),
        "preco_justo": preco_justo,
        "preco_teto": None if is_bdr else (preco_teto if preco_teto is not None else preco_justo),
        "margem_seguranca_pct": margem_seguranca_pct,
        "pvp_calculado": round(pvp_calc, 2),
        "ke_utilizado": ke_utilizado,
        "payout_conservador_utilizado": payout_utilizado,
        "desvio_mm200_pct": desvio_mm200_pct,
        "score_preco": round(score_preco, 1),
        "score_projecao": round(score_projecao, 1),
        "score_seguranca": round(score_seguranca, 1),
        "score_triplo": score_triplo,
        "alerta_risco_critico": alerta_risco_critico,
        "alerta_credito_cri": alerta_credito_cri,
    }


def calcular_rsi(serie_fechamento_ajustado: pd.Series, periodo: int = 14) -> float:
    """
    Calcula o RSI / IFR de 14 Períodos usando a Média Móvel Suavizada de Wilder
    (Wilder's Smoothing: alpha = 1 / periodo, equivalente a EMA de 27 períodos),
    operando sobre a série histórica de Preços Ajustados por Proventos ('Adj Close').
    """
    if serie_fechamento_ajustado is None or len(serie_fechamento_ajustado) < periodo + 1:
        return 50.0

    try:
        serie_limpa = pd.Series(serie_fechamento_ajustado).dropna().astype(float)
        if len(serie_limpa) < periodo + 1:
            return 50.0

        delta = serie_limpa.diff()
        ganho = delta.clip(lower=0.0)
        perda = -delta.clip(upper=0.0)

        # Wilder's Smoothing: EWM com alpha = 1/periodo (equivalente a span = 2*periodo - 1 = 27)
        media_ganho = ganho.ewm(alpha=1.0 / float(periodo), min_periods=periodo, adjust=False).mean()
        media_perda = perda.ewm(alpha=1.0 / float(periodo), min_periods=periodo, adjust=False).mean()

        ultimo_ganho = float(media_ganho.iloc[-1])
        ultima_perda = float(media_perda.iloc[-1])

        if ultima_perda == 0.0:
            return 100.0 if ultimo_ganho > 0.0 else 50.0

        rs = ultimo_ganho / ultima_perda
        rsi = 100.0 - (100.0 / (1.0 + rs))

        if np.isnan(rsi) or np.isinf(rsi):
            return 50.0
        return round(float(rsi), 2)
    except Exception:
        return 50.0


def obter_calendario_sazonal(
    tickers_selecionados: Optional[List[str]] = None,
    posicoes_usuario: Optional[List[Dict[str, Any]]] = None,
    apenas_carteira: bool = False
) -> Dict[str, Any]:
    """
    Retorna o mapa sazonal de pagamentos de proventos ao longo dos 12 meses do ano.
    - Consolida os meses de pagamento recorrente (ex: Taesa em Mai/Ago/Nov, Bancos mensalmente, FIIs todos os meses).
    - Se `apenas_carteira=True` e `posicoes_usuario` for informado, avalia exclusivamente os ativos da carteira do investidor.
    """
    renda_por_ticker: Dict[str, float] = {}
    classes_por_ticker: Dict[str, str] = {}
    tickers_carteira: List[str] = []

    if posicoes_usuario:
        for p in posicoes_usuario:
            t = str(p.get("ticker", "")).replace(".SA", "").strip().upper()
            if t.endswith("F") and len(t) > 5:
                t = t[:-1]
            if not t:
                continue
            renda_mensal = float(p.get("renda_mensal_estimada", p.get("renda_passiva_mensal", 0.0)) or 0.0)
            renda_por_ticker[t] = renda_por_ticker.get(t, 0.0) + renda_mensal
            classes_por_ticker[t] = str(p.get("classe", ""))
            if t not in tickers_carteira:
                tickers_carteira.append(t)

    if apenas_carteira:
        tickers_selecionados = tickers_carteira
    elif tickers_selecionados is None:
        tickers_selecionados = list(dict.fromkeys(list(MAPA_SAZONALIDADE_PROVENTOS.keys()) + tickers_carteira))

    grade_meses = []
    for num_mes in range(1, 13):
        nome_mes = NOMES_MESES[num_mes - 1]
        pagadores_mes = []
        pagadores_carteira_mes = []
        renda_estimada_mes = 0.0

        for t in tickers_selecionados:
            t_upper = str(t).replace(".SA", "").strip().upper()
            if t_upper.endswith("F") and len(t_upper) > 5:
                t_upper = t_upper[:-1]
            config_sazonal = MAPA_SAZONALIDADE_PROVENTOS.get(t_upper)
            classe_usr = classes_por_ticker.get(t_upper, "").upper()

            if not config_sazonal:
                if "FII" in classe_usr or (t_upper.endswith("11") and t_upper not in ETFS_SEM_PROVENTOS and t_upper not in ETFS_COM_PROVENTOS and t_upper not in UNITS_ACOES_B3):
                    config_sazonal = {"meses": list(range(1, 13)), "freq": "Mensal", "tipo": "Fundo Imobiliário"}
                elif t_upper in {"ITUB4", "ITUB3", "BBDC4", "BBDC3"}:
                    config_sazonal = {"meses": list(range(1, 13)), "freq": "Mensal", "tipo": "Banco"}

            if config_sazonal and num_mes in config_sazonal.get("meses", []):
                pagadores_mes.append(t_upper)
                if t_upper in renda_por_ticker:
                    pagadores_carteira_mes.append(t_upper)
                    qtd_meses = max(len(config_sazonal.get("meses", [1])), 1)
                    fluxo_evento = (renda_por_ticker[t_upper] * 12.0) / qtd_meses
                    renda_estimada_mes += fluxo_evento

        grade_meses.append({
            "mes_num": num_mes,
            "mes_nome": nome_mes,
            "mes_abrev": nome_mes[:3],
            "qtd_pagadores": len(pagadores_mes),
            "pagadores": pagadores_mes,
            "pagadores_carteira": pagadores_carteira_mes,
            "tem_pagamento_carteira": len(pagadores_carteira_mes) > 0,
            "renda_estimada": round(renda_estimada_mes, 2)
        })

    detalhes = []
    for t in tickers_selecionados:
        t_upper = t.replace(".SA", "").upper()
        conf = MAPA_SAZONALIDADE_PROVENTOS.get(t_upper)
        if conf is None and t_upper.endswith("11") and t_upper not in ETFS_SEM_PROVENTOS and t_upper not in ETFS_COM_PROVENTOS:
            conf = {"meses": list(range(1, 13)), "freq": "Mensal (padrão FII)", "tipo": "Fundo Imobiliário"}
        if conf is None:
            conf = {"meses": [], "freq": "Sem histórico mapeado", "tipo": "Ação/ETF B3"}
        meses_str = ", ".join([NOMES_MESES[m - 1][:3] for m in conf.get("meses", [])]) if conf.get("meses") else "—"

        detalhes.append({
            "ticker": t_upper,
            "tipo": conf.get("tipo", "Geral"),
            "frequencia": conf.get("freq", "Sazonal"),
            "meses": meses_str,
            "qtd_meses": len(conf.get("meses", []))
        })

    return {
        "grade_mensal": grade_meses,
        "detalhes_ativos": detalhes
    }


def calcular_efeito_bola_de_neve(posicoes_usuario: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calcula o Magic Number Dual (Número Mágico da Bola de Neve):
    - Para FIIs (proventos mensais): Magic Number MENSAL = ceil(Cotação / Dividendo Mensal por Cota).
    - Para Ações (pagamentos sazonais trimestrais/semestrais): Magic Number ANUAL = ceil(Cotação / Dividendo Anual por Ação).
    """
    resultado = []
    if not posicoes_usuario:
        return resultado

    for pos in posicoes_usuario:
        ticker = pos.get("ticker", "").replace(".SA", "").upper()
        classe = str(pos.get("classe", "Ação"))
        qtd_atual = float(pos.get("quantidade", 0) or 0)
        cotacao = float(pos.get("cotacao_atual", pos.get("cotacao", 0.0)) or 0.0)
        dy = float(pos.get("dy_anual", 0.0) or 0.0)

        if cotacao <= 0 or dy <= 0 or _eh_etf(ticker, classe):
            continue

        is_fii = _eh_fii(ticker, classe) or ("fii" in classe.lower())
        div_anual_cota = cotacao * (dy / 100.0)
        div_mensal_cota = div_anual_cota / 12.0

        magic_anual = int(np.ceil(cotacao / div_anual_cota)) if div_anual_cota > 0 else 0
        magic_mensal = int(np.ceil(cotacao / div_mensal_cota)) if (is_fii and div_mensal_cota > 0) else None

        if is_fii:
            magic_number = magic_mensal or 0
            periodicidade_magic = "Mensal"
            valor_total_meta = magic_number * cotacao
            progresso_pct = round(min(100.0, (qtd_atual / magic_number) * 100.0), 1) if magic_number > 0 else 0.0
            cotas_faltantes = max(0, magic_number - int(qtd_atual))
            if progresso_pct >= 100.0:
                status = "🏆 Bola de Neve Mensal Ativada! (1 cota/mês garantida)"
            elif progresso_pct >= 60.0:
                status = "🚀 Fase de Aceleração (FII Mensal)"
            elif progresso_pct >= 30.0:
                status = "🌱 Crescimento Intermediário (FII)"
            else:
                status = "🧱 Construção de Base (FII)"
        else:
            magic_number = magic_anual
            periodicidade_magic = "Anual"
            valor_total_meta = magic_number * cotacao
            progresso_pct = round(min(100.0, (qtd_atual / magic_number) * 100.0), 1) if magic_number > 0 else 0.0
            cotas_faltantes = max(0, magic_number - int(qtd_atual))
            if progresso_pct >= 100.0:
                status = "🏆 Bola de Neve Anual Ativada! (+1 ação inteira/ano)"
            elif progresso_pct >= 60.0:
                status = "🚀 Fase de Aceleração (Div. Anual)"
            elif progresso_pct >= 30.0:
                status = "🌱 Crescimento Intermediário (Ação)"
            else:
                status = "🧱 Construção de Base (Ação)"

        resultado.append({
            "ticker": ticker,
            "classe": classe,
            "periodicidade_magic": periodicidade_magic,
            "cotacao": cotacao,
            "dy_anual_pct": dy,
            "qtd_atual": int(qtd_atual),
            "magic_number": magic_number,
            "magic_number_mensal": magic_mensal,
            "magic_number_anual": magic_anual,
            "cotas_faltantes": cotas_faltantes,
            "valor_meta_total": round(valor_total_meta, 2),
            "progresso_pct": progresso_pct,
            "status": status,
        })

    resultado.sort(key=lambda x: x["progresso_pct"], reverse=True)
    return resultado


def calcular_score_saude_balanco(ticker: str) -> Dict[str, Any]:
    """
    Avalia a solidez financeira e o Score de Segurança (0 a 100) com réguas específicas por classe:
    - Ações Não-Financeiras: Dívida Líquida/EBITDA, ROE e Liquidez Corrente.
    - Bancos/Seguradoras: ROE (peso 60%) e Histórico de Crescimento de Lucro / P/VP (peso 40%), ignorando EBITDA.
    - FIIs: Estabilidade dos proventos 12m, Liquidez Diária e Adequação de P/VP (Papel vs Tijolo).
    - ETFs de Acumulação: Diversificação de índice e liquidez diária.
    """
    t_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    info = obter_info_ativo(ticker)
    setor = info.get("setor", "")
    is_etf = _eh_etf(t_limpo, setor)
    is_financeiro = (not is_etf) and _eh_banco_ou_seguradora(t_limpo, setor)
    is_fii = (not is_etf) and _eh_fii(t_limpo, setor)

    roe = float(info.get("roe", 0.0) or 0.0)
    liq_corr = float(info.get("liquidez_corrente", 0.0) or 0.0)
    margem = float(info.get("margem_liquida", 0.0) or 0.0)
    dl_ebitda = info.get("divida_liquida_ebitda")
    pvp = float(info.get("pvp", 1.0) or 1.0)
    lpa = float(info.get("lpa", 0.0) or 0.0)
    cresc_lucro = info.get("crescimento_lucro_pct")
    vol_diario = info.get("volume_medio_diario")
    estab_prov = info.get("estabilidade_dividendos_score")
    qtd_pag_12m = int(info.get("qtd_pagamentos_12m", 0) or 0)

    pontos_fortes: List[str] = []
    pontos_atencao: List[str] = []
    nivel_alerta = "normal"  # 'normal', 'warn', 'neg'

    # 1) ETF DE ACUMULAÇÃO
    if is_etf:
        score_final = 88.0
        pontos_fortes.append("Diversificação passiva em cesta de índice (risco específico diluído)")
        if vol_diario is not None and float(vol_diario) >= 10_000_000:
            score_final += 5.0
            pontos_fortes.append(f"Alta liquidez diária em bolsa (R$ {float(vol_diario)/1e6:.1f}M/dia)")
        elif vol_diario is not None and float(vol_diario) < 1_000_000:
            score_final -= 10.0
            pontos_atencao.append("Liquidez diária moderada; usar ordens limitadas")
        return {
            "ticker": ticker,
            "nome": info.get("nome", ticker),
            "setor": setor or "ETF de Índice",
            "classe_seguranca": "ETF de Acumulação",
            "score_saude": round(max(40.0, min(95.0, score_final)), 1),
            "selo": "🟢 ETF Institucional Diversificado",
            "nivel_alerta": "normal",
            "roe_pct": roe,
            "margem_liq_pct": margem,
            "divida_liq_ebitda": None,
            "liquidez_corrente": None,
            "pontos_fortes": pontos_fortes,
            "pontos_atencao": pontos_atencao,
        }

    # 2) FUNDOS IMOBILIÁRIOS (Estabilidade 12m + Liquidez Diária + Adequação P/VP)
    if is_fii:
        tipo_fii = _tipo_fii(t_limpo, setor)
        if tipo_fii == "Papel" and 0 < pvp < 0.85:
            return {
                "ticker": ticker,
                "nome": info.get("nome", ticker),
                "setor": setor,
                "classe_seguranca": f"FII ({tipo_fii})",
                "score_saude": 20.0,
                "selo": "🔴 Alerta de Risco de Crédito na Carteira de CRIs (P/VP < 0.85)",
                "nivel_alerta": "neg",
                "roe_pct": roe,
                "margem_liq_pct": margem,
                "divida_liq_ebitda": None,
                "liquidez_corrente": None,
                "pontos_fortes": [],
                "pontos_atencao": [f"FII de Papel com P/VP em {pvp:.2f}x (< 0.85): Risco de inadimplência/calote nos CRIs"],
            }
        if tipo_fii == "Tijolo" and 0 < pvp < 0.80:
            return {
                "ticker": ticker,
                "nome": info.get("nome", ticker),
                "setor": setor,
                "classe_seguranca": f"FII ({tipo_fii})",
                "score_saude": 0.0,
                "selo": "🔴 Risco Crítico: P/VP Abaixo de 0.80 (Possível Deterioração de Imóveis)",
                "nivel_alerta": "neg",
                "roe_pct": roe,
                "margem_liq_pct": margem,
                "divida_liq_ebitda": None,
                "liquidez_corrente": None,
                "pontos_fortes": [],
                "pontos_atencao": [f"P/VP em {pvp:.2f}x (< 0.80): Deságio severo sinalizando vacância ou deterioração patrimonial"],
            }

        # Sub-score Estabilidade de Proventos 12m (40%)
        if estab_prov is not None:
            sub_estab = float(estab_prov)
            if qtd_pag_12m >= 12:
                sub_estab = min(100.0, sub_estab + 5.0)
                pontos_fortes.append(f"Regularidade exemplar: {qtd_pag_12m} pagamentos nos últimos 12m (estabilidade {sub_estab:.0f}/100)")
            elif qtd_pag_12m < 10 and qtd_pag_12m > 0:
                sub_estab = max(30.0, sub_estab - 20.0)
                pontos_atencao.append(f"Histórico de proventos irregular ({qtd_pag_12m} pagamentos nos últimos 12m)")
            else:
                pontos_fortes.append(f"Estabilidade de proventos em {sub_estab:.0f}/100")
        else:
            sub_estab = 75.0
            pontos_fortes.append("Estabilidade de proventos dentro da faixa padrão FII")

        # Sub-score Liquidez Diária (30%)
        if vol_diario is not None:
            vol_f = float(vol_diario)
            if vol_f >= 3_000_000:
                sub_liq = 95.0
                pontos_fortes.append(f"Alta liquidez diária (R$ {vol_f/1e6:.1f}M/dia)")
            elif vol_f >= 1_000_000:
                sub_liq = 82.0
                pontos_fortes.append(f"Liquidez diária saudável (R$ {vol_f/1e6:.1f}M/dia)")
            elif vol_f >= 300_000:
                sub_liq = 60.0
                pontos_atencao.append(f"Liquidez diária moderada (R$ {vol_f/1e3:.0f}k/dia)")
            else:
                sub_liq = 35.0
                nivel_alerta = "warn"
                pontos_atencao.append(f"Baixa liquidez diária (R$ {vol_f/1e3:.0f}k/dia): risco de spread na saída")
        else:
            sub_liq = 75.0

        # Sub-score Adequação de P/VP (30%)
        if tipo_fii == "Papel":
            if 0.90 <= pvp <= 1.00:
                sub_pvp = 95.0
                pontos_fortes.append(f"FII de Papel na banda justa (P/VP {pvp:.2f}x entre 0.90 e 1.00)")
            elif 0.85 <= pvp < 0.90:
                sub_pvp = 72.0
                pontos_atencao.append(f"FII de Papel com leve desconto (P/VP {pvp:.2f}x): monitorar carteira de CRIs")
            else:
                sub_pvp = max(35.0, 90.0 - (pvp - 1.00) * 350.0)
                nivel_alerta = "warn" if pvp > 1.04 else nivel_alerta
                pontos_atencao.append(f"FII de Papel negociado com ágio sobre a cota patrimonial (P/VP {pvp:.2f}x > 1.00)")
        else:
            if 0.85 <= pvp <= 1.05:
                sub_pvp = 92.0
                pontos_fortes.append(f"FII de Tijolo em banda saudável (P/VP {pvp:.2f}x entre 0.85 e 1.05)")
            elif 0.80 <= pvp < 0.85:
                sub_pvp = 55.0 + ((pvp - 0.80) / 0.05) * 35.0
                pontos_atencao.append(f"FII de Tijolo com desconto intermediário (P/VP {pvp:.2f}x)")
            else:
                sub_pvp = max(45.0, 88.0 - (pvp - 1.05) * 200.0)
                pontos_atencao.append(f"FII de Tijolo com ágio relevante (P/VP {pvp:.2f}x > 1.05)")

        score_final = max(10.0, min(100.0, (sub_estab * 0.40) + (sub_liq * 0.30) + (sub_pvp * 0.30)))
        selo = (
            "🟢 FII High Grade (Liquidez + Proventos Estáveis + P/VP Justo)" if score_final >= 80.0
            else ("🔵 FII Equilibrado" if score_final >= 65.0 else "🟡 Atenção: FII com Desvio em P/VP, Liquidez ou Proventos")
        )
        return {
            "ticker": ticker,
            "nome": info.get("nome", ticker),
            "setor": setor,
            "classe_seguranca": f"FII ({tipo_fii})",
            "score_saude": round(score_final, 1),
            "selo": selo,
            "nivel_alerta": nivel_alerta,
            "roe_pct": roe,
            "margem_liq_pct": margem,
            "divida_liq_ebitda": None,
            "liquidez_corrente": None,
            "estabilidade_proventos": round(sub_estab, 1),
            "volume_medio_diario": vol_diario,
            "pontos_fortes": pontos_fortes,
            "pontos_atencao": pontos_atencao,
        }

    # 3) BANCOS & SEGURADORAS (ROE 60% + Crescimento de Lucro/P/VP 40%, ignorando EBITDA)
    if is_financeiro:
        if roe >= 18.0:
            sub_roe = 95.0
            pontos_fortes.append(f"ROE de Elite no setor financeiro ({roe:.1f}%)")
        elif roe >= 14.0:
            sub_roe = 84.0
            pontos_fortes.append(f"ROE Sólido acima do custo de capital ({roe:.1f}%)")
        elif roe >= 10.0:
            sub_roe = 68.0
            pontos_fortes.append(f"ROE Moderado ({roe:.1f}%)")
        elif roe > 0.0:
            sub_roe = 45.0
            pontos_atencao.append(f"ROE Comprimido ({roe:.1f}%) abaixo do CDI")
        else:
            sub_roe = 10.0
            nivel_alerta = "neg"
            pontos_atencao.append("ROE Negativo ou Prejuízo no exercício")

        # Sub-score Crescimento de Lucro & P/VP (40%)
        if cresc_lucro is not None:
            cr_f = float(cresc_lucro)
            if cr_f >= 10.0:
                sub_cresc = 94.0
                pontos_fortes.append(f"Lucro em expansão (+{cr_f:.1f}% YoY)")
            elif cr_f >= 0.0:
                sub_cresc = 78.0
                pontos_fortes.append(f"Lucro resiliente (+{cr_f:.1f}% YoY)")
            elif cr_f >= -15.0:
                sub_cresc = 55.0
                pontos_atencao.append(f"Retração pontual nos lucros ({cr_f:.1f}% YoY)")
            else:
                sub_cresc = 32.0
                nivel_alerta = "warn" if nivel_alerta == "normal" else nivel_alerta
                pontos_atencao.append(f"Queda acentuada nos lucros ({cr_f:.1f}% YoY)")
        else:
            sub_cresc = 72.0

        if 0.70 <= pvp <= 2.30:
            sub_pvp_fin = 88.0
        elif pvp > 2.30:
            sub_pvp_fin = 68.0
            pontos_atencao.append(f"Múltiplo P/VP esticado ({pvp:.2f}x) para instituição financeira")
        else:
            sub_pvp_fin = 48.0
            pontos_atencao.append(f"P/VP descontado ({pvp:.2f}x): atenção à rentabilidade futura / Basileia")

        sub_fin_40 = (sub_cresc * 0.65) + (sub_pvp_fin * 0.35)
        score_final = max(10.0, min(100.0, (sub_roe * 0.60) + (sub_fin_40 * 0.40)))

        if lpa < 0:
            nivel_alerta = "neg"
            score_final = min(score_final, 30.0)
            pontos_atencao.append(f"Prejuízo Contábil (LPA de R$ {lpa:.2f})")

        pontos_fortes.append("Métricas Dívida/EBITDA e Liquidez Corrente corretamente ignoradas (setor financeiro)")

        if nivel_alerta == "neg" or score_final < 45.0:
            selo = "🔴 Risco Crítico em Instituição Financeira"
        elif nivel_alerta == "warn" or score_final < 65.0:
            selo = "🟡 Alerta Moderado em ROE / Tendência de Lucros"
        elif score_final >= 80.0:
            selo = "🟢 Balanço Financeiro Fortaleza (ROE & Basileia Saudáveis)"
        else:
            selo = "🔵 Instituição Financeira Equilibrada"

        return {
            "ticker": ticker,
            "nome": info.get("nome", ticker),
            "setor": setor,
            "classe_seguranca": "Bancos/Seguradoras",
            "score_saude": round(score_final, 1),
            "selo": selo,
            "nivel_alerta": nivel_alerta,
            "roe_pct": roe,
            "margem_liq_pct": margem,
            "divida_liq_ebitda": None,
            "liquidez_corrente": None,
            "crescimento_lucro_pct": cresc_lucro,
            "pontos_fortes": pontos_fortes,
            "pontos_atencao": pontos_atencao,
        }

    # 4) AÇÕES NÃO-FINANCEIRAS (Dívida Líq./EBITDA 40% + ROE 35% + Liquidez Corrente 25%)
    if dl_ebitda is not None:
        dl_f = float(dl_ebitda)
        if dl_f <= 1.0:
            sub_dl = 98.0
            pontos_fortes.append(f"Dívida Líq./EBITDA Ultra Conservadora ({dl_f:.2f}x)")
        elif dl_f <= 1.5:
            sub_dl = 90.0
            pontos_fortes.append(f"Dívida Líq./EBITDA Conservadora ({dl_f:.2f}x) - Baixíssimo Risco")
        elif dl_f <= 2.5:
            sub_dl = 75.0
            pontos_fortes.append(f"Dívida Líq./EBITDA Controlada ({dl_f:.2f}x)")
        elif dl_f <= 3.5:
            sub_dl = 45.0
            nivel_alerta = "warn"
            pontos_atencao.append(f"Alavancagem Moderada (Dívida Líq./EBITDA em {dl_f:.2f}x > 2.5x)")
        else:
            sub_dl = 18.0
            nivel_alerta = "neg" if dl_f > 4.5 else "warn"
            pontos_atencao.append(f"Alavancagem Elevada (Dívida Líq./EBITDA em {dl_f:.2f}x > 3.5x)")
    else:
        sub_dl = 70.0

    if roe >= 18.0:
        sub_roe_nf = 95.0
        pontos_fortes.append(f"ROE de Elite ({roe:.1f}%), superando com folga o custo de capital")
    elif roe >= 12.0:
        sub_roe_nf = 80.0
        pontos_fortes.append(f"ROE Sólido ({roe:.1f}%)")
    elif roe >= 6.0:
        sub_roe_nf = 60.0
    elif roe > 0.0:
        sub_roe_nf = 40.0
        pontos_atencao.append(f"ROE Baixo ({roe:.1f}%), abaixo da taxa Selic")
    else:
        sub_roe_nf = 10.0
        nivel_alerta = "neg"
        pontos_atencao.append("ROE Negativo / Prejuízo Contábil no período")

    if liq_corr >= 1.5:
        sub_lc = 95.0
        pontos_fortes.append(f"Liquidez Corrente Confortável ({liq_corr:.2f}x)")
    elif liq_corr >= 1.1:
        sub_lc = 78.0
        pontos_fortes.append(f"Liquidez Corrente Adequada ({liq_corr:.2f}x)")
    elif liq_corr >= 1.0:
        sub_lc = 60.0
    elif liq_corr > 0.0:
        sub_lc = 30.0
        if nivel_alerta == "normal":
            nivel_alerta = "warn"
        pontos_atencao.append(f"Liquidez Corrente Abaixo de 1.0x ({liq_corr:.2f}x)")
    else:
        sub_lc = 65.0

    if margem >= 20.0:
        pontos_fortes.append(f"Margem Líquida Estelar ({margem:.1f}%)")
    elif 0 < margem < 5.0:
        pontos_atencao.append(f"Margem Comprimida ({margem:.1f}%)")

    score_final = max(10.0, min(100.0, (sub_dl * 0.40) + (sub_roe_nf * 0.35) + (sub_lc * 0.25)))

    if lpa < 0:
        nivel_alerta = "neg"
        score_final = min(score_final, 30.0)
        pontos_atencao.append(f"Prejuízo Contábil (LPA de R$ {lpa:.2f})")

    if nivel_alerta == "neg" or score_final < 45.0:
        selo = "🔴 Risco Crítico: Prejuízo Contábil ou Deterioração Patrimonial"
    elif nivel_alerta == "warn" or score_final < 65.0:
        selo = "🟡 Alerta Moderado: Alavancagem Dívida/EBITDA ou Liquidez Exige Atenção"
    elif score_final >= 80.0:
        selo = "🟢 Balanço Fortaleza (Grau Máximo de Higidez)"
    else:
        selo = "🔵 Balanço Equilibrado & Saudável"

    return {
        "ticker": ticker,
        "nome": info.get("nome", ticker),
        "setor": setor,
        "classe_seguranca": "Ações Não-Financeiras",
        "score_saude": round(score_final, 1),
        "selo": selo,
        "nivel_alerta": nivel_alerta,
        "roe_pct": roe,
        "margem_liq_pct": margem,
        "divida_liq_ebitda": dl_ebitda,
        "liquidez_corrente": liq_corr,
        "pontos_fortes": pontos_fortes,
        "pontos_atencao": pontos_atencao,
    }


def analisar_universo_besst(
    cdi_liquido: Optional[float] = None,
    cdi_bruto: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Analisa o universo BESST aplicando Valuation Segmentado:
    - Bancos/Seguradoras: Gordon Dinâmico com trava conservadora de Payout (<= 60%) e
      Bazin pela Mediana de 3-5 anos com Haircut Seletivo JCP (10% Bancos / 0% Seguradoras).
    - Ações Não-Financeiras BESST: Graham + Bazin Mediana sem Haircut JCP.
    """
    if cdi_liquido is None or cdi_bruto is None:
        macro = obter_dados_macro()
        if cdi_liquido is None:
            cdi_liquido = float(macro["cdi_liquido_anual"])
        if cdi_bruto is None:
            cdi_bruto = float(macro.get("cdi", 10.65))

    _precarregar_infos_paralelo(UNIVERSO_BESST)
    ranking = []
    for ticker_sa in UNIVERSO_BESST:
        ticker = ticker_sa.replace(".SA", "")
        info = obter_info_ativo(ticker)

        cotacao = float(info["cotacao"])
        lpa = float(info["lpa"])
        vpa = float(info["vpa"])
        dy = float(info["dy"])
        pl = float(info["pl"])
        pvp = float(info["pvp"])
        roe = float(info.get("roe", 0.0) or 0.0)
        setor = str(info.get("setor", "BESST"))
        divs_3_5a = info.get("dividendos_anuais_3_5a", [])
        payout_hist = info.get("payout_ratio")

        is_banco_seg = _eh_banco_ou_seguradora(ticker, setor)

        val_res = calcular_valuation(
            ticker=ticker,
            setor=setor,
            lpa=lpa,
            vpa=vpa,
            roe=roe,
            dy_projetado=dy,
            preco_atual=cotacao,
            pvp_override=pvp,
            cdi_anual=cdi_bruto,
            payout_historico=payout_hist,
            historico_dividendos=divs_3_5a,
        )

        preco_justo = val_res["preco_justo"]
        preco_teto_val = val_res["preco_teto"]
        margem_pj = val_res["margem_seguranca_pct"]

        preco_bazin = calcular_bazin(
            cotacao=cotacao,
            dy_pct=dy,
            yield_desejado=6.0,
            historico_dividendos=divs_3_5a,
            aplicar_haircut_jcp=is_banco_seg,
            ticker=ticker,
            setor=setor,
        )

        margem_bazin = (
            round(((preco_bazin / cotacao) - 1.0) * 100.0, 2)
            if preco_bazin and cotacao > 0 else None
        )

        spread_cdi = round(dy - cdi_liquido, 2)
        score = val_res["score_triplo"]

        tem_pj = margem_pj is not None and margem_pj > 0
        tem_bazin = margem_bazin is not None and margem_bazin > 0

        if tem_pj and tem_bazin:
            diagnostico = f"🟢 Forte Desconto ({val_res['modelo_utilizado']} + Bazin Seletivo)"
        elif tem_bazin:
            diagnostico = "🔵 Excelente Pagadora (Abaixo do Teto Bazin Mediana)"
        elif tem_pj:
            diagnostico = f"🔵 Desconto Patrimonial ({val_res['modelo_utilizado']})"
        elif dy >= cdi_liquido:
            diagnostico = "🟢 DY Acima do CDI Líquido"
        else:
            diagnostico = "🟡 Preço Justo / Neutro"

        ranking.append({
            "ticker": ticker,
            "nome": info["nome"],
            "setor": setor,
            "modelo_valuation": val_res["modelo_utilizado"],
            "cotacao": cotacao,
            "dy_anual_pct": dy,
            "pl": pl,
            "pvp": pvp,
            "lpa": lpa,
            "vpa": vpa,
            "roe": roe,
            "preco_graham": preco_justo,
            "margem_graham_pct": margem_pj,
            "preco_bazin": preco_bazin,
            "margem_bazin_pct": margem_bazin,
            "preco_teto": preco_teto_val,
            "ke_utilizado": val_res.get("ke_utilizado"),
            "payout_conservador_utilizado": val_res.get("payout_conservador_utilizado"),
            "spread_vs_cdi_liq": spread_cdi,
            "spread_vs_cdi_liquido": spread_cdi,
            "score_defensivo": round(score, 1),
            "diagnostico": diagnostico,
        })

    ranking.sort(key=lambda x: x["score_defensivo"], reverse=True)
    return ranking


def analisar_fiis(cdi_liquido: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Analisa Fundos Imobiliários segmentando em Papel vs Tijolo e aplicando o Pedágio do CDI:
    - Papel (KNCR11, KNIP11): banda 100 pts em 0.90..1.00; penalidade severa > 1.00; alerta CRI < 0.85;
      exige Spread líquido >= +1.0 p.p. sobre CDI Líquido (senão CDB/LCI isenta vence).
    - Tijolo (HGLG11, BTLG11, XPML11): banda 100 pts em 0.85..1.05; interpolação 50->100 em 0.80..0.85.
    """
    if cdi_liquido is None:
        macro = obter_dados_macro()
        cdi_liquido = float(macro["cdi_liquido_anual"])

    _precarregar_infos_paralelo(UNIVERSO_FIIS)
    resultado = []
    for ticker_sa in UNIVERSO_FIIS:
        ticker = ticker_sa.replace(".SA", "")
        info = obter_info_ativo(ticker)

        cotacao = float(info["cotacao"])
        dy = float(info["dy"])
        pvp = float(info["pvp"])
        vpa = float(info["vpa"])
        tipo_fii = _tipo_fii(ticker, info.get("setor", ""))
        spread_cdi = round(dy - cdi_liquido, 2)

        # Pedágio do CDI para FIIs de Papel: DY precisa superar CDI Líquido com prêmio >= +1.0 p.p.
        alerta_pedagio_cdi = bool(tipo_fii == "Papel" and spread_cdi < 1.0)
        if tipo_fii == "Papel":
            if spread_cdi < 1.0:
                pedagio_status = f"⚠️ Pedágio Insuficiente ({spread_cdi:+.2f} p.p.) — Renda Fixa Isenta/CDI Mais Vantajosa"
            else:
                pedagio_status = f"🟢 Prêmio Líquido Adequado ({spread_cdi:+.2f} p.p. sobre CDI Líquido)"
        else:
            pedagio_status = f"Spread Renda vs CDI: {spread_cdi:+.2f} p.p. (+ Proteção Real Imobiliária)"

        val_fii = calcular_valuation(
            ticker=ticker,
            setor=f"FII {tipo_fii}",
            lpa=0.0,
            vpa=vpa,
            roe=dy,
            dy_projetado=dy,
            preco_atual=cotacao,
            pvp_override=pvp,
        )
        saude_fii = calcular_score_saude_balanco(ticker)
        score_seg = min(float(saude_fii.get("score_saude", 75.0)), float(val_fii["score_seguranca"])) if val_fii["alerta_risco_critico"] else float(saude_fii.get("score_saude", val_fii["score_seguranca"]))
        score_triplo = round((val_fii["score_preco"] * 0.35) + (val_fii["score_projecao"] * 0.35) + (score_seg * 0.30), 1)

        if tipo_fii == "Papel":
            if pvp > 0 and pvp < 0.85:
                status = "🔴 Alerta de Risco de Crédito CRI (P/VP < 0.85)"
            elif alerta_pedagio_cdi:
                status = "🟠 Pedágio CDI Fraco — CDB/Caixa Mais Atrativo no Momento"
            elif 0.90 <= pvp <= 1.00:
                status = "🟢 FII Papel Justo (P/VP 0.90–1.00) + Prêmio CDI Saudável"
            elif pvp > 1.00:
                status = "🟡 FII Papel com Ágio (P/VP > 1.00 corrói TIR)"
            else:
                status = "🔵 FII Papel em Transição (P/VP 0.85–0.90)"
        else:
            if pvp > 0 and pvp < 0.80:
                status = "🔴 Risco Grave (P/VP < 0.80 - Segurança Zero)"
            elif 0.85 <= pvp <= 1.05 and dy >= (cdi_liquido - 2.0):
                status = "🟢 Banda Ideal Tijolo (0.85 a 1.05) + DY Atrativo"
            elif 0.85 <= pvp <= 1.05:
                status = "🔵 Banda Tijolo Ideal (Preço Máximo)"
            elif 0.80 <= pvp < 0.85:
                status = "🟡 Deságio Intermediário Tijolo (0.80 a 0.85)"
            else:
                status = "🟡 Acima do Valor Patrimonial (Ágio > 1.05)"

        resultado.append({
            "ticker": ticker,
            "nome": info["nome"],
            "tipo_fii": tipo_fii,
            "cotacao": cotacao,
            "dy_anual_pct": dy,
            "pvp": pvp,
            "vpa": vpa,
            "preco_teto": val_fii["preco_teto"],
            "cdi_liquido_ref": cdi_liquido,
            "cdi_liquido_referencia": cdi_liquido,
            "spread_cdi_pct": spread_cdi,
            "spread_vs_cdi_liquido": spread_cdi,
            "alerta_pedagio_cdi": alerta_pedagio_cdi,
            "pedagio_cdi_status": pedagio_status,
            "alerta_credito_cri": val_fii["alerta_credito_cri"],
            "score_preco": val_fii["score_preco"],
            "score_projecao": val_fii["score_projecao"],
            "score_seguranca": round(score_seg, 1),
            "score_triplo": score_triplo,
            "status": status,
        })

    resultado.sort(key=lambda x: x["score_triplo"], reverse=True)
    return resultado


def _extrair_metricas_tecnicas(df: Optional[pd.DataFrame], cotacao_fallback: float) -> Dict[str, Any]:
    """Extrai RSI Wilder(14), MM200, desvio vs MM200 e retorno 12m usando Adj Close."""
    rsi = 50.0
    mm200 = 0.0
    distancia_mm200_pct = 0.0
    retorno_12m_pct = None

    if df is not None and not df.empty:
        col_preco = "Adj Close" if "Adj Close" in df.columns else ("Close" if "Close" in df.columns else None)
        if col_preco is not None:
            serie_adj = df[col_preco].dropna()
            if len(serie_adj) >= 15:
                rsi = calcular_rsi(serie_adj, periodo=14)
            if len(serie_adj) >= 200:
                mm200 = float(serie_adj.rolling(window=200).mean().iloc[-1])
            elif len(serie_adj) >= 50:
                mm200 = float(serie_adj.rolling(window=50).mean().iloc[-1])

            if len(serie_adj) >= 2 and float(serie_adj.iloc[0]) > 0:
                retorno_12m_pct = round(((float(serie_adj.iloc[-1]) / float(serie_adj.iloc[0])) - 1.0) * 100.0, 2)

            preco_ref_mm = float(serie_adj.iloc[-1]) if len(serie_adj) > 0 else cotacao_fallback
            if mm200 > 0 and preco_ref_mm > 0:
                distancia_mm200_pct = round(((preco_ref_mm / mm200) - 1.0) * 100.0, 2)

    return {
        "rsi_14": rsi,
        "mm200": round(mm200, 2),
        "distancia_mm200_pct": distancia_mm200_pct,
        "retorno_12m_pct": retorno_12m_pct,
    }


def analisar_etfs(cdi_liquido: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Analisa ETFs de Acumulação (BOVA11, DIVO11, IVVB11) por desvio vs MM200,
    RSI(14) e tendência secular de 12 meses (sem penalização por DY inexistente).
    """
    if cdi_liquido is None:
        cdi_liquido = float(obter_dados_macro()["cdi_liquido_anual"])

    _precarregar_infos_paralelo(UNIVERSO_ETFS)
    historicos = baixar_historico_multiplo(UNIVERSO_ETFS, periodo="1y", intervalo="1d")
    resultado: List[Dict[str, Any]] = []

    for ticker_sa in UNIVERSO_ETFS:
        ticker = ticker_sa.replace(".SA", "")
        info = obter_info_ativo(ticker)
        cotacao = float(info.get("cotacao", 0.0) or 0.0)
        df = historicos.get(ticker_sa) if ticker_sa in historicos else historicos.get(ticker)
        met = _extrair_metricas_tecnicas(df, cotacao)

        val = calcular_valuation(
            ticker=ticker,
            setor="ETF de Acumulação",
            lpa=None,
            vpa=None,
            roe=None,
            dy_projetado=0.0,
            preco_atual=cotacao,
            mm200=met["mm200"],
            rsi_14=met["rsi_14"],
            retorno_12m_pct=met["retorno_12m_pct"],
        )
        saude = calcular_score_saude_balanco(ticker)
        score_seg = float(saude.get("score_saude", val["score_seguranca"]))
        score_triplo = round((val["score_preco"] * 0.35) + (val["score_projecao"] * 0.35) + (score_seg * 0.30), 1)

        desv = met["distancia_mm200_pct"]
        if desv <= -3.0 and met["rsi_14"] <= 42.0:
            diag = "🟢 ETF com Desconto vs MM200 & Pullback Favorável"
        elif desv <= 8.0:
            diag = "🔵 ETF em Tendência Secular Equilibrada"
        else:
            diag = f"🟡 ETF Esticado (+{desv:.1f}% acima da MM200) — Dosar Aportes"

        resultado.append({
            "ticker": ticker,
            "nome": info.get("nome", ticker),
            "setor": "ETF de Acumulação",
            "modelo_valuation": val["modelo_utilizado"],
            "cotacao": cotacao,
            "dy_anual_pct": 0.0,
            "pvp": 1.0,
            "mm200": met["mm200"],
            "desvio_mm200_pct": desv,
            "rsi_14": met["rsi_14"],
            "retorno_12m_pct": met["retorno_12m_pct"],
            "preco_justo": val["preco_justo"],
            "preco_teto": val["preco_teto"],
            "margem_seguranca_pct": val["margem_seguranca_pct"],
            "score_preco": val["score_preco"],
            "score_projecao": val["score_projecao"],
            "score_seguranca": round(score_seg, 1),
            "score_triplo": score_triplo,
            "cdi_liquido_ref": cdi_liquido,
            "diagnostico": diag,
        })

    resultado.sort(key=lambda x: x["score_triplo"], reverse=True)
    return resultado


def analisar_bdrs(cdi_liquido: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Analisa os principais BDRs negociados em Reais na B3 (disponíveis no app Nubank),
    isentando-os da trava de Preço Teto de Bazin e calculando o Score de Preço e Projeção
    via Tendência Secular (Cotação vs MM200), RSI 14 (pullback) e Rentabilidade Operacional (ROE / Crescimento).
    """
    if cdi_liquido is None:
        cdi_liquido = float(obter_dados_macro()["cdi_liquido_anual"])

    _precarregar_infos_paralelo(UNIVERSO_BDRS)
    historicos = baixar_historico_multiplo(UNIVERSO_BDRS, periodo="1y", intervalo="1d")
    resultado: List[Dict[str, Any]] = []

    for ticker_sa in UNIVERSO_BDRS:
        ticker = ticker_sa.replace(".SA", "")
        info = obter_info_ativo(ticker)
        cotacao = float(info.get("cotacao", 0.0) or 0.0)
        variacao_dia = float(info.get("variacao_dia", 0.0) or 0.0)
        df = historicos.get(ticker_sa) if ticker_sa in historicos else historicos.get(ticker)
        met = _extrair_metricas_tecnicas(df, cotacao)

        saude = calcular_score_saude_balanco(ticker)
        pl = float(info.get("pl", 0.0) or 0.0)
        roe = float(info.get("roe", 0.0) or 0.0)
        lpa = float(info.get("lpa", 0.0) or 0.0)
        vpa = float(info.get("vpa", 0.0) or 0.0)
        cresc_lucro = info.get("crescimento_lucro_pct")
        desv = float(met["distancia_mm200_pct"])
        rsi = float(met["rsi_14"])
        ret_12m = float(met["retorno_12m_pct"] or 0.0)

        val_bdr = calcular_valuation(
            ticker=ticker,
            setor=info.get("setor", "BDR Global"),
            lpa=lpa,
            vpa=vpa,
            roe=roe,
            dy_projetado=float(info.get("dy", 0.0) or 0.0),
            preco_atual=cotacao,
            mm200=met["mm200"],
            rsi_14=rsi,
            retorno_12m_pct=ret_12m,
            crescimento_lucro_pct=cresc_lucro,
        )

        score_seg = max(float(saude.get("score_saude", 70.0)), float(val_bdr["score_seguranca"]))
        score_preco = float(val_bdr["score_preco"])
        score_projecao = float(val_bdr["score_projecao"])
        score_geral = round((score_preco * 0.35) + (score_projecao * 0.35) + (score_seg * 0.30), 1)

        if (rsi <= 35.0 or variacao_dia <= -3.0) and score_seg >= 65.0:
            diag = "🎯 Pullback / Desconto Tático em BDR Sólido (Isento Bazin)"
        elif desv <= 0.0:
            diag = "🔵 Abaixo da MM200 (Zona de Acumulação Secular)"
        elif rsi >= 70.0:
            diag = "🟡 Esticado (RSI Alto — Dosar Aportes)"
        else:
            diag = "🟢 Tendência Secular & Rentabilidade Operacional Saudáveis" if score_geral >= 75.0 else "⚪ Tendência Neutra / Equilibrada"

        resultado.append({
            "ticker": ticker,
            "nome": info.get("nome", ticker),
            "setor": info.get("setor", "Global / Tech"),
            "modelo_valuation": val_bdr["modelo_utilizado"],
            "isento_teto_bazin": True,
            "preco_teto": None,
            "cotacao": cotacao,
            "variacao_dia_pct": variacao_dia,
            "pl": round(pl, 1) if pl > 0 else 0.0,
            "roe": round(roe, 1),
            "crescimento_lucro_pct": cresc_lucro,
            "mm200": round(float(met["mm200"]), 2),
            "desvio_mm200_pct": desv,
            "rsi_14": rsi,
            "retorno_12m_pct": ret_12m,
            "score_preco": round(score_preco, 1),
            "score_projecao": round(score_projecao, 1),
            "score_seguranca": round(score_seg, 1),
            "score_triplo": score_geral,
            "score_geral": score_geral,
            "diagnostico": diag,
        })

    resultado.sort(key=lambda x: x["score_geral"], reverse=True)
    return resultado


def executar_scanner_oportunidades() -> List[Dict[str, Any]]:
    """
    Scanner de oportunidades técnicas com filtro de qualidade fundamentalista:
    - RSI de 14 períodos com Suavização de Wilder (EMA 27) sobre 'Adj Close'.
    - Qualifica ativos em sobrevenda (RSI <= 35) pelo Score de Segurança:
      * >= 70: 'Sobrevenda de Elite (Pullback Seguro)'
      * < 70: 'Sobrevenda de Alto Risco (Evitar na Transição)'
    """
    todos_Monitorados = list(dict.fromkeys(
        UNIVERSO_BESST + UNIVERSO_CRESCIMENTO + UNIVERSO_FIIS + UNIVERSO_ETFS + UNIVERSO_BDRS
    ))
    _precarregar_infos_paralelo(todos_Monitorados)
    historicos = baixar_historico_multiplo(todos_Monitorados, periodo="1y", intervalo="1d")

    oportunidades = []

    for ticker_bruto in todos_Monitorados:
        ticker_curto = ticker_bruto.replace(".SA", "")
        df = historicos.get(ticker_bruto) if ticker_bruto in historicos else historicos.get(ticker_curto)
        info = obter_info_ativo(ticker_curto)

        cotacao = float(info["cotacao"])
        variacao_dia = float(info["variacao_dia"])
        met = _extrair_metricas_tecnicas(df, cotacao)
        rsi = float(met["rsi_14"])
        mm200 = float(met["mm200"])
        distancia_mm200_pct = float(met["distancia_mm200_pct"])

        saude = calcular_score_saude_balanco(ticker_curto)
        score_seguranca = float(saude.get("score_saude", 50.0))

        is_besst = any(b in ticker_bruto for b in UNIVERSO_BESST)
        is_etf = _eh_etf(ticker_curto, info.get("setor", ""))
        is_bdr = _eh_bdr(ticker_curto, info.get("setor", ""))
        limite_rsi = 35.0

        gatilho_rsi = rsi <= limite_rsi
        gatilho_queda = variacao_dia <= -3.0
        gatilho_mm200 = distancia_mm200_pct <= -5.0

        if gatilho_rsi or (gatilho_queda and (is_besst or is_etf or is_bdr or rsi <= 40.0)):
            if gatilho_rsi and score_seguranca >= 70.0:
                qualificacao_risco = "💎 Sobrevenda de Elite (Pullback Seguro)"
                nivel_oportunidade = "elite"
                acao_sugerida = "Pullback Saudável em Balanço Sólido — Estudo de Aporte Prioritário"
            elif gatilho_rsi:
                qualificacao_risco = "⚠️ Sobrevenda de Alto Risco (Evitar na Transição)"
                nivel_oportunidade = "alto_risco"
                acao_sugerida = "Evitar Compra na Transição — Fundamentos Fracos (Possível Faca Caindo)"
            elif score_seguranca >= 70.0:
                qualificacao_risco = "🔎 Monitoramento Tático (Queda em Ativo Saudável)"
                nivel_oportunidade = "neutro"
                acao_sugerida = "Estudo de Aporte / Aguardar Confirmação Técnica"
            else:
                qualificacao_risco = "⚠️ Queda em Balanço Sensível (Cautela)"
                nivel_oportunidade = "alto_risco"
                acao_sugerida = "Aguardar Melhora Operacional / Não Aumentar Exposição"

            severidade = "🚨 ALTA" if (rsi <= 28.0 or (gatilho_rsi and gatilho_queda)) else "⚠️ MÉDIA"
            motivo = []
            if gatilho_rsi:
                motivo.append(f"RSI Wilder (Adj Close) em {rsi:.1f} (<= 35)")
            if gatilho_queda:
                motivo.append(f"Forte queda no dia ({variacao_dia:.2f}%)")
            if gatilho_mm200:
                motivo.append(f"{distancia_mm200_pct:.1f}% abaixo da MM200")
            motivo.append(f"Score Segurança: {score_seguranca:.0f}/100")

            tipo_setor = (
                "ETF Índice" if is_etf
                else ("BDR (Global/Nubank)" if is_bdr
                else ("BESST (Defensivo)" if is_besst
                else ("FII" if _eh_fii(ticker_curto, info.get("setor", "")) else "Crescimento/Geral")))
            )

            oportunidades.append({
                "ticker": ticker_curto,
                "nome": info["nome"],
                "tipo_setor": tipo_setor,
                "cotacao": cotacao,
                "variacao_dia_pct": variacao_dia,
                "rsi_14": rsi,
                "mm200": round(mm200, 2),
                "distancia_mm200_pct": distancia_mm200_pct,
                "score_seguranca": round(score_seguranca, 1),
                "qualificacao_risco": qualificacao_risco,
                "nivel_oportunidade": nivel_oportunidade,
                "severidade": severidade,
                "motivos": " | ".join(motivo),
                "acao_sugerida": acao_sugerida,
            })

    prioridade = {"elite": 0, "neutro": 1, "alto_risco": 2}
    oportunidades.sort(key=lambda x: (prioridade.get(x["nivel_oportunidade"], 9), x["rsi_14"]))
    return oportunidades


def obter_top_melhores_compras(cdi_liquido: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Motor Quantitativo de Melhores Opções de Compra com Valuation Segmentado e SanityGate:
    - Bancos/Seguradoras: Gordon Dinâmico + Bazin c/ Haircut Seletivo (10% Bancos / 0% Seguradoras).
    - FIIs: Papel vs Tijolo + Pedágio do CDI + Score de Segurança por classe.
    - ETFs de Acumulação: MM200, RSI(14) e Tendência Secular.
    - Ações BESST Tradicionais: Benjamin Graham + Bazin Mediana.
    - SanityGate (`validar_dados_yfinance`): Ativos marcados como 'Suspeito' não podem assumir o Top 3.
    """
    macro = obter_dados_macro()
    if cdi_liquido is None:
        cdi_liquido = float(macro["cdi_liquido_anual"])
    cdi_bruto = float(macro.get("cdi", 10.65))

    acoes_besst = analisar_universo_besst(cdi_liquido=cdi_liquido, cdi_bruto=cdi_bruto)
    fiis = analisar_fiis(cdi_liquido=cdi_liquido)
    etfs = analisar_etfs(cdi_liquido=cdi_liquido)

    candidatos: List[Dict[str, Any]] = []

    for acao in acoes_besst:
        ticker = acao["ticker"]
        setor = acao.get("setor", "BESST")
        saude = calcular_score_saude_balanco(ticker)

        val = calcular_valuation(
            ticker=ticker,
            setor=setor,
            lpa=acao.get("lpa"),
            vpa=acao.get("vpa"),
            roe=acao.get("roe"),
            dy_projetado=acao.get("dy_anual_pct"),
            preco_atual=acao.get("cotacao", 0.0),
            pvp_override=acao.get("pvp"),
            cdi_anual=cdi_bruto,
            payout_conservador=acao.get("payout_conservador_utilizado"),
        )

        score_preco = val["score_preco"]
        score_projecao = val["score_projecao"]
        score_seguranca = (
            min(float(saude.get("score_saude", 70.0)), float(val["score_seguranca"]))
            if val["alerta_risco_critico"]
            else float(saude.get("score_saude", 70.0))
        )

        score_geral = round((score_preco * 0.35) + (score_projecao * 0.35) + (score_seguranca * 0.30), 1)

        dl_ebitda = saude.get("divida_liq_ebitda")
        lpa_val = float(acao.get("lpa") or 0.0)
        if lpa_val < 0:
            nivel_alerta = "neg"
        elif dl_ebitda is not None and float(dl_ebitda) > 2.5:
            nivel_alerta = "warn"
        else:
            nivel_alerta = saude.get("nivel_alerta", "normal")

        if nivel_alerta == "neg":
            veredito = "🔴 Risco Crítico: Prejuízo Contábil ou Deterioração"
            selo_cor = "#991b1b"
        elif score_geral >= 82.0:
            veredito = f"💎 Compra Ouro ({val['modelo_utilizado']}): Forte Desconto + Balanço Sólido"
            selo_cor = "#15803d"
        elif score_geral >= 72.0:
            veredito = f"🟢 Compra Confortável ({val['modelo_utilizado']}): Boa Margem e Risco Baixo"
            selo_cor = "#1b5e3a"
        elif score_geral >= 58.0:
            veredito = "🔵 Aporte Regular: Preço Justo com Renda Passiva Perene"
            selo_cor = "#2563eb"
        else:
            veredito = "🟡 Observação: Aguardar Maior Margem de Segurança"
            selo_cor = "#b45309"

        candidatos.append({
            "ticker": ticker,
            "nome": acao.get("nome", ticker),
            "tipo": "Banco / Seguradora" if _eh_banco_ou_seguradora(ticker, setor) else "Ação BESST",
            "tipo_fii": None,
            "setor": setor,
            "modelo_valuation": val["modelo_utilizado"],
            "cotacao": acao.get("cotacao", 0.0),
            "dy_anual_pct": acao.get("dy_anual_pct", 0.0),
            "pl": acao.get("pl", 8.0),
            "pvp": acao.get("pvp", 1.0),
            "lpa": lpa_val,
            "divida_liq_ebitda": dl_ebitda,
            "nivel_alerta": nivel_alerta,
            "preco_teto_bazin": acao.get("preco_bazin"),
            "preco_justo_graham": val["preco_justo"],
            "preco_teto": val["preco_teto"],
            "margem_graham_pct": val["margem_seguranca_pct"],
            "margem_bazin_pct": acao.get("margem_bazin_pct"),
            "spread_vs_cdi_liquido": acao.get("spread_vs_cdi_liquido"),
            "alerta_pedagio_cdi": False,
            "alerta_credito_cri": False,
            "score_preco": round(score_preco, 1),
            "score_projecao": round(score_projecao, 1),
            "score_seguranca": round(score_seguranca, 1),
            "score_geral": score_geral,
            "veredito": veredito,
            "selo_cor": selo_cor,
            "pontos_fortes": saude.get("pontos_fortes", [])[:2],
        })

    for fii in fiis:
        ticker = fii["ticker"]
        tipo_fii = fii.get("tipo_fii", "Tijolo")
        pvp = float(fii.get("pvp", 1.0) or 1.0)
        dy = float(fii.get("dy_anual_pct", 0.0) or 0.0)

        score_preco = float(fii["score_preco"])
        score_projecao = float(fii["score_projecao"])
        score_seguranca = float(fii["score_seguranca"])
        score_geral = float(fii["score_triplo"])
        alerta_pedagio = bool(fii.get("alerta_pedagio_cdi", False))
        alerta_cri = bool(fii.get("alerta_credito_cri", False))

        if (tipo_fii == "Tijolo" and pvp < 0.80) or alerta_cri:
            nivel_alerta = "neg"
            veredito = f"🔴 Risco Crítico: FII {tipo_fii} com Deságio Severo (P/VP {pvp:.2f}x)"
            selo_cor = "#991b1b"
        elif alerta_pedagio:
            nivel_alerta = "warn"
            veredito = "🟠 Pedágio CDI Insuficiente: Renda Fixa Isenta/CDB Mais Vantajosa"
            selo_cor = "#b45309"
        elif score_geral >= 80.0:
            nivel_alerta = "normal"
            veredito = f"🏢 FII {tipo_fii} Banda Ideal: Rendimento Mensal Isento"
            selo_cor = "#15803d"
        else:
            nivel_alerta = "normal" if ((tipo_fii == "Papel" and pvp <= 1.00) or (tipo_fii == "Tijolo" and pvp <= 1.05)) else "warn"
            veredito = f"🏢 FII {tipo_fii} Estável: Renda Mensal Recorrente"
            selo_cor = "#2563eb"

        candidatos.append({
            "ticker": ticker,
            "nome": fii.get("nome", ticker),
            "tipo": "FII",
            "tipo_fii": tipo_fii,
            "setor": f"FII {tipo_fii}",
            "modelo_valuation": f"Banda P/VP (FII {tipo_fii})",
            "cotacao": fii.get("cotacao", 0.0),
            "dy_anual_pct": dy,
            "pl": 10.0,
            "pvp": pvp,
            "lpa": 0.0,
            "divida_liq_ebitda": None,
            "nivel_alerta": nivel_alerta,
            "preco_teto_bazin": None,
            "preco_justo_graham": fii.get("vpa"),
            "preco_teto": fii.get("preco_teto"),
            "margem_graham_pct": round((1.0 - pvp) * 100.0, 2) if pvp else 0.0,
            "margem_bazin_pct": round((1.0 - pvp) * 100.0, 2) if pvp else 0.0,
            "spread_vs_cdi_liquido": fii.get("spread_vs_cdi_liquido"),
            "alerta_pedagio_cdi": alerta_pedagio,
            "alerta_credito_cri": alerta_cri,
            "score_preco": round(score_preco, 1),
            "score_projecao": round(score_projecao, 1),
            "score_seguranca": round(score_seguranca, 1),
            "score_geral": score_geral,
            "veredito": veredito,
            "selo_cor": selo_cor,
            "pontos_fortes": [f"Renda Mensal Isenta • FII {tipo_fii}", fii.get("pedagio_cdi_status", f"P/VP {pvp:.2f}x")],
        })

    for etf in etfs:
        desv = float(etf.get("desvio_mm200_pct") or 0.0)
        score_geral = float(etf["score_triplo"])
        nivel_alerta = "warn" if desv > 12.0 else "normal"
        candidatos.append({
            "ticker": etf["ticker"],
            "nome": etf["nome"],
            "tipo": "ETF de Acumulação",
            "tipo_fii": None,
            "setor": "ETF de Acumulação",
            "modelo_valuation": etf["modelo_valuation"],
            "cotacao": etf["cotacao"],
            "dy_anual_pct": 0.0,
            "pl": 12.0,
            "pvp": 1.0,
            "lpa": 1.0,
            "divida_liq_ebitda": None,
            "nivel_alerta": nivel_alerta,
            "preco_teto_bazin": None,
            "preco_justo_graham": etf.get("preco_justo"),
            "preco_teto": etf.get("preco_teto"),
            "margem_graham_pct": etf.get("margem_seguranca_pct"),
            "margem_bazin_pct": etf.get("desvio_mm200_pct"),
            "spread_vs_cdi_liquido": None,
            "alerta_pedagio_cdi": False,
            "alerta_credito_cri": False,
            "score_preco": etf["score_preco"],
            "score_projecao": etf["score_projecao"],
            "score_seguranca": etf["score_seguranca"],
            "score_geral": score_geral,
            "veredito": etf["diagnostico"],
            "selo_cor": "#15803d" if score_geral >= 78.0 else ("#2563eb" if score_geral >= 65.0 else "#b45309"),
            "pontos_fortes": [f"Desvio MM200: {desv:+.1f}% | RSI(14): {etf.get('rsi_14', 50):.1f}", "Acumulação automática com baixa volatilidade específica"],
        })

    if not candidatos:
        return []

    # Aplica o Validador de Qualidade (SanityGate)
    df_cand = pd.DataFrame(candidatos)
    df_auditado = validar_dados_yfinance(df_cand)
    registros = df_auditado.to_dict(orient="records")

    # Ordena os validados primeiro pelo score_geral para garantir que 'Suspeito' NUNCA assuma o Top 3
    validados = sorted(
        [r for r in registros if r.get("status_auditoria") == "Validado"],
        key=lambda x: x["score_geral"],
        reverse=True,
    )
    suspeitos = sorted(
        [r for r in registros if r.get("status_auditoria") == "Suspeito"],
        key=lambda x: x["score_geral"],
        reverse=True,
    )

    for s in suspeitos:
        s["veredito"] = f"⚠️ Dados Suspeitos (SanityGate) • {s['veredito']}"
        if s.get("nivel_alerta") == "normal":
            s["nivel_alerta"] = "warn"

    # Garante os Top 3 exclusivamente entre ativos Validados (se houver ao menos 3 validados)
    if len(validados) >= 3:
        top_3 = validados[:3]
        restante = sorted(validados[3:] + suspeitos, key=lambda x: (x.get("status_auditoria") == "Validado", x["score_geral"]), reverse=True)
        return top_3 + restante

    return validados + suspeitos
