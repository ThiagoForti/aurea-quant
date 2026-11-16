"""
Terminal Financeiro B3 & Renda Fixa (Versão Executiva Desktop)
Design Corporativo Elegante com Cockpit Executivo em 1 Minuto, Ticker Bar Bloomberg,
Modo Slate / Light, Barras de Progresso Nativas, Notificações Toast e Rebalanceamento Completo.
"""
import os
import json
import threading
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

from config import (
    STATE_FILE,
    EXCEL_FILE,
    LIMITE_ISENCAO_ACOES_MES,
    CODIGO_DARF_RENDA_VARIAVEL,
    UNIVERSO_ETFS,
    UNIVERSO_BDRS,
)
import importlib
import config
import data_engine
import budget_engine
import portfolio_engine
import scanner
import educational_engine
import news_intelligence
import export_excel

_MODULOS_SISTEMA = (
    config,
    data_engine,
    budget_engine,
    portfolio_engine,
    scanner,
    educational_engine,
    news_intelligence,
    export_excel,
)


def reload_modules_if_needed(force: bool = False) -> bool:
    """
    Recarrega módulos Python somente quando o botão de sincronização for acionado (force=True)
    ou quando o timestamp (mtime) de algum arquivo .py tiver mudado no disco.
    Evita I/O desnecessário no Google Drive e preserva o cache do Streamlit entre cliques.
    """
    mtimes_salvos = st.session_state.setdefault("_mod_mtimes", {})
    recarregou = False
    for mod in _MODULOS_SISTEMA:
        mod_file = getattr(mod, "__file__", None)
        if not mod_file or not os.path.exists(mod_file):
            continue
        try:
            mtime_atual = os.path.getmtime(mod_file)
        except OSError:
            continue
        nome_mod = mod.__name__
        mtime_ant = mtimes_salvos.get(nome_mod)
        if force or (mtime_ant is not None and mtime_atual != mtime_ant):
            importlib.reload(mod)
            recarregou = True
        mtimes_salvos[nome_mod] = mtime_atual
    return recarregou


reload_modules_if_needed(force=False)

from data_engine import (
    obter_dados_macro, load_user_state, save_user_state,
    obter_status_market_cache, limpar_cache_macro
)
from budget_engine import calcular_orcamento, simular_corte_gastos_fire, inferir_categoria_cfp
from portfolio_engine import (
    processar_renda_fixa, processar_renda_variavel,
    simular_venda_e_ir, calcular_rebalanceamento_aportes,
    calcular_aporte_por_classe, calcular_cobertura_reserva,
    calcular_renda_passiva_real_e_fire, construir_mapa_valuation_carteira
)
from scanner import (
    analisar_universo_besst, analisar_fiis, analisar_etfs, analisar_bdrs,
    executar_scanner_oportunidades, obter_calendario_sazonal,
    calcular_efeito_bola_de_neve, calcular_score_saude_balanco,
    obter_top_melhores_compras
)
from educational_engine import (
    obter_estudo_do_dia,
    obter_glossario_conceitos,
    obter_lista_estudos_diarios,
)
from news_intelligence import processar_radar_noticias, inferir_tese_heuristica
from export_excel import exportar_para_excel

DEMO_STATE_FILE = os.path.join(os.path.dirname(STATE_FILE), "user_state_demo.json")

# =============================================================================
# GERENCIAMENTO DE TEMA ORGÂNICO E PAINEL LATERAL (TELA CHEIA)
# =============================================================================
if "tema_slate" not in st.session_state:
    st.session_state["tema_slate"] = False

if "modo_privacidade" not in st.session_state:
    st.session_state["modo_privacidade"] = False

if "ocultar_sidebar" not in st.session_state:
    st.session_state["ocultar_sidebar"] = False

# Sincroniza antes da injeção do CSS caso o widget de toggle tenha sido acionado
if "toggle_slate_canonical" in st.session_state:
    st.session_state["tema_slate"] = bool(st.session_state["toggle_slate_canonical"])

if "toggle_priv_canonical" in st.session_state:
    st.session_state["modo_privacidade"] = bool(st.session_state["toggle_priv_canonical"])

if "toggle_sidebar_canonical" in st.session_state:
    st.session_state["ocultar_sidebar"] = bool(st.session_state["toggle_sidebar_canonical"])


# Configuração da Página
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "aurea_quant.png")
st.set_page_config(
    page_title="Aurea Quant — Private Wealth & B3",
    page_icon=ICON_PATH if os.path.exists(ICON_PATH) else "🏛️",
    layout="wide",
    initial_sidebar_state="collapsed" if st.session_state.get("ocultar_sidebar", False) else "expanded"
)


def _callback_alternar_tema() -> None:
    st.session_state["tema_slate"] = bool(st.session_state.get("toggle_slate_canonical", False))


def _callback_alternar_privacidade() -> None:
    st.session_state["modo_privacidade"] = bool(st.session_state.get("toggle_priv_canonical", False))


def _callback_alternar_sidebar() -> None:
    st.session_state["ocultar_sidebar"] = bool(st.session_state.get("toggle_sidebar_canonical", False))


is_dark = bool(st.session_state["tema_slate"])
is_sidebar_hidden = bool(st.session_state["ocultar_sidebar"])

# Paleta Institucional "Quiet Luxury" (Private Wealth / SaaS Institucional)
if is_dark:
    # Modo Noturno Mineral (Harmonizado para transição opcional)
    bg_app = "#111518"
    bg_card = "#1A2026"
    bg_card_hover = "#212930"
    bg_sidebar = "#0E1215"
    bg_sidebar_border = "#242D35"
    border_color = "#28323B"
    border_subtle = "#1F272E"
    border_input = "#334155"
    text_primary = "#F1F5F9"
    text_secondary = "#CBD5E1"
    text_muted = "#94A3B8"
    tab_bg = "#161B20"
    tab_active = "#0F5132"
    brand_accent = "#15803D"
    brand_primary = "#0F5132"
    brand_button = "#0F5132"
    brand_button_hover = "#15803D"
    accent_pos = "#22C55E"
    accent_pos_bg = "#0F291E"
    accent_pos_text = "#86EFAC"
    accent_pos_border = "#15803D"
    accent_neg = "#F87171"
    accent_neg_bg = "#341818"
    accent_warn = "#FBBF24"
    accent_warn_bg = "#2F2310"
    pill_inactive_bg = "#1E293B"
    plotly_template = "plotly_dark"
    axis_text_color = "#F1F5F9"
    grid_line_color = "#28323B"
else:
    # Modo Diurno Orgânico "Quiet Luxury 2.0" (Padrão Institucional)
    bg_app = "#F8F7F4"           # Alabastro / Linho suave (zero branco puro que cansa a vista)
    bg_card = "#FFFFFF"          # Superfície dos Cards
    bg_card_hover = "#FCFBF9"    # Elevação sutil no hover
    bg_sidebar = "#F1EFEA"       # Fundo da Sidebar
    bg_sidebar_border = "#E2E0D8"# Borda direita sutil da Sidebar
    border_color = "#E6E2D8"     # Borda tom pedra harmônico aquecido
    border_subtle = "#E6E2D8"    # Borda secundária / grade
    border_input = "#CBD5E1"     # Borda de inputs, tabelas e seletores
    text_primary = "#0F172A"     # Slate 900 (Texto principal)
    text_secondary = "#475569"   # Slate 600 (Subtítulos / labels)
    text_muted = "#64748B"       # Slate 500 (Textos de apoio / inativos)
    tab_bg = "#F1EFEA"           # Superfície de apoio
    tab_active = "#0F5132"       # Verde Institucional Profundo
    brand_accent = "#0F5132"     # Cor Primária (Verde Institucional Profundo)
    brand_primary = "#0F5132"    # Verde Institucional Profundo
    brand_button = "#0F5132"     # Botão Primário
    brand_button_hover = "#15803D"# Hover Esmeralda
    accent_pos = "#15803D"       # Verde Esmeralda para indicadores positivos e barras
    accent_pos_bg = "#DCFCE7"    # Verde sálvia claro
    accent_pos_text = "#14532D"  # Verde escuro profundo
    accent_pos_border = "#86EFAC"# Borda verde sálvia
    accent_neg = "#991B1B"       # Risco Crítico
    accent_neg_bg = "#FEE2E2"    # Fundo de Risco Crítico
    accent_warn = "#B45309"      # Alerta Moderado
    accent_warn_bg = "#FEF3C7"   # Fundo de Alerta Moderado
    pill_inactive_bg = "#F1F5F9" # Fundo de pill inativo
    plotly_template = "plotly_white"
    axis_text_color = "#1E293B"
    grid_line_color = "#E2E8F0"


# Biblioteca de Ícones SVG Minimalistas (Estilo Lucide Icons em #15803D)
LUCIDE_SVGS = {
    "target": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    "calendar": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>',
    "scale": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/></svg>',
    "sliders": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><line x1="4" x2="4" y1="21" y2="14"/><line x1="4" x2="4" y1="10" y2="3"/><line x1="12" x2="12" y1="21" y2="12"/><line x1="12" x2="12" y1="8" y2="3"/><line x1="20" x2="20" y1="21" y2="16"/><line x1="20" x2="20" y1="12" y2="3"/><line x1="2" x2="6" y1="14" y2="14"/><line x1="10" x2="14" y1="8" y2="8"/><line x1="18" x2="22" y1="16" y2="16"/></svg>',
    "edit": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>',
    "award": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>',
    "shield": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></svg>',
    "activity": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/></svg>',
    "building": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><rect width="16" height="20" x="4" y="2" rx="2" ry="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/><path d="M12 10h.01"/><path d="M12 14h.01"/><path d="M16 10h.01"/><path d="M16 14h.01"/><path d="M8 10h.01"/><path d="M8 14h.01"/></svg>',
    "trending": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>',
    "newspaper": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6Z"/></svg>',
    "book": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>',
    "compass": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>',
    "layers": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 6px;"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></svg>',
    "check": '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 4px;"><path d="M20 6 9 17l-5-5"/></svg>'
}


def titulo_secao_html(icone_key: str, texto: str, nivel: int = 3) -> str:
    """Retorna HTML de título de seção limpo com ícone SVG minimalista Lucide (#15803D) sem emojis."""
    svg = LUCIDE_SVGS.get(icone_key, LUCIDE_SVGS["layers"])
    tamanho = "1.14rem" if nivel == 3 else "1.02rem"
    return (
        f'<div style="display:flex; align-items:center; font-size:{tamanho}; font-weight:700; '
        f'color:{text_primary}; margin: 14px 0 8px 0; letter-spacing:-0.015em;">{svg}<span>{texto}</span></div>'
    )


