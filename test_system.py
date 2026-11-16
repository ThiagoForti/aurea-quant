"""
Script de Teste de Integração e Validação Quantitativa
Testa todos os módulos, gera o Excel com as 6 abas e valida regras de negócio.
"""
import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import openpyxl

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import (
    STATE_FILE, EXCEL_FILE, BANCOS_JCP, SEGURADORAS_ISENTAS, FIIS_PAPEL, FIIS_TIJOLO,
    LOCAL_CACHE_DIR, BACKUP_DIR, MACRO_CACHE_FILE, MARKET_CACHE_FILE,
)
from data_engine import (
    obter_dados_macro, calcular_rendimento_nubank, validar_dados_yfinance,
    save_user_state, load_user_state, obter_status_market_cache
)
from budget_engine import calcular_orcamento, simular_corte_gastos_fire
from portfolio_engine import (
    processar_renda_fixa, processar_renda_variavel,
    simular_venda_e_ir, calcular_rebalanceamento_aportes,
    calcular_aporte_por_classe,
    calcular_cobertura_reserva, calcular_renda_passiva_real_e_fire,
    formatar_ticker_fracionario
)
from scanner import (
    calcular_graham, calcular_bazin, obter_fator_haircut_jcp, calcular_valuation,
    calcular_score_saude_balanco, calcular_efeito_bola_de_neve,
    analisar_universo_besst, analisar_fiis, analisar_etfs, analisar_bdrs,
    executar_scanner_oportunidades, obter_top_melhores_compras
)
import pandas as pd
from educational_engine import obter_estudo_do_dia, obter_glossario_conceitos
from news_intelligence import inferir_tese_heuristica, processar_radar_noticias
from export_excel import exportar_para_excel


