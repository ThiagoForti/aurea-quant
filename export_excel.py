"""
Módulo de Exportação Sincronizada para Excel (.xlsx) - Design Executivo de Alta Fidelidade
Gera 'Gestao_Completa_Patrimonio_B3.xlsx' com 6 abas padronizadas em estilo corporativo financeiro:
- Tipografia Segoe UI
- Paleta Executiva (Navy #0F172A, Esmeralda #10B981, Cinza Suave #F8FAFC)
- Cards de KPI no topo
- Linhas alternadas (Zebra) para máxima legibilidade
- Formatação numérica impecável (Moeda, Percentual, Inteiros)
- Abas coloridas individualmente
"""
import os
import time
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import DataBarRule
from openpyxl.utils import get_column_letter
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List

from config import EXCEL_FILE
from data_engine import baixar_historico_multiplo, obter_dados_macro
from portfolio_engine import (
    calcular_cobertura_reserva,
    calcular_renda_passiva_real_e_fire,
    construir_mapa_valuation_carteira,
)
from scanner import calcular_score_saude_balanco, obter_calendario_sazonal, calcular_efeito_bola_de_neve

# =============================================================================
# PALETA DE CORES E ESTILOS EXECUTIVOS
# =============================================================================
COLOR_PRIMARY_NAVY = "0F172A"    # Azul Marinho Profundo
COLOR_SECONDARY_BLUE = "1E3A8A"  # Azul Real
COLOR_ACCENT_BLUE = "2563EB"     # Azul Destaque
COLOR_EMERALD = "059669"         # Verde Esmeralda (Lucros / Proventos)
COLOR_EMERALD_LIGHT = "ECFDF5"   # Verde Claro Suave
COLOR_ROSE = "DC2626"            # Vermelho Alerta
COLOR_ROSE_LIGHT = "FEF2F2"      # Vermelho Claro Suave
COLOR_ZEBRA = "F8FAFC"           # Cinza Quase Branco para Zebra
COLOR_CARD_BG = "F1F5F9"         # Fundo de Cards de KPI
COLOR_BORDER = "CBD5E1"          # Borda Suave
COLOR_WHITE = "FFFFFF"

# Fills
FILL_HEADER = PatternFill(start_color=COLOR_PRIMARY_NAVY, end_color=COLOR_PRIMARY_NAVY, fill_type="solid")
FILL_SUBHEADER = PatternFill(start_color=COLOR_SECONDARY_BLUE, end_color=COLOR_SECONDARY_BLUE, fill_type="solid")
FILL_CARD = PatternFill(start_color=COLOR_CARD_BG, end_color=COLOR_CARD_BG, fill_type="solid")
FILL_ZEBRA = PatternFill(start_color=COLOR_ZEBRA, end_color=COLOR_ZEBRA, fill_type="solid")
FILL_TOTAL = PatternFill(start_color=COLOR_EMERALD_LIGHT, end_color=COLOR_EMERALD_LIGHT, fill_type="solid")
FILL_ALERT = PatternFill(start_color=COLOR_ROSE_LIGHT, end_color=COLOR_ROSE_LIGHT, fill_type="solid")

# Fonts (Segoe UI)
FONT_SHEET_TITLE = Font(name="Segoe UI", size=15, bold=True, color=COLOR_PRIMARY_NAVY)
FONT_CARD_TITLE = Font(name="Segoe UI", size=9, bold=True, color="64748B")
FONT_CARD_VALUE = Font(name="Segoe UI", size=13, bold=True, color=COLOR_PRIMARY_NAVY)
FONT_HEADER = Font(name="Segoe UI", size=10, bold=True, color=COLOR_WHITE)
FONT_SECTION = Font(name="Segoe UI", size=11, bold=True, color=COLOR_PRIMARY_NAVY)
FONT_BOLD = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
FONT_REGULAR = Font(name="Segoe UI", size=10, color="1E293B")

# Borders
BORDER_THIN = Border(
    left=Side(style='thin', color=COLOR_BORDER),
    right=Side(style='thin', color=COLOR_BORDER),
    top=Side(style='thin', color=COLOR_BORDER),
    bottom=Side(style='thin', color=COLOR_BORDER)
)
BORDER_TOP_THICK_BOTTOM_DOUBLE = Border(
    top=Side(style='thin', color=COLOR_BORDER),
    bottom=Side(style='double', color=COLOR_PRIMARY_NAVY)
)

# Alignments
ALIGN_LEFT = Alignment(horizontal="left", vertical="center")
ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")
ALIGN_CENTER = Alignment(horizontal="center", vertical="center")