# =============================================================================
# CSS WEALTHTECH INSTITUCIONAL & QUIET LUXURY (PRIVATE BANKING CLEAN DESIGN)
# =============================================================================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700;800&display=swap');

    /* Animação Suave de Preenchimento das Barras de Progresso e Score Triplo */
    @keyframes fillBar {{
        from {{ width: 0%; }}
    }}

    /* Variáveis Globais do Streamlit / BaseWeb para Consistência Absoluta */
    :root,
    html,
    body,
    .stApp,
    div[data-testid="stAppViewContainer"],
    div[data-testid="stMain"],
    header[data-testid="stHeader"],
    section[data-testid="stSidebar"] {{
        --primary-color: {accent_pos} !important;
        --background-color: {bg_app} !important;
        --secondary-background-color: {bg_sidebar} !important;
        --text-color: {text_primary} !important;
        color-scheme: {'dark' if is_dark else 'light'} !important;
    }}

    /* Fundo Principal com Profundidade Sutil (Quiet Luxury 2.0) */
    .stApp,
    div[data-testid="stAppViewContainer"],
    div[data-testid="stMain"] {{
        background: {'#111518' if is_dark else 'radial-gradient(circle at 50% 0%, #FDFCFB 0%, #F4F1EA 100%)'} !important;
        background-color: {bg_app} !important;
        color: {text_primary} !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        letter-spacing: -0.01em;
    }}

    /* Tipografia Financeira e Contraste de Textos */
    div[data-testid="stMarkdownContainer"],
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stMarkdownContainer"] h1,
    div[data-testid="stMarkdownContainer"] h2,
    div[data-testid="stMarkdownContainer"] h3,
    div[data-testid="stMarkdownContainer"] h4 {{
        color: {text_primary};
        font-family: 'Inter', sans-serif;
    }}
    div[data-testid="stCaptionContainer"],
    div[data-testid="stCaptionContainer"] * {{
        color: {text_muted} !important;
        font-family: 'Inter', sans-serif !important;
    }}

    /* Blocos de Código e Equações KaTeX */
    div[data-testid="stMarkdownContainer"] code {{
        background-color: {accent_pos_bg} !important;
        color: {accent_pos_text} !important;
        padding: 2px 6px !important;
        border-radius: 6px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-variant-numeric: tabular-nums !important;
        font-size: 0.84em !important;
        border: 1px solid {accent_pos_border} !important;
    }}
    .katex, .katex * {{
        color: {text_primary} !important;
        background: transparent !important;
    }}

    /* Oculta completamente a barra superior de desenvolvimento do Streamlit (Stop, Deploy, Menu e Rodapé) */
    div[data-testid="stToolbarActions"],
    div[data-testid="stStatusWidget"],
    div[data-testid="stAppDeployButton"],
    .stDeployButton,
    .stAppDeployButton,
    div[data-testid="stDecoration"],
    #MainMenu,
    footer {{
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }}

    /* Mantém o cabeçalho invisível mas preserva o botão de abrir/fechar a Sidebar */
    header[data-testid="stHeader"] {{
        background: transparent !important;
        height: 1.8rem !important;
        pointer-events: none !important;
    }}
    header[data-testid="stHeader"] button,
    div[data-testid="collapsedControl"],
    div[data-testid="stSidebarCollapsedControl"],
    div[data-testid="stExpandSidebarButton"],
    button[data-testid="stBaseButton-headerNoPadding"] {{
        pointer-events: auto !important;
    }}

    /* Modo Tela Cheia (Quando o usuário oculta a barra lateral esquerda) */
    section[data-testid="stSidebar"] {{
        display: {'none' if is_sidebar_hidden else 'block'} !important;
        {'width: 0px !important; min-width: 0px !important; max-width: 0px !important;' if is_sidebar_hidden else ''}
    }}

    /* Scrollbar Minimalista */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    ::-webkit-scrollbar-track {{
        background: {bg_app};
    }}
    ::-webkit-scrollbar-thumb {{
        background: {border_input};
        border-radius: 999px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {text_muted};
    }}

    .block-container {{
        padding-top: 1.4rem !important;
        padding-bottom: 3.0rem !important;
        max-width: {'98%' if is_sidebar_hidden else '1420px'} !important;
    }}

    /* Cabeçalho Institucional WealthTech */
    .inst-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 16px 22px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03), 0 4px 12px -2px rgba(15, 23, 42, 0.03);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .inst-brand {{
        display: flex;
        align-items: center;
        gap: 14px;
    }}
    .inst-monogram {{
        width: 42px;
        height: 42px;
        border-radius: 10px;
        background: linear-gradient(135deg, {brand_primary} 0%, {accent_pos} 100%);
        color: #FFFFFF;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 800;
        font-size: 1.02rem;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 3px 10px rgba(15, 81, 50, 0.20);
        letter-spacing: -0.03em;
    }}
    .inst-title {{
        font-size: 1.24rem;
        font-weight: 800;
        color: {text_primary};
        line-height: 1.15;
        letter-spacing: -0.02em;
        margin: 0;
    }}
    .inst-subtitle {{
        font-size: 0.72rem;
        font-weight: 600;
        color: {text_secondary};
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 3px;
    }}
    .inst-status-pill {{
        display: inline-flex;
        align-items: center;
        gap: 7px;
        padding: 6px 13px;
        border-radius: 999px;
        background: {accent_pos_bg};
        border: 1px solid {accent_pos_border};
        color: {accent_pos_text};
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        font-variant-numeric: tabular-nums;
    }}
    .inst-dot {{
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: {accent_pos};
        box-shadow: 0 0 0 3px rgba(21, 128, 61, 0.18);
    }}

    /* Cabeçalhos de Seção Editorial Clean */
    .sec-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: 18px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid {border_subtle};
    }}
    .sec-title-wrap {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .sec-kicker {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 3px 8px;
        border-radius: 6px;
        background: {accent_pos_bg};
        color: {accent_pos_text};
        border: 1px solid {accent_pos_border};
    }}
    .sec-title {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {text_primary};
        letter-spacing: -0.015em;
        margin: 0;
    }}
    .sec-caption {{
        font-size: 0.78rem;
        color: {text_muted};
        font-weight: 500;
    }}

    /* Métricas Nativas do Streamlit (ex: Total a Alocar em #475569 uppercase e font-weight 600) */
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] *,
    div[data-testid="stMetricLabel"] p {{
        color: {text_secondary} !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }}
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] * {{
        color: {text_primary} !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-variant-numeric: tabular-nums !important;
        font-size: 1.45rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em;
    }}

    /* Ticker Bar Estilo Ribbon Institucional (Sticky com Glassmorphism) */
    .ticker-bar {{
        position: sticky;
        top: 0;
        z-index: 999;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 10px;
        background: {'rgba(26, 32, 38, 0.85)' if is_dark else 'rgba(255, 255, 255, 0.85)'};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 18px;
        box-shadow: 0 4px 20px -2px rgba(15, 81, 50, 0.05);
    }}
    .ticker-item {{
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 8px 12px;
        border-radius: 10px;
        background: {bg_app};
        border: 1px solid {border_subtle};
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .ticker-item:hover {{
        border-color: rgba(21, 128, 61, 0.4);
        transform: translateY(-2px);
        box-shadow: 0 6px 14px -4px rgba(15, 81, 50, 0.06);
    }}
    .ticker-label {{
        font-size: 0.68rem;
        font-weight: 600;
        color: {text_secondary};
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 2px;
    }}
    .ticker-val {{
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 0.98rem;
        font-weight: 700;
        color: {text_primary};
        letter-spacing: -0.02em;
    }}

    /* Cards Executivos Private Banking, Radar B3 e Posições (Com Micro-interações e Hover Nativo) */
    .exec-card {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-top: 3px solid #0F5132;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 20px -2px rgba(15, 81, 50, 0.05);
        margin-bottom: 14px;
        position: relative;
        overflow: hidden;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .exec-card::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, {brand_primary}, {accent_pos});
        opacity: 0.85;
    }}
    .exec-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 12px 24px -6px rgba(15, 81, 50, 0.08), 0 4px 8px -4px rgba(15, 23, 42, 0.04);
        border-color: rgba(21, 128, 61, 0.4);
    }}
    .exec-card-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }}
    .exec-card-title {{
        font-size: 0.72rem;
        font-weight: 600;
        color: {text_secondary};
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}
    .exec-card-tag {{
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 0.66rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 999px;
        background: {bg_app};
        border: 1px solid {border_color};
        color: {text_secondary};
    }}
    .exec-card-value {{
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 1.56rem;
        font-weight: 800;
        color: {text_primary};
        line-height: 1.18;
        letter-spacing: -0.03em;
    }}
    .exec-card-sub {{
        font-size: 0.78rem;
        font-weight: 600;
        color: {accent_pos};
        margin-top: 6px;
        font-variant-numeric: tabular-nums;
    }}
    .exec-progress-track {{
        width: 100%;
        height: 5px;
        background: {border_subtle};
        border-radius: 999px;
        overflow: hidden;
        margin-top: 10px;
    }}
    .exec-progress-fill {{
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, {brand_primary}, {accent_pos});
        animation: fillBar 0.8s ease-out forwards;
        transition: width 0.3s ease;
    }}

    /* Banner Elegante do Plano de Ação Recomendado */
    .action-plan-banner {{
        background-color: {'#F0FDF4' if not is_dark else '#0F291E'};
        border: 1px solid {accent_pos_border};
        border-left: 4px solid #15803D;
        border-radius: 10px;
        padding: 13px 16px;
        color: {'#14532D' if not is_dark else '#DCFCE7'};
        font-size: 0.88rem;
        line-height: 1.55;
        font-variant-numeric: tabular-nums;
        margin-top: 8px;
    }}
    .action-plan-banner strong {{
        color: {'#0F5132' if not is_dark else '#86EFAC'};
        font-weight: 700;
    }}
    .total-alocar-box {{
        background: {bg_app};
        border: 1px solid {border_color};
        border-radius: 10px;
        padding: 14px 16px;
        text-align: right;
    }}
    .total-alocar-label {{
        color: #475569;
        font-size: 0.74rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 4px;
    }}
    .total-alocar-val {{
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 1.42rem;
        font-weight: 800;
        color: {text_primary};
    }}

    /* Card de Ativo Fintech Minimalista (List & Grid Cards) */
    .asset-pill-card {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 15px 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.02), 0 4px 10px -2px rgba(15, 23, 42, 0.03);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .asset-pill-card:hover {{
        border-color: rgba(21, 128, 61, 0.4);
        background: {bg_card_hover};
        transform: translateY(-3px);
        box-shadow: 0 12px 24px -6px rgba(15, 81, 50, 0.08), 0 4px 8px -4px rgba(15, 23, 42, 0.04);
    }}
    .asset-pill-ticker {{
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 0.96rem;
        font-weight: 800;
        color: {text_primary};
        letter-spacing: -0.02em;
    }}
    .asset-pill-name {{
        font-size: 0.76rem;
        font-weight: 500;
        color: {text_secondary};
    }}

    /* Card Institucional de Equity Research (Radar de Oportunidades) */
    .quant-research-card {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02), 0 6px 16px -4px rgba(15, 23, 42, 0.03);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .quant-research-card:hover {{
        transform: translateY(-3px);
        border-color: rgba(21, 128, 61, 0.4);
        box-shadow: 0 12px 24px -6px rgba(15, 81, 50, 0.08), 0 4px 8px -4px rgba(15, 23, 42, 0.04);
    }}
    .qr-grid {{
        display: grid;
        grid-template-columns: 2.4fr 1.3fr 1.8fr 2.1fr;
        gap: 18px;
        align-items: center;
    }}
    .qr-rank-badge {{
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 0.72rem;
        font-weight: 800;
        padding: 3px 9px;
        border-radius: 7px;
        background: {bg_app};
        border: 1px solid {border_color};
        color: {text_primary};
    }}
    .qr-ticker {{
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 1.08rem;
        font-weight: 800;
        color: {text_primary};
        letter-spacing: -0.02em;
    }}
    .qr-metric-label {{
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: {text_secondary};
        margin-bottom: 3px;
    }}
    .qr-metric-val {{
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 1.24rem;
        font-weight: 800;
        color: {text_primary};
    }}
    .qr-bar-row {{
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.71rem;
        font-weight: 600;
        color: {text_secondary};
        margin-top: 4px;
        font-variant-numeric: tabular-nums;
    }}
    .qr-bar-track {{
        flex: 1;
        height: 5px;
        background: {border_subtle};
        border-radius: 999px;
        overflow: hidden;
    }}
    .qr-bar-fill {{
        height: 100%;
        border-radius: 999px;
        background: {accent_pos};
        animation: fillBar 0.8s ease-out forwards;
    }}

    /* Banner Didático Editorial */
    .guide-box {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-left: 4px solid {brand_primary};
        border-radius: 12px;
        padding: 14px 20px;
        margin-bottom: 18px;
        font-size: 0.88rem;
        color: {text_primary};
        line-height: 1.55;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02);
    }}

    /* Abas de Navegação (st.tabs) com Barra Inferior Verde #15803D de 3px */
    div[data-testid="stTabs"] [data-baseweb="tab-list"],
    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px !important;
        background-color: transparent !important;
        padding: 0 4px !important;
        border-bottom: 1px solid {border_color} !important;
        margin-bottom: 20px !important;
        width: 100% !important;
    }}
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: #15803D !important;
        height: 3px !important;
    }}
    div[data-testid="stTabs"] [data-baseweb="tab-border"],
    .stTabs [data-baseweb="tab-border"] {{
        display: none !important;
    }}
    div[data-testid="stTabs"] button[data-baseweb="tab"],
    .stTabs button[data-baseweb="tab"] {{
        padding: 10px 18px !important;
        height: auto !important;
        border-radius: 6px 6px 0 0 !important;
        background-color: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        color: #64748B !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }}
    div[data-testid="stTabs"] button[data-baseweb="tab"] *,
    div[data-testid="stTabs"] button[data-baseweb="tab"] div[data-testid="stMarkdownContainer"] p,
    .stTabs button[data-baseweb="tab"] *,
    .stTabs button[data-baseweb="tab"] p,
    .stTabs button[data-baseweb="tab"] span,
    .stTabs button[data-baseweb="tab"] div {{
        color: #64748B !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        opacity: 1 !important;
        transition: color 0.2s ease !important;
    }}
    div[data-testid="stTabs"] button[data-baseweb="tab"]:hover,
    .stTabs button[data-baseweb="tab"]:hover {{
        background-color: rgba(21, 128, 61, 0.05) !important;
        border-radius: 6px 6px 0 0 !important;
        color: #0F5132 !important;
    }}
    div[data-testid="stTabs"] button[data-baseweb="tab"]:hover *,
    div[data-testid="stTabs"] button[data-baseweb="tab"]:hover div[data-testid="stMarkdownContainer"] p,
    .stTabs button[data-baseweb="tab"]:hover *,
    .stTabs button[data-baseweb="tab"]:hover p,
    .stTabs button[data-baseweb="tab"]:hover span {{
        color: #0F5132 !important;
    }}
    div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"],
    .stTabs button[data-baseweb="tab"][aria-selected="true"] {{
        background-color: rgba(21, 128, 61, 0.05) !important;
        border-radius: 6px 6px 0 0 !important;
        border-bottom: 3px solid #15803D !important;
        color: {'#0F5132' if not is_dark else '#34D399'} !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] *,
    div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] div[data-testid="stMarkdownContainer"] p,
    .stTabs button[data-baseweb="tab"][aria-selected="true"] *,
    .stTabs button[data-baseweb="tab"][aria-selected="true"] p,
    .stTabs button[data-baseweb="tab"][aria-selected="true"] span,
    .stTabs button[data-baseweb="tab"][aria-selected="true"] div {{
        color: {'#0F5132' if not is_dark else '#34D399'} !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }}

    /* Caixas Expansíveis, Containers com Borda e Formulários */
    div[data-testid="stExpander"],
    div[data-testid="stForm"],
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {bg_card} !important;
        border: 1px solid {border_color} !important;
        border-radius: 12px !important;
        color: {text_primary} !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02), 0 4px 10px -2px rgba(15, 23, 42, 0.03) !important;
    }}
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary * {{
        color: {text_primary} !important;
        font-weight: 600 !important;
    }}

    /* Alertas e Callouts Orgânicos */
    div[data-testid="stAlert"] {{
        background-color: {bg_card} !important;
        border: 1px solid {border_color} !important;
        border-radius: 12px !important;
    }}
    div[data-testid="stAlert"] * {{
        color: {text_primary} !important;
    }}

    /* Inputs, Selectbox e Multiselect (Fundo #FFFFFF, Borda #CBD5E1 e Texto #0F172A) */
    input,
    select,
    textarea,
    div[data-baseweb="input"],
    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"],
    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"],
    div[data-baseweb="textarea"] textarea,
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div,
    div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    div[data-testid="stNumberInput"] div[data-baseweb="input"] > div {{
        background-color: {bg_card} !important;
        color: {text_primary} !important;
        border: 1px solid {border_input} !important;
        border-radius: 8px !important;
        font-variant-numeric: tabular-nums !important;
    }}
    div[data-baseweb="select"] input {{
        background-color: transparent !important;
        color: {text_primary} !important;
    }}
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div {{
        color: {text_primary} !important;
    }}
    div[data-baseweb="select"] svg {{
        fill: {text_secondary} !important;
        color: {text_secondary} !important;
    }}

    /* Tags Selecionadas no Multiselect (Verde Sálvia Claro #DCFCE7, Texto #14532D, Borda #86EFAC) */
    span[data-baseweb="tag"] {{
        background-color: #DCFCE7 !important;
        color: #14532D !important;
        border: 1px solid #86EFAC !important;
        border-radius: 6px !important;
        padding: 2px 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
    }}
    span[data-baseweb="tag"] *,
    span[data-baseweb="tag"] span,
    span[data-baseweb="tag"] svg {{
        color: #14532D !important;
        fill: #14532D !important;
    }}

    /* Menus, Popovers e Listbox (BaseWeb) */
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[role="listbox"],
    li[role="option"] {{
        background-color: {bg_card} !important;
        color: {text_primary} !important;
    }}
    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {{
        background-color: {accent_pos_bg} !important;
        color: {accent_pos_text} !important;
    }}

    /* Barra Lateral (Sidebar) em #F1EFEA com Borda Direita 1px solid #E2E0D8 */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div {{
        background-color: {bg_sidebar} !important;
        border-right: 1px solid {bg_sidebar_border} !important;
    }}
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] strong,
    section[data-testid="stSidebar"] div[data-testid="stCaptionContainer"] *,
    section[data-testid="stSidebar"] label {{
        color: {text_primary} !important;
    }}
    section[data-testid="stSidebar"] hr {{
        border-color: {bg_sidebar_border} !important;
    }}

    /* Navegação do Radar e Opções Horizontais em Botões Pill Modernos (Sem Bolinha de Radio) */
    div[data-testid="stRadio"] div[role="radiogroup"] {{
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] {{
        background-color: {pill_inactive_bg} !important;
        border: 1px solid {border_input} !important;
        border-radius: 999px !important;
        padding: 7px 16px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        margin: 0 !important;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child {{
        display: none !important;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] p,
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] span {{
        color: {text_secondary} !important;
        font-weight: 600 !important;
        font-size: 0.83rem !important;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"]:hover {{
        border-color: #15803D !important;
        background-color: rgba(21, 128, 61, 0.06) !important;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {{
        background-color: #0F5132 !important;
        border-color: #0F5132 !important;
        box-shadow: 0 3px 10px rgba(15, 81, 50, 0.18) !important;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) *,
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) p,
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) span {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}

    /* Checkboxes e Toggles */
    div[data-testid="stCheckbox"] label,
    div[data-testid="stCheckbox"] label *,
    div[data-testid="stToggle"] label,
    div[data-testid="stToggle"] label * {{
        color: {text_primary} !important;
        font-weight: 600 !important;
    }}

    /* Botões da Sidebar e Ações (Hover e Active Tátil) */
    div.stButton > button,
    div[data-testid="stDownloadButton"] > button,
    div[data-testid="stFormSubmitButton"] > button,
    section[data-testid="stSidebar"] div.stButton > button,
    section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] > button {{
        background: {brand_button} !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        padding: 8px 18px !important;
        box-shadow: 0 2px 5px rgba(15, 81, 50, 0.12) !important;
        transition: all 0.2s ease !important;
    }}
    div.stButton > button:hover,
    div[data-testid="stDownloadButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover,
    section[data-testid="stSidebar"] div.stButton > button:hover,
    section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] > button:hover {{
        background: {brand_button_hover} !important;
        color: #FFFFFF !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(15, 81, 50, 0.15) !important;
    }}
    div.stButton > button:active,
    div[data-testid="stDownloadButton"] > button:active,
    div[data-testid="stFormSubmitButton"] > button:active,
    section[data-testid="stSidebar"] div.stButton > button:active,
    section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] > button:active {{
        transform: translateY(0px) scale(0.98) !important;
    }}
    div.stButton > button *,
    div[data-testid="stDownloadButton"] > button *,
    div[data-testid="stFormSubmitButton"] > button *,
    section[data-testid="stSidebar"] div.stButton > button *,
    section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] > button * {{
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }}

    /* Botões de Link (st.link_button) */
    div[data-testid="stLinkButton"] a,
    a[data-testid="stLinkButton"] {{
        background: {brand_button} !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 8px 20px !important;
        text-decoration: none !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
    }}
    div[data-testid="stLinkButton"] a *,
    a[data-testid="stLinkButton"] * {{
        color: #FFFFFF !important;
    }}
    div[data-testid="stLinkButton"] a:hover,
    a[data-testid="stLinkButton"]:hover {{
        background: {brand_button_hover} !important;
        color: #FFFFFF !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(15, 81, 50, 0.15) !important;
    }}
    div[data-testid="stLinkButton"] a:active,
    a[data-testid="stLinkButton"]:active {{
        transform: translateY(0px) scale(0.98) !important;
    }}

    /* Botões de + e - nos Number Inputs */
    div[data-testid="stNumberInput"] button {{
        background-color: {bg_card} !important;
        color: {text_primary} !important;
        border: 1px solid {border_input} !important;
    }}
    div[data-testid="stNumberInput"] button * {{
        color: {text_primary} !important;
        fill: {text_primary} !important;
    }}

    /* Tabelas e DataFrames (Fundo #FFFFFF, Borda #CBD5E1 e Texto #0F172A) */
    div[data-testid="stDataFrame"],
    div[data-testid="stDataEditor"] {{
        background-color: {bg_card} !important;
        border: 1px solid {border_input} !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02) !important;
        font-variant-numeric: tabular-nums !important;
    }}

    /* Rótulos de Widgets (Labels em #475569) */
    label[data-testid="stWidgetLabel"],
    label[data-testid="stWidgetLabel"] *,
    label[data-testid="stWidgetLabel"] p {{
        color: {text_secondary} !important;
        font-weight: 600 !important;
    }}

    /* Card do Mês Sazonal (Aba Radar) */
    .mes-card {{
        background: {bg_card};
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 14px 12px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .mes-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 12px 24px -6px rgba(15, 81, 50, 0.08), 0 4px 8px -4px rgba(15, 23, 42, 0.04);
        border-color: rgba(21, 128, 61, 0.4);
    }}
    .mes-title {{
        font-size: 0.76rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: {text_secondary};
        margin-bottom: 4px;
        border-bottom: 1px solid {border_subtle};
        padding-bottom: 4px;
    }}
    .mes-renda {{
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 1.02rem;
        font-weight: 800;
        color: {accent_pos};
        margin: 6px 0;
    }}
    .mes-tickers {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.70rem;
        color: {text_muted};
        line-height: 1.3;
        min-height: 28px;
    }}

    /* Redesign do Mapa Sazonal (12 Meses - Borda 1px solid #E2E8F0 e Top 3px solid #15803D / #CBD5E1) */
    .sazonal-box-ativo {{
        background: {bg_card};
        border: 1px solid #E2E8F0;
        border-top: 3px solid #15803D;
        border-radius: 12px;
        padding: 14px 12px;
        text-align: center;
        min-height: 122px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02);
        margin-bottom: 12px;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .sazonal-box-ativo:hover {{
        transform: translateY(-3px);
        box-shadow: 0 12px 24px -6px rgba(15, 81, 50, 0.08), 0 4px 8px -4px rgba(15, 23, 42, 0.04);
        border-color: rgba(21, 128, 61, 0.4);
        border-top: 3px solid #15803D;
    }}
    .sazonal-box-vazio {{
        background-color: {bg_card};
        border: 1px solid #E2E8F0;
        border-top: 3px solid #CBD5E1;
        border-radius: 12px;
        padding: 14px 12px;
        text-align: center;
        min-height: 122px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        opacity: 0.78;
        margin-bottom: 12px;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .sazonal-box-vazio:hover {{
        transform: translateY(-3px);
        box-shadow: 0 12px 24px -6px rgba(15, 81, 50, 0.08), 0 4px 8px -4px rgba(15, 23, 42, 0.04);
        border-color: rgba(21, 128, 61, 0.4);
        border-top: 3px solid #CBD5E1;
    }}
    .sazonal-mes-header-ativo {{
        font-size: 0.74rem;
        font-weight: 700;
        color: #0F5132;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}
    .sazonal-mes-header-vazio {{
        font-size: 0.74rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}
    .sazonal-valor-ativo {{
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 1.05rem;
        font-weight: 800;
        color: #15803D;
        margin: 5px 0;
    }}
    .sazonal-valor-vazio {{
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 0.86rem;
        font-weight: 600;
        color: #64748B;
        margin: 5px 0;
    }}
    .sazonal-tickers-ativo {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.69rem;
        font-weight: 700;
        color: #14532D;
        background: #F0FDF4;
        padding: 3px 6px;
        border-radius: 6px;
        border: 1px solid #DCFCE7;
        line-height: 1.25;
    }}
    .sazonal-tickers-vazio {{
        font-size: 0.70rem;
        color: #64748B;
        line-height: 1.25;
    }}

    /* Paleta Semântica de Alertas (Badges de Segurança) */
    .badge-warn, .accent_warn {{
        background-color: #FEF3C7 !important;
        color: #B45309 !important;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        display: inline-block;
        border: 1px solid #FDE68A;
    }}
    .badge-neg, .accent_neg {{
        background-color: #FEE2E2 !important;
        color: #991B1B !important;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        display: inline-block;
        border: 1px solid #FECACA;
    }}
    .badge-pos, .accent_pos {{
        background-color: #DCFCE7 !important;
        color: #14532D !important;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        display: inline-block;
        border: 1px solid #86EFAC;
    }}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# GESTÃO DE ESTADO CENTRALIZADO (user_state.json) — ESCRITA ATÔMICA
# =============================================================================
def _garantir_defaults_estado(estado: dict) -> dict:
    if not isinstance(estado, dict):
        estado = {}
    orc = estado.setdefault("orcamento", {"receitas": [], "gastos_fixos": [], "gastos_variaveis": [], "despesas_anuais": []})
    orc.setdefault("receitas", [])
    orc.setdefault("gastos_fixos", [])
    orc.setdefault("gastos_variaveis", [])
    orc.setdefault("despesas_anuais", [])
    estado.setdefault("renda_fixa", [])
    estado.setdefault("renda_variavel", [])
    estado.setdefault("historico_patrimonial_mensal", [])
    cfg = estado.setdefault("configuracoes", {})
    cfg.setdefault("alerta_rsi_limite", 30.0)
    cfg.setdefault("meta_meses_reserva", 6)
    cfg.setdefault("prejuizo_acumulado_acoes_etfs", 0.0)
    cfg.setdefault("prejuizo_acumulado_fiis", 0.0)
    return estado


def carregar_estado() -> dict:
    try:
        return _garantir_defaults_estado(load_user_state(STATE_FILE))
    except Exception as e:
        st.error(f"Erro ao ler {STATE_FILE}: {e}")
        return _garantir_defaults_estado({})


def salvar_estado(estado: dict) -> None:
    try:
        save_user_state(_garantir_defaults_estado(estado), STATE_FILE)
    except Exception as e:
        st.error(f"Erro ao salvar estado: {e}")


if "user_state" not in st.session_state:
    st.session_state["user_state"] = carregar_estado()
else:
    st.session_state["user_state"] = _garantir_defaults_estado(st.session_state["user_state"])

estado_atual = st.session_state["user_state"]


def fmt_moeda(valor: float) -> str:
    """Formata valor monetário com proteção de privacidade quando o modo apresentação está ativo."""
    if st.session_state.get("modo_privacidade", False):
        return "R$ •••••••"
    if valor is None or np.isnan(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def escapar_cifrao_md(texto: str) -> str:
    """Escapa 'R$' para 'R\\$' em blocos Markdown puros (st.info/st.markdown) para evitar interpretação como LaTeX."""
    if not texto:
        return ""
    return str(texto).replace("R$ ", "R\\$ ").replace("R$", "R\\$")


def estilizar_grafico_plotly(
    fig: go.Figure,
    altura: int = 335,
    exibir_legenda: bool = False,
    travar_zoom: bool = True,
) -> go.Figure:
    """Aplica layout institucional Plotly adaptado ao tema Diurno/Noturno com padrão numérico brasileiro e trava de zoom."""
    fig.update_layout(
        template=plotly_template,
        height=altura,
        separators=",.",
        font=dict(family="Inter, sans-serif", color=axis_text_color, size=12),
        title=dict(font=dict(family="Inter, sans-serif", color=text_primary, size=15)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=exibir_legenda,
        legend=dict(font=dict(color=axis_text_color, size=11, family="Inter, sans-serif")),
        margin=dict(t=52, b=24, l=20, r=20),
        xaxis=dict(
            tickfont=dict(color=axis_text_color, size=11, family="Inter, sans-serif"),
            title_font=dict(color=axis_text_color, size=12, family="Inter, sans-serif"),
            gridcolor=grid_line_color,
            griddash="dot",
            zerolinecolor=grid_line_color,
            fixedrange=travar_zoom,
        ),
        yaxis=dict(
            tickfont=dict(color=axis_text_color, size=11, family="Inter, sans-serif"),
            title_font=dict(color=axis_text_color, size=12, family="Inter, sans-serif"),
            gridcolor=grid_line_color,
            griddash="dot",
            zerolinecolor=grid_line_color,
            fixedrange=travar_zoom,
        )
    )
    fig.update_traces(textfont=dict(color=text_primary, size=12, family="JetBrains Mono, monospace"))
    return fig


# =============================================================================
# CARREGAMENTO DE DADOS COM CACHE INTELIGENTE
# =============================================================================
@st.cache_data(ttl=900)
def get_macro_cached():
    return obter_dados_macro()

@st.cache_data(ttl=900)
def get_besst_cached(cdi_liq):
    return analisar_universo_besst(cdi_liquido=cdi_liq)

@st.cache_data(ttl=900)
def get_top_compras_cached(cdi_liq):
    return obter_top_melhores_compras(cdi_liquido=cdi_liq)

@st.cache_data(ttl=900)
def get_fiis_cached(cdi_liq):
    return analisar_fiis(cdi_liquido=cdi_liq)

@st.cache_data(ttl=900)
def get_etfs_cached(cdi_liq):
    return analisar_etfs(cdi_liquido=cdi_liq)

@st.cache_data(ttl=900)
def get_bdrs_cached(cdi_liq):
    return analisar_bdrs(cdi_liquido=cdi_liq)

@st.cache_data(ttl=900)
def get_valuation_map_cached(itens_tuple, cdi_liq):
    itens_mock = [{"ticker": t, "classe": c, "cotacao_atual": p} for t, c, p in itens_tuple]
    top_c = get_top_compras_cached(cdi_liq)
    return construir_mapa_valuation_carteira(itens_mock, top_compras=top_c)

@st.cache_data(ttl=900)
def get_scanner_cached():
    return executar_scanner_oportunidades()

@st.cache_data(ttl=900)
def get_noticias_cached():
    return processar_radar_noticias()

@st.cache_data(ttl=900)
def get_sazonal_cached(tickers_tuple):
    return obter_calendario_sazonal(list(tickers_tuple))

@st.cache_data(ttl=3600)
def get_estudos_diarios_cached():
    return obter_lista_estudos_diarios()

@st.cache_data(ttl=3600)
def get_glossario_cached():
    return obter_glossario_conceitos()


macro = get_macro_cached()


# =============================================================================
# PROCESSAMENTO DOS MOTORES QUANTITATIVOS
# =============================================================================
cfg_atual = estado_atual.get("configuracoes", {})
meta_meses_reserva = int(cfg_atual.get("meta_meses_reserva", 6) or 6)

orcamento_calc = calcular_orcamento(estado_atual.get("orcamento", {}))
sobra_mensal = orcamento_calc["sobra_para_investir"]
custo_vida_mensal = orcamento_calc.get("custo_vida_mensal", orcamento_calc.get("total_despesas", 0.0))

rf_calc = processar_renda_fixa(
    itens_rf=estado_atual.get("renda_fixa", []),
    cdi_anual=macro["cdi"],
    ipca_anual=macro.get("ipca_12m", macro.get("ipca", 4.5)),
)

rv_calc = processar_renda_variavel(
    itens_rv=estado_atual.get("renda_variavel", [])
)

patrimonio_total = rf_calc["total_patrimonio_rf"] + rv_calc["total_patrimonio_rv"]
renda_passiva_total = rf_calc.get("total_rendimento_mensal_rf", rf_calc.get("total_rendimento_mensal_liquido", 0.0)) + rv_calc.get("total_renda_mensal_rv", rv_calc.get("total_renda_passiva_mensal", 0.0))

itens_rv_sig = tuple((i.get("ticker", ""), i.get("classe", "Ações"), float(i.get("cotacao_atual", 0.0) or 0.0)) for i in rv_calc.get("itens", []))
valuation_map_carteira = get_valuation_map_cached(itens_rv_sig, macro["cdi_liquido_anual"])

cobertura_reserva_calc = calcular_cobertura_reserva(
    saldo_reserva_rf=rf_calc.get("total_reserva_emergencia", 0.0),
    custo_vida_mensal=custo_vida_mensal,
    meta_meses=meta_meses_reserva,
)

fire_real_calc = calcular_renda_passiva_real_e_fire(
    rf_calc=rf_calc,
    rv_calc=rv_calc,
    ipca_anual=macro.get("ipca_12m", macro.get("ipca", 4.5)),
    custo_vida_mensal=custo_vida_mensal,
    gastos_fixos_mensal=orcamento_calc.get("total_fixos", 0.0),
)


def disparar_sincronizacao_excel():
    """Gera o arquivo Excel sincronizado em segundo plano com dados atualizados."""
    try:
        ranking_besst = get_besst_cached(macro["cdi_liquido_anual"])
        fiis = get_fiis_cached(macro["cdi_liquido_anual"])
        radar = get_scanner_cached()
        noticias = get_noticias_cached()

        exportar_para_excel(
            dados_orcamento=orcamento_calc,
            dados_rf=rf_calc,
            dados_rv=rv_calc,
            ranking_besst=ranking_besst,
            teses_noticias=noticias,
            radar_intraday=radar,
            radar_fiis=fiis,
            caminho_arquivo=EXCEL_FILE,
            valuation_map=valuation_map_carteira,
            cdi_bruto_pct=macro["cdi"],
            cdi_liquido_pct=macro["cdi_liquido_anual"],
            ipca_anual=macro.get("ipca_12m", macro.get("ipca", 4.5)),
            meta_meses_reserva=meta_meses_reserva,
        )
    except Exception as e:
        print(f"[Aviso] Sincronização Excel falhou: {e}")


# =============================================================================
# BARRA LATERAL (SIDEBAR): CONTROLES E EXPORTAÇÃO
# =============================================================================
with st.sidebar:
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; padding:10px 12px; background:{bg_card}; border:1px solid {border_color}; border-radius:12px; margin-bottom:10px;">
        <div class="inst-monogram" style="width:34px; height:34px; font-size:0.88rem; border-radius:9px;">AQ</div>
        <div>
            <div style="font-weight:800; font-size:0.95rem; color:{text_primary}; line-height:1.1;">Aurea Quant</div>
            <div style="font-size:0.66rem; font-weight:700; color:{text_muted}; text-transform:uppercase; letter-spacing:0.06em;">Private Wealth Desk</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(":material/left_panel_close: Ocultar Painel Lateral", width="stretch", key="btn_hide_sidebar_left"):
        st.session_state["ocultar_sidebar"] = True
        st.session_state["toggle_sidebar_canonical"] = True
        st.rerun()
    st.caption(f"**Privacidade:** {'Ativada (Valores Ocultos)' if st.session_state['modo_privacidade'] else 'Desativada (Valores Visíveis)'}")
    st.caption(f"**Tema:** {'Noturno Mineral (Carvão Macio)' if st.session_state['tema_slate'] else 'Diurno Orgânico (Quiet Luxury)'}")

    nova_meta_meses = st.number_input(
        "Meta Reserva de Emergência (Meses):",
        min_value=1,
        max_value=24,
        value=meta_meses_reserva,
        step=1,
        key="inp_meta_meses_reserva",
        help="Define o piso de segurança da Regra Gatekeeper (sobre Gastos Fixos + Variáveis).",
    )
    if int(nova_meta_meses) != meta_meses_reserva:
        estado_atual.setdefault("configuracoes", {})["meta_meses_reserva"] = int(nova_meta_meses)
        salvar_estado(estado_atual)
        st.session_state["user_state"] = estado_atual
        st.toast(f"Meta da Reserva ajustada para {int(nova_meta_meses)} meses!")
        st.rerun()

    st.divider()

    if st.button(":material/sync: Atualizar Cotações e APIs", width="stretch"):
        reload_modules_if_needed(force=True)
        st.cache_data.clear()
        limpar_cache_macro()
        disparar_sincronizacao_excel()
        st.toast("Cotações e taxas do Banco Central sincronizadas!")
        st.rerun()

    if os.path.exists(EXCEL_FILE):
        with open(EXCEL_FILE, "rb") as f_excel:
            st.download_button(
                label=":material/download: Baixar Planilha Excel (.xlsx)",
                data=f_excel.read(),
                file_name="Gestao_Completa_Patrimonio_B3.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch"
            )

    st.divider()
    st.markdown(titulo_secao_html("sliders", "Gestão de Dados", nivel=4), unsafe_allow_html=True)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button(":material/delete: Limpar", width="stretch"):
            estado_atual = {
                "orcamento": {"receitas": [], "gastos_fixos": [], "gastos_variaveis": [], "despesas_anuais": []},
                "renda_fixa": [],
                "renda_variavel": [],
                "historico_patrimonial_mensal": [],
                "configuracoes": {
                    "alerta_rsi_limite": 30.0,
                    "meta_meses_reserva": 6,
                    "prejuizo_acumulado_acoes_etfs": 0.0,
                    "prejuizo_acumulado_fiis": 0.0,
                }
            }
            salvar_estado(estado_atual)
            st.session_state["user_state"] = estado_atual
            disparar_sincronizacao_excel()
            st.toast("Dados da carteira zerados!")
            st.rerun()

    with col_btn2:
        if st.button(":material/database: Demo", width="stretch"):
            if os.path.exists(DEMO_STATE_FILE):
                with open(DEMO_STATE_FILE, "r", encoding="utf-8") as f_demo:
                    estado_atual = _garantir_defaults_estado(json.load(f_demo))
                salvar_estado(estado_atual)
                st.session_state["user_state"] = estado_atual
                disparar_sincronizacao_excel()
                st.toast("Carteira de exemplo carregada!")
                st.rerun()

    st.divider()
    status_cache_mkt = obter_status_market_cache()
    dot_sgs = "#eab308" if macro.get("is_cached") else "#22c55e"
    label_sgs = "Cache Local" if macro.get("is_cached") else "Online"
    dot_b3 = "#eab308" if status_cache_mkt.get("usando_cache") else "#22c55e"
    label_b3 = f"{status_cache_mkt.get('ativos_em_cache', 0)} ativos"

    st.markdown(f"""
    <div style="padding:10px 12px; background:{bg_card}; border:1px solid {border_color}; border-radius:10px; font-size:0.75rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
            <span style="color:{text_muted}; font-weight:600;">Banco Central SGS</span>
            <span style="display:inline-flex; align-items:center; gap:5px; color:{text_primary}; font-weight:700;">
                <span style="width:7px; height:7px; border-radius:50%; background:{dot_sgs}; display:inline-block;"></span>
                {label_sgs}
            </span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="color:{text_muted}; font-weight:600;">Mercado B3</span>
            <span style="display:inline-flex; align-items:center; gap:5px; color:{text_primary}; font-weight:700;">
                <span style="width:7px; height:7px; border-radius:50%; background:{dot_b3}; display:inline-block;"></span>
                {label_b3}
            </span>
        </div>
        <div style="margin-top:6px; font-size:0.67rem; color:{text_muted}; text-align:right;">
            Atualizado: {macro['data_atualizacao']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    if st.button(":material/power_settings_new: Encerrar Aplicativo", width="stretch"):
        st.toast("Encerrando servidor Aurea Quant com segurança...")
        st.success("Servidor encerrado com segurança. Você já pode fechar esta janela.")
        threading.Timer(0.8, lambda: os._exit(0)).start()
        st.stop()


# =============================================================================
# TOPO: CABEÇALHO WEALTHTECH INSTITUCIONAL + MACRO RIBBON
# =============================================================================
col_title, col_top_opt0, col_top_opt1, col_top_opt2 = st.columns([3.7, 1.1, 1.1, 1.0])
with col_title:
    dot_header = "#eab308" if macro.get("is_cached") else "#22c55e"
    origem_header = "Cache Local" if macro.get("is_cached") else "SGS/BCB"
    st.markdown(f"""
    <div class="inst-header">
        <div class="inst-brand">
            <div class="inst-monogram">AQ</div>
            <div>
                <div class="inst-title">Aurea Quant — Private Wealth & B3</div>
                <div class="inst-subtitle">Gestão Patrimonial Quantitativa • Renda Fixa, Dividendos BESST & FIIs</div>
            </div>
        </div>
        <div class="inst-status-pill">
            <span class="inst-dot" style="background:{dot_header};"></span>
            <span>{origem_header} • {macro['data_atualizacao']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_top_opt0:
    st.write("")
    st.toggle(
        ":material/fullscreen: Tela Cheia",
        value=st.session_state.get("ocultar_sidebar", False),
        key="toggle_sidebar_canonical",
        on_change=_callback_alternar_sidebar,
        help="Oculta a barra lateral esquerda para expandir a área de informações.",
    )

with col_top_opt1:
    st.write("")
    st.toggle(
        ":material/visibility_off: Apresentação",
        value=st.session_state.get("modo_privacidade", False),
        key="toggle_priv_canonical",
        on_change=_callback_alternar_privacidade
    )

with col_top_opt2:
    st.write("")
    st.toggle(
        ":material/dark_mode: Noturno",
        value=st.session_state.get("tema_slate", False),
        key="toggle_slate_canonical",
        on_change=_callback_alternar_tema
    )

# TICKER BAR HORIZONTAL: 6 colunas com tipografia tabular JetBrains Mono
st.markdown(f"""
<div class="ticker-bar">
    <div class="ticker-item">
        <span class="ticker-label">Selic Meta</span>
        <span class="ticker-val">{macro['selic']:.2f}% <span style="font-size:0.70rem; color:{text_muted}; font-weight:600;">a.a.</span></span>
    </div>
    <div class="ticker-item">
        <span class="ticker-label">CDI Líquido (IR 15%)</span>
        <span class="ticker-val" style="color: {accent_pos};">{macro['cdi_liquido_anual']:.2f}% <span style="font-size:0.70rem; color:{text_muted}; font-weight:600;">a.a.</span></span>
    </div>
    <div class="ticker-item">
        <span class="ticker-label">Inflação IPCA 12m</span>
        <span class="ticker-val">{macro['ipca_12m']:.2f}% <span style="font-size:0.70rem; color:{text_muted}; font-weight:600;">12m</span></span>
    </div>
    <div class="ticker-item">
        <span class="ticker-label">Juro Real Ex-Post</span>
        <span class="ticker-val" style="color: {brand_accent};">+{macro.get('juro_real_anual', 6.71):.2f}% <span style="font-size:0.70rem; color:{text_muted}; font-weight:600;">real</span></span>
    </div>
    <div class="ticker-item">
        <span class="ticker-label">Câmbio Dólar PTAX</span>
        <span class="ticker-val">R$ {macro['ptax']:.2f}</span>
    </div>
    <div class="ticker-item">
        <span class="ticker-label">Sobra Mensal CFP</span>
        <span class="ticker-val" style="color: {accent_pos};">{fmt_moeda(sobra_mensal)}</span>
    </div>
</div>
""", unsafe_allow_html=True)

if macro.get("is_cached", False):
    st.markdown(
        f'<div style="margin-bottom: 12px;"><span class="badge-warn">ℹ️ Modo Offline: Sem conexão à internet no momento. Operando com taxas do cache local ({macro.get("data_atualizacao")}).</span></div>',
        unsafe_allow_html=True
    )


# =============================================================================
# AS 5 ABAS PRINCIPAIS VISUAIS E FOCADAS (ZERO SCROLL LATERAL / ZERO SETINHAS)
# =============================================================================
tab_cockpit, tab1, tab2, tab_radar, tab_estudos = st.tabs([
    ":material/analytics: Cockpit",
    ":material/account_balance_wallet: Minha Carteira & IR",
    ":material/pie_chart: Meu Orçamento",
    ":material/radar: Radar de Oportunidades",
    ":material/menu_book: Guia Educacional & Estudos"
])


# =============================================================================
# ABA 0: COCKPIT EXECUTIVO (RESUMO EM 1 MINUTO - ZERO POLUIÇÃO)
# =============================================================================
with tab_cockpit:
    gastos_fixos_val = orcamento_calc.get("total_fixos", 0.0)
    renda_real_mensal = fire_real_calc.get("renda_real_mensal_total", renda_passiva_total)
    cobertura_proventos = fire_real_calc.get("cobertura_gastos_fixos_real_pct", 0.0)
    cobertura_proventos_nom = fire_real_calc.get("cobertura_gastos_fixos_nominal_pct", 0.0)
    meses_reserva = cobertura_reserva_calc.get("cobertura_meses", 0.0)
    pct_rf_total = (rf_calc["total_patrimonio_rf"] / patrimonio_total * 100.0) if patrimonio_total > 0 else 0.0
    pct_rv_total = (rv_calc["total_patrimonio_rv"] / patrimonio_total * 100.0) if patrimonio_total > 0 else 0.0
    prog_cobertura = min(100.0, max(4.0, cobertura_proventos))
    prog_reserva = min(100.0, max(4.0, (meses_reserva / max(1, meta_meses_reserva)) * 100.0))
    prog_poupanca = min(100.0, max(4.0, (orcamento_calc['taxa_poupanca_pct'] / 30.0) * 100.0))

    # 4 Cards Consolidados com Micro-Barras de Progresso e Tags Institucionais
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 14px;">
        <div class="exec-card" style="border-top: 3px solid #0F5132;">
            <div class="exec-card-header">
                <span class="exec-card-title">Patrimônio Consolidado</span>
                <span class="exec-card-tag">{pct_rf_total:.0f}% RF • {pct_rv_total:.0f}% B3</span>
            </div>
            <div class="exec-card-value">{fmt_moeda(patrimonio_total)}</div>
            <div class="exec-progress-track">
                <div class="exec-progress-fill" style="width: {max(10.0, pct_rv_total):.1f}%;"></div>
            </div>
            <div class="exec-card-sub" style="color: {text_muted};">Custódia Integrada Nubank + B3</div>
        </div>
        <div class="exec-card" style="border-top: 3px solid #0F5132;">
            <div class="exec-card-header">
                <span class="exec-card-title">Renda Passiva Sustentável</span>
                <span class="exec-card-tag">FISHER REAL</span>
            </div>
            <div class="exec-card-value" style="color: {accent_pos};">{fmt_moeda(renda_real_mensal)}<span style="font-size:0.85rem; font-weight:600;">/mês</span></div>
            <div class="exec-progress-track">
                <div class="exec-progress-fill" style="width: {prog_cobertura:.1f}%;"></div>
            </div>
            <div class="exec-card-sub" style="color: {text_muted};">Nominal: {fmt_moeda(renda_passiva_total)}/mês (desc. IPCA CDI/Papel)</div>
        </div>
        <div class="exec-card" style="border-top: 3px solid #0F5132;">
            <div class="exec-card-header">
                <span class="exec-card-title">Cobertura da Reserva</span>
                <span class="exec-card-tag">META: {meta_meses_reserva}M (FIXOS+VAR.)</span>
            </div>
            <div class="exec-card-value" style="color: {accent_pos if not cobertura_reserva_calc['gatekeeper_ativo'] else accent_warn};">{meses_reserva:.2f} <span style="font-size:0.95rem; font-weight:600;">meses</span></div>
            <div class="exec-progress-track">
                <div class="exec-progress-fill" style="width: {prog_reserva:.1f}%;"></div>
            </div>
            <div class="exec-card-sub" style="color: {accent_pos if not cobertura_reserva_calc['gatekeeper_ativo'] else accent_warn};">
                {'✓ Porto Seguro Consolidado' if not cobertura_reserva_calc['gatekeeper_ativo'] else f"Gatekeeper Ativo (faltam {fmt_moeda(cobertura_reserva_calc['deficit_rs'])})"}
            </div>
        </div>
        <div class="exec-card" style="border-top: 3px solid #0F5132;">
            <div class="exec-card-header">
                <span class="exec-card-title">Sobra p/ Investir</span>
                <span class="exec-card-tag">CFP 50/30/20</span>
            </div>
            <div class="exec-card-value" style="color: {brand_accent};">{fmt_moeda(sobra_mensal)}</div>
            <div class="exec-progress-track">
                <div class="exec-progress-fill" style="width: {prog_poupanca:.1f}%;"></div>
            </div>
            <div class="exec-card-sub" style="color: {text_muted};">Taxa de Poupança: {orcamento_calc['taxa_poupanca_pct']:.1f}% da renda</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Card Especial: Índice de Cobertura de Vida pela Renda Passiva
    st.markdown(f"""
    <div class="exec-card" style="margin-bottom: 14px; border-left: 4px solid {brand_accent};">
        <div class="exec-card-header">
            <span class="exec-card-title">Índice de Cobertura de Vida pela Renda Passiva</span>
            <span class="exec-card-tag">AUTONOMIA DOS GASTOS ESSENCIAIS</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:12px;">
            <div class="exec-card-value" style="color: {brand_accent}; font-size:1.55rem;">
                {cobertura_proventos:.1f}% <span style="font-size:0.88rem; font-weight:600; color:{text_secondary};">dos seus gastos fixos essenciais já são pagos automaticamente</span>
            </div>
            <div style="font-family:'JetBrains Mono', monospace; font-size:0.80rem; color:{text_muted};">
                {fmt_moeda(renda_real_mensal)}/mês reais de {fmt_moeda(gastos_fixos_val)}/mês fixos (Nom.: {cobertura_proventos_nom:.1f}%)
            </div>
        </div>
        <div class="exec-progress-track" style="margin-top: 8px;">
            <div class="exec-progress-fill" style="width: {prog_cobertura:.1f}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if cobertura_reserva_calc.get("gatekeeper_ativo"):
        st.warning(escapar_cifrao_md(
            f"**Regra Gatekeeper de Segurança Acionada:** Sua Reserva de Emergência cobre atualmente "
            f"**{meses_reserva:.2f} meses** do seu custo de vida total (Fixos + Variáveis = {fmt_moeda(custo_vida_mensal)}/mês), "
            f"abaixo da meta de **{meta_meses_reserva} meses**. Até recompor o colchão ({fmt_moeda(cobertura_reserva_calc['deficit_rs'])}), "
            f"**{cobertura_reserva_calc['pct_sobra_minimo_rf']:.0f}% da sobra mensal** é priorizada na Renda Fixa."
        ))

    # Card Central: "Plano de Ação do Mês"
    posicoes_rv = rv_calc.get("itens", [])
    carteira_vazia = (len(estado_atual.get("renda_fixa", [])) == 0 and len(posicoes_rv) == 0)

    if not carteira_vazia and sobra_mensal > 0 and posicoes_rv:
        rebal_cockpit = calcular_aporte_por_classe(
            itens_rv=posicoes_rv,
            rf_investimento_atual=rf_calc["total_caixa_oportunidade"],
            sobra_para_investir=sobra_mensal,
            valuation_map=valuation_map_carteira,
            saldo_reserva_emergencia=rf_calc["total_reserva_emergencia"],
            custo_vida_mensal=custo_vida_mensal,
            meta_meses_reserva=meta_meses_reserva,
        )
        sugestoes = [s for s in rebal_cockpit.get("aportes", []) if not s.get("bloqueado") and s["cotas_a_comprar"] > 0][:3]
        sugestoes_html = " &nbsp;|&nbsp; ".join([
            f"<strong>+{s['cotas_a_comprar']} {s['ticker']}</strong> ({fmt_moeda(s['valor_aporte_sugerido'])}) "
            f"<span class='exec-card-tag' style='margin-left:3px;'>{s.get('micro_tag', 'Elegível')}</span>"
            for s in sugestoes
        ])
        rf_dest = rebal_cockpit.get("aporte_renda_fixa", 0.0)
        redir_caixa = rebal_cockpit.get("valor_redirecionado_oportunidade", 0.0)
        rf_tag = " <span class='exec-card-tag'>Reserva de Oportunidade / Selic</span>" if redir_caixa > 10.0 or cobertura_reserva_calc["gatekeeper_ativo"] else ""
        rf_html = f" &nbsp;|&nbsp; <strong>Renda Fixa / Caixa:</strong> {fmt_moeda(rf_dest)}{rf_tag}" if rf_dest > 0 else ""

        with st.container(border=True):
            c_act1, c_act2 = st.columns([3, 1])
            with c_act1:
                st.markdown(titulo_secao_html("target", "Plano de Ação Recomendado para Este Mês", nivel=4), unsafe_allow_html=True)
                if sugestoes_html or rf_html:
                    st.markdown(
                        f'<div style="font-size:0.90rem; color:{text_secondary}; margin-bottom:8px;">Com a sua sobra de <strong style="color:{text_primary};">{fmt_moeda(sobra_mensal)}</strong>, a alocação quantitativa (pós-filtro de Teto e Gatekeeper) sugere:</div>'
                        f'<div class="action-plan-banner">{sugestoes_html}{rf_html}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="action-plan-banner">Carteira equilibrada ou ativos acima do Preço Teto: destinar <strong>{fmt_moeda(sobra_mensal)}</strong> para Caixa Selic / Caixinha Nubank (Reserva de Oportunidade).</div>',
                        unsafe_allow_html=True
                    )
                bloq_ck = rebal_cockpit.get("bloqueios", [])
                if bloq_ck:
                    nomes_b = ", ".join(f"{b['ticker']} ({b['motivo_status']})" for b in bloq_ck[:3])
                    st.caption(f"Ativos em espera por Valuation/SanityGate: {nomes_b}")
            with c_act2:
                st.markdown(f"""
                <div class="total-alocar-box">
                    <div class="total-alocar-label">TOTAL A ALOCAR</div>
                    <div class="total-alocar-val">{fmt_moeda(sobra_mensal)}</div>
                    <div style="font-size:0.72rem; color:{text_muted}; margin-top:4px;">Normalizado c/ Trava de Teto & Reserva</div>
                </div>
                """, unsafe_allow_html=True)
    elif carteira_vazia:
        st.info("**Bem-vindo ao seu Cockpit!** Sua carteira ainda está vazia. Você pode clicar em **'Demo'** na barra lateral para carregar um exemplo completo ou ir na aba **'Minha Carteira'** para cadastrar seus ativos.")

    # Destaque de Melhores Oportunidades de Compra Segundo a Tríade (Preço + Projeção + Segurança)
    top_compras_mercado = get_top_compras_cached(macro["cdi_liquido_anual"])[:3]
    if top_compras_mercado:
        st.markdown("""
        <div class="sec-header">
            <div class="sec-title-wrap">
                <span class="sec-kicker">RADAR B3</span>
                <span class="sec-title">Melhores Oportunidades de Entrada Hoje (Filtro Anti-Risco)</span>
            </div>
            <span class="sec-caption">Top 3 ativos auditados pelo SanityGate • Score Triplo Segmentado</span>
        </div>
        """, unsafe_allow_html=True)
        cols_destaque = st.columns(3)
        for idx_top, op_compra in enumerate(top_compras_mercado):
            dy_isento_ck = float(op_compra.get("dy_anual_pct", 0.0))
            dy_bruto_ck = float(op_compra.get("dy_bruto_cdi_pct", dy_isento_ck / (1.0 - 0.15)))
            with cols_destaque[idx_top]:
                st.markdown(f"""
                <div class="asset-pill-card" style="border-left: 4px solid {op_compra['selo_cor']}; flex-direction: column; align-items: flex-start;">
                    <div style="display: flex; justify-content: space-between; width: 100%; align-items: center; margin-bottom: 6px;">
                        <div>
                            <span class="qr-rank-badge">#{idx_top+1}</span>
                            <span class="asset-pill-ticker" style="margin-left: 6px;">{op_compra['ticker']}</span>
                        </div>
                        <span style="font-family: 'JetBrains Mono', monospace; font-weight: 800; color: {accent_pos}; font-size: 1.02rem;">R$ {op_compra['cotacao']:.2f}</span>
                    </div>
                    <div class="asset-pill-name">{op_compra['nome']} • <strong>{op_compra['tipo']}</strong></div>
                    <div style="width: 100%; margin: 10px 0 6px 0; padding-top: 8px; border-top: 1px solid {border_subtle}; display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.76rem; font-weight: 700; color: {text_muted}; text-transform: uppercase;">Score Triplo</span>
                        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.90rem; font-weight: 800; color: {op_compra['selo_cor']};">{op_compra['score_geral']:.0f}/100</span>
                    </div>
                    <div class="exec-progress-track" style="margin-top: 2px; margin-bottom: 8px;">
                        <div class="exec-progress-fill" style="width: {op_compra['score_geral']:.0f}%;"></div>
                    </div>
                    <div style="font-size: 0.78rem; color: {text_primary}; margin-top: 2px;">
                        DY Projetado: <strong>{dy_isento_ck:.1f}% a.a.</strong> <span style="color:#636b78; font-size:12px;">(equivale a {dy_bruto_ck:.1f}% bruto no CDI)</span>
                    </div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.70rem; color: {text_muted}; margin-top: 4px;">
                        Preço: {op_compra['score_preco']:.0f} | Proj: {op_compra['score_projecao']:.0f} | Seg: {op_compra['score_seguranca']:.0f}
                    </div>
                    <div style="font-size: 0.75rem; margin-top: 8px; font-weight: 700; color: {op_compra['selo_cor']};">
                        {op_compra['veredito']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # 2 Gráficos Executivos Lado a Lado em Containers Refinados
    col_ck1, col_ck2 = st.columns(2)
    with col_ck1:
        with st.container(border=True):
            dados_donut = []
            if rf_calc["total_reserva_emergencia"] > 0:
                dados_donut.append({"Classe": "Reserva de Emergência", "Valor": rf_calc["total_reserva_emergencia"]})
            if rf_calc["total_caixa_oportunidade"] > 0:
                dados_donut.append({"Classe": "Caixa Oportunidade / Títulos", "Valor": rf_calc["total_caixa_oportunidade"]})

            df_rv_itens = pd.DataFrame(posicoes_rv)
            if not df_rv_itens.empty and "classe" in df_rv_itens.columns:
                for cls, grp in df_rv_itens.groupby("classe"):
                    dados_donut.append({"Classe": cls, "Valor": grp["patrimonio_atual"].sum()})

            df_donut = pd.DataFrame(dados_donut)
            if not df_donut.empty:
                fig_donut = px.pie(
                    df_donut,
                    names="Classe",
                    values="Valor",
                    title="Alocação Patrimonial por Macroclasse",
                    hole=0.64,
                    color_discrete_sequence=["#0F5132", "#15803D", "#0F766E", "#B45309", "#64748B"]
                )
                fig_donut.update_traces(
                    textposition='outside',
                    textinfo='percent+label',
                    outsidetextfont=dict(color=text_primary, size=12, family="Inter, sans-serif"),
                    insidetextfont=dict(color="#ffffff", size=12)
                )
                estilizar_grafico_plotly(fig_donut, altura=335, exibir_legenda=False, travar_zoom=True)
                st.plotly_chart(fig_donut, width="stretch", theme=None, config={"displayModeBar": False, "responsive": True})

    with col_ck2:
        with st.container(border=True):
            sazonal_res = obter_calendario_sazonal(posicoes_usuario=posicoes_rv)
            grade_saz = sazonal_res.get("grade_mensal", [])
            mes_atual_idx = datetime.now().month - 1
            proximos_meses = [grade_saz[(mes_atual_idx + i) % 12] for i in range(5)]
            df_prox = pd.DataFrame(proximos_meses)

            fig_prox = px.bar(
                df_prox,
                x="mes_nome",
                y="renda_estimada",
                text="renda_estimada",
                title="Projeção de Proventos nos Próximos 5 Meses",
                labels={"mes_nome": "Mês", "renda_estimada": "Renda Estimada (R$)"},
                color_discrete_sequence=[brand_button]
            )
            if st.session_state.get("modo_privacidade"):
                fig_prox.update_traces(text=["R$ •••" for _ in range(len(df_prox))], textposition="outside")
            else:
                fig_prox.update_traces(texttemplate='R$ %{y:,.0f}', textposition='outside', marker_line_width=0)
            estilizar_grafico_plotly(fig_prox, altura=335, exibir_legenda=False, travar_zoom=True)
            max_y_prox = float(df_prox["renda_estimada"].max()) if not df_prox.empty else 100.0
            fig_prox.update_yaxes(range=[0, max(100.0, max_y_prox * 1.22)])
            st.plotly_chart(fig_prox, width="stretch", theme=None, config={"displayModeBar": False, "responsive": True})


# =============================================================================
# ABA 1: MINHA CARTEIRA & SIMULADOR FISCAL
# =============================================================================
with tab1:
    st.markdown("""
    <div class="guide-box">
        <strong>O que esta tela faz:</strong> Gestão consolidada de <strong>Renda Fixa</strong> e <strong>Bolsa B3</strong>. 
        Inclui o <strong>Simulador Fiscal de Venda</strong> com a regra dos R$ 20.000 para ações e 20% para FIIs, 
        e o <strong>Aporte Inteligente</strong> com rebalanceamento automático por classes.
    </div>
    """, unsafe_allow_html=True)

    # Cards de Destaque dos Maiores Ativos da Carteira com Régua Visual (PM vs Cotação vs Teto) e YoC
    if posicoes_rv:
        mapa_val_cart = valuation_map_carteira
        top_ativos = sorted(posicoes_rv, key=lambda x: x.get("patrimonio_atual", 0.0), reverse=True)[:4]
        st.markdown("**Maiores Posições da Carteira (Régua de Preço Médio, Teto & Yield on Cost):**")
        cols_top = st.columns(len(top_ativos))
        for idx, at in enumerate(top_ativos):
            with cols_top[idx]:
                lucro_cor = "#15803D" if at.get("lucro_prejuizo_pct", 0) >= 0 else "#ef4444"
                pm_at = float(at.get("preco_medio", 0.0))
                cot_at = float(at.get("cotacao_atual", pm_at))
                dy_at = float(at.get("dy_anual", 0.0))
                yoc_at = (cot_at * (dy_at / 100.0) / pm_at * 100.0) if pm_at > 0 else dy_at

                val_ref = mapa_val_cart.get(at["ticker"], {})
                teto_unif = val_ref.get("preco_teto") or val_ref.get("preco_teto_bazin")
                pvp_ref = val_ref.get("pvp")
                tipo_fii_ref = val_ref.get("tipo_fii")

                if teto_unif is not None and float(teto_unif) > 0:
                    teto_f = float(teto_unif)
                    ref_teto_str = f"Teto: R$ {teto_f:.2f}"
                    if cot_at <= teto_f:
                        tag_teto_html = '<span class="badge-pos" style="font-size:0.65rem; padding:2px 7px;">✓ Abaixo do Teto — Aportar</span>'
                    else:
                        tag_teto_html = '<span class="badge-warn" style="font-size:0.65rem; padding:2px 7px;">Acima do Teto — Aguardar</span>'
                elif at.get("classe") == "FIIs" and pvp_ref is not None:
                    ref_teto_str = f"P/VP: {pvp_ref:.2f}x"
                    lim_max_pvp = 1.00 if tipo_fii_ref == "Papel" else 1.05
                    lim_min_pvp = 0.90 if tipo_fii_ref == "Papel" else 0.85
                    if lim_min_pvp <= pvp_ref <= lim_max_pvp:
                        tag_teto_html = f'<span class="badge-pos" style="font-size:0.65rem; padding:2px 7px;">✓ Banda {tipo_fii_ref or "FII"} Ideal</span>'
                    else:
                        tag_teto_html = f'<span class="badge-warn" style="font-size:0.65rem; padding:2px 7px;">P/VP {pvp_ref:.2f}x ({tipo_fii_ref or "FII"})</span>'
                else:
                    ref_teto_str = f"DY: {dy_at:.1f}%"
                    tag_teto_html = f'<span class="exec-card-tag">{at.get("classe", "B3")}</span>'

                st.markdown(f"""
                <div class="asset-pill-card" style="flex-direction: column; align-items: stretch; gap: 6px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                        <div>
                            <div class="asset-pill-ticker">{at['ticker']}</div>
                            <div class="asset-pill-name">{at.get('classe', 'Ação')} • {at.get('quantidade', 0)} cotas</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-family: 'JetBrains Mono', monospace; font-weight: 800; font-size: 0.95rem; color: {text_primary};">{fmt_moeda(at.get('patrimonio_atual', 0.0))}</div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; font-weight: 700; color: {lucro_cor};">
                                {at.get('lucro_prejuizo_pct', 0.0):+.1f}%
                            </div>
                        </div>
                    </div>
                    <div style="border-top: 1px solid {border_subtle}; padding-top: 6px; font-family: 'JetBrains Mono', monospace; font-size: 0.69rem; color: {text_secondary}; display: flex; justify-content: space-between;">
                        <span>PM: R$ {pm_at:.2f}</span>
                        <span>B3: R$ {cot_at:.2f}</span>
                        <span>{ref_teto_str}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 2px;">
                        {tag_teto_html}
                        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.70rem; font-weight: 700; color: {accent_pos};">YoC: {yoc_at:.1f}% a.a.</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.write("")

    # =========================================================================
    # MAPA VISUAL DE SAZONALIDADE DE PROVENTOS DA CARTEIRA (JAN A DEZ)
    # =========================================================================
    st.markdown(titulo_secao_html("calendar", "Mapa Visual de Sazonalidade de Proventos (Fluxo de Caixa Mensal)"), unsafe_allow_html=True)
    st.caption(
        "Visualize em quais meses do ano os proventos caem na conta. Meses ativos recebem destaque em **Verde Folha** "
        "com o valor projetado e os tickers pagadores; meses sem previsão ficam inativos em **Cinza Pedra**."
    )

    tickers_carteira_atual = [p.get("ticker", "").upper() for p in posicoes_rv if p.get("ticker")]
    opcoes_filtro_sazonal = list(dict.fromkeys(tickers_carteira_atual + ["TAEE11", "BBSE3", "CXSE3", "ITUB4", "BBAS3", "HGLG11", "KNCR11"]))
    default_sazonal = tickers_carteira_atual if tickers_carteira_atual else ["TAEE11", "BBSE3", "BBAS3"]

    tickers_sazonal_sel = st.multiselect(
        "Filtrar Ativos para o Mapa Sazonal (padrão: toda a sua carteira):",
        options=opcoes_filtro_sazonal,
        default=default_sazonal,
        key="ms_mapa_sazonal_portfolio"
    )

    posicoes_filtradas_saz = [
        p for p in posicoes_rv if str(p.get("ticker", "")).upper() in tickers_sazonal_sel
    ]
    # Caso o usuário adicione no filtro um ticker de teste que ainda não está na carteira, simula uma posição base
    tickers_presentes_pos = {str(p.get("ticker", "")).upper() for p in posicoes_filtradas_saz}
    for t_extra in tickers_sazonal_sel:
        if t_extra not in tickers_presentes_pos:
            posicoes_filtradas_saz.append({
                "ticker": t_extra,
                "classe": "FIIs" if t_extra.endswith("11") and t_extra not in {"TAEE11", "SANB11", "SAPR11"} else "Ações",
                "renda_mensal_estimada": 45.0
            })

    dados_sazonal_port = obter_calendario_sazonal(
        tickers_selecionados=tickers_sazonal_sel,
        posicoes_usuario=posicoes_filtradas_saz,
        apenas_carteira=True
    )
    grade_port = dados_sazonal_port.get("grade_mensal", [])

    # Grid de 12 blocos (Jan a Dez) dividido em 2 linhas de 6 colunas para leitura perfeita em qualquer tela
    for linha_idx in (0, 6):
        cols_saz = st.columns(6)
        for col_offset in range(6):
            m_info = grade_port[linha_idx + col_offset]
            pagadores_c = m_info.get("pagadores_carteira", m_info.get("pagadores", []))
            renda_m = float(m_info.get("renda_estimada", 0.0))
            tem_fluxo = (len(pagadores_c) > 0) or (renda_m > 0.0)

            with cols_saz[col_offset]:
                if tem_fluxo:
                    tickers_exib = ", ".join(pagadores_c[:4])
                    if len(pagadores_c) > 4:
                        tickers_exib += f" +{len(pagadores_c) - 4}"
                    st.markdown(f"""
                    <div class="sazonal-box-ativo" title="Pagadores em {m_info['mes_nome']}: {', '.join(pagadores_c)}">
                        <div class="sazonal-mes-header-ativo">{m_info['mes_nome']}</div>
                        <div class="sazonal-valor-ativo">{fmt_moeda(renda_m)}</div>
                        <div class="sazonal-tickers-ativo">{tickers_exib}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="sazonal-box-vazio" title="Sem previsão de dividendos em {m_info['mes_nome']} para a seleção atual">
                        <div class="sazonal-mes-header-vazio">{m_info['mes_nome']}</div>
                        <div class="sazonal-valor-vazio">R$ 0,00</div>
                        <div class="sazonal-tickers-vazio">Sem proventos</div>
                    </div>
                    """, unsafe_allow_html=True)

    meses_ativos_qtd = sum(1 for m in grade_port if m.get("tem_pagamento_carteira") or m.get("renda_estimada", 0) > 0)
    st.caption(
        f"**Cobertura Sazonal da Seleção:** Proventos recorrentes em **{meses_ativos_qtd} de 12 meses** do ano "
        f"(Taesa paga em Mai/Ago/Nov, Bancos pagam mensalmente/trimestralmente e FIIs pagam todos os meses)."
    )

    st.divider()

    # =========================================================================
    # SIMULADOR DE VENDA E IMPOSTO DE RENDA (IR / DARF) — ISOLADO COM @st.fragment
    # =========================================================================
    @st.fragment
    def _render_fragment_simulador_fiscal() -> None:
        st.markdown(titulo_secao_html("scale", "Simulador Fiscal de Venda, Prejuízos Acumulados & Alerta de DARF"), unsafe_allow_html=True)
        with st.expander(":material/help_outline: Regras de Tributação, Compensação de Prejuízos e Exceções da Receita Federal"):
            st.markdown(r"""
            - **Ações Brasil (Swing Trade):** Isenção mensal se a soma exclusiva de vendas de **Ações** no mês for **$\le$ R\$ 20.000,00** (FIIs, ETFs e BDRs **NÃO entram** nessa soma!). Vendas isentas **não consomem** prejuízo acumulado. Se passar de R\$ 20k, **15%** após abater o prejuízo acumulado em Ações/ETFs/BDRs (Código DARF 6015).
            - **Trava A — ETFs (`BOVA11`, `IVVB11`, `NASD11`, `WRLD11`) e BDRs Nubank (`NVDC34`, `AAPL34`):** **NÃO possuem isenção de R\$ 20.000,00!** Incide **15%** sobre qualquer lucro líquido em Swing Trade após compensar eventual prejuízo acumulado em Ações/ETFs/BDRs.
            - **Trava B — Direitos de Subscrição de FIIs (Tickers finalizados em `12`, ex: `HGLG12`, `MXRF12`):** **Sem isenção**, alíquota de **20%** e **Custo de Aquisição (Preço Médio) igual a ZERO (`R$ 0,00`)**.
            - **Fundos Imobiliários (FIIs):** **Sem isenção de 20k!** Alíquota de **20% fixos** sobre o lucro líquido na venda após abater o prejuízo acumulado específico de FIIs.
            - **Trava Legal DARF < R\$ 10,00:** DARF menor que R\$ 10,00 não pode ser emitida e acumula para os meses seguintes (Art. 67 Lei 9.430/96).
            """)

        prej_ac_salvo = float(estado_atual.get("configuracoes", {}).get("prejuizo_acumulado_acoes_etfs", 0.0) or 0.0)
        prej_fii_salvo = float(estado_atual.get("configuracoes", {}).get("prejuizo_acumulado_fiis", 0.0) or 0.0)

        col_mem1, col_mem2, col_mem3 = st.columns([1.4, 1.4, 1.2])
        with col_mem1:
            inp_prej_ac = st.number_input(
                "Prejuízo Acumulado Ações/ETFs/BDRs (R$):",
                min_value=0.0,
                value=prej_ac_salvo,
                step=100.0,
                key="inp_prej_acum_ac_etf",
                help="Saldo de prejuízos passados em Swing Trade de Ações, ETFs e BDRs para compensação antes da DARF.",
            )
        with col_mem2:
            inp_prej_fii = st.number_input(
                "Prejuízo Acumulado FIIs (R$):",
                min_value=0.0,
                value=prej_fii_salvo,
                step=100.0,
                key="inp_prej_acum_fiis",
                help="Saldo de prejuízos passados exclusivamente em FIIs (regra segregada da Receita Federal).",
            )
        with col_mem3:
            st.write("")
            st.write("")
            if st.button(":material/save: Salvar Saldos de Prejuízo", width="stretch", key="btn_save_prejuizos"):
                estado_atual.setdefault("configuracoes", {})["prejuizo_acumulado_acoes_etfs"] = round(float(inp_prej_ac), 2)
                estado_atual["configuracoes"]["prejuizo_acumulado_fiis"] = round(float(inp_prej_fii), 2)
                salvar_estado(estado_atual)
                st.session_state["user_state"] = estado_atual
                st.toast("Memória de prejuízos acumulados salva no user_state.json!")
                st.rerun()

        col_sim1, col_sim2, col_sim3, col_sim4, col_sim5, col_sim6 = st.columns(6)
        tickers_cart = [item["ticker"] for item in estado_atual.get("renda_variavel", [])]
        tickers_especiais_ir = [
            "BOVA11", "IVVB11", "NASD11", "WRLD11", "DIVO11",
            "NVDC34", "AAPL34", "MSFT34", "GOGL34",
            "HGLG12", "MXRF12", "ITUB4", "BBAS3", "TAEE11", "HGLG11"
        ]
        tickers_disponiveis = list(dict.fromkeys(tickers_cart + tickers_especiais_ir))

        with col_sim1:
            sim_ticker = st.selectbox("Ativo para Venda:", tickers_disponiveis)

        item_ativo = next((i for i in rv_calc["itens"] if i["ticker"] == sim_ticker), None)
        ticker_sim_up = str(sim_ticker).strip().upper()
        eh_subscricao_12 = ticker_sim_up.endswith("12")
        eh_etf_sel = ticker_sim_up in ({t.replace(".SA", "").upper() for t in UNIVERSO_ETFS} | {"SPXI11", "HASH11"})
        eh_bdr_sel = ticker_sim_up in {t.replace(".SA", "").upper() for t in UNIVERSO_BDRS} or (
            len(ticker_sim_up) == 6 and ticker_sim_up.endswith(("32", "33", "34", "35"))
        )

        pm_padrao = 0.0 if eh_subscricao_12 else (item_ativo["preco_medio"] if item_ativo else 30.0)
        cot_padrao = 2.50 if eh_subscricao_12 else (item_ativo["cotacao_atual"] if item_ativo else 35.0)
        qtd_padrao = min(100, item_ativo["quantidade"] if item_ativo else 100)
        classe_padrao = (
            "FIIs" if eh_subscricao_12
            else ("ETFs" if eh_etf_sel else ("BDRs" if eh_bdr_sel else (item_ativo["classe"] if item_ativo else "Ações")))
        )

        with col_sim2:
            sim_tipo_op = st.selectbox("Modalidade:", ["Swing Trade (Normal)", "Day Trade"])
        with col_sim3:
            sim_qtd = st.number_input("Qtd a Vender:", min_value=1, value=int(qtd_padrao), step=10)
        with col_sim4:
            sim_preco = st.number_input("Preço Venda (R$):", min_value=0.01, value=float(cot_padrao), step=0.5)
        with col_sim5:
            sim_taxas = st.number_input("Taxas Corretora (R$):", min_value=0.0, value=0.0, step=1.0)
        with col_sim6:
            sim_vendas_ant = st.number_input(
                "Vendas Prévias Ações Mês (R$):",
                min_value=0.0,
                value=0.0,
                step=1000.0,
                help="Considere APENAS vendas anteriores de Ações no mês para a regra dos R$ 20k (FIIs e ETFs não entram nesta soma).",
            )

        sim_res = simular_venda_e_ir(
            ticker=sim_ticker,
            classe=classe_padrao,
            quantidade_venda=sim_qtd,
            preco_venda=sim_preco,
            preco_medio=pm_padrao,
            vendas_acumuladas_mes=sim_vendas_ant,
            tipo_operacao=sim_tipo_op,
            taxas_corretora=sim_taxas,
            prejuizo_acumulado_acoes_etfs=inp_prej_ac,
            prejuizo_acumulado_fiis=inp_prej_fii,
        )

        st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 12px; margin-bottom: 14px;">
            <div class="exec-card">
                <div class="exec-card-header">
                    <span class="exec-card-title">Valor da Venda</span>
                    <span class="exec-card-tag">{sim_res.get('classe', 'B3')}</span>
                </div>
                <div class="exec-card-value">{fmt_moeda(sim_res['valor_venda'])}</div>
                <div class="exec-card-sub" style="color: {text_muted};">{sim_qtd} cotas @ R$ {sim_preco:.2f} (PM: R$ {sim_res['preco_medio']:.2f})</div>
            </div>
            <div class="exec-card">
                <div class="exec-card-header">
                    <span class="exec-card-title">Base Tributável Líquida</span>
                    <span class="exec-card-tag">PÓS PREJUÍZO & IRRF</span>
                </div>
                <div class="exec-card-value" style="color: {accent_pos if sim_res['resultado_liquido'] >= 0 else accent_neg};">
                    {fmt_moeda(sim_res['resultado_liquido'])}
                </div>
                <div class="exec-card-sub" style="color: {text_muted};">
                    Compensado: -{fmt_moeda(sim_res.get('prejuizo_compensado', 0.0))} | Dedo-Duro: -R$ {sim_res['irrf']:.2f}
                </div>
            </div>
            <div class="exec-card">
                <div class="exec-card-header">
                    <span class="exec-card-title">Alíquota & Teto 20k Ações</span>
                    <span class="exec-card-tag">{'ISENTO' if sim_res['isento'] else 'RECEITA FEDERAL'}</span>
                </div>
                <div class="exec-card-value">{sim_res['aliquota_ir_pct']:.1f}%</div>
                <div class="exec-card-sub" style="color: {text_muted};">Teto 20k Ações após op.: {fmt_moeda(sim_res.get('vendas_acoes_mes_atualizadas', 0.0))}</div>
            </div>
            <div class="exec-card">
                <div class="exec-card-header">
                    <span class="exec-card-title">DARF Devido</span>
                    <span class="exec-card-tag">CÓD. {CODIGO_DARF_RENDA_VARIAVEL}</span>
                </div>
                <div class="exec-card-value" style="color: {accent_neg if sim_res['ir_devido'] > 0 else accent_pos};">
                    {fmt_moeda(sim_res['ir_devido'])}
                </div>
                <div class="exec-card-sub" style="color: {text_muted};">{sim_res.get('status_darf', f'Código DARF {CODIGO_DARF_RENDA_VARIAVEL}')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if sim_res["isento"]:
            st.success(escapar_cifrao_md(sim_res["detalhes"]))
        elif sim_res["ir_devido"] > 0:
            st.error(escapar_cifrao_md(sim_res["detalhes"]))
        else:
            st.info(escapar_cifrao_md(sim_res["detalhes"]))

        st.caption(
            f"**Previsão de Saldos de Prejuízo pós-operação:** "
            f"Ações/ETFs = {fmt_moeda(sim_res.get('novo_prejuizo_acumulado_acoes_etfs', inp_prej_ac))} | "
            f"FIIs = {fmt_moeda(sim_res.get('novo_prejuizo_acumulado_fiis', inp_prej_fii))}"
        )

    _render_fragment_simulador_fiscal()

    st.divider()

    # =========================================================================
    # REBALANCEAMENTO INTELIGENTE (B9: MACROCLASSES vs ATIVO A ATIVO)
    # =========================================================================
    st.markdown(titulo_secao_html("sliders", "Aporte Inteligente, Filtro de Preço Teto & Gatekeeper"), unsafe_allow_html=True)
    
    col_reb1, col_reb2 = st.columns([2, 1])
    with col_reb1:
        tipo_rebal = st.radio(
            "Modo de Alocação do Aporte:",
            ["Por Macroclasses (Renda Fixa x Ações x FIIs x ETFs x BDRs)", "Apenas em Renda Variável (Ativo a Ativo)"],
            index=0,
            horizontal=True
        )
    with col_reb2:
        incluir_caixa = st.checkbox("Incluir Caixa de Oportunidade no aporte", value=False)
    
    caixa_extra = rf_calc["total_caixa_oportunidade"] if incluir_caixa else 0.0

    if tipo_rebal.startswith("Por Macroclasses"):
        preset_aloc = st.selectbox(
            "Perfil / Preset de Alocação:",
            [
                "Transição Conservadora (70% Renda Fixa | 20% Ações | 10% FIIs)",
                "Moderado / Equilibrado (40% Renda Fixa | 35% Ações | 15% FIIs | 5% ETFs | 5% BDRs)",
                "Arrojado / Foco Dividendos & Global (20% Renda Fixa | 45% Ações | 25% FIIs | 5% ETFs | 5% BDRs)",
                "Personalizado (Definir manualmente)"
            ],
            index=0
        )
        if "70%" in preset_aloc:
            padrao_rf, padrao_ac, padrao_fii, padrao_etf, padrao_bdr = 70.0, 20.0, 10.0, 0.0, 0.0
        elif "40%" in preset_aloc:
            padrao_rf, padrao_ac, padrao_fii, padrao_etf, padrao_bdr = 40.0, 35.0, 15.0, 5.0, 5.0
        elif "Arrojado" in preset_aloc:
            padrao_rf, padrao_ac, padrao_fii, padrao_etf, padrao_bdr = 20.0, 45.0, 25.0, 5.0, 5.0
        else:
            padrao_rf, padrao_ac, padrao_fii, padrao_etf, padrao_bdr = 50.0, 30.0, 15.0, 5.0, 0.0

        with st.expander(":material/tune: Ajustar Percentuais das Metas Alvo (%)", expanded=("Personalizado" in preset_aloc)):
            cm1, cm2, cm3, cm4, cm5 = st.columns(5)
            with cm1:
                meta_rf = st.number_input("Renda Fixa (%)", min_value=0.0, max_value=100.0, value=padrao_rf, step=5.0, key="inp_meta_rf")
            with cm2:
                meta_acoes = st.number_input("Ações (%)", min_value=0.0, max_value=100.0, value=padrao_ac, step=5.0, key="inp_meta_ac")
            with cm3:
                meta_fiis = st.number_input("FIIs (%)", min_value=0.0, max_value=100.0, value=padrao_fii, step=5.0, key="inp_meta_fii")
            with cm4:
                meta_etfs = st.number_input("ETFs (%)", min_value=0.0, max_value=100.0, value=padrao_etf, step=5.0, key="inp_meta_etf")
            with cm5:
                meta_bdrs = st.number_input("BDRs (%)", min_value=0.0, max_value=100.0, value=padrao_bdr, step=5.0, key="inp_meta_bdr")

        metas_user = {"Renda Fixa": meta_rf, "Ações": meta_acoes, "FIIs": meta_fiis, "ETFs": meta_etfs, "BDRs": meta_bdrs}
        rebal_classe = calcular_aporte_por_classe(
            itens_rv=rv_calc["itens"],
            rf_investimento_atual=rf_calc["total_caixa_oportunidade"],
            sobra_para_investir=sobra_mensal,
            metas_classe=metas_user,
            caixa_oportunidade_usada=caixa_extra,
            valuation_map=valuation_map_carteira,
            saldo_reserva_emergencia=rf_calc["total_reserva_emergencia"],
            custo_vida_mensal=custo_vida_mensal,
            meta_meses_reserva=meta_meses_reserva,
        )

        for av in rebal_classe.get("avisos", []):
            st.warning(escapar_cifrao_md(av))

        st.markdown("**1. Distribuição Sugerida por Classe:**")
        df_cls = pd.DataFrame(rebal_classe["resumo_classes"])
        if not df_cls.empty:
            st.dataframe(
                df_cls,
                column_config={
                    "classe": "Classe",
                    "valor_atual": st.column_config.NumberColumn("Patrimônio Atual", format="R$ %.2f"),
                    "pct_atual": st.column_config.ProgressColumn("Peso Atual", format="%.1f%%", min_value=0, max_value=100),
                    "meta_pct": st.column_config.NumberColumn("Meta Alvo", format="%.1f%%"),
                    "aporte_sugerido": st.column_config.NumberColumn("Aporte Sugerido", format="R$ %.2f"),
                    "pct_apos_aporte": st.column_config.ProgressColumn("Peso Projetado", format="%.1f%%", min_value=0, max_value=100)
                },
                width="stretch",
                hide_index=True
            )

        if rebal_classe["aportes"]:
            st.markdown("**2. Compras em Renda Variável (Pós-Trava Preço Teto & Normalização de Gaps):**")
            df_ap = pd.DataFrame(rebal_classe["aportes"])
            st.dataframe(
                df_ap[["ticker", "classe", "cotacao", "preco_teto", "peso_na_classe_pct", "gap_reais", "cotas_a_comprar", "valor_aporte_sugerido", "motivo_status", "micro_tag"]],
                column_config={
                    "ticker": "Ticker",
                    "classe": "Classe",
                    "cotacao": st.column_config.NumberColumn("Cotação", format="R$ %.2f"),
                    "preco_teto": st.column_config.NumberColumn("Preço Teto", format="R$ %.2f"),
                    "peso_na_classe_pct": st.column_config.NumberColumn("Peso na Classe", format="%.1f%%"),
                    "gap_reais": st.column_config.NumberColumn("Gap Efetivo", format="R$ %.2f"),
                    "cotas_a_comprar": st.column_config.NumberColumn("Cotas a Comprar", format="%d"),
                    "valor_aporte_sugerido": st.column_config.NumberColumn("Aporte Sugerido", format="R$ %.2f"),
                    "motivo_status": "Elegibilidade Valuation",
                    "micro_tag": "Racional Quantitativo",
                },
                width="stretch",
                hide_index=True
            )

        st.info(escapar_cifrao_md(
            f"**Capital Total:** {fmt_moeda(rebal_classe['capital_disponivel'])}  |  "
            f"**Destinado à Renda Fixa:** {fmt_moeda(rebal_classe['aporte_renda_fixa'])} "
            f"(inclui {fmt_moeda(rebal_classe.get('valor_redirecionado_oportunidade', 0.0))} redirecionados p/ Reserva de Oportunidade)  |  "
            f"**Destinado à Bolsa (RV):** {fmt_moeda(rebal_classe['capital_alocado_rv'])}"
        ))
    else:
        rebal = calcular_rebalanceamento_aportes(
            itens_rv=rv_calc["itens"],
            sobra_para_investir=sobra_mensal,
            caixa_oportunidade=caixa_extra,
            valuation_map=valuation_map_carteira,
        )
        if rebal["aportes"]:
            df_rebal = pd.DataFrame(rebal["aportes"])
            st.dataframe(
                df_rebal[["ticker", "classe", "cotacao", "preco_teto", "peso_atual_pct", "peso_alvo_pct", "gap_reais", "cotas_a_comprar", "valor_aporte_sugerido", "motivo_status", "micro_tag"]],
                column_config={
                    "ticker": "Ticker",
                    "classe": "Classe",
                    "cotacao": st.column_config.NumberColumn("Cotação", format="R$ %.2f"),
                    "preco_teto": st.column_config.NumberColumn("Preço Teto", format="R$ %.2f"),
                    "peso_atual_pct": st.column_config.ProgressColumn("Peso Atual", format="%.1f%%", min_value=0, max_value=100),
                    "peso_alvo_pct": st.column_config.NumberColumn("Peso Alvo", format="%.1f%%"),
                    "gap_reais": st.column_config.NumberColumn("Gap Efetivo", format="R$ %.2f"),
                    "cotas_a_comprar": st.column_config.NumberColumn("Cotas a Comprar", format="%d"),
                    "valor_aporte_sugerido": st.column_config.NumberColumn("Aporte Sugerido", format="R$ %.2f"),
                    "motivo_status": "Elegibilidade",
                    "micro_tag": "Racional Quantitativo",
                },
                width="stretch",
                hide_index=True
            )
            st.info(escapar_cifrao_md(f"**Capital Alocado:** {fmt_moeda(rebal['capital_alocado'])}  |  **Redirecionado à Reserva de Oportunidade (Selic/Nubank):** {fmt_moeda(rebal['sobra_residual'])}"))
        else:
            st.caption("Cadastre seus ativos com pesos-alvo para ver as sugestões de compra.")

    st.divider()

    # =========================================================================
    # CADASTRO E EDIÇÃO DAS CARTEIRAS COM NOTIFICAÇÃO TOAST
    # =========================================================================
    st.markdown(titulo_secao_html("edit", "Cadastrar ou Editar Carteira"), unsafe_allow_html=True)

    tab_cad_rf, tab_cad_rv = st.tabs([
        ":material/savings: 1. Renda Fixa (Nubank, CDBs e Tesouro)",
        ":material/trending_up: 2. Renda Variável (Ações, FIIs e ETFs)"
    ])

    with tab_cad_rf:
        with st.form("form_ed_rf_clean"):
            df_rf_edit = pd.DataFrame(estado_atual.get("renda_fixa", []))
            if df_rf_edit.empty:
                df_rf_edit = pd.DataFrame([{
                    "nome": "Caixinha Nubank Reserva",
                    "tipo": "Reserva de Emergência",
                    "valor_aplicado": 1000.0,
                    "saldo_atual": 1000.0,
                    "taxa_cdi": 100.0,
                    "dias_corridos": 365
                }])
            cols_rf = ["nome", "tipo", "valor_aplicado", "saldo_atual", "taxa_cdi", "dias_corridos"]
            ed_rf = st.data_editor(
                df_rf_edit[cols_rf],
                num_rows="dynamic",
                width="stretch",
                key="ed_rf_clean",
                column_config={
                    "nome": st.column_config.TextColumn("Nome da Conta / Título"),
                    "tipo": st.column_config.SelectboxColumn("Tipo / Destino", options=["Reserva de Emergência", "Investimento/Caixa"]),
                    "valor_aplicado": st.column_config.NumberColumn("Valor Aplicado (R$)", format="R$ %.2f"),
                    "saldo_atual": st.column_config.NumberColumn("Saldo Atual (R$)", format="R$ %.2f"),
                    "taxa_cdi": st.column_config.NumberColumn("Taxa (% do CDI)", default=100.0, format="%.1f%%"),
                    "dias_corridos": st.column_config.NumberColumn("Prazo em Dias", default=365)
                }
            )

            if st.form_submit_button(":material/save: Salvar Renda Fixa e Recalcular"):
                if not ed_rf.empty:
                    estado_atual["renda_fixa"] = ed_rf.dropna(subset=["nome"]).to_dict(orient="records")
                    salvar_estado(estado_atual)
                    st.cache_data.clear()
                    disparar_sincronizacao_excel()
                    st.toast("Renda Fixa salva com sucesso!")
                    st.rerun()

    with tab_cad_rv:
        with st.form("form_ed_rv_clean"):
            df_rv_edit = pd.DataFrame(estado_atual.get("renda_variavel", []))
            if df_rv_edit.empty:
                df_rv_edit = pd.DataFrame([{
                    "ticker": "ITUB4",
                    "classe": "Ações",
                    "quantidade": 100,
                    "preco_medio": 32.50,
                    "peso_alvo": 20.0
                }])
            cols_rv = ["ticker", "classe", "quantidade", "preco_medio", "peso_alvo"]
            ed_rv = st.data_editor(
                df_rv_edit[cols_rv],
                num_rows="dynamic",
                width="stretch",
                key="ed_rv_clean",
                column_config={
                    "ticker": st.column_config.TextColumn("Ticker B3"),
                    "classe": st.column_config.SelectboxColumn("Classe", options=["Ações", "FIIs", "ETFs", "BDRs"]),
                    "quantidade": st.column_config.NumberColumn("Quantidade", min_value=1, step=1),
                    "preco_medio": st.column_config.NumberColumn("Preço Médio (R$)", format="R$ %.2f"),
                    "peso_alvo": st.column_config.NumberColumn("Peso Alvo (%)", format="%.1f%%")
                }
            )

            if st.form_submit_button(":material/save: Salvar Renda Variável e Recalcular"):
                if not ed_rv.empty:
                    ed_rv["ticker"] = ed_rv["ticker"].astype(str).str.upper().str.strip()
                    estado_atual["renda_variavel"] = ed_rv.dropna(subset=["ticker"]).to_dict(orient="records")
                    salvar_estado(estado_atual)
                    st.cache_data.clear()
                    disparar_sincronizacao_excel()
                    st.toast("Renda Variável salva com sucesso!")
                    st.rerun()


# =============================================================================
# ABA 2: MEU ORÇAMENTO PESSOAL (CFP STANDARD 2.0 + PROVISÃO ANUAL + FECHAMENTO)
# =============================================================================
with tab2:
    st.markdown("""
    <div class="guide-box">
        <strong>O que esta tela faz:</strong> Controle de fluxo de caixa pela regra <strong>50/30/20 (CFP) Desacoplada</strong> 
        (classifica cada gasto fixo ou variável entre <em>Essencial 50%</em> e <em>Estilo de Vida 30%</em>), 
        calcula o <strong>Carimbo Mensal de Provisão Anual (IPVA/IPTU/Seguros/Viagens &divide; 12)</strong> antes da Sobra Líquida 
        e registra o <strong>Histórico Patrimonial Mensal</strong>.
    </div>
    """, unsafe_allow_html=True)

    tot_ess_cfp = float(orcamento_calc.get("total_essenciais_cfp", orcamento_calc["total_fixos"]))
    pct_ess_cfp = float(orcamento_calc.get("pct_essenciais_cfp", orcamento_calc["pct_fixos"]))
    tot_est_cfp = float(orcamento_calc.get("total_estilo_cfp", orcamento_calc["total_variaveis"]))
    pct_est_cfp = float(orcamento_calc.get("pct_estilo_cfp", orcamento_calc["pct_variaveis"]))
    prov_anual_m = float(orcamento_calc.get("provisao_mensal_anual", 0.0))
    pct_prov_anual = float(orcamento_calc.get("pct_provisao_anual", 0.0))
    tot_anual_bruto = float(orcamento_calc.get("total_despesas_anuais", 0.0))

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px;">
        <div class="exec-card">
            <div class="exec-card-header">
                <span class="exec-card-title">Receita Líquida Total</span>
                <span class="exec-card-tag">100% BASE</span>
            </div>
            <div class="exec-card-value">{fmt_moeda(orcamento_calc['total_receitas'])}</div>
            <div class="exec-progress-track"><div class="exec-progress-fill" style="width: 100%;"></div></div>
            <div class="exec-card-sub" style="color: {text_muted};">Fixos: {fmt_moeda(orcamento_calc['total_fixos'])} • Var.: {fmt_moeda(orcamento_calc['total_variaveis'])}</div>
        </div>
        <div class="exec-card">
            <div class="exec-card-header">
                <span class="exec-card-title">Essenciais (CFP)</span>
                <span class="exec-card-tag">TETO: 50%</span>
            </div>
            <div class="exec-card-value">{fmt_moeda(tot_ess_cfp)}</div>
            <div class="exec-progress-track"><div class="exec-progress-fill" style="width: {min(100.0, pct_ess_cfp):.1f}%;"></div></div>
            <div class="exec-card-sub" style="color: {accent_pos if pct_ess_cfp <= 50 else accent_neg};">
                {pct_ess_cfp:.1f}% da renda (Fixos + Var. Essenciais)
            </div>
        </div>
        <div class="exec-card">
            <div class="exec-card-header">
                <span class="exec-card-title">Estilo de Vida + Provisões</span>
                <span class="exec-card-tag">TETO ESTILO: 30%</span>
            </div>
            <div class="exec-card-value">{fmt_moeda(tot_est_cfp + prov_anual_m)}</div>
            <div class="exec-progress-track"><div class="exec-progress-fill" style="width: {min(100.0, pct_est_cfp + pct_prov_anual):.1f}%;"></div></div>
            <div class="exec-card-sub" style="color: {accent_pos if pct_est_cfp <= 30 else accent_neg};">
                Estilo: {pct_est_cfp:.1f}% • Provisão Anual (1/12): {fmt_moeda(prov_anual_m)}
            </div>
        </div>
        <div class="exec-card">
            <div class="exec-card-header">
                <span class="exec-card-title">Sobra p/ Investir (Líquida)</span>
                <span class="exec-card-tag">META: &ge; 20%</span>
            </div>
            <div class="exec-card-value" style="color: {accent_pos};">{fmt_moeda(orcamento_calc['sobra_para_investir'])}</div>
            <div class="exec-progress-track"><div class="exec-progress-fill" style="width: {min(100.0, orcamento_calc['taxa_poupanca_pct']):.1f}%;"></div></div>
            <div class="exec-card-sub" style="color: {accent_pos if orcamento_calc['taxa_poupanca_pct'] >= 20 else accent_warn};">
                Taxa de Poupança Livre: {orcamento_calc['taxa_poupanca_pct']:.1f}% (pós-provisão)
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.info(escapar_cifrao_md(f"**Diagnóstico CFP 50/30/20:** {orcamento_calc['diagnostico']}"))

    if prov_anual_m > 0:
        st.markdown(f"""
        <div class="quant-research-card" style="margin-bottom: 14px; border-left: 4px solid #0F5132;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <div style="font-size:0.78rem; font-weight:700; color:{text_primary}; text-transform:uppercase; letter-spacing:0.04em;">
                        Proteção Contra Resgates — Carimbo Mensal de Despesas Anuais & Sazonais (Valor Anual &divide; 12)
                    </div>
                    <div style="font-size:0.81rem; color:{text_secondary}; margin-top:4px;">
                        Total Anual Mapeado: <strong style="font-family:'JetBrains Mono',monospace;">{fmt_moeda(tot_anual_bruto)}/ano</strong> &rarr;
                        Separe <strong style="color:{accent_pos}; font-family:'JetBrains Mono',monospace;">{fmt_moeda(prov_anual_m)}/mês</strong> ({pct_prov_anual:.1f}% da receita)
                        em uma <strong>Caixinha de Provisão Anual (100% CDI)</strong> separada da Reserva de Emergência antes de aportar em Renda Variável.
                    </div>
                </div>
                <span class="badge-pos">Blindagem de Liquidez Ativa</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Ponte 50/30/20 & Índice de Cobertura de Vida pela Renda Passiva
    regra_ponte = orcamento_calc.get("regra_50_30_20", {})
    cob_fixos_real = fire_real_calc.get("cobertura_gastos_fixos_real_pct", 0.0)
    cob_total_real = fire_real_calc.get("cobertura_custo_vida_real_pct", 0.0)
    renda_real_m = fire_real_calc.get("renda_real_mensal_total", renda_passiva_total)

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-bottom: 14px;">
        <div class="exec-card" style="border-left: 4px solid {brand_accent};">
            <div class="exec-card-header">
                <span class="exec-card-title">Índice de Cobertura de Vida pela Renda Passiva</span>
                <span class="exec-card-tag">PROVENTOS REAIS</span>
            </div>
            <div class="exec-card-value" style="color: {brand_accent};">{cob_fixos_real:.1f}% <span style="font-size:0.85rem; font-weight:600; color:{text_secondary};">dos Gastos Fixos</span></div>
            <div class="exec-progress-track"><div class="exec-progress-fill" style="width: {min(100.0, cob_fixos_real):.1f}%;"></div></div>
            <div class="exec-card-sub" style="color: {text_muted};">
                Renda real {fmt_moeda(renda_real_m)}/mês • Cobre {cob_total_real:.1f}% do custo de vida total ({fmt_moeda(custo_vida_mensal)})
            </div>
        </div>
        <div class="exec-card" style="border-left: 4px solid {accent_pos if not cobertura_reserva_calc['gatekeeper_ativo'] else accent_warn};">
            <div class="exec-card-header">
                <span class="exec-card-title">Cobertura da Reserva (Custo Total)</span>
                <span class="exec-card-tag">GATEKEEPER: {meta_meses_reserva}M</span>
            </div>
            <div class="exec-card-value" style="color: {accent_pos if not cobertura_reserva_calc['gatekeeper_ativo'] else accent_warn};">{cobertura_reserva_calc['cobertura_meses']:.2f} <span style="font-size:0.90rem; font-weight:600;">meses</span></div>
            <div class="exec-progress-track"><div class="exec-progress-fill" style="width: {min(100.0, cobertura_reserva_calc['cobertura_meses'] / max(1, meta_meses_reserva) * 100.0):.1f}%;"></div></div>
            <div class="exec-card-sub" style="color: {text_muted};">
                Reserva: {fmt_moeda(rf_calc['total_reserva_emergencia'])} vs Meta {fmt_moeda(cobertura_reserva_calc['meta_valor_rs'])}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Ponte CFP 50/30/20 Detalhada
    if regra_ponte:
        st.markdown(f"""
        <div class="quant-research-card" style="margin-bottom: 16px;">
            <div style="font-weight:700; font-size:0.88rem; color:{text_primary}; margin-bottom:10px;">
                Ponte Executiva da Regra 50 / 30 / 20 Desacoplada (Receita Líquida &rarr; Alocação Real CFP)
            </div>
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:12px;">
                <div>
                    <div class="qr-metric-label">1. Receita Líquida</div>
                    <div class="qr-metric-val">{fmt_moeda(orcamento_calc['total_receitas'])}</div>
                    <div style="font-size:0.74rem; color:{text_muted};">100.0% Base Mensal</div>
                </div>
                <div>
                    <div class="qr-metric-label">2. Essenciais (&le; 50%)</div>
                    <div class="qr-metric-val" style="color:{accent_pos if regra_ponte['essenciais_ok'] else accent_neg};">{pct_ess_cfp:.1f}%</div>
                    <div style="font-size:0.74rem; color:{text_muted};">Ideal: {fmt_moeda(regra_ponte['meta_essenciais_rs'])} (Desvio: {fmt_moeda(regra_ponte['desvio_essenciais_rs'])})</div>
                </div>
                <div>
                    <div class="qr-metric-label">3. Estilo de Vida (&le; 30%)</div>
                    <div class="qr-metric-val" style="color:{accent_pos if regra_ponte['estilo_ok'] else accent_neg};">{pct_est_cfp:.1f}%</div>
                    <div style="font-size:0.74rem; color:{text_muted};">Ideal: {fmt_moeda(regra_ponte['meta_estilo_rs'])} (Desvio: {fmt_moeda(regra_ponte['desvio_estilo_rs'])})</div>
                </div>
                <div>
                    <div class="qr-metric-label">4. Sobra / Aporte (&ge; 20%)</div>
                    <div class="qr-metric-val" style="color:{accent_pos if regra_ponte['investimentos_ok'] else accent_warn};">{orcamento_calc['taxa_poupanca_pct']:.1f}%</div>
                    <div style="font-size:0.74rem; color:{text_muted};">Piso: {fmt_moeda(regra_ponte['meta_investimentos_rs'])} (Folga: {fmt_moeda(regra_ponte['desvio_investimentos_rs'])})</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Gráficos de Fluxo do Dinheiro: Barra Horizontal Empilhada 100% + Waterfall
    col_flx1, col_flx2 = st.columns(2)
    with col_flx1:
        with st.container(border=True):
            pct_sobra_bar = max(0.0, float(orcamento_calc.get("taxa_poupanca_pct", 0.0)))
            fig_stack = go.Figure()
            blocos_fluxo = [
                ("Essenciais (50%)", pct_ess_cfp, tot_ess_cfp, "#0F5132"),
                ("Estilo de Vida (30%)", pct_est_cfp, tot_est_cfp, "#D97706"),
                ("Provisões Anuais (1/12)", pct_prov_anual, prov_anual_m, "#0F766E"),
                ("Sobra p/ Investir", pct_sobra_bar, max(0.0, orcamento_calc["sobra_para_investir"]), "#15803D"),
            ]
            for nome_b, pct_b, val_b, cor_b in blocos_fluxo:
                label_txt = f"{pct_b:.1f}%" if pct_b >= 6.0 else ""
                fig_stack.add_trace(go.Bar(
                    name=f"{nome_b} ({pct_b:.1f}%)",
                    y=["100% da Receita"],
                    x=[pct_b],
                    orientation="h",
                    text=[label_txt],
                    textposition="inside",
                    insidetextanchor="middle",
                    marker=dict(color=cor_b),
                    hovertemplate=f"<b>{nome_b}</b>: {pct_b:.1f}% ({fmt_moeda(val_b)})<extra></extra>",
                ))
            fig_stack.update_layout(
                barmode="stack",
                title="Decomposição de 100% da Receita Líquida (CFP + Provisões)",
                xaxis=dict(range=[0, max(100.0, pct_ess_cfp + pct_est_cfp + pct_prov_anual + pct_sobra_bar)], ticksuffix="%"),
            )
            estilizar_grafico_plotly(fig_stack, altura=360, exibir_legenda=True, travar_zoom=True)
            fig_stack.update_traces(textfont=dict(color="#FFFFFF", size=12, family="JetBrains Mono, monospace"))
            st.plotly_chart(fig_stack, width="stretch", theme=None, config={"displayModeBar": False, "responsive": True})

    with col_flx2:
        with st.container(border=True):
            waterfall_txt = [
                f"+{fmt_moeda(orcamento_calc['total_receitas'])}",
                f"-{fmt_moeda(tot_ess_cfp)}",
                f"-{fmt_moeda(tot_est_cfp)}",
                f"-{fmt_moeda(prov_anual_m)}",
                f"{fmt_moeda(orcamento_calc['sobra_para_investir'])}"
            ] if not st.session_state.get("modo_privacidade") else ["+R$ •••", "-R$ •••", "-R$ •••", "-R$ •••", "R$ •••"]

            fig_waterfall = go.Figure(go.Waterfall(
                name="Fluxo Mensal",
                orientation="v",
                measure=["relative", "relative", "relative", "relative", "total"],
                x=["Receitas", "Essenciais (50%)", "Estilo (30%)", "Provisão Anual", "Sobra p/ Investir"],
                textposition="outside",
                text=waterfall_txt,
                textfont={"family": "Inter, sans-serif", "color": axis_text_color, "size": 11},
                y=[
                    orcamento_calc['total_receitas'],
                    -tot_ess_cfp,
                    -tot_est_cfp,
                    -prov_anual_m,
                    orcamento_calc['sobra_para_investir']
                ],
                connector={"line": {"color": "#94a3b8"}},
                decreasing={"marker": {"color": "#ef4444"}},
                increasing={"marker": {"color": "#15803D"}},
                totals={"marker": {"color": brand_button}}
            ))
            fig_waterfall.update_layout(title="Demonstrativo de Fluxo de Caixa Mensal (R$)")
            estilizar_grafico_plotly(fig_waterfall, altura=360, exibir_legenda=False, travar_zoom=True)
            st.plotly_chart(fig_waterfall, width="stretch", theme=None, config={"displayModeBar": False, "responsive": True})

    # Simulador de Corte de Gastos no Orçamento -> Aceleração FIRE (Isolado com @st.fragment)
    @st.fragment
    def _render_fragment_simulador_corte_fire() -> None:
        with st.container(border=True):
            st.markdown(titulo_secao_html("zap", "Simulador: Reduzir Gastos de Estilo de Vida e Antecipar sua Liberdade Financeira (FIRE)", nivel=4), unsafe_allow_html=True)
            max_corte = max(500.0, float(orcamento_calc.get("total_estilo_cfp", orcamento_calc.get("total_variaveis", 1000.0)) or 1000.0))
            corte_sim = st.slider(
                "Quanto deseja reduzir por mês em Estilo de Vida para redirecionar em Aportes?",
                min_value=0.0,
                max_value=float(round(max_corte, -2)),
                value=min(500.0, float(round(max_corte * 0.25, -2)) or 200.0),
                step=100.0,
                key="slider_corte_gastos_fire",
            )
            yield_ref_sim = max(4.5, float(fire_real_calc.get("yield_real_anual_portfolio_pct", 6.0) or 6.0))
            sim_fire_corte = simular_corte_gastos_fire(
                corte_mensal_rs=corte_sim,
                patrimonio_atual_rs=patrimonio_total,
                aporte_mensal_atual_rs=max(0.0, sobra_mensal),
                custo_vida_mensal_atual_rs=custo_vida_mensal,
                retorno_real_anual_pct=max(3.5, float(macro.get("juro_real_anual", 5.5) or 5.5)),
                yield_medio_real_pct=yield_ref_sim,
            )
            col_cf1, col_cf2, col_cf3, col_cf4 = st.columns(4)
            col_cf1.metric("Tempo Antecipado no FIRE", f"-{sim_fire_corte['meses_antecipados']} meses", f"{sim_fire_corte['anos_antecipados']:.1f} anos mais cedo")
            col_cf2.metric("Dividendos Extras (Ano 1)", fmt_moeda(sim_fire_corte["dividendos_anuais_extras_ano1"]), "Renda anual incremental")
            col_cf3.metric("Patrimônio Extra (10 Anos)", fmt_moeda(sim_fire_corte["patrimonio_extra_10_anos"]), "Juros compostos reais")
            col_cf4.metric("Nova Sobra para Aportes", fmt_moeda(sim_fire_corte["nova_sobra_mensal"]), f"Custo FIRE cai {fmt_moeda(sim_fire_corte['reducao_meta_fire'])}")

    _render_fragment_simulador_corte_fire()

    st.divider()

    # =========================================================================
    # HISTÓRICO PATRIMONIAL MENSAL & REGISTRO DE FECHAMENTO DO MÊS
    # =========================================================================
    col_hist_h1, col_hist_h2 = st.columns([3, 1.2])
    with col_hist_h1:
        st.markdown(titulo_secao_html("trending", "Evolução Patrimonial Mensal & Fechamento de Caixa"), unsafe_allow_html=True)
        st.caption("Fotografe o fechamento de cada mês (`YYYY-MM`) para acompanhar a curva de acumulação entre Renda Fixa, Renda Variável e Proventos.")
    with col_hist_h2:
        st.write("")
        if st.button("📸 Registrar Fechamento do Mês", width="stretch", key="btn_registrar_fechamento_mes"):
            mes_ref = datetime.now().strftime("%Y-%m")
            novo_snap = {
                "mes": mes_ref,
                "receita": round(float(orcamento_calc["total_receitas"]), 2),
                "despesas": round(float(orcamento_calc["total_despesas"]), 2),
                "taxa_poupanca_pct": round(float(orcamento_calc["taxa_poupanca_pct"]), 2),
                "patrimonio_rf": round(float(rf_calc["total_patrimonio_rf"]), 2),
                "patrimonio_rv": round(float(rv_calc["total_patrimonio_rv"]), 2),
                "patrimonio_total": round(float(patrimonio_total), 2),
                "proventos_mensais": round(float(renda_passiva_total), 2),
            }
            hist_lista = list(estado_atual.get("historico_patrimonial_mensal", []))
            idx_exist = next((idx for idx, h in enumerate(hist_lista) if h.get("mes") == mes_ref), None)
            if idx_exist is not None:
                hist_lista[idx_exist] = novo_snap
            else:
                hist_lista.append(novo_snap)
            hist_lista.sort(key=lambda x: str(x.get("mes", "")))
            estado_atual["historico_patrimonial_mensal"] = hist_lista
            salvar_estado(estado_atual)
            st.session_state["user_state"] = estado_atual
            st.toast(f"Fechamento de {mes_ref} registrado com sucesso no histórico patrimonial!")
            st.rerun()

    hist_patrimonial = estado_atual.get("historico_patrimonial_mensal", [])
    if hist_patrimonial:
        df_hist_p = pd.DataFrame(hist_patrimonial).sort_values("mes")
        if "patrimonio_total" not in df_hist_p.columns:
            df_hist_p["patrimonio_total"] = df_hist_p.get("patrimonio_rf", 0.0) + df_hist_p.get("patrimonio_rv", 0.0)
        with st.container(border=True):
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Scatter(
                x=df_hist_p["mes"],
                y=df_hist_p["patrimonio_total"],
                mode="lines+markers+text",
                name="Patrimônio Total",
                line=dict(color="#0F5132", width=3),
                marker=dict(size=8, color="#15803D"),
                text=[fmt_moeda(v) if not st.session_state.get("modo_privacidade") else "R$ •••" for v in df_hist_p["patrimonio_total"]],
                textposition="top center",
            ))
            fig_hist.add_trace(go.Scatter(
                x=df_hist_p["mes"],
                y=df_hist_p["patrimonio_rv"],
                mode="lines+markers",
                name="Renda Variável (B3)",
                line=dict(color="#0F766E", width=2, dash="dot"),
            ))
            fig_hist.add_trace(go.Scatter(
                x=df_hist_p["mes"],
                y=df_hist_p["patrimonio_rf"],
                mode="lines+markers",
                name="Renda Fixa (Nubank/Tesouro)",
                line=dict(color="#B45309", width=2, dash="dash"),
            ))
            fig_hist.update_layout(title="Curva de Evolução Patrimonial Mensal Consolidada")
            estilizar_grafico_plotly(fig_hist, altura=340, exibir_legenda=True, travar_zoom=True)
            max_y_h = float(df_hist_p["patrimonio_total"].max()) if not df_hist_p.empty else 1000.0
            fig_hist.update_yaxes(range=[0, max(1000.0, max_y_h * 1.18)])
            st.plotly_chart(fig_hist, width="stretch", theme=None, config={"displayModeBar": False, "responsive": True})

    st.divider()

    # =========================================================================
    # EDITOR DE ORÇAMENTO E DESPESAS ANUAIS (ISOLADO COM @st.fragment)
    # =========================================================================
    @st.fragment
    def _render_fragment_editor_orcamento() -> None:
        st.markdown(titulo_secao_html("edit", "Cadastrar Receitas, Despesas (c/ Classificação 50/30/20) e Provisões Anuais"), unsafe_allow_html=True)
        with st.form("form_orc_clean"):
            c_o1, c_o2 = st.columns(2)
            with c_o1:
                st.markdown("**1. Receitas Mensais**")
                df_rec = pd.DataFrame(estado_atual.get("orcamento", {}).get("receitas", []))
                if df_rec.empty:
                    df_rec = pd.DataFrame([{"nome": "Salário Líquido", "valor": 0.0, "categoria": "Trabalho"}])
                ed_rec = st.data_editor(
                    df_rec,
                    num_rows="dynamic",
                    width="stretch",
                    key="ed_rec_clean",
                    column_config={
                        "nome": st.column_config.TextColumn("Fonte de Renda"),
                        "valor": st.column_config.NumberColumn("Valor Mensal (R$)", format="R$ %.2f"),
                        "categoria": st.column_config.TextColumn("Categoria"),
                    },
                )

            with c_o2:
                st.markdown("**4. Despesas Anuais & Sazonais (IPVA, Seguros, IPTU, Viagens)**")
                df_anual = pd.DataFrame(estado_atual.get("orcamento", {}).get("despesas_anuais", []))
                if df_anual.empty:
                    df_anual = pd.DataFrame([{"nome": "IPVA + Licenciamento", "valor_anual": 0.0, "vencimento": "Janeiro"}])
                for col_a, def_a in [("nome", ""), ("valor_anual", 0.0), ("vencimento", "Anual")]:
                    if col_a not in df_anual.columns:
                        df_anual[col_a] = def_a
                ed_anual = st.data_editor(
                    df_anual[["nome", "valor_anual", "vencimento"]],
                    num_rows="dynamic",
                    width="stretch",
                    key="ed_anual_clean",
                    column_config={
                        "nome": st.column_config.TextColumn("Despesa Anual / Sazonal"),
                        "valor_anual": st.column_config.NumberColumn("Valor Anual (R$)", format="R$ %.2f"),
                        "vencimento": st.column_config.TextColumn("Mês / Vencimento"),
                    },
                )

            c_o3, c_o4 = st.columns(2)
            with c_o3:
                st.markdown("**2. Gastos Fixos Recorrentes (c/ Regra 50/30/20)**")
                lista_fix = estado_atual.get("orcamento", {}).get("gastos_fixos", [])
                for it_f in lista_fix:
                    it_f.setdefault("categoria_cfp", inferir_categoria_cfp(it_f, eh_fixo=True))
                df_fix = pd.DataFrame(lista_fix)
                if df_fix.empty:
                    df_fix = pd.DataFrame([{"nome": "Aluguel / Condomínio", "valor": 0.0, "categoria": "Moradia", "categoria_cfp": "Essencial (50%)"}])
                for col_f, def_f in [("nome", ""), ("valor", 0.0), ("categoria", "Moradia"), ("categoria_cfp", "Essencial (50%)")]:
                    if col_f not in df_fix.columns:
                        df_fix[col_f] = def_f
                ed_fix = st.data_editor(
                    df_fix[["nome", "valor", "categoria", "categoria_cfp"]],
                    num_rows="dynamic",
                    width="stretch",
                    key="ed_fix_clean",
                    column_config={
                        "nome": st.column_config.TextColumn("Despesa Fixa"),
                        "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                        "categoria": st.column_config.TextColumn("Categoria"),
                        "categoria_cfp": st.column_config.SelectboxColumn(
                            "Regra 50/30/20 (CFP)",
                            options=["Essencial (50%)", "Estilo de Vida (30%)"],
                            required=True,
                        ),
                    },
                )

            with c_o4:
                st.markdown("**3. Gastos Variáveis (c/ Regra 50/30/20)**")
                lista_var = estado_atual.get("orcamento", {}).get("gastos_variaveis", [])
                for it_v in lista_var:
                    it_v.setdefault("categoria_cfp", inferir_categoria_cfp(it_v, eh_fixo=False))
                df_var = pd.DataFrame(lista_var)
                if df_var.empty:
                    df_var = pd.DataFrame([{"nome": "Supermercado", "valor": 0.0, "categoria": "Alimentação", "categoria_cfp": "Essencial (50%)"}])
                for col_v, def_v in [("nome", ""), ("valor", 0.0), ("categoria", "Alimentação"), ("categoria_cfp", "Estilo de Vida (30%)")]:
                    if col_v not in df_var.columns:
                        df_var[col_v] = def_v
                ed_var = st.data_editor(
                    df_var[["nome", "valor", "categoria", "categoria_cfp"]],
                    num_rows="dynamic",
                    width="stretch",
                    key="ed_var_clean",
                    column_config={
                        "nome": st.column_config.TextColumn("Despesa Variável"),
                        "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                        "categoria": st.column_config.TextColumn("Categoria"),
                        "categoria_cfp": st.column_config.SelectboxColumn(
                            "Regra 50/30/20 (CFP)",
                            options=["Essencial (50%)", "Estilo de Vida (30%)"],
                            required=True,
                        ),
                    },
                )

            if st.form_submit_button(":material/save: Salvar Orçamento e Recalcular"):
                estado_atual.setdefault("orcamento", {})["receitas"] = ed_rec.dropna(subset=["nome"]).to_dict(orient="records")
                estado_atual["orcamento"]["gastos_fixos"] = ed_fix.dropna(subset=["nome"]).to_dict(orient="records")
                estado_atual["orcamento"]["gastos_variaveis"] = ed_var.dropna(subset=["nome"]).to_dict(orient="records")
                estado_atual["orcamento"]["despesas_anuais"] = ed_anual.dropna(subset=["nome"]).to_dict(orient="records")
                salvar_estado(estado_atual)
                st.cache_data.clear()
                disparar_sincronizacao_excel()
                st.toast("Orçamento 50/30/20 e Provisões Anuais recalculados com sucesso!")
                st.rerun()

    _render_fragment_editor_orcamento()


# =============================================================================
# ABA 3: RADAR DE OPORTUNIDADES & MERCADO (ISOLADO COM @st.fragment)
# =============================================================================
@st.fragment
def _render_fragment_radar_oportunidades() -> None:
    st.markdown("""
    <div class="guide-box">
        <strong>Central de Análise & Oportunidades:</strong> Navegue pelas visões especializadas do mercado 
        sem poluição visual. O foco é identificar <strong>Preço com Desconto</strong>, <strong>Projeção de Dividendos</strong> 
        e <strong>Segurança Patrimonial de Balanço</strong>.
    </div>
    """, unsafe_allow_html=True)

    sub_radar = st.radio(
        "Selecione a Visão de Análise:",
        [
            "Top Melhores Compras (Preço + Projeção + Segurança)",
            "Setores Defensivos (BESST), FIIs, ETFs & BDRs (Nubank)",
            "Scanner Técnico (RSI Sobrevenda)",
            "Calendário Sazonal & Bola de Neve",
            "Notícias & Fatos Relevantes"
        ],
        horizontal=True,
        key="radio_sub_radar_nav"
    )

    st.write("")

    # -------------------------------------------------------------------------
    # SUB-VISÃO 1: TOP MELHORES COMPRAS (TRÍADE: PREÇO, PROJEÇÃO E SEGURANÇA)
    # -------------------------------------------------------------------------
    if sub_radar.startswith("Top Melhores Compras"):
        st.markdown(titulo_secao_html("award", "Ranking Quantitativo: As Melhores Compras da Bolsa"), unsafe_allow_html=True)
        st.caption("Filtro rigoroso para perfil defensivo / transição de Renda Fixa. Avalia **35% Preço**, **35% Projeção** e **30% Segurança**.")

        top_compras_todas = get_top_compras_cached(macro["cdi_liquido_anual"])
        df_top = pd.DataFrame(top_compras_todas)

        if not df_top.empty:
            st.markdown(titulo_secao_html("shield", "Top Recomendações em Destaque (Alta Segurança)", nivel=4), unsafe_allow_html=True)
            st.caption("Cards limpos com as maiores pontuações segundo a Tríade (35% Preço + 35% Projeção + 30% Segurança).")

            # Exibe as 4 melhores compras em elegantes Cards Institucionais de Equity Research
            for i_top in range(min(4, len(top_compras_todas))):
                item_d = top_compras_todas[i_top]
                dy_isento = float(item_d.get("dy_anual_pct", 0.0))
                dy_bruto = dy_isento / (1.0 - 0.15)
                pvp_item = float(item_d.get("pvp", 1.0))
                pl_item = float(item_d.get("pl", 10.0))
                sc_p = float(item_d.get("score_preco", 0.0))
                sc_pr = float(item_d.get("score_projecao", 0.0))
                sc_s = float(item_d.get("score_seguranca", 0.0))

                # Badge Semântico de Segurança (CSS Customizado)
                if (item_d.get("tipo") == "FII" and pvp_item < 0.80) or (item_d.get("tipo") != "FII" and pl_item < 0):
                    badge_seg_html = '<span class="badge-neg">Risco Crítico (Prejuízo / P/VP &lt; 0.80)</span>'
                elif item_d.get("status_auditoria") == "Suspeito":
                    badge_seg_html = '<span class="badge-warn">Auditoria SanityGate: Múltiplo Atípico</span>'
                else:
                    badge_seg_html = '<span class="badge-pos">✓ Auditoria Validada</span>'

                st.markdown(f"""
                <div class="quant-research-card">
                    <div class="qr-grid">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                                <span class="qr-rank-badge">#{i_top+1}</span>
                                <span class="qr-ticker">{item_d['ticker']}</span>
                                <span class="exec-card-tag">{item_d['tipo']}</span>
                            </div>
                            <div style="font-size: 0.84rem; font-weight: 600; color: {text_primary}; margin-bottom: 6px;">
                                {item_d['nome']}
                            </div>
                            <div>{badge_seg_html}</div>
                        </div>
                        <div>
                            <div class="qr-metric-label">Cotação B3</div>
                            <div class="qr-metric-val">R$ {item_d['cotacao']:.2f}</div>
                            <div style="font-size: 0.72rem; color: {text_muted}; margin-top: 3px;">
                                {item_d.get('modelo_valuation', 'Valuation Quant')}
                            </div>
                        </div>
                        <div>
                            <div class="qr-metric-label">{'Tendência / Retorno 12m' if item_d.get('tipo') == 'ETF de Acumulação' else 'DY Projetado (Isento)'}</div>
                            <div class="qr-metric-val" style="color: {accent_pos};">{(f"{item_d.get('margem_bazin_pct') or 0:+.1f}% vs MM200" if item_d.get('tipo') == 'ETF de Acumulação' else f"{dy_isento:.1f}% <span style='font-size:0.78rem;'>a.a.</span>")}</div>
                            <div style="margin-top: 3px;">
                                <span style="color:#636b78; font-size:12px;">{('ETF de Acumulação (Reinvestimento Automático)' if item_d.get('tipo') == 'ETF de Acumulação' else f'(equivale a {dy_bruto:.1f}% bruto no CDI)')}</span>
                            </div>
                        </div>
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span class="qr-metric-label" style="margin:0;">Score Triplo</span>
                                <span style="font-family: 'JetBrains Mono', monospace; font-size: 1.05rem; font-weight: 800; color: {accent_pos};">{item_d['score_geral']:.0f}/100</span>
                            </div>
                            <div class="qr-bar-row">
                                <span style="width: 58px;">Preço</span>
                                <div class="qr-bar-track"><div class="qr-bar-fill" style="width: {sc_p:.0f}%;"></div></div>
                                <span style="width: 26px; text-align: right; font-family: 'JetBrains Mono', monospace;">{sc_p:.0f}</span>
                            </div>
                            <div class="qr-bar-row">
                                <span style="width: 58px;">Projeção</span>
                                <div class="qr-bar-track"><div class="qr-bar-fill" style="width: {sc_pr:.0f}%;"></div></div>
                                <span style="width: 26px; text-align: right; font-family: 'JetBrains Mono', monospace;">{sc_pr:.0f}</span>
                            </div>
                            <div class="qr-bar-row">
                                <span style="width: 58px;">Segurança</span>
                                <div class="qr-bar-track"><div class="qr-bar-fill" style="width: {sc_s:.0f}%;"></div></div>
                                <span style="width: 26px; text-align: right; font-family: 'JetBrains Mono', monospace;">{sc_s:.0f}</span>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander(f":material/analytics: Raio-X Detalhado de {item_d['ticker']} (Valuation e Margem de Segurança)"):
                    c_dt1, c_dt2, c_dt3 = st.columns(3)
                    with c_dt1:
                        teto_u = item_d.get("preco_teto") or item_d.get("preco_teto_bazin")
                        teto_str = f"R$ {float(teto_u):.2f}" if teto_u is not None else "N/A"
                        st.markdown(f"• **Preço Teto / Limite de Compra:** {teto_str}")
                        st.caption("Bazin Seletivo (10% Bancos / 0% Seguradoras), Banda P/VP FIIs ou MM200 ETFs.")
                    with c_dt2:
                        graham_str = f"R$ {item_d['preco_justo_graham']:.2f}" if item_d.get('preco_justo_graham') is not None else f"Banda P/VP ({pvp_item:.2f}x)"
                        modelo_val = item_d.get("modelo_valuation", "Graham / Gordon")
                        st.markdown(f"• **Preço Justo ({modelo_val}):** {graham_str}")
                        st.caption("Gordon Dinâmico (Ke=CDI+4%, Payout<=60%), Papel vs Tijolo FIIs, Graham BESST.")
                    with c_dt3:
                        spread_str = f"{item_d['spread_vs_cdi_liquido']:+.2f} p.p." if item_d.get("spread_vs_cdi_liquido") is not None else "N/A (ETF)"
                        st.markdown(f"• **Selo de Entrada:** {item_d['veredito']}")
                        st.caption(f"Spread vs CDI Líquido ({macro['cdi_liquido_anual']:.2f}%): {spread_str}")

            st.write("")
            with st.expander(":material/table_chart: Ver Tabela Completa (BESST, FIIs e ETFs Auditados)", expanded=False):
                st.dataframe(
                    df_top,
                    column_config={
                        "ticker": "Ticker",
                        "nome": "Empresa / Ativo",
                        "tipo": "Classe",
                        "cotacao": st.column_config.NumberColumn("Cotação", format="R$ %.2f"),
                        "dy_anual_pct": st.column_config.NumberColumn("DY Estimado", format="%.1f%%"),
                        "preco_teto": st.column_config.NumberColumn("Preço Teto", format="R$ %.2f"),
                        "score_geral": st.column_config.ProgressColumn("Score Triplo (0-100)", min_value=0, max_value=100, format="%.0f"),
                        "score_preco": st.column_config.NumberColumn("Score Preço", format="%.0f"),
                        "score_projecao": st.column_config.NumberColumn("Score Projeção", format="%.0f"),
                        "score_seguranca": st.column_config.NumberColumn("Score Segurança", format="%.0f"),
                        "preco_teto_bazin": st.column_config.NumberColumn("Teto Bazin", format="R$ %.2f"),
                        "preco_justo_graham": st.column_config.NumberColumn("Valor Justo", format="R$ %.2f"),
                        "spread_vs_cdi_liquido": st.column_config.NumberColumn("Spread CDI Líq.", format="%+.2f p.p."),
                        "veredito": "Veredito Quantitativo"
                    },
                    width="stretch",
                    hide_index=True
                )

            with st.expander(":material/info: Como funciona a Tríade de Recomendação de Compra?"):
                st.markdown("""
                - **1. Preço (35%):** Desconto sobre Gordon Dinâmico (`Ke = max(12%, CDI + 4%)`, trava de Payout `<= 60%`), Bazin Seletivo (`10%` Bancos / `0%` Seguradoras), Banda P/VP (`Papel 0.90–1.00` vs `Tijolo 0.85–1.05`) ou desvio vs `MM200` (ETFs).
                - **2. Projeção (35%):** Dividend Yield anual projetado e Pedágio do CDI (exigindo prêmio líquido real em FIIs de Papel), ou tendência secular (12m/MM200) para ETFs de acumulação.
                - **3. Segurança (30%):** Régua específica por classe: Dívida Líq./EBITDA + ROE + Liquidez (Ações Não-Financeiras); ROE 60% + Lucros/P/VP 40% ignorando EBITDA (Bancos/Seguradoras); Estabilidade 12m + Liquidez Diária + P/VP (FIIs).
                """)

    # -------------------------------------------------------------------------
    # SUB-VISÃO 2: SETORES DEFENSIVOS (BESST) & FIIS
    # -------------------------------------------------------------------------
    elif sub_radar.startswith("Setores Defensivos"):
        besst_dados = get_besst_cached(macro["cdi_liquido_anual"])
        df_besst = pd.DataFrame(besst_dados)

        st.markdown(titulo_secao_html("shield", "Universo BESST: Gordon Dinâmico, Graham & Bazin Seletivo"), unsafe_allow_html=True)
        if not df_besst.empty:
            st.dataframe(
                df_besst,
                column_config={
                    "ticker": "Ticker",
                    "nome": "Empresa",
                    "setor": "Setor",
                    "modelo_valuation": "Modelo",
                    "cotacao": st.column_config.NumberColumn("Cotação", format="R$ %.2f"),
                    "dy_anual_pct": st.column_config.NumberColumn("DY 12m", format="%.1f%%"),
                    "preco_graham": st.column_config.NumberColumn("Valor Justo", format="R$ %.2f"),
                    "margem_graham_pct": st.column_config.NumberColumn("Margem Justo", format="%.1f%%"),
                    "preco_bazin": st.column_config.NumberColumn("Teto Bazin", format="R$ %.2f"),
                    "preco_teto": st.column_config.NumberColumn("Preço Teto Unif.", format="R$ %.2f"),
                    "spread_vs_cdi_liq": st.column_config.NumberColumn("Spread vs CDI Líq.", format="%+.2f p.p."),
                    "diagnostico": "Diagnóstico",
                    "score_defensivo": st.column_config.ProgressColumn("Score Defensivo", min_value=0, max_value=100)
                },
                width="stretch",
                hide_index=True
            )

        st.divider()

        # Raio-X do Balanço (com Régua Específica por Classe)
        st.markdown(titulo_secao_html("activity", "Raio-X Fundamentalista do Balanço (Régua Específica por Classe)"), unsafe_allow_html=True)
        fiis_dados = get_fiis_cached(macro["cdi_liquido_anual"])
        etfs_dados = get_etfs_cached(macro["cdi_liquido_anual"])
        bdrs_dados = get_bdrs_cached(macro["cdi_liquido_anual"])
        lista_analise = sorted(list(set(
            [b["ticker"] for b in besst_dados]
            + [f["ticker"] for f in fiis_dados]
            + [e["ticker"] for e in etfs_dados]
            + [bd["ticker"] for bd in bdrs_dados]
            + [p["ticker"] for p in posicoes_rv]
        )))
        ticker_sel_saude = st.selectbox("Selecione um Ativo para Raio-X:", lista_analise, index=0)
        score_saude = calcular_score_saude_balanco(ticker_sel_saude)

        col_h1, col_h2, col_h3, col_h4 = st.columns(4)
        with col_h1:
            st.markdown(f"""
            <div class="exec-card">
                <div class="exec-card-header">
                    <span class="exec-card-title">Score Segurança (0-100)</span>
                    <span class="exec-card-tag">{score_saude.get('classe_seguranca', 'B3')}</span>
                </div>
                <div class="exec-card-value" style="color: {brand_primary};">{score_saude['score_saude']:.0f}</div>
                <div class="exec-card-sub">{score_saude['selo']}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_h2:
            dl_val = score_saude.get('divida_liq_ebitda')
            cresc_l = score_saude.get('crescimento_lucro_pct')
            estab_p = score_saude.get('estabilidade_proventos')
            if dl_val is not None:
                dl_title = "Dívida Líq. / EBITDA"
                dl_str = f"{dl_val:.2f}x"
                dl_badge = '<span class="badge-warn">Alerta (&gt; 2.5x)</span>' if dl_val > 2.5 else '<span class="badge-pos">✓ Controlada</span>'
            elif estab_p is not None:
                dl_title = "Estabilidade Div. 12m"
                dl_str = f"{estab_p:.0f}/100"
                dl_badge = '<span class="badge-pos">FII (EBITDA N/A)</span>'
            elif cresc_l is not None:
                dl_title = "Cresc. Lucro YoY"
                dl_str = f"{float(cresc_l):+.1f}%"
                dl_badge = '<span class="badge-pos">Financeiro (EBITDA Ignorado)</span>'
            else:
                dl_title = "Métrica Estrutural"
                dl_str = "Regulado / FII"
                dl_badge = f'<span style="color: {text_muted};">Régua Própria da Classe</span>'
            st.markdown(f"""
            <div class="exec-card">
                <div class="exec-card-title">{dl_title}</div>
                <div class="exec-card-value">{dl_str}</div>
                <div class="exec-card-sub">{dl_badge}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_h3:
            liq_c = score_saude.get('liquidez_corrente')
            vol_d = score_saude.get('volume_medio_diario')
            if liq_c is not None:
                lc_title = "Liquidez Corrente"
                lc_str = f"{float(liq_c):.2f}x"
                lc_sub = 'Caixa Confortável' if float(liq_c) >= 1.5 else 'Equilibrado'
            elif vol_d is not None:
                lc_title = "Liquidez Diária Média"
                lc_str = f"R$ {float(vol_d)/1e6:.1f}M"
                lc_sub = "Volume Financeiro B3"
            else:
                lc_title = "Liquidez / Regulação"
                lc_str = "Banco / FII / ETF"
                lc_sub = "Isento de EBITDA/LC padrão"
            st.markdown(f"""
            <div class="exec-card">
                <div class="exec-card-title">{lc_title}</div>
                <div class="exec-card-value">{lc_str}</div>
                <div class="exec-card-sub" style="color: {text_muted};">{lc_sub}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_h4:
            st.markdown(f"""
            <div class="exec-card">
                <div class="exec-card-title">ROE & Margem Líquida</div>
                <div class="exec-card-value" style="color: {accent_pos};">{score_saude['roe_pct']:.1f}%</div>
                <div class="exec-card-sub">Margem: {score_saude['margem_liq_pct']:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

        col_diag1, col_diag2 = st.columns(2)
        with col_diag1:
            st.markdown("**Pontos Fortes:**")
            for pf in score_saude.get("pontos_fortes", []):
                st.success(f"✓ {pf}")
        with col_diag2:
            st.markdown("**Pontos de Atenção:**")
            if score_saude.get("pontos_atencao"):
                for pa in score_saude["pontos_atencao"]:
                    st.warning(f"• {pa}")
            else:
                st.success("✓ Nenhum sinal de estresse financeiro identificado.")

        st.divider()

        st.markdown(titulo_secao_html("building", "Fundos Imobiliários: Tijolo vs. Papel & Pedágio do CDI"), unsafe_allow_html=True)
        df_fiis = pd.DataFrame(fiis_dados)
        if not df_fiis.empty:
            st.dataframe(
                df_fiis,
                column_config={
                    "ticker": "Ticker FII",
                    "nome": "Fundo",
                    "tipo_fii": "Segmento",
                    "cotacao": st.column_config.NumberColumn("Cotação", format="R$ %.2f"),
                    "pvp": st.column_config.NumberColumn("P/VP", format="%.2f"),
                    "preco_teto": st.column_config.NumberColumn("Preço Teto", format="R$ %.2f"),
                    "dy_anual_pct": st.column_config.NumberColumn("DY 12m", format="%.1f%%"),
                    "cdi_liquido_referencia": st.column_config.NumberColumn("CDI Líq.", format="%.1f%%"),
                    "spread_vs_cdi_liquido": st.column_config.NumberColumn("Spread CDI", format="%+.2f p.p."),
                    "pedagio_cdi_status": "Pedágio do CDI",
                    "status": "Diagnóstico de Atratividade",
                },
                width="stretch",
                hide_index=True
            )

        st.divider()
        st.markdown(titulo_secao_html("layers", "ETFs de Acumulação na B3 / Nubank (MM200, RSI 14 e Tendência Secular)"), unsafe_allow_html=True)
        df_etfs = pd.DataFrame(etfs_dados)
        if not df_etfs.empty:
            st.dataframe(
                df_etfs[["ticker", "nome", "cotacao", "mm200", "desvio_mm200_pct", "rsi_14", "retorno_12m_pct", "preco_teto", "score_triplo", "diagnostico"]],
                column_config={
                    "ticker": "ETF",
                    "nome": "Índice",
                    "cotacao": st.column_config.NumberColumn("Cotação", format="R$ %.2f"),
                    "mm200": st.column_config.NumberColumn("MM200", format="R$ %.2f"),
                    "desvio_mm200_pct": st.column_config.NumberColumn("Desvio MM200", format="%+.1f%%"),
                    "rsi_14": st.column_config.NumberColumn("RSI (14p)", format="%.1f"),
                    "retorno_12m_pct": st.column_config.NumberColumn("Retorno 12m", format="%+.1f%%"),
                    "preco_teto": st.column_config.NumberColumn("Teto Tático", format="R$ %.2f"),
                    "score_triplo": st.column_config.ProgressColumn("Score ETF", min_value=0, max_value=100, format="%.0f"),
                    "diagnostico": "Leitura Secular",
                },
                width="stretch",
                hide_index=True
            )

        st.divider()
        st.markdown(titulo_secao_html("globe", "BDRs & Ações Globais no Nubank (Em Reais na B3)"), unsafe_allow_html=True)
        st.caption("Empresas globais (Nvidia, Apple, Microsoft, Google, Amazon, Meta, Tesla, TSMC, Mercado Livre e Berkshire) negociadas em Reais no app do Nubank. Atenção fiscal: BDRs não possuem isenção de R$ 20k/mês.")
        df_bdrs = pd.DataFrame(bdrs_dados)
        if not df_bdrs.empty:
            st.dataframe(
                df_bdrs[["ticker", "nome", "cotacao", "variacao_dia_pct", "pl", "roe", "desvio_mm200_pct", "rsi_14", "score_seguranca", "score_geral", "diagnostico"]],
                column_config={
                    "ticker": "BDR",
                    "nome": "Empresa Global",
                    "cotacao": st.column_config.NumberColumn("Cotação (R$)", format="R$ %.2f"),
                    "variacao_dia_pct": st.column_config.NumberColumn("Dia %", format="%+.2f%%"),
                    "pl": st.column_config.NumberColumn("P/L", format="%.1fx"),
                    "roe": st.column_config.NumberColumn("ROE", format="%.1f%%"),
                    "desvio_mm200_pct": st.column_config.NumberColumn("Desvio MM200", format="%+.1f%%"),
                    "rsi_14": st.column_config.NumberColumn("RSI (14p)", format="%.1f"),
                    "score_seguranca": st.column_config.ProgressColumn("Segurança", min_value=0, max_value=100, format="%.0f"),
                    "score_geral": st.column_config.ProgressColumn("Score Oport.", min_value=0, max_value=100, format="%.0f"),
                    "diagnostico": "Leitura Tática",
                },
                width="stretch",
                hide_index=True
            )

    # -------------------------------------------------------------------------
    # SUB-VISÃO 3: SCANNER TÉCNICO (RSI SOBREVENDA)
    # -------------------------------------------------------------------------
    elif sub_radar.startswith("Scanner Técnico"):
        st.markdown(titulo_secao_html("activity", "Scanner de Oportunidades: Sobrevenda Técnica + Filtro de Segurança"), unsafe_allow_html=True)
        st.caption("Cruza sobrevenda técnica (RSI < 30 geral ou <= 35 BESST/Qualidade) com o Score de Segurança (>= 70) para distinguir Pullbacks Seguros de 'Facas Caindo'.")

        if st.button(":material/radar: Executar Nova Varredura Agora", key="btn_varredura_radar"):
            st.cache_data.clear()
            st.toast("Scanner quantitativo executado com sucesso!")
            st.rerun()

        oportunidades = get_scanner_cached()

        if oportunidades:
            elites = [op for op in oportunidades if op.get("nivel_oportunidade") == "elite"]
            if elites:
                st.success(f"**{len(elites)} ativo(s) em Sobrevenda de Elite (Pullback Seguro)** e **{len(oportunidades)} sinal(is) técnico(s)** detectados no total:")
            else:
                st.warning(f"**{len(oportunidades)} sinal(is) de sobrevenda técnica** encontrado(s) — atenção ao filtro de saúde do balanço antes de alocar.")

            for op in oportunidades:
                var_dia = op.get("variacao_dia_pct")
                var_cor = accent_pos if (var_dia or 0.0) >= 0 else "#DC2626"
                var_str = f"{var_dia:+.2f}%" if var_dia is not None else "0.00%"
                rsi_val = op.get("rsi_14")
                rsi_str = f"{rsi_val:.1f}" if rsi_val is not None else "N/D"
                dist_mm200 = op.get("distancia_mm200_pct")
                mm200_str = f"{dist_mm200:+.1f}%" if dist_mm200 is not None else "N/D"
                score_seg = op.get("score_seguranca", 0.0)
                nivel = op.get("nivel_oportunidade", "neutro")
                qualif = op.get("qualificacao_risco", op.get("severidade", "Monitoramento"))
                acao_sug = op.get("acao_sugerida", "")

                if nivel == "elite":
                    pill_bg, pill_fg, pill_bd = "#DCFCE7", "#0F5132", "#86EFAC"
                    card_border = "border-left: 4px solid #15803D;"
                elif nivel == "alto_risco":
                    pill_bg, pill_fg, pill_bd = "#FEE2E2", "#991B1B", "#FCA5A5"
                    card_border = "border-left: 4px solid #DC2626;"
                else:
                    pill_bg, pill_fg, pill_bd = "#FEF3C7", "#92400E", "#FCD34D"
                    card_border = "border-left: 4px solid #D97706;"

                st.markdown(f"""
                <div class="quant-research-card" style="margin-bottom: 12px; {card_border}">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <div style="flex: 1; min-width: 260px;">
                            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                                <span style="font-size: 1.15rem; font-weight: 800; color: {text_primary};">{op['ticker']}</span>
                                <span style="font-size: 0.78rem; font-weight: 500; color: {text_secondary};">• {op['nome']} ({op['tipo_setor']})</span>
                                <span style="background: {pill_bg}; color: {pill_fg}; border: 1px solid {pill_bd}; font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 999px;">{qualif}</span>
                            </div>
                            <div style="font-size: 0.78rem; color: {text_muted}; margin-top: 5px;">Gatilhos: <strong style="color: {text_secondary};">{op.get('motivos', '-')}</strong></div>
                            {f'<div style="font-size: 0.76rem; color: {pill_fg}; margin-top: 3px; font-weight: 600;">Diretriz de Transição: {acao_sug}</div>' if acao_sug else ''}
                        </div>
                        <div style="display: flex; gap: 20px; align-items: center;">
                            <div style="text-align: right;">
                                <div style="font-size: 0.68rem; font-weight: 600; color: {text_secondary}; text-transform: uppercase;">Cotação B3</div>
                                <div style="font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; font-size: 1.1rem; font-weight: 800; color: {text_primary};">R$ {op['cotacao']:.2f} <span style="font-size: 0.78rem; color: {var_cor};">({var_str})</span></div>
                            </div>
                            <div style="text-align: right; min-width: 145px;">
                                <div style="font-size: 0.68rem; font-weight: 600; color: {text_secondary}; text-transform: uppercase;">RSI (14p) • Seg. {score_seg:.0f}/100</div>
                                <div style="font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; font-size: 1.05rem; font-weight: 700; color: {accent_pos if nivel == 'elite' else '#DC2626' if nivel == 'alto_risco' else accent_warn};">{rsi_str} <span style="font-size: 0.72rem; color: {text_muted};">| MM200: {mm200_str}</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✓ Nenhum ativo em sobrevenda severa hoje. Mercado operando dentro de bandas normais.")

    # -------------------------------------------------------------------------
    # SUB-VISÃO 4: CALENDÁRIO SAZONAL & BOLA DE NEVE
    # -------------------------------------------------------------------------
    elif sub_radar.startswith("Calendário Sazonal"):
        sazonal = obter_calendario_sazonal(posicoes_usuario=posicoes_rv)
        grade = sazonal["grade_mensal"]

        st.markdown(titulo_secao_html("calendar", "Calendário Mensal de Pagamentos (Jan a Dez)"), unsafe_allow_html=True)

        cols_ano1 = st.columns(6)
        for i in range(6):
            m = grade[i]
            with cols_ano1[i]:
                tickers_str = ", ".join(m["pagadores"][:4]) if m["pagadores"] else "Nenhum"
                if len(m["pagadores"]) > 4:
                    tickers_str += f" +{len(m['pagadores'])-4}"
                tem_renda_cart = m["renda_estimada"] > 0
                borda_cor = accent_pos if tem_renda_cart else "#CBD5E1"

                st.markdown(f"""
                <div class="mes-card" style="border-top: 3px solid {borda_cor};">
                    <div class="mes-title">{m['mes_nome']}</div>
                    <div class="mes-renda">{fmt_moeda(m['renda_estimada']) if tem_renda_cart else '—'}</div>
                    <div class="mes-tickers" title="{', '.join(m['pagadores'])}">
                        {tickers_str}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.write("")
        cols_ano2 = st.columns(6)
        for i in range(6, 12):
            m = grade[i]
            with cols_ano2[i - 6]:
                tickers_str = ", ".join(m["pagadores"][:4]) if m["pagadores"] else "Nenhum"
                if len(m["pagadores"]) > 4:
                    tickers_str += f" +{len(m['pagadores'])-4}"
                tem_renda_cart = m["renda_estimada"] > 0
                borda_cor = accent_pos if tem_renda_cart else "#CBD5E1"

                st.markdown(f"""
                <div class="mes-card" style="border-top: 3px solid {borda_cor};">
                    <div class="mes-title">{m['mes_nome']}</div>
                    <div class="mes-renda">{fmt_moeda(m['renda_estimada']) if tem_renda_cart else '—'}</div>
                    <div class="mes-tickers" title="{', '.join(m['pagadores'])}">
                        {tickers_str}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.write("")
        with st.container(border=True):
            df_grade = pd.DataFrame(grade)
            fig_sazonal = px.bar(
                df_grade,
                x="mes_nome",
                y="renda_estimada",
                text="renda_estimada",
                title="Projeção Anual de Renda Passiva da Minha Carteira (R$/mês)",
                labels={"mes_nome": "Mês", "renda_estimada": "Renda Passiva (R$)"},
                color_discrete_sequence=[brand_button]
            )
            if st.session_state.get("modo_privacidade"):
                fig_sazonal.update_traces(text=["R$ •••" for _ in range(12)], textposition="outside")
            else:
                fig_sazonal.update_traces(texttemplate='R$ %{y:,.0f}', textposition='outside')
            estilizar_grafico_plotly(fig_sazonal, altura=360, exibir_legenda=False, travar_zoom=True)
            max_y_saz = float(df_grade["renda_estimada"].max()) if not df_grade.empty else 100.0
            fig_sazonal.update_yaxes(range=[0, max(100.0, max_y_saz * 1.22)])
            st.plotly_chart(fig_sazonal, width="stretch", theme=None, config={"displayModeBar": False, "responsive": True})

        st.divider()

        # Bola de Neve (Magic Number)
        st.markdown(titulo_secao_html("layers", "Simulador da Bola de Neve (Número Mágico)"), unsafe_allow_html=True)
        dados_bola = calcular_efeito_bola_de_neve(posicoes_rv)

        if dados_bola:
            col_bn1, col_bn2, col_bn3 = st.columns(3)
            atingidos = sum(1 for d in dados_bola if d["progresso_pct"] >= 100.0)
            com_progresso = [d for d in dados_bola if d["progresso_pct"] < 100.0]
            mais_proximo = max(com_progresso, key=lambda x: x["progresso_pct"]) if com_progresso else None
            pct_autonomos = (atingidos / len(dados_bola) * 100.0) if dados_bola else 0.0

            with col_bn1:
                st.markdown(f"""
                <div class="exec-card">
                    <div class="exec-card-header">
                        <span class="exec-card-title">Ativos Monitorados</span>
                        <span class="exec-card-badge">Custódia B3</span>
                    </div>
                    <div class="exec-card-value">{len(dados_bola)} ativos</div>
                    <div class="exec-progress-track"><div class="exec-progress-fill" style="width: 100%;"></div></div>
                    <div class="exec-card-sub">Elegíveis ao cálculo do Número Mágico</div>
                </div>
                """, unsafe_allow_html=True)
            with col_bn2:
                st.markdown(f"""
                <div class="exec-card">
                    <div class="exec-card-header">
                        <span class="exec-card-title">Bolas de Neve Ativadas</span>
                        <span class="exec-card-badge">Auto-Reinvestimento</span>
                    </div>
                    <div class="exec-card-value" style="color: {accent_pos};">{atingidos} de {len(dados_bola)}</div>
                    <div class="exec-progress-track"><div class="exec-progress-fill" style="width: {min(100.0, pct_autonomos):.0f}%;"></div></div>
                    <div class="exec-card-sub" style="color: {accent_pos if atingidos > 0 else text_muted};">{'✓ Geram novas cotas sozinhos' if atingidos > 0 else 'Em fase de acumulação'}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_bn3:
                if mais_proximo:
                    st.markdown(f"""
                    <div class="exec-card">
                        <div class="exec-card-header">
                            <span class="exec-card-title">Mais Próximo da Meta</span>
                            <span class="exec-card-badge">Faltam {mais_proximo['cotas_faltantes']} cotas</span>
                        </div>
                        <div class="exec-card-value">{mais_proximo['ticker']}</div>
                        <div class="exec-progress-track"><div class="exec-progress-fill" style="width: {min(100.0, mais_proximo['progresso_pct']):.0f}%;"></div></div>
                        <div class="exec-card-sub" style="color: {accent_pos}; font-weight: 600;">{mais_proximo['progresso_pct']:.1f}% concluído</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="exec-card">
                        <div class="exec-card-header">
                            <span class="exec-card-title">Status Global</span>
                            <span class="exec-card-badge">100%</span>
                        </div>
                        <div class="exec-card-value" style="color: {accent_pos};">Concluído</div>
                        <div class="exec-progress-track"><div class="exec-progress-fill" style="width: 100%;"></div></div>
                        <div class="exec-card-sub" style="color: {accent_pos};">✓ Todas as metas batidas!</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.write("")
            df_bola = pd.DataFrame(dados_bola)
            st.dataframe(
                df_bola,
                column_config={
                    "ticker": "Ticker",
                    "classe": "Classe",
                    "periodicidade_magic": "Horizonte Magic",
                    "cotacao": st.column_config.NumberColumn("Cotação", format="R$ %.2f"),
                    "dy_anual_pct": st.column_config.NumberColumn("DY Anual", format="%.1f%%"),
                    "qtd_atual": st.column_config.NumberColumn("Cotas Atuais", format="%d"),
                    "magic_number": st.column_config.NumberColumn("Magic Number (Meta)", format="%d"),
                    "cotas_faltantes": st.column_config.NumberColumn("Faltam Cotas", format="%d"),
                    "valor_meta_total": st.column_config.NumberColumn("Capital Meta", format="R$ %.2f"),
                    "progresso_pct": st.column_config.ProgressColumn("Progresso da Meta", format="%.1f%%", min_value=0, max_value=100),
                    "status": "Diagnóstico da Bola de Neve"
                },
                width="stretch",
                hide_index=True
            )
            st.caption("Periodicidade Dual: **FIIs** calculam o Magic Number **Mensal** (renda todo mês); **Ações** calculam o Magic Number **Anual** (para respeitar a sazonalidade de dividendos e JCP).")
        else:
            st.caption("Cadastre seus ativos na aba 'Minha Carteira' para calcular o Magic Number.")

        st.divider()

        # FIRE REAL AJUSTADO À INFLAÇÃO (EQUAÇÃO DE FISHER)
        st.markdown(titulo_secao_html("compass", "Simulador de Independência Financeira Real (FIRE Ajustado ao IPCA)"), unsafe_allow_html=True)
        gasto_total_mensal = custo_vida_mensal if custo_vida_mensal > 0 else orcamento_calc.get("total_despesas", orcamento_calc.get("total_gastos", 0.0))
        meta_fire_real = fire_real_calc.get("patrimonio_fire_real", 0.0)
        progresso_fire_real = fire_real_calc.get("progresso_fire_real_pct", 0.0)
        renda_real_tot = fire_real_calc.get("renda_real_mensal_total", 0.0)
        renda_nom_tot = fire_real_calc.get("renda_nominal_mensal_total", 0.0)
        rf_real_m = fire_real_calc.get("rf_real_mensal", 0.0)
        rf_nom_m = fire_real_calc.get("rf_nominal_mensal", 0.0)
        papel_real_m = fire_real_calc.get("rv_papel_real_mensal", 0.0)
        papel_nom_m = fire_real_calc.get("rv_papel_nominal_mensal", 0.0)
        yield_real_port = fire_real_calc.get("yield_real_anual_portfolio_pct", 0.0)
        ipca_ref = fire_real_calc.get("ipca_referencia_pct", 4.5)

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            st.markdown(f"""
            <div class="exec-card">
                <div class="exec-card-header">
                    <span class="exec-card-title">Custo de Vida Real / Ano</span>
                    <span class="exec-card-badge">Orçamento Mensal x 12</span>
                </div>
                <div class="exec-card-value">{fmt_moeda(gasto_total_mensal * 12.0)}</div>
                <div class="exec-progress-track"><div class="exec-progress-fill" style="width: 100%;"></div></div>
                <div class="exec-card-sub">Base mensal: {fmt_moeda(gasto_total_mensal)}/mês (Fixos + Variáveis)</div>
            </div>
            """, unsafe_allow_html=True)
        with col_f2:
            st.markdown(f"""
            <div class="exec-card">
                <div class="exec-card-header">
                    <span class="exec-card-title">Patrimônio FIRE Real</span>
                    <span class="exec-card-badge">Yield Real {yield_real_port:.2f}% a.a.</span>
                </div>
                <div class="exec-card-value">{fmt_moeda(meta_fire_real)}</div>
                <div class="exec-progress-track"><div class="exec-progress-fill" style="width: {min(100.0, progresso_fire_real):.0f}%;"></div></div>
                <div class="exec-card-sub">Desconta IPCA ({ipca_ref:.2f}% a.a.) em RF CDI e FIIs Papel via Fisher</div>
            </div>
            """, unsafe_allow_html=True)
        with col_f3:
            st.markdown(f"""
            <div class="exec-card">
                <div class="exec-card-header">
                    <span class="exec-card-title">Progresso FIRE Real</span>
                    <span class="exec-card-badge">Poder de Compra</span>
                </div>
                <div class="exec-card-value" style="color: {accent_pos};">{progresso_fire_real:.1f}%</div>
                <div class="exec-progress-track"><div class="exec-progress-fill" style="width: {min(100.0, progresso_fire_real):.0f}%;"></div></div>
                <div class="exec-card-sub" style="color: {accent_pos}; font-weight: 600;">{'✓ Independência Real Atingida' if progresso_fire_real >= 100 else 'Renda p/ gasto seguro sem corroer principal'}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="quant-research-card" style="margin-top: 10px; border-left: 4px solid #0F5132;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div>
                    <div style="font-size: 0.78rem; font-weight: 700; color: {text_primary}; text-transform: uppercase; letter-spacing: 0.04em;">Decomposição Fisher — Renda Passiva Nominal vs. Renda Real Disponível para Gasto</div>
                    <div style="font-size: 0.80rem; color: {text_secondary}; margin-top: 4px;">
                        RF CDI: <span style="font-family:'JetBrains Mono',monospace;">{fmt_moeda(rf_nom_m)}</span> nominal → <strong style="color:{accent_pos};font-family:'JetBrains Mono',monospace;">{fmt_moeda(rf_real_m)}</strong> real &nbsp;|&nbsp;
                        FIIs Papel: <span style="font-family:'JetBrains Mono',monospace;">{fmt_moeda(papel_nom_m)}</span> nominal → <strong style="color:{accent_pos};font-family:'JetBrains Mono',monospace;">{fmt_moeda(papel_real_m)}</strong> real
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.70rem; color: {text_secondary}; text-transform: uppercase;">Disponível p/ Gasto Mensal Real</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; font-size: 1.08rem; font-weight: 800; color: {accent_pos};">{fmt_moeda(renda_real_tot)} <span style="font-size: 0.78rem; color: {text_muted}; font-weight: 500;">(vs {fmt_moeda(renda_nom_tot)} nominal)</span></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # SUB-VISÃO 5: NOTÍCIAS & FATOS RELEVANTES
    # -------------------------------------------------------------------------
    elif sub_radar.startswith("Notícias"):
        st.markdown(titulo_secao_html("newspaper", "Radar de Notícias Global & Brasil: Pensamento de 2ª e 3ª Ordem"), unsafe_allow_html=True)
        st.caption("Monitora fontes do Brasil e dos EUA (CNBC Finance/Tech e Investing Global), mapeando impactos em Ações, ETFs e BDRs do Nubank.")

        teses_noticias = get_noticias_cached()
        for item in teses_noticias:
            is_aberta = "JANELA ABERTA" in item["status_assimetria"]
            var_cor_not = accent_pos if item['variacao_dia_pct'] >= 0 else "#DC2626"
            escopo_txt = item.get("escopo", "Nacional")
            escopo_icon = "🌎 Internacional" if escopo_txt == "Internacional" else "🇧🇷 Brasil"
            link_not = item.get("link", "")
            with st.container(border=True):
                col_not1, col_not2 = st.columns([3, 1])
                with col_not1:
                    st.markdown(f"#### {item['titulo']}")
                    link_md = f" • [Ler notícia original]({link_not})" if link_not else ""
                    st.caption(f"{escopo_icon} • Status: **{item['status_assimetria']}** • Fonte: {item['fonte']}{link_md}")
                    st.info(f"**1ª Ordem (Fato):** {item['fato_1a_ordem']}")
                    st.warning(f"**2ª Ordem (Transmissão):** {item['consequencia_2a_ordem']}")
                    st.success(f"**3ª Ordem (Tese B3 / Nubank):** {item['tese_3a_ordem']}")
                with col_not2:
                    st.markdown(f"""
                    <div class="exec-card" style="height: auto;">
                        <div class="exec-card-header">
                            <span class="exec-card-title">Ativo Alvo</span>
                            <span class="exec-card-badge">{item['ticker_alvo']}</span>
                        </div>
                        <div class="exec-card-value">R$ {item['cotacao_atual']:.2f}</div>
                        <div class="exec-card-sub" style="color: {var_cor_not}; font-weight: 700; font-family: 'JetBrains Mono', monospace;">{item['variacao_dia_pct']:+.2f}% hoje</div>
                        <div style="font-size: 0.74rem; color: {text_secondary}; margin-top: 8px; line-height: 1.35;">{item['justificativa']}</div>
                    </div>
                    """, unsafe_allow_html=True)

        st.divider()

        st.markdown(titulo_secao_html("cpu", "Simulador Interativo de Notícias"), unsafe_allow_html=True)
        noticia_input = st.text_input("Manchete ou Fato de Mercado:", value="Copom eleva projeções de inflação e mercado antecipa aperto monetário")
        if st.button(":material/bolt: Deduzir Cadeia Causal"):
            tese_sim = inferir_tese_heuristica({"titulo": noticia_input, "fonte": "Simulador Quant"})
            with st.container(border=True):
                st.markdown(titulo_secao_html("target", f"Tese Resultante para {tese_sim.ticker_alvo} ({tese_sim.direcao})"), unsafe_allow_html=True)
                st.info(f"**1ª Ordem:** {tese_sim.fato_1a_ordem}")
                st.warning(f"**2ª Ordem:** {tese_sim.consequencia_2a_ordem}")
                st.success(f"**3ª Ordem:** {tese_sim.tese_3a_ordem}")
                st.caption(f"{tese_sim.justificativa}")


with tab_radar:
    _render_fragment_radar_oportunidades()


# =============================================================================
# ABA 4: GUIA EDUCACIONAL & ESTUDOS DIÁRIOS (CARREGAMENTO SOB DEMANDA)
# =============================================================================
with tab_estudos:
    st.markdown("""
    <div class="guide-box">
        <strong>Guia Educacional & Formação do Investidor:</strong> Conceitos fundamentais de valuation, 
        segurança patrimonial e disciplina financeira explicados <strong>sem jargões matemáticos desnecessários</strong>. 
        Todo dia você encontra um novo artigo/estudo de autoridade selecionado para elevar seu nível como investidor.
    </div>
    """, unsafe_allow_html=True)

    estudos_diarios_lista = get_estudos_diarios_cached()

    # 1. ESTUDO DO DIA ROTATIVO
    dia_hoje = datetime.now().day
    col_e1, col_e2 = st.columns([3, 1])
    with col_e1:
        st.markdown(titulo_secao_html("book", f"Recomendação de Estudo do Dia (Dia {dia_hoje})"), unsafe_allow_html=True)
    with col_e2:
        dia_escolhido = st.selectbox(
            "Navegar nos Estudos:",
            options=list(range(1, 32)),
            index=(dia_hoje - 1),
            format_func=lambda d: f"Dia {d}: {estudos_diarios_lista[d-1]['titulo'][:28]}..."
        )

    estudo_ativo = obter_estudo_do_dia(dia_escolhido)

    with st.container(border=True):
        col_card1, col_card2 = st.columns([3, 1])
        with col_card1:
            st.markdown(f"## {estudo_ativo['titulo']}")
            st.caption(f"**Autor/Referência:** {estudo_ativo['autor']} • **Categoria:** `{estudo_ativo['categoria']}` • **Leitura Estimada:** {estudo_ativo['tempo_leitura']}")
            st.markdown(f"**Resumo Conceitual:** {estudo_ativo['resumo']}")
            st.info(f"**Lição Prática para a sua Carteira:** {estudo_ativo['licao_pratica']}")
        with col_card2:
            st.write("")
            st.write("")
            st.link_button(
                ":material/open_in_new: Acessar Fonte Oficial",
                url=estudo_ativo["link"],
                width="stretch"
            )
            st.caption("Link externo 100% verificado de portal financeiro oficial.")

        with st.expander(":material/menu_book: Ler Artigo Completo do Estudo (Direto no Terminal, Sem Jargões)", expanded=True):
            st.markdown(estudo_ativo.get("texto_completo", estudo_ativo.get("resumo", "")))

    st.divider()

    # 2. GLOSSÁRIO E METODOLOGIAS PERMANENTES
    st.markdown(titulo_secao_html("layers", "Acervo Permanente de Metodologias & Conceitos Quantitativos"), unsafe_allow_html=True)
    st.caption("Consulte a qualquer momento as fórmulas matemáticas, critérios de segurança e lógica que o Terminal utiliza para calcular seus investimentos.")

    glossario = get_glossario_cached()

    tab_cat1, tab_cat2, tab_cat3 = st.tabs([
        ":material/target: Valuation & Timing de Compra",
        ":material/verified_user: Segurança & Saúde Patrimonial",
        ":material/payments: Renda Passiva & Fiscalidade"
    ])

    cat1_ids = ['graham', 'bazin', 'rsi', 'triade']
    cat2_ids = ['balanco', 'rebal_macro', 'cfp_orc']
    cat3_ids = ['snowball', 'fiscal_darf', 'cdi_liq']

    with tab_cat1:
        st.caption("Modelos matemáticos para calcular quanto a ação 'vale' vs quanto ela 'custa' e momentos de oportunidade com RSI.")
        for conc in glossario:
            if conc["id"] in cat1_ids:
                with st.expander(f"{conc['titulo']} — {conc['analogia']}", expanded=(conc['id'] in ['graham', 'triade'])):
                    st.markdown(f"**Resumo:** {conc.get('resumo_curto', '')}")
                    st.divider()
                    st.markdown(conc["explicacao"])
                    st.success(f"**Como Usar no Dia a Dia:** {conc['como_usar']}")

    with tab_cat2:
        st.caption("Filtros anti-risco para evitar empresas endividadas, alavancadas ou com risco de falência, além de regras de fluxo de caixa.")
        for conc in glossario:
            if conc["id"] in cat2_ids:
                with st.expander(f"{conc['titulo']} — {conc['analogia']}", expanded=(conc['id'] == 'balanco')):
                    st.markdown(f"**Resumo:** {conc.get('resumo_curto', '')}")
                    st.divider()
                    st.markdown(conc["explicacao"])
                    st.success(f"**Como Usar no Dia a Dia:** {conc['como_usar']}")

    with tab_cat3:
        st.caption("Regras fiscais de DARF, isenção dos R$ 20.000, juros compostos da Bola de Neve e comparação com a Renda Fixa do Nubank.")
        for conc in glossario:
            if conc["id"] in cat3_ids:
                with st.expander(f"{conc['titulo']} — {conc['analogia']}", expanded=(conc['id'] == 'fiscal_darf')):
                    st.markdown(f"**Resumo:** {conc.get('resumo_curto', '')}")
                    st.divider()
                    st.markdown(conc["explicacao"])
                    st.success(f"**Como Usar no Dia a Dia:** {conc['como_usar']}")