def executar_testes():
    print("=" * 70)
    print("INICIANDO SUÍTE DE TESTES QUANTITATIVOS B3 & RENDA FIXA")
    print("=" * 70)

    # 1. Persistência Atômica & Schema
    print("\n[1/8] Testando persistência atômica (user_state.json) e cache offline...")
    demo_file = Path(__file__).resolve().parent / "user_state_demo.json"
    assert os.path.exists(STATE_FILE) or os.path.exists(demo_file), "Arquivo de estado (user_state.json ou user_state_demo.json) não encontrado!"
    estado = load_user_state(STATE_FILE)
    assert os.path.exists(STATE_FILE), "Arquivo user_state.json deveria existir ou ser inicializado a partir de user_state_demo.json!"
    assert "prejuizo_acumulado_acoes_etfs" in estado
    assert "prejuizo_acumulado_fiis" in estado
    assert estado["configuracoes"]["meta_meses_reserva"] >= 1
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_state = Path(tmpdir) / "user_state_test.json"
        tmp_backups = Path(tmpdir) / "backups"
        save_user_state(estado, filepath=tmp_state)
        reloaded = load_user_state(tmp_state)
        assert reloaded["configuracoes"]["meta_meses_reserva"] == estado["configuracoes"]["meta_meses_reserva"]
        with patch("data_engine.STATE_FILE", str(tmp_state)), patch("data_engine.BACKUP_DIR", str(tmp_backups)):
            save_user_state(estado, filepath=str(tmp_state))
            assert tmp_backups.exists() and len(list(tmp_backups.glob("user_state_*.json"))) == 1
    assert Path(MACRO_CACHE_FILE).parent == Path(LOCAL_CACHE_DIR)
    assert Path(MARKET_CACHE_FILE).parent == Path(LOCAL_CACHE_DIR)
    status_cache = obter_status_market_cache()
    assert "usando_cache" in status_cache and "ativos_em_cache" in status_cache
    print(f" -> Estado carregado ({Path(STATE_FILE).name}), cache local fora do Drive e backup rotativo validados.")

    # 2. Camada de Dados Macro & Renda Fixa Base 252
    print("\n[2/8] Testando Banco Central SGS e Renda Fixa Base 252...")
    macro = obter_dados_macro()
    print(f" -> Selic: {macro['selic']}% | CDI: {macro['cdi']}% | IPCA: {macro['ipca_12m']}% | PTAX: R$ {macro['ptax']}")
    assert macro["selic"] > 0, "Taxa Selic inválida!"

    calc_nubank = calcular_rendimento_nubank(saldo_atual=50000.0, percentual_cdi=100.0, dias_corridos=365, cdi_anual=13.65)
    fator_diario_esp = round((1.0 + 0.1365) ** (1.0 / 252.0), 8)
    assert calc_nubank["fator_diario"] == fator_diario_esp, f"Base 252 divergente: {calc_nubank['fator_diario']} vs {fator_diario_esp}"
    assert calc_nubank["ir_acumulado"] > 0 and calc_nubank["rendimento_mensal_liquido"] > 0
    print(f" -> Base 252 validada (fator={fator_diario_esp:.8f}, liq={calc_nubank['rendimento_mensal_liquido']:.2f}/mês, eq={calc_nubank['taxa_liquida_mensal_pct']:.4f}% a.m.).")

    # 3. Módulo de Orçamento + Ponte 50/30/20 Desacoplada + Provisão Anual + Simulador Corte FIRE
    print("\n[3/8] Testando Motor de Orçamento CFP 2.0 (50/30/20 Desacoplado + Provisão Anual) e Simulador Corte FIRE...")
    orc = calcular_orcamento(estado["orcamento"])
    assert "custo_vida_mensal" in orc and "regra_50_30_20" in orc
    assert "total_essenciais_cfp" in orc and "total_estilo_cfp" in orc
    assert "provisao_mensal_anual" in orc and "total_despesas_anuais" in orc
    assert orc["provisao_mensal_anual"] == round(orc["total_despesas_anuais"] / 12.0, 2)
    assert round(orc["total_receitas"] - orc["total_fixos"] - orc["total_variaveis"] - orc["provisao_mensal_anual"], 2) == orc["sobra_para_investir"]
    assert orc["sobra_para_investir"] > 0

    # Validar desacoplamento explícito entre Fixo/Variável e Essencial (50%) / Estilo de Vida (30%)
    orc_desacoplado = calcular_orcamento({
        "receitas": [{"nome": "Salário", "valor": 10000.0}],
        "gastos_fixos": [
            {"nome": "Aluguel", "valor": 2500.0, "categoria_cfp": "Essencial (50%)"},
            {"nome": "Streaming Fixo", "valor": 200.0, "categoria_cfp": "Estilo de Vida (30%)"},
        ],
        "gastos_variaveis": [
            {"nome": "Supermercado Variável", "valor": 1500.0, "categoria_cfp": "Essencial (50%)"},
            {"nome": "Restaurantes", "valor": 800.0, "categoria_cfp": "Estilo de Vida (30%)"},
        ],
        "despesas_anuais": [
            {"nome": "IPVA + Seguro", "valor_anual": 6000.0, "vencimento": "Janeiro"},
        ],
    })
    assert orc_desacoplado["total_fixos"] == 2700.0 and orc_desacoplado["total_variaveis"] == 2300.0
    assert orc_desacoplado["total_essenciais_cfp"] == 4000.0 and orc_desacoplado["pct_essenciais_cfp"] == 40.0
    assert orc_desacoplado["total_estilo_cfp"] == 1000.0 and orc_desacoplado["pct_estilo_cfp"] == 10.0
    assert orc_desacoplado["provisao_mensal_anual"] == 500.0
    assert orc_desacoplado["sobra_para_investir"] == 4500.0

    sim_corte = simular_corte_gastos_fire(
        corte_mensal_rs=400.0,
        patrimonio_atual_rs=100000.0,
        aporte_mensal_atual_rs=orc["sobra_para_investir"],
        custo_vida_mensal_atual_rs=orc["custo_vida_mensal"],
        yield_medio_real_pct=6.5,
    )
    assert sim_corte["anos_antecipados"] >= 0 and sim_corte["reducao_meta_fire"] > 0
    print(
        f" -> Custo de Vida: R$ {orc['custo_vida_mensal']:,.2f} | Provisão Anual (1/12): R$ {orc['provisao_mensal_anual']:,.2f} "
        f"| Sobra Líquida: R$ {orc['sobra_para_investir']:,.2f} | Antecipação FIRE c/ corte: {sim_corte['anos_antecipados']:.1f} anos"
    )

    # 4. Módulo de Carteira, Gatekeeper, Fisher FIRE e Simulador de IR c/ Prejuízo Acumulado
    print("\n[4/8] Testando Carteira, Gatekeeper da Reserva, FIRE Real (Fisher) e IR c/ Compensação...")
    rf_res = processar_renda_fixa(estado["renda_fixa"], cdi_anual=macro["cdi"], ipca_anual=macro["ipca_12m"])
    rv_res = processar_renda_variavel(estado["renda_variavel"])

    # Gatekeeper abaixo da meta (ex.: 2 meses < 6 meses) deve travar 50%-100% na RF
    gk_baixo = calcular_cobertura_reserva(saldo_reserva_rf=10000.0, custo_vida_mensal=5000.0, meta_meses=6)
    assert gk_baixo["gatekeeper_ativo"] is True and gk_baixo["pct_sobra_minimo_rf"] >= 50.0
    gk_ok = calcular_cobertura_reserva(saldo_reserva_rf=40000.0, custo_vida_mensal=5000.0, meta_meses=6)
    assert gk_ok["gatekeeper_ativo"] is False and gk_ok["cobertura_meses"] == 8.0

    # Validar trava efetiva no aporte por classe quando reserva está abaixo da meta
    plano_gk = calcular_aporte_por_classe(
        itens_rv=rv_res["itens"],
        rf_investimento_atual=rf_res["total_patrimonio_rf"],
        sobra_para_investir=2000.0,
        saldo_reserva_emergencia=10000.0,
        custo_vida_mensal=5000.0,
        meta_meses_reserva=6,
    )
    assert plano_gk["aporte_renda_fixa"] >= round(2000.0 * (gk_baixo["pct_sobra_minimo_rf"] / 100.0), 2) - 1.0

    # FIRE Real com Equação de Fisher (desconto de IPCA em RF CDI e FIIs de Papel)
    fire_real = calcular_renda_passiva_real_e_fire(
        rf_calc=rf_res,
        rv_calc=rv_res,
        ipca_anual=macro["ipca_12m"],
        custo_vida_mensal=orc["custo_vida_mensal"],
        gastos_fixos_mensal=orc["total_fixos"],
    )
    if fire_real["rf_nominal_mensal"] > 0:
        assert fire_real["rf_real_mensal"] < fire_real["rf_nominal_mensal"]
    assert fire_real["patrimonio_fire_real"] > 0

    # Teste de Isenção de IR em Ações (Abaixo de 20k)
    ir_acao_isenta = simular_venda_e_ir(
        ticker="BBAS3", classe="Ações", quantidade_venda=100, preco_venda=30.0, preco_medio=25.0, vendas_acumuladas_mes=0.0
    )
    assert ir_acao_isenta["isento"] is True and ir_acao_isenta["ir_devido"] == 0.0

    # Teste Isolamento da Cota R$ 20k: vender FII/ETF retorna vendas_acoes_mes_atualizadas=0 (não consome cota R$ 20k)
    ir_fii_cota = simular_venda_e_ir(
        ticker="HGLG11", classe="FIIs", quantidade_venda=100, preco_venda=160.0, preco_medio=150.0,
        vendas_acumuladas_mes=0.0
    )
    assert ir_fii_cota["vendas_acoes_mes_atualizadas"] == 0.0
    ir_acao_apos_fii = simular_venda_e_ir(
        ticker="BBAS3", classe="Ações", quantidade_venda=500, preco_venda=30.0, preco_medio=25.0,
        vendas_acumuladas_mes=ir_fii_cota["vendas_acoes_mes_atualizadas"]
    )
    assert ir_acao_apos_fii["isento"] is True and ir_acao_apos_fii["vendas_acoes_mes_atualizadas"] == 15000.0

    # Teste Compensação de Prejuízo Acumulado em Ações/ETFs (>20k) e em FIIs (buckets segregados)
    ir_acao_trib_comp = simular_venda_e_ir(
        ticker="BBAS3", classe="Ações", quantidade_venda=800, preco_venda=30.0, preco_medio=25.0,
        vendas_acumuladas_mes=0.0, taxas_corretora=10.0, prejuizo_acumulado_acoes_etfs=1000.0
    )
    assert ir_acao_trib_comp["isento"] is False
    irrf_esp = round(24000.0 * 0.00005, 4)
    res_liq_esp = round((30.0 - 25.0) * 800 - 10.0 - irrf_esp, 2)
    base_pos_prej = round(res_liq_esp - 1000.0, 2)
    assert ir_acao_trib_comp["prejuizo_compensado"] == 1000.0
    assert ir_acao_trib_comp["ir_devido"] == round(base_pos_prej * 0.15, 2)
    assert ir_acao_trib_comp["novo_prejuizo_acumulado_acoes_etfs"] == 0.0

    # Teste Venda de FII com Compensação de Prejuízo em FII (20% SEM isenção)
    ir_fii = simular_venda_e_ir(
        ticker="HGLG11", classe="FIIs", quantidade_venda=10, preco_venda=170.0, preco_medio=150.0,
        prejuizo_acumulado_fiis=50.0
    )
    assert ir_fii["isento"] is False
    irrf_fii_esp = round(1700.0 * 0.00005, 4)
    res_liq_fii_esp = round((170.0 - 150.0) * 10 - irrf_fii_esp, 2)
    assert ir_fii["prejuizo_compensado"] == 50.0
    assert ir_fii["ir_devido"] == round((res_liq_fii_esp - 50.0) * 0.20, 2)
    assert ir_fii["novo_prejuizo_acumulado_fiis"] == 0.0

    # Teste Trava A: ETFs sem isenção de 20k -> 15% sobre lucro e sem consumo de cota 20k
    ir_etf = simular_venda_e_ir(
        ticker="BOVA11", classe="ETFs", quantidade_venda=10, preco_venda=130.0, preco_medio=110.0
    )
    assert ir_etf["isento"] is False and ir_etf["aliquota_ir_pct"] == 15.0 and ir_etf["vendas_acoes_mes_atualizadas"] == 0.0

    # Teste Trava B: Direitos de Subscrição de FIIs (Final 12 -> PM = 0 e 20% sobre 100% da venda bruta)
    ir_sub12 = simular_venda_e_ir(
        ticker="HGLG12", classe="FIIs", quantidade_venda=200, preco_venda=2.50, preco_medio=150.0
    )
    assert ir_sub12["isento"] is False and ir_sub12["preco_medio"] == 0.0 and ir_sub12["ir_devido"] == 100.0

    # Teste Trava A2: BDRs (Nubank) sem isenção de 20k -> 15% sobre lucro e sem consumo de cota 20k
    ir_bdr = simular_venda_e_ir(
        ticker="NVDC34", classe="BDRs", quantidade_venda=20, preco_venda=50.0, preco_medio=40.0
    )
    assert ir_bdr["isento"] is False and ir_bdr["aliquota_ir_pct"] == 15.0 and ir_bdr["vendas_acoes_mes_atualizadas"] == 0.0

    # Teste Mercado Fracionário Inteligente
    assert formatar_ticker_fracionario("BBAS3", "Ação", 25) == "BBAS3F"
    assert formatar_ticker_fracionario("BBAS3", "Ações", 100) == "BBAS3"
    assert formatar_ticker_fracionario("HGLG11", "FII", 15) == "HGLG11"
    assert formatar_ticker_fracionario("NVDC34", "BDRs", 10) == "NVDC34"

    # Teste Rebalanceamento Normalizado + Bloqueio por Teto de Preço + Redirecionamento p/ Caixa
    itens_rv_teste = [
        {"ticker": "BBAS3", "classe": "Ações", "cotacao_atual": 25.0, "peso_alvo": 50.0, "peso_atual": 50.0, "patrimonio_atual": 1000.0, "status": "OK"},
        {"ticker": "TAEE11", "classe": "Ações", "cotacao_atual": 45.0, "peso_alvo": 50.0, "peso_atual": 50.0, "patrimonio_atual": 1000.0, "status": "OK"},
    ]
    mapa_val_teste = {
        "BBAS3": {"preco_teto": 32.0, "status_auditoria": "Validado", "spread_cdi_liquido": None},
        "TAEE11": {"preco_teto": 38.0, "status_auditoria": "Validado", "spread_cdi_liquido": None},  # Acima do teto -> bloqueado!
    }
    rebal = calcular_rebalanceamento_aportes(
        itens_rv_teste, sobra_para_investir=1000.0, valuation_map=mapa_val_teste
    )
    assert len(rebal["bloqueios"]) == 1 and "TAEE11" in rebal["bloqueios"][0]["ticker"]
    elegiveis = [s for s in rebal["aportes"] if not s.get("bloqueado") and s.get("cotas_a_comprar", 0) > 0]
    assert len(elegiveis) == 1 and elegiveis[0]["ticker_base"] == "BBAS3" and elegiveis[0]["cotas_a_comprar"] == 40
    assert round(rebal["capital_alocado"] + rebal["valor_redirecionado_oportunidade"], 2) == 1000.0
    print(f" -> [OK] Gatekeeper, FIRE Real, IR c/ Prejuízos, Trava Teto de Preço e Rebalanceamento Normalizado validados!")

    # 5. Scanner & Metodologia Quantitativa Segmentada
    print("\n[5/8] Testando Bazin Seletivo, Gordon Dinâmico, FII Papel vs Tijolo, ETFs, Score Segurança e Scanner...")
    assert calcular_graham(lpa=-1.5, vpa=10.0) is None
    assert calcular_graham(lpa=2.5, vpa=-5.0) is None

    # 5a. Haircut seletivo de JCP no Modelo de Bazin
    assert obter_fator_haircut_jcp("BBSE3") == 1.00
    assert obter_fator_haircut_jcp("CXSE3") == 1.00
    assert obter_fator_haircut_jcp("ITUB4") == 0.90
    assert obter_fator_haircut_jcp("BBAS3") == 0.90
    bazin_seg = calcular_bazin(cotacao=30.0, dy_pct=8.0, historico_dividendos=[2.0, 2.40, 10.0], ticker="BBSE3")
    bazin_bco = calcular_bazin(cotacao=30.0, dy_pct=8.0, historico_dividendos=[2.0, 2.40, 10.0], ticker="ITUB4")
    assert bazin_seg == round(2.40 / 0.06, 2)
    assert bazin_bco == round((2.40 * 0.90) / 0.06, 2)

    # 5b. Gordon Dinâmico com piso 12% ou CDI+4% e trava Payout <= 60%
    val_banco_selic_alta = calcular_valuation(
        "BBAS3", "Banco", lpa=6.0, vpa=30.0, roe=0.20, dy_projetado=0.10,
        preco_atual=28.0, cdi_anual=13.65, payout_historico=0.80
    )
    # Ke = 0.1365 + 0.04 = 0.1765, Payout travado em 0.60, g = 0.04 -> 30 * (0.20 * 0.60) / (0.1765 - 0.04) = 26.37
    assert "Gordon" in val_banco_selic_alta["modelo_utilizado"]
    assert abs(val_banco_selic_alta["preco_justo"] - round(30.0 * (0.20 * 0.60) / (0.1765 - 0.04), 2)) <= 0.05

    # 5c. FIIs Papel vs Tijolo & Fim do Limbo 0.80..0.85
    val_papel_ok = calcular_valuation("KNCR11", "FII", lpa=0.0, vpa=100.0, roe=0.0, dy_projetado=0.12, preco_atual=95.0)
    val_papel_agio = calcular_valuation("KNCR11", "FII", lpa=0.0, vpa=100.0, roe=0.0, dy_projetado=0.12, preco_atual=106.0)
    val_papel_risco = calcular_valuation("KNIP11", "FII", lpa=0.0, vpa=100.0, roe=0.0, dy_projetado=0.12, preco_atual=82.0)
    assert val_papel_ok["score_preco"] == 100.0
    assert val_papel_agio["score_preco"] < 70.0
    assert val_papel_risco["alerta_credito_cri"] is True and val_papel_risco["score_seguranca"] < 50.0

    val_tijolo_interp = calcular_valuation("HGLG11", "FII", lpa=0.0, vpa=100.0, roe=0.0, dy_projetado=0.09, preco_atual=82.5)
    assert abs(val_tijolo_interp["score_preco"] - 75.0) <= 0.1, f"Interpolação 0.80..0.85 falhou: {val_tijolo_interp['score_preco']}"
    val_fii_grave = calcular_valuation("HCTR11", "FII", lpa=0.0, vpa=100.0, roe=0.0, dy_projetado=0.12, preco_atual=75.0)
    assert val_fii_grave["score_seguranca"] == 0.0

    # 5d. ETFs de Acumulação (MM200, RSI e Tendência 12m) e BDRs Globais (Isentos de Teto Bazin)
    val_etf = calcular_valuation(
        "IVVB11", "ETF", lpa=0.0, vpa=0.0, roe=0.0, dy_projetado=0.0, preco_atual=310.0,
        rsi_14=32.0, mm200=300.0, retorno_12m_pct=18.0
    )
    assert "MM200" in val_etf["modelo_utilizado"] and val_etf["score_projecao"] > 0

    val_bdr = calcular_valuation(
        "NVDC34", "BDR", lpa=1.5, vpa=5.0, roe=0.65, dy_projetado=0.001, preco_atual=120.0,
        rsi_14=42.0, mm200=115.0, retorno_12m_pct=35.0, crescimento_lucro_pct=45.0
    )
    assert "BDR" in val_bdr["modelo_utilizado"]
    assert val_bdr["isento_teto_bazin"] is True and val_bdr["preco_teto"] is None
    assert val_bdr["score_preco"] >= 75.0 and val_bdr["score_projecao"] >= 80.0

    # 5e. Score de Segurança Segmentado por Classe (Ações Não-Financeiras, Bancos, FIIs, ETFs)
    mock_infos_seg = {
        "WEGE3": {"ticker": "WEGE3", "nome": "WEG", "setor": "Bens Industriais", "divida_liquida_ebitda": -0.5, "roe": 25.0, "liquidez_corrente": 2.1, "margem_liquida": 18.0, "pvp": 7.0, "lpa": 1.5},
        "ITUB4": {"ticker": "ITUB4", "nome": "Itaú", "setor": "Bancos", "divida_liquida_ebitda": None, "roe": 21.0, "crescimento_lucro_pct": 12.0, "pvp": 1.8, "margem_liquida": 22.0, "lpa": 3.5},
        "HGLG11": {"ticker": "HGLG11", "nome": "CSHG Logística", "setor": "FII Tijolo", "estabilidade_dividendos_score": 92.0, "volume_medio_diario": 5_000_000.0, "pvp": 0.95},
        "IVVB11": {"ticker": "IVVB11", "nome": "iShares S&P 500", "setor": "ETF de Índice", "volume_medio_diario": 20_000_000.0},
    }
    with patch("scanner.obter_info_ativo", side_effect=lambda t: mock_infos_seg[t.replace(".SA", "").upper()]):
        seg_ind = calcular_score_saude_balanco("WEGE3")
        seg_bco = calcular_score_saude_balanco("ITUB4")
        seg_fii = calcular_score_saude_balanco("HGLG11")
        seg_etf = calcular_score_saude_balanco("IVVB11")
        assert seg_ind["classe_seguranca"] == "Ações Não-Financeiras" and seg_ind["score_saude"] >= 85.0
        assert seg_bco["classe_seguranca"] == "Bancos/Seguradoras" and seg_bco["divida_liq_ebitda"] is None and seg_bco["score_saude"] >= 70.0
        assert seg_fii["classe_seguranca"] == "FII (Tijolo)" and seg_fii["score_saude"] >= 80.0
        assert seg_etf["classe_seguranca"] == "ETF de Acumulação" and seg_etf["score_saude"] >= 88.0

    # 5f. Dual Magic Number (FIIs Mensal vs Ações Anual)
    bolas = calcular_efeito_bola_de_neve([
        {"ticker": "HGLG11", "classe": "FIIs", "cotacao_atual": 150.0, "quantidade": 10},
        {"ticker": "BBAS3", "classe": "Ações", "cotacao_atual": 28.0, "quantidade": 20},
    ])
    mapa_bolas = {b["ticker"]: b for b in bolas}
    if "HGLG11" in mapa_bolas:
        assert mapa_bolas["HGLG11"]["periodicidade_magic"] == "Mensal"
    if "BBAS3" in mapa_bolas:
        assert mapa_bolas["BBAS3"]["periodicidade_magic"] == "Anual"

    # 5g. SanityGate (validar_dados_yfinance)
    df_sanity = pd.DataFrame([
        {"ticker": "TAEE11", "dy": 0.09, "pl": 8.5, "pvp": 1.4},
        {"ticker": "DIST3", "dy": 0.25, "pl": 5.0, "pvp": 1.0},
        {"ticker": "DIST4", "dy": 0.05, "pl": 1.5, "pvp": 0.2},
    ])
    df_validado = validar_dados_yfinance(df_sanity)
    assert list(df_validado["status_auditoria"]) == ["Validado", "Suspeito", "Suspeito"]

    # 5h. Scanner Elite vs Alto Risco (mock controlado + varredura ao vivo)
    fake_hist = pd.DataFrame({"Adj Close": [100.0] * 185 + [98.0 - i * 1.8 for i in range(25)]})
    mock_scan_info = {
        "BBSE3": {"ticker": "BBSE3", "nome": "BB Seguridade", "setor": "Seguradoras", "cotacao": 34.0, "variacao_dia": -1.2, "roe": 55.0, "divida_liquida_ebitda": None, "liquidez_corrente": None, "pvp": 5.0, "crescimento_lucro_pct": 12.0, "margem_liquida": 45.0, "lpa": 4.2, "status_auditoria": "Validado"},
        "RISK3": {"ticker": "RISK3", "nome": "Risco Corp", "setor": "Consumo Cíclico", "cotacao": 10.0, "variacao_dia": -4.0, "roe": 1.0, "divida_liquida_ebitda": 5.0, "liquidez_corrente": 0.6, "pvp": 1.0, "margem_liquida": 2.0, "lpa": 0.5, "status_auditoria": "Validado"},
    }
    with patch("scanner.UNIVERSO_BESST", ["BBSE3.SA"]), \
         patch("scanner.UNIVERSO_CRESCIMENTO", ["RISK3.SA"]), \
         patch("scanner.UNIVERSO_FIIS", []), \
         patch("scanner.UNIVERSO_ETFS", []), \
         patch("scanner.UNIVERSO_BDRS", []), \
         patch("scanner.baixar_historico_multiplo", return_value={"BBSE3.SA": fake_hist, "RISK3.SA": fake_hist}), \
         patch("scanner.obter_info_ativo", side_effect=lambda t: mock_scan_info[t.replace(".SA", "").upper()]):
        op_mock = executar_scanner_oportunidades()
        mapa_op = {o["ticker"]: o for o in op_mock}
        assert mapa_op["BBSE3"]["nivel_oportunidade"] == "elite"
        assert "Elite" in mapa_op["BBSE3"]["qualificacao_risco"]
        assert mapa_op["RISK3"]["nivel_oportunidade"] == "alto_risco"
        assert "Alto Risco" in mapa_op["RISK3"]["qualificacao_risco"]

    besst = analisar_universo_besst(cdi_liquido=macro["cdi_liquido_anual"], cdi_bruto=macro["cdi"])
    fiis = analisar_fiis(cdi_liquido=macro["cdi_liquido_anual"])
    etfs = analisar_etfs(cdi_liquido=macro["cdi_liquido_anual"])
    bdrs = analisar_bdrs(cdi_liquido=macro["cdi_liquido_anual"])
    scanner = executar_scanner_oportunidades()
    top_compras = obter_top_melhores_compras(cdi_liquido=macro["cdi_liquido_anual"])
    assert len(besst) > 0 and len(fiis) > 0 and len(etfs) >= 7 and len(bdrs) >= 8 and len(top_compras) > 0
    assert any(b["ticker"] == "NVDC34" for b in bdrs)
    print(f" -> [OK] Scanner, ETFs ({len(etfs)}), BDRs ({len(bdrs)}), FIIs ({len(fiis)}), BESST ({len(besst)}) e Tríade ({len(top_compras)}) validados!")

    # 6. Educacional e Radar de Notícias (Nacional + Internacional)
    print("\n[6/8] Testando Motor Educacional e Radar de Notícias Global...")
    estudo_hoje = obter_estudo_do_dia()
    assert estudo_hoje is not None and "link" in estudo_hoje
    glossario = obter_glossario_conceitos()
    assert len(glossario) >= 5
    tese_exemplo = inferir_tese_heuristica({"titulo": "Copom mantém tom duro e sinaliza juros elevados por mais tempo"})
    assert tese_exemplo.ticker_alvo in {"ITUB4", "BBAS3", "BBSE3"}
    tese_nvda = inferir_tese_heuristica({
        "titulo": "Jensen Huang's exit from Nvidia raises critical questions for AI chips",
        "escopo": "Internacional",
        "fonte": "CNBC Tech (EUA)",
        "link": "https://example.com/nvda"
    })
    assert tese_nvda.ticker_alvo == "NVDC34"
    print(" -> Motor Educacional e Heurísticas de Notícias (BR + EUA/BDRs) validados.")

    # 7. Exportação para Excel em 6 Abas + Novas Colunas
    print("\n[7/8] Gerando e validando Gestao_Completa_Patrimonio_B3.xlsx...")
    noticias = processar_radar_noticias()
    assert len(noticias) > 0 and all("escopo" in n and "link" in n for n in noticias)
    caminho_xlsx = exportar_para_excel(
        dados_orcamento=orc,
        dados_rf=rf_res,
        dados_rv=rv_res,
        ranking_besst=besst,
        teses_noticias=noticias,
        radar_intraday=scanner,
        radar_fiis=fiis,
        caminho_arquivo=EXCEL_FILE,
        valuation_map=mapa_val_teste,
        cdi_bruto_pct=macro["cdi"],
        cdi_liquido_pct=macro["cdi_liquido_anual"],
        ipca_anual=macro["ipca_12m"],
        meta_meses_reserva=6,
    )
    assert os.path.exists(caminho_xlsx), "Arquivo Excel não foi gerado!"

    wb = openpyxl.load_workbook(caminho_xlsx, read_only=False, data_only=False)
    abas_esperadas = [
        "1_Orcamento_Mensal",
        "2_Minha_Carteira",
        "3_Setores_Mais_Seguros",
        "4_Teses_Futuras_Noticias",
        "5_Radar_Intradiario_e_FIIs",
        "6_Risco_e_Correlacao",
        "7_Calendario_Sazonal",
    ]
    for aba in abas_esperadas:
        assert aba in wb.sheetnames, f"Aba obrigatória {aba} ausente!"
        ws_check = wb[aba]
        assert ws_check.views.sheetView[0].showGridLines is False, f"Gridlines deveriam estar ocultas em {aba}!"
        assert ws_check.freeze_panes is not None, f"Freeze panes ausente em {aba}!"

    # Validar fórmulas vivas na Aba 1 (Orçamento) e Aba 2 (Minha Carteira)
    ws1 = wb["1_Orcamento_Mensal"]
    celulas_aba1 = [str(c.value) for row in ws1.iter_rows(min_row=1, max_row=45) for c in row if c.value is not None]
    assert any(v.startswith("=SUM(") for v in celulas_aba1), "Fórmula =SUM(...) ausente na Aba 1!"
    assert any("/12" in v and v.startswith("=") for v in celulas_aba1), "Fórmula de provisão anual (/12) ausente na Aba 1!"

    ws2 = wb["2_Minha_Carteira"]
    cabecalhos_aba2 = [str(c.value or "") for row in ws2.iter_rows(min_row=1, max_row=25) for c in row if c.value is not None]
    assert any("Preço Teto" in h for h in cabecalhos_aba2), "Coluna Preço Teto ausente na Aba 2!"
    assert any("Spread vs. CDI" in h for h in cabecalhos_aba2), "Coluna Spread vs CDI ausente na Aba 2!"
    assert any(v.startswith("=SUM(") for v in cabecalhos_aba2), "Fórmula =SUM(...) ausente na Aba 2!"
    assert any(v.startswith("=C") and "*D" in v for v in cabecalhos_aba2), "Fórmula =C*D (Valor Investido) ausente na Aba 2!"
    assert any(v.startswith("=C") and "*E" in v for v in cabecalhos_aba2), "Fórmula =C*E (Patrimônio Atual) ausente na Aba 2!"
    assert ws2.auto_filter.ref is not None, "Auto-filtro ausente na Aba 2!"
    assert len(ws2.conditional_formatting) >= 1, "DataBarRule ausente na Aba 2!"

    ws3 = wb["3_Setores_Mais_Seguros"]
    assert ws3.auto_filter.ref is not None, "Auto-filtro ausente na Aba 3!"
    assert len(ws3.conditional_formatting) >= 1, "DataBarRule ausente na Aba 3!"

    ws5 = wb["5_Radar_Intradiario_e_FIIs"]
    assert ws5.auto_filter.ref is not None, "Auto-filtro ausente na Aba 5!"

    wb.close()

    # 8. Consistência final
    print("\n[8/8] Verificação concluída com integridade total.")
    print("=" * 70)
    print("[OK] TODOS OS TESTES PASSARAM COM SUCESSO ABSOLUTO!")
    print("=" * 70)


if __name__ == "__main__":
    executar_testes()
