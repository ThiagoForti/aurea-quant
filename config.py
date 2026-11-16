"""
Configurações Globais do Sistema Quantitativo B3 & Renda Fixa
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "user_state.json"
DEMO_STATE_FILE = BASE_DIR / "user_state_demo.json"
EXCEL_FILE = BASE_DIR / "Gestao_Completa_Patrimonio_B3.xlsx"
BACKUP_DIR = BASE_DIR / "backups"

# Caches temporários com suporte cross-platform (Windows: %LOCALAPPDATA% | Linux/macOS: ~/.cache/AureaQuant)
_local_appdata = os.getenv("LOCALAPPDATA")
if _local_appdata:
    LOCAL_CACHE_DIR = Path(_local_appdata) / "AureaQuant" / "cache"
else:
    LOCAL_CACHE_DIR = Path.home() / ".cache" / "AureaQuant"

try:
    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    LOCAL_CACHE_DIR = BASE_DIR / ".cache"
    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

MACRO_CACHE_FILE = LOCAL_CACHE_DIR / "macro_cache.json"
MARKET_CACHE_FILE = LOCAL_CACHE_DIR / "market_cache.json"
LEGACY_MACRO_CACHE_FILE = BASE_DIR / "macro_cache.json"
LEGACY_MARKET_CACHE_FILE = BASE_DIR / "market_cache.json"

# Segmentação Financeira (Haircut seletivo de JCP no Método de Bazin)
BANCOS_JCP = ["ITUB4", "BBDC4", "BBAS3", "SANB11"]          # Mesclam JCP e dividendos -> haircut ponderado 10% (x 0.90)
SEGURADORAS_ISENTAS = ["BBSE3", "CXSE3"]                      # Quase 100% dividendos isentos -> haircut 0% (x 1.00)

# Universo Base de Ativos da B3
UNIVERSO_BESST = [
    "TAEE11.SA", "EGIE3.SA", "ISAE4.SA", "CPFE3.SA", "CMIG4.SA",
    "SBSP3.SA", "SAPR11.SA", "CSMG3.SA", "ITUB4.SA", "BBAS3.SA",
    "BBDC4.SA", "BBSE3.SA", "CXSE3.SA", "VIVT3.SA"
]

UNIVERSO_CRESCIMENTO = [
    "WEGE3.SA", "VALE3.SA", "PETR4.SA", "PRIO3.SA", "SUZB3.SA",
    "RADL3.SA", "SLCE3.SA", "SMTO3.SA", "RENT3.SA", "TOTS3.SA", "GGBR4.SA"
]

# Segmentação de Fundos Imobiliários: Papel (CRIs) vs. Tijolo (Imóveis Físicos)
FIIS_PAPEL = ["KNCR11", "KNIP11"]
FIIS_TIJOLO = ["HGLG11", "BTLG11", "XPML11"]

UNIVERSO_FIIS = [
    "HGLG11.SA", "KNCR11.SA", "BTLG11.SA", "XPML11.SA", "KNIP11.SA"
]

UNIVERSO_ETFS = [
    "BOVA11.SA", "DIVO11.SA", "IVVB11.SA", "NASD11.SA", "WRLD11.SA", "SMAL11.SA", "GOLD11.SA"
]

# Principais BDRs internacionais negociados em Reais na B3 (disponíveis no app Nubank)
UNIVERSO_BDRS = [
    "NVDC34.SA", "AAPL34.SA", "MSFT34.SA", "GOGL34.SA", "AMZO34.SA",
    "M1TA34.SA", "TSLA34.SA", "TSMC34.SA", "MELI34.SA", "BERK34.SA"
]

TODOS_TICKERS = list(dict.fromkeys(
    UNIVERSO_BESST + UNIVERSO_CRESCIMENTO + UNIVERSO_FIIS + UNIVERSO_ETFS + UNIVERSO_BDRS
))

# Códigos SGS do Banco Central do Brasil
SGS_SELIC_META = 432      # Taxa Selic Meta (% a.a.)
SGS_CDI_DIARIO = 4389     # Taxa CDI Anualizada (% a.a.)
SGS_IPCA_12M = 13522      # IPCA acumulado 12 meses oficial (% a.a.) - Série oficial BCB
SGS_PTAX_VENDA = 1        # Dólar PTAX Venda (R$)

# Alíquotas de IR Regressivo Renda Fixa (Tabela RF Brasil)
IR_RENDA_FIXA_TABELA = [
    (180, 0.225),  # Até 180 dias: 22,5%
    (360, 0.200),  # De 181 a 360 dias: 20,0%
    (720, 0.175),  # De 361 a 720 dias: 17,5%
    (float('inf'), 0.150)  # Acima de 720 dias: 15,0%
]

# Regras de Imposto de Renda B3
LIMITE_ISENCAO_ACOES_MES = 20000.0  # R$ 20.000,00 no mês para Ações (Swing Trade)
ALIQUOTA_IR_ACOES = 0.15           # 15% sobre o ganho líquido
ALIQUOTA_IR_FIIS = 0.20            # 20% sobre o ganho líquido (sem isenção!)
CODIGO_DARF_RENDA_VARIAVEL = "6015" # Código DARF para Pessoa Física no Sicalc

# Feeds RSS para Monitoramento de Notícias (Nacionais e Internacionais)
RSS_FEEDS = [
    {"source": "InfoMoney Mercados", "url": "https://www.infomoney.com.br/mercados/feed/", "scope": "Nacional"},
    {"source": "InfoMoney Economia", "url": "https://www.infomoney.com.br/economia/feed/", "scope": "Nacional"},
    {"source": "G1 Economia", "url": "https://g1.globo.com/rss/g1/economia/", "scope": "Nacional"},
    {"source": "Valor Econômico", "url": "https://pox.globo.com/rss/valor", "scope": "Nacional"},
    {"source": "Investing Global", "url": "https://br.investing.com/rss/news.rss", "scope": "Internacional"},
    {"source": "CNBC Finance (EUA)", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", "scope": "Internacional"},
    {"source": "CNBC Tech (Big Techs)", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910", "scope": "Internacional"},
]
