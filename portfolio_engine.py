"""
Módulo de Gestão de Carteira Consolidada:
- Renda Fixa (Nubank Caixinhas e Títulos)
- Renda Variável (Ações, FIIs, ETFs)
- Simulador de Imposto de Renda e Alerta de DARF (Regra dos R$ 20k, Dedo-Duro 0,005% e FIIs a 20%)
- Algoritmo de Aporte Inteligente com roteamento automático para Mercado Fracionário (Ticker + 'F')
"""
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from config import (
    LIMITE_ISENCAO_ACOES_MES,
    ALIQUOTA_IR_ACOES,
    ALIQUOTA_IR_FIIS,
    CODIGO_DARF_RENDA_VARIAVEL,
    FIIS_PAPEL,
    UNIVERSO_ETFS,
    UNIVERSO_BDRS,
)
from data_engine import calcular_rendimento_nubank, obter_dados_macro, obter_info_ativo, obter_infos_multiplos

SET_FIIS_PAPEL_CARTEIRA = {t.upper() for t in FIIS_PAPEL} | {"MXRF11"}
SET_BDRS_CARTEIRA = {t.upper() for t in UNIVERSO_BDRS}

CLASSES_ALOCACAO = ["Renda Fixa", "Ações", "FIIs", "ETFs", "BDRs"]
METAS_CLASSE_PADRAO = {"Renda Fixa": 20.0, "Ações": 50.0, "FIIs": 25.0, "ETFs": 5.0, "BDRs": 0.0}


def normalizar_classe(classe: str) -> str:
    """Padroniza o nome da classe (aceita 'Ações', 'Ação', 'acoes', 'FII', 'ETF', 'BDR'...)."""
    c = str(classe or "").strip().lower()
    if "fii" in c or "imobili" in c:
        return "FIIs"
    if "etf" in c:
        return "ETFs"
    if "bdr" in c:
        return "BDRs"
    return "Ações"


def formatar_ticker_fracionario(ticker: str, classe: str, quantidade_sugerida: int) -> str:
    """
    Mercado Fracionário Inteligente:
    Se a classe for 'Ação' / 'Ações' e a quantidade sugerida estiver entre 1 e 99 unidades,
    anexa 'F' ao ticker (ex: BBAS3 -> BBAS3F). Se for FII, ETF ou BDR, mantém inalterado.
    """
    ticker_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    if not ticker_limpo:
        return ticker_limpo

    classe_norm = normalizar_classe(classe)
    if classe_norm == "Ações" and not _eh_bdr_renda_variavel(ticker_limpo, classe) and 1 <= int(quantidade_sugerida) <= 99:
        if not ticker_limpo.endswith("F"):
            return f"{ticker_limpo}F"
    return ticker_limpo