def auto_ajustar_colunas(ws, max_padding: int = 3, min_width: int = 12):
    """Ajusta as larguras das colunas para visualização sem cortes (ignorando o comprimento bruto de fórmulas '=')."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if val_str.startswith("="):
                val_len = 14
            else:
                val_len = len(val_str)
            if val_len > max_len:
                max_len = val_len
        ws.column_dimensions[col_letter].width = max(max_len + max_padding, min_width)


def criar_card_kpi(ws, start_row: int, start_col: int, titulo: str, valor: Any, formato: str = None):
    """Renderiza um card visual elegante de KPI no topo da planilha."""
    c_title = ws.cell(row=start_row, column=start_col, value=titulo)
    c_title.font = FONT_CARD_TITLE
    c_title.fill = FILL_CARD
    c_title.alignment = ALIGN_CENTER
    c_title.border = BORDER_THIN

    c_val = ws.cell(row=start_row + 1, column=start_col, value=valor)
    c_val.font = FONT_CARD_VALUE
    c_val.fill = FILL_CARD
    c_val.alignment = ALIGN_CENTER
    c_val.border = BORDER_THIN
    if formato:
        c_val.number_format = formato


def exportar_para_excel(
    dados_orcamento: Dict[str, Any],
    dados_rf: Dict[str, Any],
    dados_rv: Dict[str, Any],
    ranking_besst: List[Dict[str, Any]],
    teses_noticias: List[Dict[str, Any]],
    radar_intraday: List[Dict[str, Any]],
    radar_fiis: List[Dict[str, Any]],
    caminho_arquivo: Path = EXCEL_FILE,
    valuation_map: Dict[str, Dict[str, Any]] = None,
    cdi_bruto_pct: float = None,
    cdi_liquido_pct: float = None,
    ipca_anual: float = None,
    meta_meses_reserva: int = 6,
) -> str:
    """Gera o arquivo Excel completo e visualmente sofisticado com 7 abas executivas."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove aba padrão

    if cdi_bruto_pct is None or cdi_liquido_pct is None or ipca_anual is None:
        macro_ref = obter_dados_macro()
        if cdi_bruto_pct is None:
            cdi_bruto_pct = float(macro_ref.get("cdi", 10.65))
        if cdi_liquido_pct is None:
            cdi_liquido_pct = float(macro_ref.get("cdi_liquido_anual", cdi_bruto_pct * 0.85))
        if ipca_anual is None:
            ipca_anual = float(macro_ref.get("ipca_12m", macro_ref.get("ipca", 4.5)))

    if valuation_map is None:
        valuation_map = construir_mapa_valuation_carteira(dados_rv.get("itens", []))

    custo_vida_mensal = float(dados_orcamento.get("custo_vida_mensal", dados_orcamento.get("total_despesas", 0.0)) or 0.0)
    gastos_fixos_mensal = float(dados_orcamento.get("total_fixos", 0.0) or 0.0)
    saldo_reserva_rf = float(dados_rf.get("total_reserva_emergencia", 0.0) or 0.0)
    cob_reserva = calcular_cobertura_reserva(saldo_reserva_rf, custo_vida_mensal, meta_meses=meta_meses_reserva)
    fire_real = calcular_renda_passiva_real_e_fire(
        rf_calc=dados_rf,
        rv_calc=dados_rv,
        ipca_anual=ipca_anual,
        custo_vida_mensal=custo_vida_mensal,
        gastos_fixos_mensal=gastos_fixos_mensal,
    )

    # =========================================================================
    # ABA 1: 1_Orcamento_Mensal (Aba Verde Esmeralda — Fórmulas Vivas)
    # =========================================================================
    ws1 = wb.create_sheet(title="1_Orcamento_Mensal")
    ws1.sheet_properties.tabColor = "10B981"
    ws1.views.sheetView[0].showGridLines = False
    ws1.freeze_panes = "A8"

    ws1["A1"] = "DEMONSTRATIVO DE FLUXO DE CAIXA PESSOAL & CAPACIDADE DE APORTE (CFP 50/30/20)"
    ws1["A1"].font = FONT_SHEET_TITLE

    # Seções Detalhadas com Fórmulas Nativas =SUM(...)
    row_cursor = 6
    totais_coords: Dict[str, str] = {}

    for secao_chave, secao_nome, itens in [
        ("receitas", "1. RECEITAS MENSAIS", dados_orcamento.get("receitas", [])),
        ("fixos", "2. GASTOS FIXOS", dados_orcamento.get("gastos_fixos", [])),
        ("variaveis", "3. GASTOS VARIÁVEIS", dados_orcamento.get("gastos_variaveis", [])),
    ]:
        ws1.cell(row=row_cursor, column=1, value=secao_nome).font = FONT_SECTION
        row_cursor += 1

        headers = ["Descrição do Item", "Categoria", "Classificação CFP (50/30)", "Valor Mensal (R$)"]
        for c_idx, h in enumerate(headers, start=1):
            cell = ws1.cell(row=row_cursor, column=c_idx, value=h)
            cell.font = FONT_HEADER
            cell.fill = FILL_HEADER
            cell.border = BORDER_THIN
            cell.alignment = ALIGN_CENTER if c_idx in [2, 3] else (ALIGN_RIGHT if c_idx == 4 else ALIGN_LEFT)
        row_cursor += 1

        start_sec_row = row_cursor
        if not itens:
            ws1.cell(row=row_cursor, column=1, value="(Nenhum item cadastrado)").font = FONT_REGULAR
            ws1.cell(row=row_cursor, column=2, value="-").alignment = ALIGN_CENTER
            ws1.cell(row=row_cursor, column=3, value="-").alignment = ALIGN_CENTER
            c_zero = ws1.cell(row=row_cursor, column=4, value=0.0)
            c_zero.number_format = 'R$ #,##0.00'
            c_zero.alignment = ALIGN_RIGHT
            row_cursor += 1
        else:
            for idx, item in enumerate(itens):
                cat_cfp = item.get("categoria_cfp", "Receita" if secao_chave == "receitas" else "Essencial (50%)")
                c_desc = ws1.cell(row=row_cursor, column=1, value=item.get("nome", ""))
                c_cat = ws1.cell(row=row_cursor, column=2, value=item.get("categoria", ""))
                c_cfp = ws1.cell(row=row_cursor, column=3, value="Entrada Líquida" if secao_chave == "receitas" else cat_cfp)
                c_val = ws1.cell(row=row_cursor, column=4, value=float(item.get("valor", 0.0)))

                for c in (c_desc, c_cat, c_cfp, c_val):
                    c.font = FONT_REGULAR
                    c.border = BORDER_THIN
                    if idx % 2 == 1:
                        c.fill = FILL_ZEBRA

                c_desc.alignment = ALIGN_LEFT
                c_cat.alignment = ALIGN_CENTER
                c_cfp.alignment = ALIGN_CENTER
                c_val.alignment = ALIGN_RIGHT
                c_val.number_format = 'R$ #,##0.00'
                row_cursor += 1

        end_sec_row = row_cursor - 1
        c_tot_lbl = ws1.cell(row=row_cursor, column=1, value=f"TOTAL {secao_nome[3:]}")
        c_tot_b1 = ws1.cell(row=row_cursor, column=2, value="")
        c_tot_b2 = ws1.cell(row=row_cursor, column=3, value="")
        c_tot_val = ws1.cell(row=row_cursor, column=4, value=f"=SUM(D{start_sec_row}:D{end_sec_row})")
        c_tot_val.number_format = 'R$ #,##0.00'
        c_tot_val.alignment = ALIGN_RIGHT
        for c in (c_tot_lbl, c_tot_b1, c_tot_b2, c_tot_val):
            c.font = FONT_BOLD
            c.fill = FILL_TOTAL
            c.border = BORDER_TOP_THICK_BOTTOM_DOUBLE
        totais_coords[secao_chave] = f"D{row_cursor}"
        row_cursor += 2

    # Seção 4: Despesas Anuais & Sazonais (Carimbo Mensal = Valor Anual / 12)
    ws1.cell(row=row_cursor, column=1, value="4. DESPESAS ANUAIS & SAZONAIS (PROVISÃO MENSAL 1/12)").font = FONT_SECTION
    row_cursor += 1
    anual_headers = ["Descrição da Despesa Anual", "Mês / Vencimento", "Valor Anual Estimado (R$)", "Carimbo Mensal Provisão (R$)"]
    for c_idx, h in enumerate(anual_headers, start=1):
        cell = ws1.cell(row=row_cursor, column=c_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_SUBHEADER
        cell.border = BORDER_THIN
        cell.alignment = ALIGN_CENTER if c_idx == 2 else (ALIGN_RIGHT if c_idx in [3, 4] else ALIGN_LEFT)
    row_cursor += 1

    start_anual_row = row_cursor
    itens_anuais = dados_orcamento.get("despesas_anuais", [])
    if not itens_anuais:
        ws1.cell(row=row_cursor, column=1, value="(Nenhuma despesa anual cadastrada)").font = FONT_REGULAR
        ws1.cell(row=row_cursor, column=2, value="-").alignment = ALIGN_CENTER
        c_v0 = ws1.cell(row=row_cursor, column=3, value=0.0)
        c_v0.number_format = 'R$ #,##0.00'
        c_p0 = ws1.cell(row=row_cursor, column=4, value=f"=C{row_cursor}/12")
        c_p0.number_format = 'R$ #,##0.00'
        row_cursor += 1
    else:
        for idx, item in enumerate(itens_anuais):
            c_desc = ws1.cell(row=row_cursor, column=1, value=item.get("nome", ""))
            c_venc = ws1.cell(row=row_cursor, column=2, value=item.get("vencimento", "Anual"))
            c_vanual = ws1.cell(row=row_cursor, column=3, value=float(item.get("valor_anual", item.get("valor", 0.0)) or 0.0))
            c_pmensal = ws1.cell(row=row_cursor, column=4, value=f"=C{row_cursor}/12")
            for c in (c_desc, c_venc, c_vanual, c_pmensal):
                c.font = FONT_REGULAR
                c.border = BORDER_THIN
                if idx % 2 == 1:
                    c.fill = FILL_ZEBRA
            c_desc.alignment = ALIGN_LEFT
            c_venc.alignment = ALIGN_CENTER
            c_vanual.alignment = ALIGN_RIGHT
            c_vanual.number_format = 'R$ #,##0.00'
            c_pmensal.alignment = ALIGN_RIGHT
            c_pmensal.number_format = 'R$ #,##0.00'
            row_cursor += 1

    end_anual_row = row_cursor - 1
    c_atot_lbl = ws1.cell(row=row_cursor, column=1, value="TOTAL DESPESAS ANUAIS & CARIMBO MENSAL")
    c_atot_b = ws1.cell(row=row_cursor, column=2, value="")
    c_atot_anual = ws1.cell(row=row_cursor, column=3, value=f"=SUM(C{start_anual_row}:C{end_anual_row})")
    c_atot_mensal = ws1.cell(row=row_cursor, column=4, value=f"=SUM(D{start_anual_row}:D{end_anual_row})")
    c_atot_anual.number_format = 'R$ #,##0.00'
    c_atot_mensal.number_format = 'R$ #,##0.00'
    c_atot_anual.alignment = ALIGN_RIGHT
    c_atot_mensal.alignment = ALIGN_RIGHT
    for c in (c_atot_lbl, c_atot_b, c_atot_anual, c_atot_mensal):
        c.font = FONT_BOLD
        c.fill = FILL_TOTAL
        c.border = BORDER_TOP_THICK_BOTTOM_DOUBLE
    totais_coords["provisao_anual"] = f"D{row_cursor}"

    # Cards de KPI no Topo conectados às Fórmulas Nativas
    criar_card_kpi(ws1, 3, 1, "RECEITA LÍQUIDA", f"={totais_coords['receitas']}", 'R$ #,##0.00')
    criar_card_kpi(ws1, 3, 2, "GASTOS FIXOS", f"={totais_coords['fixos']}", 'R$ #,##0.00')
    criar_card_kpi(ws1, 3, 3, "GASTOS VARIÁVEIS", f"={totais_coords['variaveis']}", 'R$ #,##0.00')
    criar_card_kpi(ws1, 3, 4, "SOBRA LÍQUIDA (APORTES)", f"=A4-B4-C4-{totais_coords['provisao_anual']}", 'R$ #,##0.00')
    criar_card_kpi(ws1, 3, 5, "TAXA DE POUPANÇA", "=IF(A4>0,D4/A4,0)", '0.0%')
    criar_card_kpi(ws1, 3, 6, "PROVISÃO ANUAL / MÊS", f"={totais_coords['provisao_anual']}", 'R$ #,##0.00')
    criar_card_kpi(ws1, 3, 7, "RESERVA COBERTA (MESES)", cob_reserva.get("cobertura_meses", 0.0), '0.0" m"')

    auto_ajustar_colunas(ws1)

    # =========================================================================
    # ABA 2: 2_Minha_Carteira (Aba Azul Marinho — Fórmulas Vivas & DataBars)
    # =========================================================================
    ws2 = wb.create_sheet(title="2_Minha_Carteira")
    ws2.sheet_properties.tabColor = "1E3A8A"
    ws2.views.sheetView[0].showGridLines = False

    ws2["A1"] = "CONSOLIDAÇÃO PATRIMONIAL: RENDA FIXA (NUBANK/TESOURO) & RENDA VARIÁVEL (B3)"
    ws2["A1"].font = FONT_SHEET_TITLE

    # Bloco Renda Fixa
    ws2.cell(row=6, column=1, value="1. RENDA FIXA (RESERVA DE EMERGÊNCIA & CAIXA)").font = FONT_SECTION

    rf_headers = [
        "Nome da Conta / Título", "Finalidade", "Valor Aplicado (R$)", "Saldo Atual (R$)",
        "Taxa (% CDI)", "Prazo (Dias)", "Alíquota IR (%)", "Rend. Mensal Líq. (R$)"
    ]
    for c_idx, h in enumerate(rf_headers, start=1):
        cell = ws2.cell(row=7, column=c_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.border = BORDER_THIN
        cell.alignment = ALIGN_CENTER if c_idx in [2, 5, 6, 7] else (ALIGN_RIGHT if c_idx in [3, 4, 8] else ALIGN_LEFT)

    rf_first_row = 8
    rf_row = 8
    itens_rf = dados_rf.get("itens", [])
    if not itens_rf:
        ws2.cell(row=rf_row, column=1, value="(Nenhuma aplicação em Renda Fixa cadastrada)").font = FONT_REGULAR
        for c_i in (3, 4, 8):
            c_z = ws2.cell(row=rf_row, column=c_i, value=0.0)
            c_z.number_format = 'R$ #,##0.00'
        rf_row += 1
    else:
        for idx, item in enumerate(itens_rf):
            vals = [
                item.get("nome"), item.get("tipo"), item.get("valor_aplicado"), item.get("saldo_atual"),
                item.get("taxa_cdi") / 100.0, item.get("dias_corridos"), item.get("aliquota_ir_pct") / 100.0,
                item.get("rendimento_mensal_liquido")
            ]
            fill_row = FILL_ZEBRA if idx % 2 == 1 else None
            for c_idx, v in enumerate(vals, start=1):
                c = ws2.cell(row=rf_row, column=c_idx, value=v)
                c.font = FONT_REGULAR
                c.border = BORDER_THIN
                if fill_row:
                    c.fill = fill_row
                if c_idx in [3, 4, 8]:
                    c.number_format = 'R$ #,##0.00'
                    c.alignment = ALIGN_RIGHT
                elif c_idx in [5, 7]:
                    c.number_format = '0.0%'
                    c.alignment = ALIGN_CENTER
                elif c_idx == 6:
                    c.number_format = '#,##0'
                    c.alignment = ALIGN_CENTER
                elif c_idx == 2:
                    c.alignment = ALIGN_CENTER
                else:
                    c.alignment = ALIGN_LEFT
            rf_row += 1

    rf_last_row = rf_row - 1
    rf_total_row = rf_row
    ws2.cell(row=rf_total_row, column=1, value="TOTAL RENDA FIXA").font = FONT_BOLD
    ws2.cell(row=rf_total_row, column=3, value=f"=SUM(C{rf_first_row}:C{rf_last_row})").number_format = 'R$ #,##0.00'
    ws2.cell(row=rf_total_row, column=4, value=f"=SUM(D{rf_first_row}:D{rf_last_row})").number_format = 'R$ #,##0.00'
    ws2.cell(row=rf_total_row, column=8, value=f"=SUM(H{rf_first_row}:H{rf_last_row})").number_format = 'R$ #,##0.00'
    for c_i in range(1, 9):
        cell_t = ws2.cell(row=rf_total_row, column=c_i)
        cell_t.font = FONT_BOLD
        cell_t.fill = FILL_TOTAL
        cell_t.border = BORDER_TOP_THICK_BOTTOM_DOUBLE
        if c_i in [3, 4, 8]:
            cell_t.alignment = ALIGN_RIGHT
    rf_row += 1

    # Bloco Renda Variável com Inteligência Fiscal & Fórmulas Nativas
    rv_start = rf_row + 1
    ws2.cell(row=rv_start, column=1, value="2. RENDA VARIÁVEL B3 & CONTROLE FISCAL DE ISENÇÃO (RFB)").font = FONT_SECTION

    rv_headers = [
        "Ticker", "Classe", "Qtd", "Preço Médio (R$)", "Cotação Atual (R$)",
        "Custo Total (R$)", "Patrimônio Atual (R$)", "Lucro/Prejuízo (R$)", "Rentabilidade (%)",
        "DY Anual (%)", "Renda Mensal Est. (R$)", "Peso Atual (%)", "Peso Alvo (%)",
        "Preço Teto (Bazin/Graham)", "Status Valuation (Aportar / Aguardar)", "Spread vs. CDI Líquido (%)",
        "Regra Fiscal (IRPF)", "Alíquota Ganho Capital"
    ]
    rv_header_row = rv_start + 1
    for c_idx, h in enumerate(rv_headers, start=1):
        cell = ws2.cell(row=rv_header_row, column=c_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_SUBHEADER
        cell.border = BORDER_THIN
        cell.alignment = ALIGN_CENTER if c_idx in [1, 2, 12, 13, 15, 17, 18] else (ALIGN_RIGHT if c_idx in [3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 16] else ALIGN_LEFT)

    rv_first_row = rv_start + 2
    rv_row = rv_first_row
    itens_rv = dados_rv.get("itens", [])
    rv_total_row_expected = rv_first_row + max(1, len(itens_rv))

    if not itens_rv:
        ws2.cell(row=rv_row, column=1, value="(Nenhum ativo de Renda Variável cadastrado)").font = FONT_REGULAR
        for c_i in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13):
            ws2.cell(row=rv_row, column=c_i, value=0.0)
        rv_row += 1
    else:
        for idx, item in enumerate(itens_rv):
            classe = item.get("classe", "Ações")
            is_fii = "fii" in classe.lower()
            is_etf = "etf" in classe.lower()
            is_bdr = "bdr" in classe.lower()

            if is_fii:
                regra_ir = "Sem Isenção (Tributável)"
                aliq_ir = "20% fixo"
            elif is_etf or is_bdr:
                regra_ir = "Sem Isenção"
                aliq_ir = "15% fixo"
            else:
                regra_ir = "Isento até R$ 20k no mês"
                aliq_ir = "15% se > R$ 20k"

            t_base = str(item.get("ticker", "")).replace(".SA", "").strip().upper()
            vinfo = (valuation_map or {}).get(t_base, {})
            cot_val = float(item.get("cotacao_atual", 0.0) or 0.0)
            dy_val = float(item.get("dy_anual", 0.0) or 0.0)
            teto_val = vinfo.get("preco_teto")
            status_aud = vinfo.get("status_auditoria", "Validado")

            if status_aud == "Suspeito" or vinfo.get("alerta_risco_critico"):
                status_val = "🔴 Bloqueado (SanityGate / Risco)"
            elif is_bdr or vinfo.get("isento_teto_bazin"):
                status_val = "🟢 Elegível (Isento Teto Bazin)"
            elif teto_val is not None and float(teto_val) > 0:
                if cot_val <= float(teto_val):
                    status_val = "🟢 Aportar (Abaixo do Teto)"
                else:
                    status_val = "⏸️ Aguardar (Acima do Teto)"
            else:
                status_val = "⚪ Sem Teto Definido"

            spread_cdi_dec = ((dy_val - float(cdi_liquido_pct)) / 100.0) if not (is_etf or is_bdr) else None

            # Fórmulas Nativas do Excel: Custo (Qtd*PM), Patrimônio (Qtd*Cotação), P&L, Rentabilidade %, Renda Mensal e Peso Atual %
            vals = [
                item.get("ticker"),
                classe,
                int(item.get("quantidade", 0)),
                float(item.get("preco_medio", 0.0)),
                cot_val,
                f"=C{rv_row}*D{rv_row}",
                f"=C{rv_row}*E{rv_row}",
                f"=G{rv_row}-F{rv_row}",
                f"=IF(F{rv_row}>0,(G{rv_row}-F{rv_row})/F{rv_row},0)",
                dy_val / 100.0,
                f"=(G{rv_row}*J{rv_row})/12",
                f"=IF($G${rv_total_row_expected}>0,G{rv_row}/$G${rv_total_row_expected},0)",
                float(item.get("peso_alvo", 0.0)) / 100.0,
                round(float(teto_val), 2) if (teto_val is not None and float(teto_val) > 0 and not is_bdr) else "Isento/N.A.",
                status_val,
                spread_cdi_dec if spread_cdi_dec is not None else "Crescimento/Acum.",
                regra_ir,
                aliq_ir,
            ]

            fill_row = FILL_ZEBRA if idx % 2 == 1 else None
            for c_idx, v in enumerate(vals, start=1):
                c = ws2.cell(row=rv_row, column=c_idx, value=v)
                c.font = FONT_REGULAR
                c.border = BORDER_THIN
                if fill_row:
                    c.fill = fill_row
                if c_idx in [4, 5, 6, 7, 8, 11] or (c_idx == 14 and isinstance(v, (int, float))):
                    c.number_format = 'R$ #,##0.00'
                    c.alignment = ALIGN_RIGHT
                elif c_idx in [9, 10, 12, 13]:
                    c.number_format = '0.0%'
                    c.alignment = ALIGN_RIGHT
                elif c_idx == 16 and isinstance(v, (int, float)):
                    c.number_format = '+0.0%;-0.0%;0.0%'
                    c.alignment = ALIGN_RIGHT
                elif c_idx == 3:
                    c.number_format = '#,##0'
                    c.alignment = ALIGN_RIGHT
                elif c_idx in [1, 2, 14, 15, 16, 17, 18]:
                    c.alignment = ALIGN_CENTER
                else:
                    c.alignment = ALIGN_LEFT
            rv_row += 1

    rv_last_row = rv_row - 1
    rv_total_row = rv_row
    ws2.cell(row=rv_total_row, column=1, value="TOTAL RENDA VARIÁVEL B3")
    ws2.cell(row=rv_total_row, column=6, value=f"=SUM(F{rv_first_row}:F{rv_last_row})").number_format = 'R$ #,##0.00'
    ws2.cell(row=rv_total_row, column=7, value=f"=SUM(G{rv_first_row}:G{rv_last_row})").number_format = 'R$ #,##0.00'
    ws2.cell(row=rv_total_row, column=8, value=f"=G{rv_total_row}-F{rv_total_row}").number_format = 'R$ #,##0.00'
    ws2.cell(row=rv_total_row, column=9, value=f"=IF(F{rv_total_row}>0,H{rv_total_row}/F{rv_total_row},0)").number_format = '0.0%'
    ws2.cell(row=rv_total_row, column=11, value=f"=SUM(K{rv_first_row}:K{rv_last_row})").number_format = 'R$ #,##0.00'
    ws2.cell(row=rv_total_row, column=12, value=f"=SUM(L{rv_first_row}:L{rv_last_row})").number_format = '0.0%'
    ws2.cell(row=rv_total_row, column=13, value=f"=SUM(M{rv_first_row}:M{rv_last_row})").number_format = '0.0%'
    for c_i in range(1, 19):
        cell_t = ws2.cell(row=rv_total_row, column=c_i)
        cell_t.font = FONT_BOLD
        cell_t.fill = FILL_TOTAL
        cell_t.border = BORDER_TOP_THICK_BOTTOM_DOUBLE
        if c_i in [6, 7, 8, 9, 11, 12, 13]:
            cell_t.alignment = ALIGN_RIGHT

    # Cards de KPI no Topo de ws2 alimentados por Fórmulas Nativas
    criar_card_kpi(ws2, 3, 1, "PATRIMÔNIO TOTAL", "=B4+C4", 'R$ #,##0.00')
    criar_card_kpi(ws2, 3, 2, "RENDA FIXA TOTAL", f"=D{rf_total_row}", 'R$ #,##0.00')
    criar_card_kpi(ws2, 3, 3, "RENDA VARIÁVEL B3", f"=G{rv_total_row}", 'R$ #,##0.00')
    criar_card_kpi(ws2, 3, 4, "LUCRO/PREJUÍZO B3", f"=H{rv_total_row}", 'R$ #,##0.00')
    criar_card_kpi(ws2, 3, 5, "PROVENTOS / MÊS", f"=H{rf_total_row}+K{rv_total_row}", 'R$ #,##0.00')

    # Freeze Panes, AutoFilter e DataBarRule em Peso Atual vs Alvo (Aba 2)
    ws2.freeze_panes = f"A{rv_first_row}"
    ws2.auto_filter.ref = f"A{rv_header_row}:R{rv_last_row}"
    if rv_last_row >= rv_first_row:
        rule_peso_atual = DataBarRule(start_type="num", start_value=0.0, end_type="num", end_value=0.30, color="10B981", showValue="None", minLength=None, maxLength=None)
        rule_peso_alvo = DataBarRule(start_type="num", start_value=0.0, end_type="num", end_value=0.30, color="2563EB", showValue="None", minLength=None, maxLength=None)
        ws2.conditional_formatting.add(f"L{rv_first_row}:L{rv_last_row}", rule_peso_atual)
        ws2.conditional_formatting.add(f"M{rv_first_row}:M{rv_last_row}", rule_peso_alvo)

    auto_ajustar_colunas(ws2)

    # =========================================================================
    # ABA 3: 3_Setores_Mais_Seguros (Aba Azul Royal)
    # =========================================================================
    ws3 = wb.create_sheet(title="3_Setores_Mais_Seguros")
    ws3.sheet_properties.tabColor = "2563EB"
    ws3.views.sheetView[0].showGridLines = False
    ws3.freeze_panes = "A4"

    ws3["A1"] = "UNIVERSO BESST: SETORES DEFENSIVOS & VALUATION (GRAHAM & BAZIN)"
    ws3["A1"].font = FONT_SHEET_TITLE

    besst_headers = [
        "Ticker", "Nome da Empresa", "Setor", "Cotação (R$)", "DY 12m (%)",
        "P/L", "P/VP", "LPA", "VPA", "Preço Justo Graham (R$)",
        "Margem Graham (%)", "Preço Teto Bazin (R$)", "Margem Bazin (%)",
        "Spread vs CDI Líq (%)", "Diagnóstico de Valor", "Score Geral",
        "Score Saúde (0-100)", "Selo de Higidez", "Dívida Líq/EBITDA", "ROE (%)", "Margem Líq (%)", "Liquidez Corrente"
    ]
    for c_idx, h in enumerate(besst_headers, start=1):
        cell = ws3.cell(row=3, column=c_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.border = BORDER_THIN
        cell.alignment = ALIGN_CENTER

    b_row = 4
    for idx, b in enumerate(ranking_besst):
        ticker_item = b.get("ticker", "")
        saude = calcular_score_saude_balanco(ticker_item)

        vals = [
            ticker_item, b.get("nome"), b.get("setor"), b.get("cotacao"),
            b.get("dy_anual_pct") / 100.0 if b.get("dy_anual_pct") else 0.0,
            b.get("pl"), b.get("pvp"), b.get("lpa"), b.get("vpa"),
            b.get("preco_graham"),
            (b.get("margem_graham_pct") / 100.0) if b.get("margem_graham_pct") is not None else None,
            b.get("preco_bazin"),
            (b.get("margem_bazin_pct") / 100.0) if b.get("margem_bazin_pct") is not None else None,
            (b.get("spread_vs_cdi_liq") / 100.0) if b.get("spread_vs_cdi_liq") is not None else 0.0,
            b.get("diagnostico", "Neutro"),
            b.get("score_defensivo"),
            saude.get("score_saude"),
            saude.get("selo"),
            saude.get("divida_liq_ebitda"),
            saude.get("roe_pct") / 100.0 if saude.get("roe_pct") else 0.0,
            saude.get("margem_liq_pct") / 100.0 if saude.get("margem_liq_pct") else 0.0,
            saude.get("liquidez_corrente")
        ]
        fill_row = FILL_ZEBRA if idx % 2 == 1 else None
        for c_idx, val in enumerate(vals, start=1):
            cell = ws3.cell(row=b_row, column=c_idx, value=val)
            cell.font = FONT_REGULAR
            cell.border = BORDER_THIN
            if fill_row:
                cell.fill = fill_row
            if c_idx in [4, 8, 9, 10, 12] and val is not None:
                cell.number_format = 'R$ #,##0.00'
                cell.alignment = ALIGN_RIGHT
            elif c_idx in [5, 11, 13, 14, 20, 21] and val is not None:
                cell.number_format = '0.0%'
                cell.alignment = ALIGN_RIGHT
            elif c_idx in [6, 7, 16, 17, 19, 22] and val is not None:
                cell.number_format = '#,##0.0'
                cell.alignment = ALIGN_RIGHT
            elif c_idx in [1, 3, 15, 18]:
                cell.alignment = ALIGN_CENTER
            else:
                cell.alignment = ALIGN_LEFT
        b_row += 1

    ws3.auto_filter.ref = f"A3:V{max(4, b_row - 1)}"
    if b_row > 4:
        rule_score_geral = DataBarRule(start_type="num", start_value=0.0, end_type="num", end_value=100.0, color="10B981", showValue="None", minLength=None, maxLength=None)
        ws3.conditional_formatting.add(f"P4:P{b_row - 1}", rule_score_geral)

    auto_ajustar_colunas(ws3)

    # =========================================================================
    # ABA 4: 4_Teses_Futuras_Noticias (Aba Roxo / Púrpura)
    # =========================================================================
    ws4 = wb.create_sheet(title="4_Teses_Futuras_Noticias")
    ws4.sheet_properties.tabColor = "7C3AED"
    ws4.views.sheetView[0].showGridLines = False
    ws4.freeze_panes = "A4"

    ws4["A1"] = "RADAR DE NOTÍCIAS & SECOND-ORDER THINKING (IMPACTO CAUSAL NA B3)"
    ws4["A1"].font = FONT_SHEET_TITLE

    not_headers = [
        "Título da Notícia", "Fonte", "1ª Ordem (Fato Objetivo)",
        "2ª Ordem (Transmissão Econômica)", "3ª Ordem (Tese Resultante B3)",
        "Ativo Alvo", "Cotação (R$)", "Variação Dia (%)", "Status de Assimetria"
    ]
    for c_idx, h in enumerate(not_headers, start=1):
        cell = ws4.cell(row=3, column=c_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_SUBHEADER
        cell.border = BORDER_THIN
        cell.alignment = ALIGN_CENTER

    n_row = 4
    for idx, tese in enumerate(teses_noticias):
        vals = [
            tese.get("titulo"), tese.get("fonte"), tese.get("fato_1a_ordem"),
            tese.get("consequencia_2a_ordem"), tese.get("tese_3a_ordem"),
            tese.get("ticker_alvo"), tese.get("cotacao_atual"),
            (tese.get("variacao_dia_pct", 0.0) / 100.0),
            tese.get("status_assimetria")
        ]
        fill_row = FILL_ZEBRA if idx % 2 == 1 else None
        for c_idx, val in enumerate(vals, start=1):
            cell = ws4.cell(row=n_row, column=c_idx, value=val)
            cell.font = FONT_REGULAR
            cell.border = BORDER_THIN
            if fill_row:
                cell.fill = fill_row
            if c_idx == 7:
                cell.number_format = 'R$ #,##0.00'
                cell.alignment = ALIGN_RIGHT
            elif c_idx == 8:
                cell.number_format = '0.00%'
                cell.alignment = ALIGN_RIGHT
            elif c_idx in [2, 6, 9]:
                cell.alignment = ALIGN_CENTER
            else:
                cell.alignment = ALIGN_LEFT
        n_row += 1

    auto_ajustar_colunas(ws4)

    # =========================================================================
    # ABA 5: 5_Radar_Intradiario_e_FIIs (Aba Âmbar)
    # =========================================================================
    ws5 = wb.create_sheet(title="5_Radar_Intradiario_e_FIIs")
    ws5.sheet_properties.tabColor = "D97706"
    ws5.views.sheetView[0].showGridLines = False
    ws5.freeze_panes = "A5"

    ws5["A1"] = "SCANNER TÉCNICO INTRADIÁRIO & SPREAD DE FIIS SOBRE CDI LÍQUIDO"
    ws5["A1"].font = FONT_SHEET_TITLE

    ws5["A3"] = "1. ATIVOS EM SOBREVENDA (RSI 14 < 30/35 E MM200)"
    ws5["A3"].font = FONT_SECTION

    radar_headers = [
        "Ticker", "Nome", "Setor", "Cotação (R$)", "Variação Dia (%)",
        "RSI (14)", "MM200 (R$)", "Distância MM200 (%)", "Severidade", "Gatilhos Identificados"
    ]
    for c_idx, h in enumerate(radar_headers, start=1):
        cell = ws5.cell(row=4, column=c_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.border = BORDER_THIN
        cell.alignment = ALIGN_CENTER

    rad_row = 5
    for idx, r in enumerate(radar_intraday):
        vals = [
            r.get("ticker"), r.get("nome"), r.get("tipo_setor"), r.get("cotacao"),
            r.get("variacao_dia_pct", 0.0) / 100.0, r.get("rsi_14"), r.get("mm200"),
            r.get("distancia_mm200_pct", 0.0) / 100.0, r.get("severidade"), r.get("motivos")
        ]
        fill_row = FILL_ZEBRA if idx % 2 == 1 else None
        for c_idx, val in enumerate(vals, start=1):
            cell = ws5.cell(row=rad_row, column=c_idx, value=val)
            cell.font = FONT_REGULAR
            cell.border = BORDER_THIN
            if fill_row:
                cell.fill = fill_row
            if c_idx in [4, 7]:
                cell.number_format = 'R$ #,##0.00'
                cell.alignment = ALIGN_RIGHT
            elif c_idx in [5, 8]:
                cell.number_format = '0.0%'
                cell.alignment = ALIGN_RIGHT
            elif c_idx in [1, 6, 9]:
                cell.alignment = ALIGN_CENTER
            else:
                cell.alignment = ALIGN_LEFT
        rad_row += 1

    # FIIs Section
    fii_start = rad_row + 2
    ws5.cell(row=fii_start, column=1, value="2. FUNDOS IMOBILIÁRIOS VS. CDI LÍQUIDO NUBANK").font = FONT_SECTION

    fii_headers = [
        "Ticker FII", "Nome", "Cotação (R$)", "P/VP", "DY 12m (%)",
        "CDI Líquido Nubank (%)", "Spread vs CDI Líq (%)", "Diagnóstico Quantitativo"
    ]
    for c_idx, h in enumerate(fii_headers, start=1):
        cell = ws5.cell(row=fii_start + 1, column=c_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_SUBHEADER
        cell.border = BORDER_THIN
        cell.alignment = ALIGN_CENTER

    fii_row = fii_start + 2
    for idx, f in enumerate(radar_fiis):
        vals = [
            f.get("ticker"), f.get("nome"), f.get("cotacao"), f.get("pvp"),
            f.get("dy_anual_pct", 0.0) / 100.0, f.get("cdi_liquido_referencia", 0.0) / 100.0,
            f.get("spread_cdi_pct", 0.0) / 100.0, f.get("status")
        ]
        fill_row = FILL_ZEBRA if idx % 2 == 1 else None
        for c_idx, val in enumerate(vals, start=1):
            cell = ws5.cell(row=fii_row, column=c_idx, value=val)
            cell.font = FONT_REGULAR
            cell.border = BORDER_THIN
            if fill_row:
                cell.fill = fill_row
            if c_idx == 3:
                cell.number_format = 'R$ #,##0.00'
                cell.alignment = ALIGN_RIGHT
            elif c_idx == 4:
                cell.number_format = '0.00'
                cell.alignment = ALIGN_RIGHT
            elif c_idx in [5, 6, 7]:
                cell.number_format = '0.0%'
                cell.alignment = ALIGN_RIGHT
            elif c_idx == 1:
                cell.alignment = ALIGN_CENTER
            else:
                cell.alignment = ALIGN_LEFT
        fii_row += 1

    ws5.auto_filter.ref = f"A4:J{max(5, rad_row - 1)}"
    auto_ajustar_colunas(ws5)

    # =========================================================================
    # ABA 6: 6_Risco_e_Correlacao (Aba Rose / Vermelha)
    # =========================================================================
    ws6 = wb.create_sheet(title="6_Risco_e_Correlacao")
    ws6.sheet_properties.tabColor = "E11D48"
    ws6.views.sheetView[0].showGridLines = False
    ws6.freeze_panes = "A5"

    ws6["A1"] = "MATRIZ DE RISCO, VOLATILIDADE E CORRELAÇÃO DE RETORNOS DIÁRIOS"
    ws6["A1"].font = FONT_SHEET_TITLE

    tickers_rv = [i["ticker"] for i in dados_rv.get("itens", []) if i.get("ticker")]
    pesos_rv_map = {
        str(i.get("ticker", "")).strip().upper(): float(i.get("patrimonio_atual", 0.0) or 0.0)
        for i in dados_rv.get("itens", [])
        if i.get("ticker")
    }
    soma_pat_rv_sheet = sum(pesos_rv_map.values())

    row_comp_start = 3
    if len(tickers_rv) >= 1:
        try:
            hist = baixar_historico_multiplo(tickers_rv, periodo="1y", intervalo="1d")
            series_fech = {}
            for t in tickers_rv:
                df_t = hist.get(t)
                if df_t is None or df_t.empty:
                    df_t = hist.get(f"{t}.SA")
                if df_t is not None and not df_t.empty:
                    col_p = "Adj Close" if "Adj Close" in df_t.columns else ("Close" if "Close" in df_t.columns else None)
                    if col_p:
                        series_fech[t] = df_t[col_p]

            if len(series_fech) >= 2:
                df_precos = pd.DataFrame(series_fech).dropna()
                df_retornos = df_precos.pct_change().dropna()
                matriz_corr = df_retornos.corr().round(2)

                ws6["A3"] = "Matriz de Correlação de Pearson (Retornos Diários 1 Ano):"
                ws6["A3"].font = FONT_SECTION

                col_tickers = list(matriz_corr.columns)
                for c_idx, t in enumerate(col_tickers, start=2):
                    cell = ws6.cell(row=4, column=c_idx, value=t)
                    cell.font = FONT_HEADER
                    cell.fill = FILL_HEADER
                    cell.border = BORDER_THIN
                    cell.alignment = ALIGN_CENTER

                for r_idx, t_row in enumerate(col_tickers, start=5):
                    c_header = ws6.cell(row=r_idx, column=1, value=t_row)
                    c_header.font = FONT_HEADER
                    c_header.fill = FILL_HEADER
                    c_header.border = BORDER_THIN
                    c_header.alignment = ALIGN_CENTER

                    for c_idx, t_col in enumerate(col_tickers, start=2):
                        val_corr = float(matriz_corr.loc[t_row, t_col])
                        cell = ws6.cell(row=r_row, column=c_idx, value=val_corr)
                        cell.font = FONT_REGULAR
                        cell.border = BORDER_THIN
                        cell.number_format = '0.00'
                        cell.alignment = ALIGN_CENTER

                        # Heatmap condicional suave
                        if t_row == t_col:
                            cell.fill = FILL_CARD
                        elif val_corr > 0.7:
                            cell.fill = FILL_ALERT
                        elif val_corr < 0.3:
                            cell.fill = FILL_TOTAL

                row_comp_start = 5 + len(col_tickers) + 2
            else:
                ws6["A3"] = "Cadastre ao menos 2 ativos com série histórica para gerar a matriz de correlação."
                ws6["A3"].font = FONT_REGULAR
                row_comp_start = 5

            # Comparativo Histórico de Retorno Acumulado (12m) vs CDI no período
            if series_fech:
                ws6.cell(row=row_comp_start, column=1, value="COMPARATIVO DE RETORNO ACUMULADO (1 ANO): CARTEIRA RV & ATIVOS VS. CDI ACUMULADO").font = FONT_SECTION
                comp_headers = [
                    "Ativo / Portfólio", "Retorno Acumulado 12m (%)", "CDI Bruto 12m (%)",
                    "CDI Líquido 12m (%)", "Alpha vs. CDI Líquido (%)", "Veredito no Período"
                ]
                for c_idx, h in enumerate(comp_headers, start=1):
                    cell = ws6.cell(row=row_comp_start + 1, column=c_idx, value=h)
                    cell.font = FONT_HEADER
                    cell.fill = FILL_SUBHEADER
                    cell.border = BORDER_THIN
                    cell.alignment = ALIGN_CENTER

                cdi_bruto_dec = float(cdi_bruto_pct) / 100.0
                cdi_liq_dec = float(cdi_liquido_pct) / 100.0

                linhas_comp = []
                retorno_ponderado_carteira = 0.0
                peso_valido_total = 0.0

                for t, serie in series_fech.items():
                    s_limpa = pd.Series(serie).dropna()
                    if len(s_limpa) >= 2 and float(s_limpa.iloc[0]) > 0:
                        ret_12m = (float(s_limpa.iloc[-1]) / float(s_limpa.iloc[0])) - 1.0
                        alpha = ret_12m - cdi_liq_dec
                        veredito = "🏆 Superou CDI Líquido" if alpha >= 0 else "🟡 Abaixo do CDI Líquido"
                        linhas_comp.append((t, ret_12m, cdi_bruto_dec, cdi_liq_dec, alpha, veredito, False))

                        peso_t = pesos_rv_map.get(t, 0.0) / soma_pat_rv_sheet if soma_pat_rv_sheet > 0 else (1.0 / len(series_fech))
                        retorno_ponderado_carteira += ret_12m * peso_t
                        peso_valido_total += peso_t

                if peso_valido_total > 0:
                    ret_cart = retorno_ponderado_carteira / peso_valido_total
                    alpha_cart = ret_cart - cdi_liq_dec
                    veredito_cart = "🏆 Carteira Superou CDI Líquido" if alpha_cart >= 0 else "🟡 Carteira Abaixo do CDI Líquido"
                    linhas_comp.insert(0, ("📌 CARTEIRA RV (PONDERADA)", ret_cart, cdi_bruto_dec, cdi_liq_dec, alpha_cart, veredito_cart, True))

                r_comp = row_comp_start + 2
                for idx_c, (nome_c, ret_v, cdi_b, cdi_l, alpha_v, vered_v, is_total) in enumerate(linhas_comp):
                    vals_c = [nome_c, ret_v, cdi_b, cdi_l, alpha_v, vered_v]
                    fill_c = FILL_TOTAL if is_total else (FILL_ZEBRA if idx_c % 2 == 1 else None)
                    for c_idx, val_c in enumerate(vals_c, start=1):
                        cell = ws6.cell(row=r_comp, column=c_idx, value=val_c)
                        cell.font = FONT_BOLD if is_total else FONT_REGULAR
                        cell.border = BORDER_THIN
                        if fill_c:
                            cell.fill = fill_c
                        if c_idx in [2, 3, 4, 5]:
                            cell.number_format = '+0.0%;-0.0%;0.0%'
                            cell.alignment = ALIGN_RIGHT
                        elif c_idx == 1:
                            cell.alignment = ALIGN_LEFT
                        else:
                            cell.alignment = ALIGN_CENTER
                    r_comp += 1
        except Exception as e:
            ws6["A3"] = f"Aviso na geração da matriz e comparativo CDI: {e}"
    else:
        ws6["A3"] = "Cadastre ao menos 1 ativo de renda variável para gerar o comparativo de retorno vs. CDI."
        ws6["A3"].font = FONT_REGULAR

    auto_ajustar_colunas(ws6)

    # =========================================================================
    # ABA 7: 7_Calendario_Sazonal (Aba Roxo Ametista)
    # =========================================================================
    ws7 = wb.create_sheet(title="7_Calendario_Sazonal")
    ws7.sheet_properties.tabColor = "8B5CF6"
    ws7.views.sheetView[0].showGridLines = False
    ws7.freeze_panes = "A4"

    ws7["A1"] = "CALENDÁRIO SAZONAL DE PROVENTOS DA B3 & FLUXO DE CAIXA MENSAL"
    ws7["A1"].font = FONT_SHEET_TITLE

    sazonal_res = obter_calendario_sazonal(posicoes_usuario=dados_rv.get("itens", []))
    grade_m = sazonal_res.get("grade_mensal", [])

    saz_headers = ["Mês", "Nome do Mês", "Qtd Pagadores na B3", "Ativos Pagadores Previstos", "Renda Passiva Estimada (R$)"]
    for c_idx, h in enumerate(saz_headers, start=1):
        cell = ws7.cell(row=3, column=c_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.border = BORDER_THIN
        cell.alignment = ALIGN_CENTER

    for idx, gm in enumerate(grade_m, start=1):
        r = 3 + idx
        vals = [
            gm["mes_num"],
            gm["mes_nome"],
            gm["qtd_pagadores"],
            ", ".join(gm["pagadores"]),
            gm["renda_estimada"]
        ]
        fill_row = FILL_ZEBRA if idx % 2 == 1 else None
        for c_idx, val in enumerate(vals, start=1):
            cell = ws7.cell(row=r, column=c_idx, value=val)
            cell.font = FONT_REGULAR
            cell.border = BORDER_THIN
            if fill_row:
                cell.fill = fill_row
            if c_idx == 5:
                cell.number_format = 'R$ #,##0.00'
                cell.alignment = ALIGN_RIGHT
            elif c_idx in [1, 3]:
                cell.alignment = ALIGN_CENTER
            else:
                cell.alignment = ALIGN_LEFT

    # Tabela detalhada de sazonalidade dos ativos B3
    start_det = 18
    ws7.cell(row=start_det, column=1, value="Sazonalidade Histórica Detalhada por Ativo da Bolsa:").font = FONT_SECTION
    det_headers = ["Ticker", "Classe / Segmento", "Frequência", "Meses Históricos de Pagamento", "Total de Meses no Ano"]
    for c_idx, h in enumerate(det_headers, start=1):
        cell = ws7.cell(row=start_det + 1, column=c_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_SUBHEADER
        cell.border = BORDER_THIN
        cell.alignment = ALIGN_CENTER

    det_itens = sazonal_res.get("detalhes_ativos", [])
    for idx, d in enumerate(det_itens, start=1):
        r = start_det + 1 + idx
        vals = [
            d["ticker"],
            d["tipo"],
            d["frequencia"],
            d["meses"],
            d["qtd_meses"]
        ]
        fill_row = FILL_ZEBRA if idx % 2 == 1 else None
        for c_idx, val in enumerate(vals, start=1):
            cell = ws7.cell(row=r, column=c_idx, value=val)
            cell.font = FONT_REGULAR
            cell.border = BORDER_THIN
            if fill_row:
                cell.fill = fill_row
            if c_idx in [1, 3, 5]:
                cell.alignment = ALIGN_CENTER
            else:
                cell.alignment = ALIGN_LEFT

    auto_ajustar_colunas(ws7)

    # Salva de forma atômica e resiliente contra bloqueios momentâneos do Google Drive
    target = Path(caminho_arquivo)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f"{target.name}.tmp")
    wb.save(tmp_path)
    wb.close()

    for tentativa in range(6):
        try:
            os.replace(tmp_path, target)
            break
        except (PermissionError, OSError):
            if tentativa == 5:
                try:
                    alt_path = target.with_name(f"{target.stem}_exportado{target.suffix}")
                    os.replace(tmp_path, alt_path)
                    return str(alt_path)
                except Exception:
                    pass
            time.sleep(0.2 * (tentativa + 1))

    return str(caminho_arquivo)