def processar_renda_fixa(
    itens_rf: List[Dict[str, Any]],
    cdi_anual: Optional[float] = None,
    ipca_anual: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Processa a carteira de Renda Fixa (Nubank, CDBs, Tesouro) em Base 252 dias úteis.
    Separa Reserva de Emergência vs. Investimento/Caixa de Oportunidade e calcula
    o rendimento real descontado do IPCA pela Equação de Fisher.
    """
    if cdi_anual is None or ipca_anual is None:
        macro = obter_dados_macro()
        if cdi_anual is None:
            cdi_anual = float(macro["cdi"])
        if ipca_anual is None:
            ipca_anual = float(macro.get("ipca_12m", macro.get("ipca", 4.5)))

    ipca_dec = max(0.0, float(ipca_anual) / 100.0)
    itens_processados = []
    total_patrimonio_rf = 0.0
    total_reserva_emergencia = 0.0
    total_caixa_oportunidade = 0.0
    total_rendimento_mensal_rf = 0.0
    total_rendimento_mensal_real_rf = 0.0

    for item in itens_rf:
        nome = item.get("nome", "Caixinha Nubank")
        tipo = item.get("tipo", "Reserva de Emergência")
        valor_aplicado = float(item.get("valor_aplicado", 0.0))
        saldo_atual = float(item.get("saldo_atual", valor_aplicado))
        taxa_cdi = float(item.get("taxa_cdi", 100.0))
        dias_corridos = int(item.get("dias_corridos", 365))

        calc = calcular_rendimento_nubank(
            saldo_atual=saldo_atual,
            percentual_cdi=taxa_cdi,
            dias_corridos=dias_corridos,
            cdi_anual=cdi_anual,
            valor_aplicado=valor_aplicado if valor_aplicado > 0 else None,
        )

        rend_mensal = calc["rendimento_mensal_liquido"]
        taxa_liq_anual = calc["taxa_liquida_anual_pct"]
        taxa_real_anual = max(0.0, ((1.0 + (taxa_liq_anual / 100.0)) / (1.0 + ipca_dec)) - 1.0)
        rend_mensal_real = round(saldo_atual * ((1.0 + taxa_real_anual) ** (1.0 / 12.0) - 1.0), 2)

        total_patrimonio_rf += saldo_atual
        total_rendimento_mensal_rf += rend_mensal
        total_rendimento_mensal_real_rf += rend_mensal_real

        if "emergência" in tipo.lower() or "emergencia" in tipo.lower():
            total_reserva_emergencia += saldo_atual
        else:
            total_caixa_oportunidade += saldo_atual

        itens_processados.append({
            "nome": nome,
            "tipo": tipo,
            "valor_aplicado": round(valor_aplicado, 2),
            "saldo_atual": round(saldo_atual, 2),
            "taxa_cdi": taxa_cdi,
            "dias_corridos": dias_corridos,
            "dias_uteis": calc.get("dias_uteis"),
            "aliquota_ir_pct": round(calc["aliquota_ir"] * 100.0, 1),
            "taxa_liq_anual_pct": taxa_liq_anual,
            "taxa_liq_mensal_pct": calc.get("taxa_liquida_mensal_pct", 0.0),
            "rendimento_mensal_liquido": rend_mensal,
            "rendimento_mensal_real": rend_mensal_real,
            "rendimento_bruto_acumulado": calc.get("rendimento_bruto_acumulado", 0.0),
            "ir_acumulado": calc.get("ir_acumulado", 0.0),
            "rendimento_liquido_acumulado": calc.get("rendimento_liquido_acumulado", 0.0),
            "saldo_liquido_resgate": calc.get("saldo_liquido_resgate", saldo_atual),
        })

    return {
        "itens": itens_processados,
        "total_patrimonio_rf": round(total_patrimonio_rf, 2),
        "total_reserva_emergencia": round(total_reserva_emergencia, 2),
        "total_caixa_oportunidade": round(total_caixa_oportunidade, 2),
        "total_rendimento_mensal_rf": round(total_rendimento_mensal_rf, 2),
        "total_rendimento_mensal_liquido": round(total_rendimento_mensal_rf, 2),
        "total_rendimento_mensal_real_rf": round(total_rendimento_mensal_real_rf, 2),
    }


def calcular_cobertura_reserva(
    saldo_reserva_rf: float,
    custo_vida_mensal: float,
    meta_meses: int = 6,
) -> Dict[str, Any]:
    """
    Trava de Reserva de Emergência (Regra Gatekeeper):
    - Cruza o saldo da Reserva de Renda Fixa de liquidez imediata contra (Gastos Fixos + Variáveis).
    - Se Cobertura < meta_meses (padrão 6 meses), bloqueia de 50% a 100% da sobra líquida mensal
      exclusivamente para recomposição da Renda Fixa.
    """
    saldo = max(0.0, float(saldo_reserva_rf or 0.0))
    custo = max(0.0, float(custo_vida_mensal or 0.0))
    meta = max(1, int(meta_meses or 6))

    meta_valor_rs = round(custo * meta, 2)
    cobertura_meses = round(saldo / custo, 2) if custo > 0 else float(meta)
    deficit_rs = round(max(0.0, meta_valor_rs - saldo), 2)
    gatekeeper_ativo = bool(custo > 0 and cobertura_meses < float(meta))

    if not gatekeeper_ativo:
        pct_minimo_rf = 0.0
        status = f"🟢 Reserva Blindada ({cobertura_meses:.1f} meses >= meta de {meta} meses)"
    elif cobertura_meses < (meta * 0.5):
        pct_minimo_rf = 100.0
        status = f"🔴 Gatekeeper Crítico: Reserva em {cobertura_meses:.1f} meses (< {meta/2:.0f}m) — 100% da sobra para Renda Fixa"
    else:
        progresso_deficit = (meta - cobertura_meses) / max(0.5, meta * 0.5)
        pct_minimo_rf = round(min(100.0, max(50.0, 50.0 + (progresso_deficit * 50.0))), 1)
        status = (
            f"🟡 Gatekeeper Ativo: Reserva em {cobertura_meses:.2f}/{meta} meses "
            f"(faltam R$ {deficit_rs:,.2f}) — mínimo de {pct_minimo_rf:.0f}% da sobra travado em Renda Fixa"
        )

    return {
        "saldo_reserva_rf": round(saldo, 2),
        "custo_vida_mensal": round(custo, 2),
        "meta_meses": meta,
        "meta_valor_rs": meta_valor_rs,
        "cobertura_meses": cobertura_meses,
        "deficit_rs": deficit_rs,
        "gatekeeper_ativo": gatekeeper_ativo,
        "pct_sobra_minimo_rf": pct_minimo_rf,
        "status": status,
    }


def calcular_renda_passiva_real_e_fire(
    rf_calc: Dict[str, Any],
    rv_calc: Dict[str, Any],
    ipca_anual: float = 4.5,
    custo_vida_mensal: float = 0.0,
    gastos_fixos_mensal: float = 0.0,
) -> Dict[str, Any]:
    """
    Simulador FIRE Real (Equação de Fisher):
    - Na Renda Fixa CDI e nos FIIs de Papel (CRIs atrelados a CDI/IPCA), desconta a inflação (IPCA)
      via Equação de Fisher para calcular apenas o Juro Real disponível para consumo sem corroer
      o poder de compra do patrimônio principal.
    - Para Ações de Dividendos e FIIs de Tijolo, o provento tende a ser corrigido pela economia real.
    """
    ipca_dec = max(0.0, float(ipca_anual or 0.0) / 100.0)
    rf_nominal_mensal = float(rf_calc.get("total_rendimento_mensal_rf", 0.0) or 0.0)
    rf_real_mensal = float(rf_calc.get("total_rendimento_mensal_real_rf", 0.0) or 0.0)

    if rf_real_mensal <= 0 and rf_nominal_mensal > 0:
        pat_rf = float(rf_calc.get("total_patrimonio_rf", 0.0) or 0.0)
        if pat_rf > 0:
            taxa_nom_anual = (1.0 + (rf_nominal_mensal / pat_rf)) ** 12 - 1.0
            taxa_real_anual = max(0.0, ((1.0 + taxa_nom_anual) / (1.0 + ipca_dec)) - 1.0)
            rf_real_mensal = pat_rf * ((1.0 + taxa_real_anual) ** (1.0 / 12.0) - 1.0)

    rv_nominal_mensal = 0.0
    rv_real_mensal = 0.0
    rv_papel_nominal_mensal = 0.0
    rv_papel_real_mensal = 0.0

    for item in rv_calc.get("itens", []):
        ticker = str(item.get("ticker", "")).replace(".SA", "").strip().upper()
        pat_item = float(item.get("patrimonio_atual", 0.0) or 0.0)
        dy_item = float(item.get("dy_anual", 0.0) or 0.0)
        rend_nom = float(item.get("renda_mensal_estimada", (pat_item * (dy_item / 100.0)) / 12.0) or 0.0)
        rv_nominal_mensal += rend_nom

        if ticker in SET_FIIS_PAPEL_CARTEIRA:
            dy_real_anual = max(0.0, ((1.0 + (dy_item / 100.0)) / (1.0 + ipca_dec)) - 1.0)
            rend_real = (pat_item * dy_real_anual) / 12.0
            rv_papel_nominal_mensal += rend_nom
            rv_papel_real_mensal += rend_real
            rv_real_mensal += rend_real
        else:
            rv_real_mensal += rend_nom

    renda_nominal_total = rf_nominal_mensal + rv_nominal_mensal
    renda_real_total = rf_real_mensal + rv_real_mensal

    pat_total = float(rf_calc.get("total_patrimonio_rf", 0.0) or 0.0) + float(rv_calc.get("total_patrimonio_rv", 0.0) or 0.0)
    yield_real_portfolio = ((renda_real_total * 12.0) / pat_total) if pat_total > 0 and renda_real_total > 0 else 0.055
    yield_real_efetivo = max(0.03, yield_real_portfolio)

    patrimonio_fire_real = round((custo_vida_mensal * 12.0) / yield_real_efetivo, 2) if custo_vida_mensal > 0 else 0.0
    progresso_fire_real_pct = round(min(100.0, (pat_total / patrimonio_fire_real) * 100.0), 1) if patrimonio_fire_real > 0 else 0.0

    cob_fixos_real = round((renda_real_total / gastos_fixos_mensal) * 100.0, 1) if gastos_fixos_mensal > 0 else 0.0
    cob_custo_real = round((renda_real_total / custo_vida_mensal) * 100.0, 1) if custo_vida_mensal > 0 else 0.0
    cob_fixos_nom = round((renda_nominal_total / gastos_fixos_mensal) * 100.0, 1) if gastos_fixos_mensal > 0 else 0.0

    return {
        "ipca_referencia_pct": round(ipca_dec * 100.0, 2),
        "renda_nominal_mensal_total": round(renda_nominal_total, 2),
        "renda_real_mensal_total": round(renda_real_total, 2),
        "rf_nominal_mensal": round(rf_nominal_mensal, 2),
        "rf_real_mensal": round(rf_real_mensal, 2),
        "rv_nominal_mensal": round(rv_nominal_mensal, 2),
        "rv_real_mensal": round(rv_real_mensal, 2),
        "rv_papel_nominal_mensal": round(rv_papel_nominal_mensal, 2),
        "rv_papel_real_mensal": round(rv_papel_real_mensal, 2),
        "yield_real_anual_portfolio_pct": round(yield_real_portfolio * 100.0, 2),
        "patrimonio_fire_real": patrimonio_fire_real,
        "progresso_fire_real_pct": progresso_fire_real_pct,
        "cobertura_gastos_fixos_real_pct": cob_fixos_real,
        "cobertura_custo_vida_real_pct": cob_custo_real,
        "cobertura_gastos_fixos_nominal_pct": cob_fixos_nom,
    }


def processar_renda_variavel(
    itens_rv: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Processa a carteira de Renda Variável atualizando cotações, P&L,
    renda passiva estimada e pesos da carteira.
    """
    itens_processados = []
    total_custo_rv = 0.0
    total_patrimonio_rv = 0.0
    total_renda_mensal_rv = 0.0

    tickers_batch = [str(i.get("ticker", "")).strip().upper() for i in (itens_rv or []) if i.get("ticker")]
    if tickers_batch and getattr(obter_info_ativo, "__module__", "") == "data_engine":
        obter_infos_multiplos(tickers_batch, max_workers=8)

    for item in itens_rv:
        ticker = str(item.get("ticker", "")).strip().upper()
        if not ticker:
            continue

        classe = item.get("classe", "Ações")
        quantidade = int(item.get("quantidade", 0))
        preco_medio = float(item.get("preco_medio", 0.0))
        peso_alvo = float(item.get("peso_alvo", 0.0))

        info = obter_info_ativo(ticker)
        cotacao_atual = float(info.get("cotacao", 0.0) or 0.0)
        if cotacao_atual <= 0.0:
            cotacao_atual = preco_medio

        custo_total = round(quantidade * preco_medio, 2)
        patrimonio_atual = round(quantidade * cotacao_atual, 2)
        lucro_prejuizo_bruto = round(patrimonio_atual - custo_total, 2)
        lucro_prejuizo_pct = round(((cotacao_atual / preco_medio) - 1.0) * 100.0, 2) if preco_medio > 0 else 0.0

        dy_anual = float(info.get("dy", 0.0) or 0.0)
        renda_mensal_estimada = round((patrimonio_atual * (dy_anual / 100.0)) / 12.0, 2)

        total_custo_rv += custo_total
        total_patrimonio_rv += patrimonio_atual
        total_renda_mensal_rv += renda_mensal_estimada

        itens_processados.append({
            "ticker": ticker,
            "classe": classe,
            "quantidade": quantidade,
            "preco_medio": preco_medio,
            "cotacao_atual": cotacao_atual,
            "custo_total": custo_total,
            "patrimonio_atual": patrimonio_atual,
            "lucro_prejuizo_bruto": lucro_prejuizo_bruto,
            "lucro_prejuizo_pct": lucro_prejuizo_pct,
            "dy_anual": dy_anual,
            "renda_mensal_estimada": renda_mensal_estimada,
            "renda_passiva_mensal": renda_mensal_estimada,
            "peso_alvo": peso_alvo,
            "peso_atual": 0.0,
            "desvio_peso": 0.0
        })

    for item in itens_processados:
        peso_atual = (item["patrimonio_atual"] / total_patrimonio_rv * 100.0) if total_patrimonio_rv > 0 else 0.0
        desvio = round(peso_atual - item["peso_alvo"], 2)
        item["peso_atual"] = round(peso_atual, 2)
        item["desvio_peso"] = desvio

    lucro_total_rv = round(total_patrimonio_rv - total_custo_rv, 2)
    rentabilidade_total_rv_pct = round((lucro_total_rv / total_custo_rv * 100.0), 2) if total_custo_rv > 0 else 0.0

    return {
        "itens": itens_processados,
        "total_custo_rv": round(total_custo_rv, 2),
        "total_patrimonio_rv": round(total_patrimonio_rv, 2),
        "lucro_total_rv": lucro_total_rv,
        "rentabilidade_total_rv_pct": rentabilidade_total_rv_pct,
        "total_renda_mensal_rv": round(total_renda_mensal_rv, 2),
        "total_renda_passiva_mensal": round(total_renda_mensal_rv, 2)
    }


ETFS_RENDA_VARIAVEL_B3 = {
    "BOVA11", "IVVB11", "DIVO11", "SMAL11", "HASH11", "NASD11",
    "GOLD11", "SPXI11", "ACWI11", "XINA11", "BOVV11", "NDIV11",
    "BRAX11", "ECOO11", "PIBB11", "FIND11", "MATB11", "GOVE11", "ISUS11",
    "WRLD11",
} | {t.upper() for t in UNIVERSO_ETFS}


def _eh_etf_renda_variavel(ticker: str, classe: str) -> bool:
    """
    Verifica se o ativo é um ETF de Renda Variável (pelo ticker B3 ou pela classe informada).
    ETFs NÃO possuem isenção mensal de R$ 20.000,00 em Swing Trade.
    """
    ticker_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    if ticker_limpo.endswith("F") and len(ticker_limpo) > 5:
        ticker_limpo = ticker_limpo[:-1]
    classe_norm = str(classe or "").strip().upper()
    return ("ETF" in classe_norm) or (ticker_limpo in ETFS_RENDA_VARIAVEL_B3)


def _eh_bdr_renda_variavel(ticker: str, classe: str) -> bool:
    """
    Verifica se o ativo é um BDR negociado na B3 (ex: NVDC34, AAPL34 no app do Nubank).
    Assim como ETFs, BDRs NÃO possuem isenção mensal de R$ 20.000,00 em Swing Trade
    e não utilizam o sufixo fracionário 'F'.
    """
    ticker_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    classe_norm = str(classe or "").strip().upper()
    return (
        ("BDR" in classe_norm)
        or (ticker_limpo in SET_BDRS_CARTEIRA)
        or (len(ticker_limpo) == 6 and ticker_limpo.endswith(("32", "33", "34", "35")))
    )


def _eh_direito_subscricao_fii(ticker: str) -> bool:
    """
    Verifica se o ticker representa Direitos/Recibos de Subscrição de FIIs (finalizados em '12',
    ex: HGLG12, MXRF12, KNCR12, XPML12).
    """
    ticker_limpo = str(ticker or "").replace(".SA", "").strip().upper()
    return len(ticker_limpo) >= 6 and ticker_limpo.endswith("12")


def simular_venda_e_ir(
    ticker: str,
    classe: str,
    quantidade_venda: int,
    preco_venda: float,
    preco_medio: float,
    vendas_acumuladas_mes: float = 0.0,
    tipo_operacao: str = "Swing Trade",
    taxas_corretora: float = 0.0,
    prejuizo_acumulado_acoes_etfs: float = 0.0,
    prejuizo_acumulado_fiis: float = 0.0,
) -> Dict[str, Any]:
    """
    Simulador Fiscal Avançado de Venda e Cálculo de Imposto de Renda / DARF (Receita Federal / B3):
    - Memória de Prejuízos Acumulados: abate prejuízos da mesma categoria (`Ações/ETFs` 15% ou `FIIs` 20%)
      antes de calcular a DARF (vendas isentas <= R$ 20k de Ações NÃO consomem prejuízo acumulado).
    - Isolamento R$ 20k: a soma mensal da isenção considera EXCLUSIVAMENTE vendas de Ações em Swing Trade
      (FIIs e ETFs nunca entram na contagem dos R$ 20.000,00).
    - Trava A (ETFs de Renda Variável): sem isenção R$ 20k -> 15% sobre lucro após compensação.
    - Trava B (Direitos de Subscrição FII - final '12'): PM=0 e 20% sobre 100% da venda bruta.
    - Dedo-Duro da Receita (Swing Trade): `irrf = valor_total_venda * 0.00005` (0,005%).
    """
    try:
        ticker_limpo = str(ticker or "").replace(".SA", "").strip().upper()
        qtd = max(0, int(quantidade_venda))
        p_venda = max(0.0, float(preco_venda))
        taxas_corr = round(max(0.0, float(taxas_corretora or 0.0)), 2)
        is_day_trade = "day" in str(tipo_operacao).lower()

        prej_ac_etf = round(max(0.0, float(prejuizo_acumulado_acoes_etfs or 0.0)), 2)
        prej_fii = round(max(0.0, float(prejuizo_acumulado_fiis or 0.0)), 2)
        novo_prej_ac_etf = prej_ac_etf
        novo_prej_fii = prej_fii
        prejuizo_compensado = 0.0
        base_calculo_ir = 0.0

        # Trava B: Direitos de Subscrição de FIIs (Tickers finalizados em '12') -> PM = 0.0
        is_direito_fii_12 = _eh_direito_subscricao_fii(ticker_limpo)
        if is_direito_fii_12:
            p_medio = 0.0
        else:
            p_medio = max(0.0, float(preco_medio))

        valor_venda = round(float(qtd) * p_venda, 2)
        custo_total = round(float(qtd) * p_medio, 2)
        lucro_bruto = round((p_venda - p_medio) * float(qtd), 2)

        # Dedo-Duro da Receita Federal: 0,005% sobre o valor total da venda em Swing Trade
        irrf_dedo_duro = (
            round(valor_venda * 0.00005, 4)
            if not is_day_trade
            else round(max(0.0, lucro_bruto) * 0.01, 4)
        )

        # Resultado Líquido: (preco_venda - preco_medio) * qtd - taxas_corretora - irrf
        resultado_liquido = round(lucro_bruto - taxas_corr - irrf_dedo_duro, 2)
        lucro_pct = round((resultado_liquido / custo_total) * 100.0, 2) if custo_total > 0 else (100.0 if valor_venda > 0 else 0.0)

        # Identificação de Classe Fiscal (Trava A e Trava B)
        is_etf = _eh_etf_renda_variavel(ticker_limpo, classe)
        is_bdr = (not is_etf) and (not is_direito_fii_12) and _eh_bdr_renda_variavel(ticker_limpo, classe)
        classe_normalizada = str(classe or "Ações").strip().capitalize()
        if is_direito_fii_12:
            classe_normalizada = "Direito de Subscrição FII (Final 12)"
            is_fii = True
            is_acao = False
        elif is_etf:
            classe_normalizada = "ETFs"
            is_fii = False
            is_acao = False
        elif is_bdr:
            classe_normalizada = "BDRs"
            is_fii = False
            is_acao = False
        else:
            is_fii = "Fii" in classe_normalizada or (
                ticker_limpo.endswith("11") and ticker_limpo not in {"TAEE11", "SANB11", "ALUP11", "KLBN11", "SAPR11", "ENGI11", "BPAC11"}
            )
            is_acao = not is_fii and not is_etf and not is_bdr

        # Contagem isolada da regra de isenção R$ 20k (apenas Ações em Swing Trade)
        vendas_acoes_mes_antes = round(max(0.0, float(vendas_acumuladas_mes or 0.0)), 2)
        vendas_acoes_mes_atualizadas = round(
            vendas_acoes_mes_antes + (valor_venda if (is_acao and not is_day_trade) else 0.0),
            2,
        )

        isento = False
        aliquota = 0.0
        ir_devido = 0.0
        status_darf = "NÃO SE APLICA"
        detalhes = ""

        # Regra Especial B: Direitos de Subscrição de FII (Final 12) -> 20% sobre 100% da venda bruta
        if is_direito_fii_12 and valor_venda > 0:
            isento = False
            aliquota = 0.20
            base_calculo_ir = valor_venda
            ir_devido = round(0.20 * (p_venda * float(qtd)), 2)
            detalhes = (
                f"🚨 Direito de Subscrição de FII ({ticker_limpo}): Pela regra da Receita Federal, "
                f"o Custo de Aquisição (Preço Médio) é ZERO (R$ 0,00) e não há isenção. "
                f"Alíquota de 20% aplicada integralmente sobre 100% do valor bruto da venda "
                f"(20% de R$ {valor_venda:,.2f} = R$ {ir_devido:,.2f})."
            )
        elif resultado_liquido <= 0:
            isento = False
            ir_devido = 0.0
            status_darf = "SEM DARF (PREJUÍZO A COMPENSAR)"
            prejuizo_op = round(abs(resultado_liquido), 2)
            if is_fii:
                novo_prej_fii = round(prej_fii + prejuizo_op, 2)
                bucket_nome = "FIIs (alíquota 20%)"
                saldo_novo = novo_prej_fii
            else:
                novo_prej_ac_etf = round(prej_ac_etf + prejuizo_op, 2)
                bucket_nome = "Ações/ETFs/BDRs Swing Trade (alíquota 15%)"
                saldo_novo = novo_prej_ac_etf
            detalhes = (
                f"Operação com prejuízo líquido apurado de R$ {prejuizo_op:,.2f} ({lucro_pct:.2f}%), "
                f"após taxas (R$ {taxas_corr:,.2f}) e IRRF Dedo-Duro (R$ {irrf_dedo_duro:.4f}). "
                f"Não há imposto a recolher. Saldo acumulado em {bucket_nome} atualizado para R$ {saldo_novo:,.2f}."
            )
        else:
            if is_day_trade:
                isento = False
                aliquota = 0.20
                base_calculo_ir = resultado_liquido
                ir_devido = round(base_calculo_ir * aliquota, 2)
                detalhes = (
                    f"⚡ Day Trade apurado! Alíquota de 20% sobre o resultado líquido (R$ {resultado_liquido:,.2f}). "
                    f"Operações de Day Trade NÃO possuem isenção de R$ 20.000 e não compensam prejuízos de Swing Trade."
                )
            elif is_etf or is_bdr:
                isento = False
                aliquota = 0.15
                prejuizo_compensado = round(min(resultado_liquido, prej_ac_etf), 2)
                base_calculo_ir = round(max(0.0, resultado_liquido - prejuizo_compensado), 2)
                novo_prej_ac_etf = round(prej_ac_etf - prejuizo_compensado, 2)
                ir_devido = round(base_calculo_ir * aliquota, 2)
                if is_bdr:
                    detalhes = (
                        f"🚨 Trava Fiscal BDR ({ticker_limpo}): BDRs negociados na B3 (ex: Nubank) NÃO possuem isenção mensal de R$ 20.000,00. "
                        f"Lucro líquido de R$ {resultado_liquido:,.2f}"
                    )
                else:
                    detalhes = (
                        f"🚨 Trava Fiscal ETF ({ticker_limpo}): ETFs NÃO entram na isenção mensal de R$ 20.000,00. "
                        f"Lucro líquido de R$ {resultado_liquido:,.2f}"
                    )
                if prejuizo_compensado > 0:
                    detalhes += (
                        f" menos prejuízo acumulado compensado (R$ {prejuizo_compensado:,.2f}) = "
                        f"Base tributável R$ {base_calculo_ir:,.2f} (15% = R$ {ir_devido:,.2f}). "
                        f"Prejuízo restante Ações/ETFs/BDRs: R$ {novo_prej_ac_etf:,.2f}."
                    )
                else:
                    detalhes += f" tributado em 15% (= R$ {ir_devido:,.2f})."
            elif is_fii:
                isento = False
                aliquota = ALIQUOTA_IR_FIIS
                prejuizo_compensado = round(min(resultado_liquido, prej_fii), 2)
                base_calculo_ir = round(max(0.0, resultado_liquido - prejuizo_compensado), 2)
                novo_prej_fii = round(prej_fii - prejuizo_compensado, 2)
                ir_devido = round(base_calculo_ir * aliquota, 2)
                detalhes = (
                    f"🚨 FIIs NÃO possuem isenção de R$ 20.000,00 (e não consomem o limite das Ações). "
                    f"Lucro líquido de R$ {resultado_liquido:,.2f}"
                )
                if prejuizo_compensado > 0:
                    detalhes += (
                        f" menos prejuízo acumulado FII compensado (R$ {prejuizo_compensado:,.2f}) = "
                        f"Base tributável R$ {base_calculo_ir:,.2f} (20% = R$ {ir_devido:,.2f}). "
                        f"Prejuízo restante FIIs: R$ {novo_prej_fii:,.2f}."
                    )
                else:
                    detalhes += f" tributado em 20% (= R$ {ir_devido:,.2f})."
            elif is_acao:
                volume_total_mes = vendas_acoes_mes_atualizadas
                if volume_total_mes <= LIMITE_ISENCAO_ACOES_MES:
                    isento = True
                    aliquota = 0.0
                    base_calculo_ir = 0.0
                    ir_devido = 0.0
                    status_darf = "ISENTO (Art. 3º Lei 11.033/2004)"
                    detalhes = (
                        f"✅ Isento de IR! Vendas exclusivas de Ações no mês somaram "
                        f"R$ {volume_total_mes:,.2f} (<= R$ 20.000,00). "
                        f"Lucro líquido de R$ {resultado_liquido:,.2f} preservado (sem consumir prejuízo acumulado)."
                    )
                else:
                    isento = False
                    aliquota = ALIQUOTA_IR_ACOES
                    prejuizo_compensado = round(min(resultado_liquido, prej_ac_etf), 2)
                    base_calculo_ir = round(max(0.0, resultado_liquido - prejuizo_compensado), 2)
                    novo_prej_ac_etf = round(prej_ac_etf - prejuizo_compensado, 2)
                    ir_devido = round(base_calculo_ir * aliquota, 2)
                    detalhes = (
                        f"⚠️ Operação Tributável! Vendas exclusivas de Ações no mês somaram "
                        f"R$ {volume_total_mes:,.2f} (> R$ 20k). Lucro líquido de R$ {resultado_liquido:,.2f}"
                    )
                    if prejuizo_compensado > 0:
                        detalhes += (
                            f" após compensar R$ {prejuizo_compensado:,.2f} de prejuízo acumulado -> "
                            f"Base tributável R$ {base_calculo_ir:,.2f} (15% = R$ {ir_devido:,.2f}). "
                            f"Saldo restante de prejuízo: R$ {novo_prej_ac_etf:,.2f}."
                        )
                    else:
                        detalhes += f" tributado em 15% (= R$ {ir_devido:,.2f})."

        if ir_devido > 0:
            if ir_devido < 10.00:
                status_darf = "DARF < R$ 10,00 (ACUMULAR)"
                detalhes += (
                    f" 📌 Atenção: A Receita Federal veda emissão de DARF inferior a R$ 10,00 (Art. 67 Lei 9.430/96). "
                    f"Acumule o valor de R$ {ir_devido:,.2f} para os meses seguintes."
                )
            else:
                status_darf = f"GERAR DARF {CODIGO_DARF_RENDA_VARIAVEL}"
                detalhes += (
                    f" Emita a DARF código {CODIGO_DARF_RENDA_VARIAVEL} no valor de R$ {ir_devido:,.2f} "
                    f"até o último dia útil do mês subsequente."
                )
        elif resultado_liquido > 0 and prejuizo_compensado > 0 and not isento and status_darf == "NÃO SE APLICA":
            status_darf = "SEM DARF (COMPENSADO COM PREJUÍZO)"

        return {
            "ticker": ticker_limpo,
            "classe": classe_normalizada,
            "eh_etf": is_etf,
            "eh_fii": is_fii,
            "eh_acao": is_acao,
            "eh_direito_subscricao_12": is_direito_fii_12,
            "quantidade_venda": qtd,
            "preco_venda": p_venda,
            "preco_medio": p_medio,
            "valor_venda": valor_venda,
            "vendas_acoes_mes_atualizadas": vendas_acoes_mes_atualizadas,
            "custo_total": custo_total,
            "taxas_corretora": taxas_corr,
            "irrf": irrf_dedo_duro,
            "lucro_bruto": lucro_bruto,
            "resultado_liquido": resultado_liquido,
            "prejuizo_compensado": prejuizo_compensado,
            "base_calculo_ir": base_calculo_ir,
            "novo_prejuizo_acumulado_acoes_etfs": novo_prej_ac_etf,
            "novo_prejuizo_acumulado_fiis": novo_prej_fii,
            "lucro_pct": lucro_pct,
            "isento": isento,
            "aliquota_ir_pct": round(aliquota * 100.0, 1),
            "ir_devido": ir_devido,
            "lucro_liquido_pos_ir": round(resultado_liquido - ir_devido, 2),
            "status_darf": status_darf,
            "codigo_darf": CODIGO_DARF_RENDA_VARIAVEL,
            "detalhes": detalhes,
        }
    except Exception as e:
        return {
            "ticker": str(ticker),
            "classe": str(classe),
            "eh_etf": False,
            "eh_fii": False,
            "eh_acao": False,
            "eh_direito_subscricao_12": False,
            "quantidade_venda": 0,
            "preco_venda": 0.0,
            "preco_medio": 0.0,
            "valor_venda": 0.0,
            "vendas_acoes_mes_atualizadas": 0.0,
            "custo_total": 0.0,
            "taxas_corretora": 0.0,
            "irrf": 0.0,
            "lucro_bruto": 0.0,
            "resultado_liquido": 0.0,
            "prejuizo_compensado": 0.0,
            "base_calculo_ir": 0.0,
            "novo_prejuizo_acumulado_acoes_etfs": float(prejuizo_acumulado_acoes_etfs or 0.0),
            "novo_prejuizo_acumulado_fiis": float(prejuizo_acumulado_fiis or 0.0),
            "lucro_pct": 0.0,
            "isento": False,
            "aliquota_ir_pct": 0.0,
            "ir_devido": 0.0,
            "lucro_liquido_pos_ir": 0.0,
            "status_darf": "ERRO DE CÁLCULO",
            "codigo_darf": CODIGO_DARF_RENDA_VARIAVEL,
            "detalhes": f"Não foi possível calcular o imposto: {e}",
        }


def construir_mapa_valuation_carteira(
    itens_rv: List[Dict[str, Any]],
    top_compras: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Monta um dicionário {ticker_base: metricas_valuation} combinando o Top Compras
    (com SanityGate) e avaliação direta dos demais ativos da carteira.
    """
    from scanner import calcular_valuation
    from data_engine import validar_dados_yfinance

    mapa: Dict[str, Dict[str, Any]] = {}
    if top_compras:
        for c in top_compras:
            t = str(c.get("ticker", "")).replace(".SA", "").strip().upper()
            if t:
                mapa[t] = dict(c)

    macro = None
    pendentes = []
    for it in itens_rv or []:
        t = str(it.get("ticker", "")).replace(".SA", "").strip().upper()
        if not t or t in mapa:
            continue
        pendentes.append(it)

    if pendentes:
        try:
            macro = obter_dados_macro()
            cdi_bruto = float(macro.get("cdi", 10.65))
            cdi_liq = float(macro.get("cdi_liquido_anual", cdi_bruto * 0.85))
        except Exception:
            cdi_bruto = 10.65
            cdi_liq = 9.05

        for it in pendentes:
            t = str(it.get("ticker", "")).replace(".SA", "").strip().upper()
            classe_it = str(it.get("classe", "Ações"))
            info = obter_info_ativo(t)
            cot = float(info.get("cotacao", it.get("cotacao_atual", 0.0)) or 0.0)
            lpa = float(info.get("lpa", 0.0) or 0.0)
            vpa = float(info.get("vpa", 0.0) or 0.0)
            roe = float(info.get("roe", 0.0) or 0.0)
            dy = float(info.get("dy", it.get("dy_anual", 0.0)) or 0.0)
            pvp = float(info.get("pvp", 1.0) or 1.0)
            pl = float(info.get("pl", 8.0) or 8.0)
            setor_it = str(info.get("setor", classe_it))

            val = calcular_valuation(
                ticker=t,
                setor=setor_it,
                lpa=lpa,
                vpa=vpa,
                roe=roe,
                dy_projetado=dy,
                preco_atual=cot,
                pvp_override=pvp,
                cdi_anual=cdi_bruto,
                payout_historico=info.get("payout_ratio"),
                historico_dividendos=info.get("dividendos_anuais_3_5a"),
                crescimento_lucro_pct=info.get("crescimento_lucro_pct"),
            )
            is_bdr_it = _eh_bdr_renda_variavel(t, classe_it) or bool(val.get("eh_bdr"))
            row = {
                "ticker": t,
                "nome": info.get("nome", t),
                "tipo": val["modelo_utilizado"],
                "tipo_fii": val.get("tipo_fii"),
                "setor": setor_it,
                "cotacao": cot,
                "dy_anual_pct": dy,
                "pl": pl,
                "pvp": pvp,
                "lpa": lpa,
                "divida_liq_ebitda": info.get("divida_liquida_ebitda"),
                "preco_teto": None if is_bdr_it else val.get("preco_teto"),
                "isento_teto_bazin": bool(val.get("isento_teto_bazin", is_bdr_it)),
                "preco_justo_graham": val.get("preco_justo"),
                "margem_graham_pct": val.get("margem_seguranca_pct"),
                "spread_vs_cdi_liquido": round(dy - cdi_liq, 2),
                "score_geral": val.get("score_triplo"),
                "score_seguranca": val.get("score_seguranca"),
                "alerta_risco_critico": val.get("alerta_risco_critico", False),
            }
            df_row = validar_dados_yfinance(pd.DataFrame([row]))
            rec = df_row.to_dict(orient="records")[0]
            mapa[t] = rec

    return mapa


def _avaliar_elegibilidade_ativo(
    item: Dict[str, Any],
    valuation_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Passo 1 (Filtro de Valuation e SanityGate):
    Verifica se o ativo está aprovado no SanityGate e se Cotação <= Preço Teto.
    Se reprovado, zera o Gap Efetivo e retorna motivo explícito.
    """
    t = str(item.get("ticker", "")).replace(".SA", "").strip().upper()
    vinfo = (valuation_map or {}).get(t, {})

    cotacao = float(item.get("cotacao_atual", item.get("cotacao", vinfo.get("cotacao", 0.0))) or 0.0)
    status_aud = item.get("status_auditoria", vinfo.get("status_auditoria", "Validado"))
    alerta_critico = bool(item.get("alerta_risco_critico", vinfo.get("alerta_risco_critico", False)))
    preco_teto = item.get("preco_teto", vinfo.get("preco_teto"))
    dy_pct = float(item.get("dy_anual", vinfo.get("dy_anual_pct", 0.0)) or 0.0)
    score_geral = vinfo.get("score_geral", item.get("score_geral"))
    score_seg = vinfo.get("score_seguranca", item.get("score_seguranca"))
    spread_cdi = vinfo.get("spread_vs_cdi_liquido", item.get("spread_vs_cdi_liquido"))
    alerta_pedagio = bool(vinfo.get("alerta_pedagio_cdi", item.get("alerta_pedagio_cdi", False)))

    is_bdr_item = _eh_bdr_renda_variavel(t, item.get("classe", "")) or bool(vinfo.get("isento_teto_bazin") and "BDR" in str(vinfo.get("tipo", "")))
    teto_f = None if is_bdr_item else (float(preco_teto) if (preco_teto is not None and float(preco_teto) > 0) else None)

    bloqueado = False
    motivo_status = "Elegível para Aporte"
    micro_tag = "Rebalanceamento Peso-Alvo"

    if status_aud == "Suspeito":
        bloqueado = True
        motivo_status = "Bloqueado pelo SanityGate (Dados Suspeitos) — Aguardar"
        micro_tag = "SanityGate: Dados Suspeitos"
    elif alerta_critico:
        bloqueado = True
        motivo_status = "Bloqueado por Risco Crítico Fundamentalista — Aguardar"
        micro_tag = "Risco Crítico no Balanço"
    elif teto_f is not None and cotacao > teto_f:
        bloqueado = True
        motivo_status = "Bloqueado pelo Teto de Preço — Aguardar"
        excess_pct = ((cotacao / teto_f) - 1.0) * 100.0
        micro_tag = f"Acima do Teto R$ {teto_f:.2f} (+{excess_pct:.1f}%)"
    else:
        partes_tag = []
        if teto_f is not None and cotacao > 0:
            desc_pct = ((teto_f / cotacao) - 1.0) * 100.0
            partes_tag.append(f"Abaixo do Teto (+{desc_pct:.1f}%)")
        if score_geral is not None:
            partes_tag.append(f"Score {float(score_geral):.0f}/100")
        elif score_seg is not None:
            partes_tag.append(f"Seg. {float(score_seg):.0f}")
        if dy_pct > 0:
            partes_tag.append(f"DY {dy_pct:.1f}%")
        if alerta_pedagio:
            partes_tag.append("Pedágio CDI Baixo (Monitorar CDB)")
        elif spread_cdi is not None and float(spread_cdi) > 0:
            partes_tag.append(f"+{float(spread_cdi):.1f}p.p. vs CDI Líq")
        micro_tag = " • ".join(partes_tag[:3]) if partes_tag else "Elegível • Peso-Alvo"

    return {
        "ticker_base": t,
        "bloqueado": bloqueado,
        "motivo_status": motivo_status,
        "micro_tag": micro_tag,
        "preco_teto": round(teto_f, 2) if teto_f is not None else None,
        "status_auditoria": status_aud,
        "dy_pct": dy_pct,
        "score_geral": score_geral,
        "alerta_pedagio_cdi": alerta_pedagio,
    }


def _alocar_ativos_normalizados(
    validos: List[Dict[str, Any]],
    verba: float,
    valor_classe_base: float,
    valuation_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Executa os Passos 1, 2 e 3 sobre uma lista de ativos de RV:
    - Bloqueia ativos acima do Preço Teto ou reprovados no SanityGate (Gap_Efetivo = 0).
    - Normaliza gaps elegíveis: Verba_Ativo_i = Verba * (Gap_Efetivo_i / Soma_Gaps_Efetivos).
    - Converte verba em cotas inteiras e identifica excedente para Caixa Conservador.
    """
    soma_pesos = sum(max(0.0, float(i.get("peso_alvo", 0.0) or 0.0)) for i in validos)
    valor_classe_proj = valor_classe_base + verba

    linhas = []
    bloqueios = []
    houve_bloqueio = False

    for i in validos:
        peso_rel = (max(0.0, float(i.get("peso_alvo", 0.0) or 0.0)) / soma_pesos) if soma_pesos > 0 else (1.0 / len(validos))
        alvo_ativo = valor_classe_proj * peso_rel
        gap_bruto = max(0.0, alvo_ativo - float(i.get("patrimonio_atual", 0.0) or 0.0))

        elig = _avaliar_elegibilidade_ativo(i, valuation_map=valuation_map)
        if elig["bloqueado"]:
            houve_bloqueio = True
            gap_efetivo = 0.0
            bloqueios.append({
                "ticker": elig["ticker_base"],
                "classe": i.get("classe", "Ações"),
                "cotacao": float(i.get("cotacao_atual", 0.0) or 0.0),
                "preco_teto": elig["preco_teto"],
                "gap_original": round(gap_bruto, 2),
                "motivo_status": elig["motivo_status"],
                "micro_tag": elig["micro_tag"],
            })
        else:
            gap_efetivo = gap_bruto

        linhas.append({
            "item": i,
            "peso_rel": peso_rel,
            "gap_bruto": gap_bruto,
            "gap": gap_efetivo,
            "elig": elig,
            "verba_teorica": 0.0,
            "cotas": 0,
        })

    elegiveis = [l for l in linhas if not l["elig"]["bloqueado"]]
    total_gap_efetivo = sum(l["gap"] for l in elegiveis)

    if not elegiveis or verba <= 0:
        return {
            "linhas": linhas,
            "bloqueios": bloqueios,
            "gasto_total": 0.0,
            "redirecionado_caixa": round(max(0.0, verba), 2),
            "todos_bloqueados": len(validos) > 0 and len(elegiveis) == 0,
        }

    # Normalização de Gaps: Verba_Ativo_i = Verba_Macroclasse * (Gap_Efetivo_i / Soma_Gaps_Efetivos)
    if total_gap_efetivo > 0:
        for l in elegiveis:
            l["verba_teorica"] = verba * (l["gap"] / total_gap_efetivo)
    elif not houve_bloqueio:
        soma_pesos_el = sum(l["peso_rel"] for l in elegiveis)
        for l in elegiveis:
            fator = (l["peso_rel"] / soma_pesos_el) if soma_pesos_el > 0 else (1.0 / len(elegiveis))
            l["verba_teorica"] = verba * fator
    else:
        # Ativos baratos já estão acima do peso alvo e os subalocados estão acima do teto: preserva caixa
        return {
            "linhas": linhas,
            "bloqueios": bloqueios,
            "gasto_total": 0.0,
            "redirecionado_caixa": round(verba, 2),
            "todos_bloqueados": False,
        }

    restante = verba
    for l in elegiveis:
        preco = float(l["item"]["cotacao_atual"])
        l["cotas"] = int(l["verba_teorica"] // preco) if preco > 0 else 0
        restante -= l["cotas"] * preco

    # Alocação gulosa do troco entre ativos elegíveis (respeitando gap ou maior subalocação)
    while True:
        candidatos = [
            l for l in elegiveis
            if float(l["item"]["cotacao_atual"]) > 0
            and float(l["item"]["cotacao_atual"]) <= restante
            and (l["verba_teorica"] - l["cotas"] * float(l["item"]["cotacao_atual"])) > 0.01
        ]
        if not candidatos:
            break
        melhor = max(
            candidatos,
            key=lambda l: (l["verba_teorica"] - l["cotas"] * float(l["item"]["cotacao_atual"])),
        )
        melhor["cotas"] += 1
        restante -= float(melhor["item"]["cotacao_atual"])

    gasto_total = round(sum(l["cotas"] * float(l["item"]["cotacao_atual"]) for l in elegiveis), 2)
    redirecionado_caixa = round(max(0.0, verba - gasto_total), 2)

    return {
        "linhas": linhas,
        "bloqueios": bloqueios,
        "gasto_total": gasto_total,
        "redirecionado_caixa": redirecionado_caixa,
        "todos_bloqueados": False,
    }


def calcular_rebalanceamento_aportes(
    itens_rv: List[Dict[str, Any]],
    sobra_para_investir: float,
    caixa_oportunidade: float = 0.0,
    valuation_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Algoritmo de Aporte Inteligente com Normalização de Gaps e Filtro de Valuation:
    - Bloqueia ativos acima do Preço Teto ou reprovados no SanityGate (Gap_Efetivo = 0).
    - Normaliza os gaps positivos elegíveis para distribuir 100% da verba entre ativos descontados.
    - Redireciona saldo não alocado para Reserva de Oportunidade (Caixa Selic/Nubank).
    - Converte quantidades de Ações entre 1 e 99 unidades para Mercado Fracionário ('F').
    """
    capital_disponivel = max(0.0, float(sobra_para_investir) + float(caixa_oportunidade))
    validos = [i for i in (itens_rv or []) if float(i.get("cotacao_atual", 0.0) or 0.0) > 0]
    if not validos or capital_disponivel <= 0.0:
        return {
            "aportes": [],
            "bloqueios": [],
            "capital_disponivel": round(capital_disponivel, 2),
            "capital_alocado": 0.0,
            "sobra_residual": round(capital_disponivel, 2),
            "valor_redirecionado_oportunidade": round(capital_disponivel, 2),
        }

    patrimonio_atual_rv = sum(float(item.get("patrimonio_atual", 0.0) or 0.0) for item in validos)
    aloc = _alocar_ativos_normalizados(
        validos=validos,
        verba=capital_disponivel,
        valor_classe_base=patrimonio_atual_rv,
        valuation_map=valuation_map,
    )

    aportes_sugeridos = []
    for l in aloc["linhas"]:
        item = l["item"]
        preco = float(item.get("cotacao_atual", 0.0) or 0.0)
        qtd_cotas = int(l["cotas"])
        valor_aporte = round(qtd_cotas * preco, 2)
        pat_atual = float(item.get("patrimonio_atual", 0.0) or 0.0)
        ticker_base = str(item.get("ticker", "")).strip().upper()
        ticker_operacional = formatar_ticker_fracionario(ticker_base, item.get("classe", "Ações"), qtd_cotas)

        aportes_sugeridos.append({
            "ticker": ticker_operacional,
            "ticker_base": ticker_base,
            "classe": item.get("classe", "Ações"),
            "cotacao": preco,
            "peso_atual_pct": item.get("peso_atual", 0.0),
            "peso_alvo_pct": item.get("peso_alvo", 0.0),
            "gap_reais": round(l["gap"], 2),
            "gap_original_reais": round(l["gap_bruto"], 2),
            "verba_teorica_normalizada": round(l["verba_teorica"], 2),
            "preco_teto": l["elig"]["preco_teto"],
            "bloqueado": l["elig"]["bloqueado"],
            "motivo_status": l["elig"]["motivo_status"],
            "micro_tag": l["elig"]["micro_tag"],
            "cotas_a_comprar": qtd_cotas,
            "valor_aporte_sugerido": valor_aporte,
            "novo_patrimonio": round(pat_atual + valor_aporte, 2),
        })

    capital_utilizado = round(aloc["gasto_total"], 2)
    sobra_residual = round(max(0.0, capital_disponivel - capital_utilizado), 2)

    return {
        "aportes": aportes_sugeridos,
        "bloqueios": aloc["bloqueios"],
        "capital_disponivel": round(capital_disponivel, 2),
        "capital_alocado": capital_utilizado,
        "sobra_residual": sobra_residual,
        "valor_redirecionado_oportunidade": sobra_residual,
    }


def calcular_aporte_por_classe(
    itens_rv: List[Dict[str, Any]],
    rf_investimento_atual: float,
    sobra_para_investir: float,
    metas_classe: Optional[Dict[str, float]] = None,
    caixa_oportunidade_usada: float = 0.0,
    valuation_map: Optional[Dict[str, Dict[str, Any]]] = None,
    saldo_reserva_emergencia: Optional[float] = None,
    custo_vida_mensal: Optional[float] = None,
    meta_meses_reserva: int = 6,
) -> Dict[str, Any]:
    """
    Rebalanceamento Conservador em 2 Níveis (Gatekeeper + Macroclasses + Ativos Normalizados):
    1) Trava Gatekeeper de Reserva de Emergência (50% a 100% da sobra para RF se < meta_meses_reserva).
    2) Nível 1: distribui verba entre classes rumo às metas de transição.
    3) Nível 2: filtra SanityGate + Preço Teto (`Bloqueado pelo Teto de Preço — Aguardar`),
       normaliza gaps positivos elegíveis e redireciona excedentes/troco para Reserva de Oportunidade.
    """
    metas = dict(METAS_CLASSE_PADRAO if not metas_classe else metas_classe)
    avisos: List[str] = []

    itens_por_classe: Dict[str, List[Dict[str, Any]]] = {c: [] for c in CLASSES_ALOCACAO if c != "Renda Fixa"}
    for it in (itens_rv or []):
        itens_por_classe[normalizar_classe(it.get("classe"))].append(it)

    rf_atual = max(0.0, float(rf_investimento_atual) - float(caixa_oportunidade_usada))
    valores_atuais = {"Renda Fixa": rf_atual}
    for c, lst in itens_por_classe.items():
        valores_atuais[c] = sum(float(i.get("patrimonio_atual", 0.0) or 0.0) for i in lst)

    for c in list(itens_por_classe.keys()):
        if metas.get(c, 0.0) > 0 and not itens_por_classe[c]:
            avisos.append(f"A classe {c} tem meta de {metas[c]:.0f}% mas nenhum ativo cadastrado; a meta foi redistribuída.")
            metas[c] = 0.0

    soma_metas = sum(max(0.0, v) for v in metas.values())
    if soma_metas <= 0:
        metas = {c: (100.0 if c == "Renda Fixa" else 0.0) for c in CLASSES_ALOCACAO}
        soma_metas = 100.0
    if abs(soma_metas - 100.0) > 0.01:
        avisos.append(f"As metas somavam {soma_metas:.1f}%; foram ajustadas proporcionalmente para 100%.")
    metas = {c: (max(0.0, metas.get(c, 0.0)) / soma_metas) * 100.0 for c in CLASSES_ALOCACAO}

    capital = max(0.0, float(sobra_para_investir) + float(caixa_oportunidade_usada))
    patrimonio_investivel = sum(valores_atuais.values())
    patrimonio_projetado = patrimonio_investivel + capital

    gaps = {}
    for c in CLASSES_ALOCACAO:
        alvo = patrimonio_projetado * metas[c] / 100.0
        gaps[c] = max(0.0, alvo - valores_atuais[c])
    total_gap = sum(gaps.values())

    verba_classe = {}
    for c in CLASSES_ALOCACAO:
        if capital <= 0:
            verba_classe[c] = 0.0
        elif total_gap > 0:
            verba_classe[c] = capital * gaps[c] / total_gap
        else:
            verba_classe[c] = capital * metas[c] / 100.0

    # Trava Gatekeeper de Reserva de Emergência integrada ao Orçamento
    cobertura_reserva_info: Optional[Dict[str, Any]] = None
    if saldo_reserva_emergencia is not None and custo_vida_mensal is not None and float(custo_vida_mensal) > 0:
        cobertura_reserva_info = calcular_cobertura_reserva(
            saldo_reserva_rf=float(saldo_reserva_emergencia),
            custo_vida_mensal=float(custo_vida_mensal),
            meta_meses=meta_meses_reserva,
        )
        if cobertura_reserva_info["gatekeeper_ativo"] and float(sobra_para_investir) > 0:
            piso_rf_gatekeeper = min(
                capital,
                float(sobra_para_investir) * (cobertura_reserva_info["pct_sobra_minimo_rf"] / 100.0),
            )
            if verba_classe["Renda Fixa"] < piso_rf_gatekeeper:
                restante_para_rv = max(0.0, capital - piso_rf_gatekeeper)
                verba_rv_atual = sum(verba_classe[c] for c in itens_por_classe.keys())
                verba_classe["Renda Fixa"] = piso_rf_gatekeeper
                if verba_rv_atual > 0:
                    fator_rv = restante_para_rv / verba_rv_atual
                    for c in itens_por_classe.keys():
                        verba_classe[c] *= fator_rv
                else:
                    for c in itens_por_classe.keys():
                        verba_classe[c] = 0.0
            avisos.append(
                f"🛡️ Gatekeeper de Reserva Ativo: Cobertura atual em {cobertura_reserva_info['cobertura_meses']:.2f} "
                f"meses (meta: {meta_meses_reserva}m; faltam R$ {cobertura_reserva_info['deficit_rs']:,.2f}). "
                f"{cobertura_reserva_info['pct_sobra_minimo_rf']:.0f}% da sobra mensal foi priorizada para Renda Fixa."
            )

    aportes_ativos: List[Dict[str, Any]] = []
    bloqueios_totais: List[Dict[str, Any]] = []
    gasto_por_classe = {c: 0.0 for c in CLASSES_ALOCACAO}
    valor_redirecionado_oportunidade = 0.0

    for c, lst in itens_por_classe.items():
        verba = verba_classe[c]
        validos = [i for i in lst if float(i.get("cotacao_atual", 0.0) or 0.0) > 0]
        if verba <= 0 or not validos:
            continue

        aloc = _alocar_ativos_normalizados(
            validos=validos,
            verba=verba,
            valor_classe_base=valores_atuais[c],
            valuation_map=valuation_map,
        )
        bloqueios_totais.extend(aloc["bloqueios"])
        gasto_por_classe[c] = aloc["gasto_total"]
        valor_redirecionado_oportunidade += aloc["redirecionado_caixa"]

        if aloc["todos_bloqueados"] and verba > 0:
            avisos.append(
                f"🏦 Classe {c}: Todos os ativos estão caros (acima do Preço Teto) ou bloqueados no SanityGate. "
                f"Na transição conservadora não se compra ativo caro apenas para bater meta: R$ {verba:,.2f} "
                f"redirecionados para Caixinha Nubank / Selic (Reserva de Oportunidade)."
            )
        elif aloc["bloqueios"] and aloc["redirecionado_caixa"] > 5.0:
            nomes_bloq = ", ".join(b["ticker"] for b in aloc["bloqueios"])
            avisos.append(
                f"⏸️ Ativo(s) bloqueado(s) em {c} ({nomes_bloq}): verba redistribuída entre pares elegíveis "
                f"(sobra residual de R$ {aloc['redirecionado_caixa']:,.2f} enviada à Reserva de Oportunidade)."
            )

        for l in aloc["linhas"]:
            preco = float(l["item"]["cotacao_atual"])
            valor = round(l["cotas"] * preco, 2)
            ticker_original = str(l["item"].get("ticker", "")).strip().upper()
            ticker_final = formatar_ticker_fracionario(ticker_original, c, l["cotas"])
            aportes_ativos.append({
                "ticker": ticker_final,
                "ticker_base": ticker_original,
                "classe": c,
                "cotacao": preco,
                "peso_na_classe_pct": round(l["peso_rel"] * 100.0, 1),
                "gap_reais": round(l["gap"], 2),
                "gap_original_reais": round(l["gap_bruto"], 2),
                "verba_teorica_normalizada": round(l["verba_teorica"], 2),
                "preco_teto": l["elig"]["preco_teto"],
                "bloqueado": l["elig"]["bloqueado"],
                "motivo_status": l["elig"]["motivo_status"],
                "micro_tag": l["elig"]["micro_tag"],
                "cotas_a_comprar": l["cotas"],
                "valor_aporte_sugerido": valor,
            })

    sobra_arredondamento = sum(verba_classe[c] - gasto_por_classe[c] for c in itens_por_classe.keys())
    gasto_por_classe["Renda Fixa"] = round(verba_classe["Renda Fixa"] + max(0.0, sobra_arredondamento), 2)

    resumo_classes = []
    total_pos = patrimonio_investivel + capital
    for c in CLASSES_ALOCACAO:
        novo_valor = valores_atuais[c] + gasto_por_classe[c]
        resumo_classes.append({
            "classe": c,
            "valor_atual": round(valores_atuais[c], 2),
            "pct_atual": round((valores_atuais[c] / patrimonio_investivel * 100.0) if patrimonio_investivel > 0 else 0.0, 1),
            "meta_pct": round(metas[c], 1),
            "aporte_sugerido": round(gasto_por_classe[c], 2),
            "pct_apos_aporte": round((novo_valor / total_pos * 100.0) if total_pos > 0 else 0.0, 1),
        })

    aportes_ativos.sort(key=lambda x: (not x["bloqueado"], x["valor_aporte_sugerido"]), reverse=True)
    return {
        "resumo_classes": resumo_classes,
        "aportes": aportes_ativos,
        "bloqueios": bloqueios_totais,
        "cobertura_reserva": cobertura_reserva_info,
        "capital_disponivel": round(capital, 2),
        "aporte_renda_fixa": gasto_por_classe["Renda Fixa"],
        "aporte_renda_fixa_meta_base": round(verba_classe["Renda Fixa"], 2),
        "valor_redirecionado_oportunidade": round(max(0.0, valor_redirecionado_oportunidade), 2),
        "capital_alocado_rv": round(sum(gasto_por_classe[c] for c in itens_por_classe.keys()), 2),
        "avisos": avisos,
    }
