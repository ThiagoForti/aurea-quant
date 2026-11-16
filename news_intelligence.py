"""
Motor Autônomo de Inferência de Notícias (Second-Order Thinking)
Dedução de cadeias causais:
Fato (1ª Ordem) -> Consequência Econômica (2ª Ordem) -> Tese na B3 (3ª Ordem)
Detecção de Janelas Abertas de Assimetria via yfinance.
"""
import os
import re
import feedparser
import yfinance as yf
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from config import RSS_FEEDS, UNIVERSO_BESST, UNIVERSO_CRESCIMENTO
from data_engine import obter_info_ativo


class TeseNoticia(BaseModel):
    titulo: str = Field(description="Título da notícia analisada")
    fonte: str = Field(description="Fonte do feed ou publicação")
    fato_1a_ordem: str = Field(description="Fato objetivo e imediato (1ª ordem)")
    consequencia_2a_ordem: str = Field(description="Impacto econômico/setorial intermediário (2ª ordem)")
    tese_3a_ordem: str = Field(description="Tese resultante na B3 (3ª ordem)")
    ticker_alvo: str = Field(description="Ticker do ativo mais impactado na B3 (ex: PETR4, TAEE11)")
    direcao: str = Field(description="Impacto esperado: POSITIVA, NEGATIVA ou NEUTRA")
    justificativa: str = Field(description="Raciocínio lógico e causal da oportunidade")


def extrair_noticias_rss(limite_por_feed: int = 5) -> List[Dict[str, str]]:
    """Extrai manchetes e resumos dos principais feeds financeiros nacionais e internacionais."""
    noticias = []
    for item_feed in RSS_FEEDS:
        try:
            feed = feedparser.parse(item_feed["url"])
            for entrada in feed.entries[:limite_por_feed]:
                titulo = entrada.get("title", "")
                resumo = re.sub(r'<[^>]+>', '', entrada.get("summary", entrada.get("description", "")))
                link = entrada.get("link", "")
                if titulo:
                    noticias.append({
                        "fonte": item_feed["source"],
                        "escopo": item_feed.get("scope", "Nacional"),
                        "titulo": titulo.strip(),
                        "resumo": resumo.strip()[:300],
                        "link": link
                    })
        except Exception as e:
            print(f"[Aviso] Falha ao ler feed {item_feed['source']}: {e}")
    return noticias


def _contem(texto: str, termos: List[str]) -> bool:
    """Busca termos como PALAVRAS inteiras (evita 'real' casar com 'realizar')."""
    return any(re.search(rf"(?<!\w){re.escape(t)}(?!\w)", texto) for t in termos)


# Vocabulário econômico mínimo (PT + EN) para uma notícia entrar no radar
TERMOS_ECONOMICOS = [
    "selic", "copom", "juros", "juro", "banco central", "fed", "fomc", "powell", "inflação", "inflation",
    "ipca", "igp-m", "pib", "gdp", "dólar", "dollar", "câmbio", "bolsa", "ibovespa", "b3", "nasdaq",
    "s&p 500", "wall street", "dow jones", "dividendos", "dividends", "proventos",
    "lucro", "profit", "prejuízo", "loss", "receita", "revenue", "balanço", "earnings", "resultado trimestral",
    "ebitda", "dívida pública", "fiscal", "arcabouço", "tesouro", "treasury", "títulos públicos", "yield",
    "petróleo", "oil", "brent", "opep", "opec", "minério", "commodities", "commodity", "soja",
    "milho", "açúcar", "celulose", "siderurgia", "energia elétrica", "tarifa", "tariffs", "bandeira tarifária",
    "saneamento", "privatização", "concessão", "leilão", "fii", "fiis", "fundos imobiliários", "etf", "bdr",
    "mercado financeiro", "market", "markets", "investidores", "investors", "economia", "economy", "economic",
    "exportações", "importações", "safra", "varejo", "retail", "indústria", "desemprego", "crédito", "bancos",
    "banks", "seguradora", "imposto de renda", "reforma tributária", "iof", "recessão", "recession", "tarifaço",
    "guerra comercial", "rating", "moody's", "fitch", "ipo", "fusão", "aquisição", "merger", "acquisition",
    "debêntures", "cdi", "poupança", "gasolina", "diesel", "combustíveis",
    "petrobras", "itaú", "bradesco", "banco do brasil", "weg", "eletrobras", "ações", "stocks", "stock", "shares",
    "nvidia", "nvda", "jensen huang", "apple", "iphone", "microsoft", "azure", "google", "alphabet",
    "amazon", "aws", "meta", "tesla", "tsmc", "amd", "intel", "mercado livre", "meli",
    "semicondutores", "semiconductor", "semiconductors", "chips", "chip", "ai", "inteligência artificial",
    "artificial intelligence", "tech", "ceo", "guidance", "interest rate", "rate cut", "rate hike",
]


def eh_noticia_economica(noticia: Dict[str, str], minimo_termos: int = 1) -> bool:
    """
    Filtro de relevância (B7): descarta notícias sem relação com economia/mercado
    (ex.: política criminal, esportes, celebridades) para não gerar teses forçadas.
    """
    texto = (noticia.get("titulo", "") + " " + noticia.get("resumo", "")).lower()
    encontrados = sum(1 for t in TERMOS_ECONOMICOS if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", texto))
    return encontrados >= minimo_termos


def inferir_tese_heuristica(noticia: Dict[str, str]) -> TeseNoticia:
    """
    Motor quantitativo heurístico especialista para dedução de 2ª e 3ª ordem.
    Garante funcionamento 100% autônomo e imediato sem necessidade de API key externa.
    """
    texto = (noticia.get("titulo", "") + " " + noticia.get("resumo", "")).lower()
    fonte = noticia.get("fonte", "Mercado Financeiro")

    if _contem(texto, ["selic", "copom", "juros", "banco central", "taxa básica"]):
        if _contem(texto, ["alta", "eleva", "elevação", "subir", "sobe", "aperta", "aperto", "hawkish", "manutenção", "mantém"]):
            return TeseNoticia(
                titulo=noticia.get("titulo", ""),
                fonte=fonte,
                fato_1a_ordem="Banco Central sinaliza manutenção ou alta da Taxa Selic.",
                consequencia_2a_ordem="Elevação do custo de captação de dívidas e aumento da atratividade do CDI.",
                tese_3a_ordem="Bancos e FIIs de recebíveis (papel) expandem margem de intermediação e yield em CDI.",
                ticker_alvo="ITUB4",
                direcao="POSITIVA",
                justificativa="Grandes bancos e títulos CDI ganham rentabilidade operacional em ciclos de juros firmes."
            )
        else:
            return TeseNoticia(
                titulo=noticia.get("titulo", ""),
                fonte=fonte,
                fato_1a_ordem="Banco Central aponta espaço para afrouxamento ou corte de juros.",
                consequencia_2a_ordem="Queda das taxas futuras de juros (DIs) e expansão de múltiplos de empresas alavancadas.",
                tese_3a_ordem="Aumento do valor presente dos fluxos futuros em concessões de infraestrutura e consumo.",
                ticker_alvo="RENT3",
                direcao="POSITIVA",
                justificativa="Queda de juros reduz despesa financeira e expande margem líquida."
            )

    if _contem(texto, ["petróleo", "brent", "opep", "combustível", "gasolina", "diesel"]):
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Volatilidade ou choque na cotação internacional do barril de petróleo.",
            consequencia_2a_ordem="Alteração direta na receita em dólares e geração de caixa de produtoras locais.",
            tese_3a_ordem="Empresas de exploração (E&P) de baixo lifting cost mantêm geração de caixa livre robusta.",
            ticker_alvo="PRIO3",
            direcao="POSITIVA",
            justificativa="Aumento do spread operacional por barril eleva lucro líquido e ROE das petroleiras eficientes."
        )

    if _contem(texto, ["dólar", "câmbio", "desvalorização do real", "moeda americana"]):
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Pressão cambial e valorização da moeda norte-americana.",
            consequencia_2a_ordem="Exportadoras brasileiras convertem receitas dolarizadas a um câmbio mais favorável.",
            tese_3a_ordem="Empresas com receita em moeda forte e custos fabris em reais expandem Ebitda.",
            ticker_alvo="WEGE3",
            direcao="POSITIVA",
            justificativa="Hedge cambial natural através de líderes industriais globais listadas na B3."
        )

    if _contem(texto, ["chuva", "chuvas", "seca", "reservatório", "reservatórios", "energia elétrica", "bandeira tarifária", "hidrelétricas"]):
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Mudança nos níveis hidrológicos ou acionamento de bandeira tarifária de energia.",
            consequencia_2a_ordem="Flutuação do PLD (Preço de Liquidação das Diferenças) e GSF de geradoras elétricas.",
            tese_3a_ordem="Transmissoras de energia com RAP fixa e blindada contra volume permanecem estáveis.",
            ticker_alvo="TAEE11",
            direcao="POSITIVA",
            justificativa="Transmissão não corre risco hidrológico (recebe pela disponibilidade da linha, não pela energia transportada)."
        )

    if _contem(texto, ["nvidia", "nvda", "jensen huang", "semicondutores", "semiconductor", "semiconductors", "gpus", "gpu"]):
        eh_queda_ou_risco = _contem(texto, [
            "exit", "saída", "saiu", "deixa", "renúncia", "resign", "drop", "fall", "plunge",
            "queda", "tombo", "desaba", "selloff", "sell-off", "cut", "warning", "probe", "ban"
        ])
        if eh_queda_ou_risco:
            return TeseNoticia(
                titulo=noticia.get("titulo", ""),
                fonte=fonte,
                fato_1a_ordem="Fato corporativo/setorial de alta volatilidade envolvendo Nvidia ou semicondutores.",
                consequencia_2a_ordem="Aumento da percepção de risco de curto prazo, pressão nas ações da Nasdaq e realização de lucros no setor de IA.",
                tese_3a_ordem="O BDR NVDC34 (negociado em Reais na B3/Nubank) reflete o movimento e pode abrir janela de monitoramento para pullback.",
                ticker_alvo="NVDC34",
                direcao="NEGATIVA",
                justificativa="Risco de governança/transição ou realização de lucros gera desconto técnico; acompanhar estabilização antes de aportar."
            )
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Avanço operacional, novos contratos ou demanda aquecida em chips e inteligência artificial.",
            consequencia_2a_ordem="Expansão de receita e margens na cadeia global de data centers e computação acelerada.",
            tese_3a_ordem="Exposição direta via BDR NVDC34 ou ETF NASD11 na B3 (disponíveis no Nubank).",
            ticker_alvo="NVDC34",
            direcao="POSITIVA",
            justificativa="Liderança tecnológica em IA sustenta forte geração de caixa e múltiplos de crescimento."
        )

    if _contem(texto, ["apple", "iphone", "ipad", "tim cook"]):
        eh_risco = _contem(texto, ["drop", "fall", "queda", "lawsuit", "antitrust", "ban", "decline", "miss", "exit"])
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Notícia corporativa relevante envolvendo a Apple e seu ecossistema global.",
            consequencia_2a_ordem="Reajuste de expectativas de vendas de hardware, serviços e margens no mercado americano.",
            tese_3a_ordem="Impacto direto no BDR AAPL34 (negociado em Reais na B3/Nubank).",
            ticker_alvo="AAPL34",
            direcao="NEGATIVA" if eh_risco else "POSITIVA",
            justificativa="Movimento afeta diretamente o valuation de uma das maiores posições do S&P 500 e Nasdaq."
        )

    if _contem(texto, ["microsoft", "azure", "openai", "satya nadella"]):
        eh_risco = _contem(texto, ["drop", "fall", "queda", "lawsuit", "antitrust", "decline", "miss", "exit"])
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Movimentação estratégica da Microsoft em nuvem corporativa (Azure) e IA.",
            consequencia_2a_ordem="Alteração nas expectativas de receita recorrente B2B e capex em data centers.",
            tese_3a_ordem="Reflexo direto no BDR MSFT34 (negociado em Reais na B3/Nubank).",
            ticker_alvo="MSFT34",
            direcao="NEGATIVA" if eh_risco else "POSITIVA",
            justificativa="Receita corporativa recorrente e liderança em software corporativo."
        )

    if _contem(texto, ["google", "alphabet", "youtube", "gemini", "sundar pichai"]):
        eh_risco = _contem(texto, ["drop", "fall", "queda", "lawsuit", "antitrust", "breakup", "decline", "miss"])
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Fato relevante sobre Alphabet/Google (buscas, anúncios, nuvem ou regulação).",
            consequencia_2a_ordem="Impacto na expectativa de fluxo de caixa em publicidade digital e cloud.",
            tese_3a_ordem="Impacto direto no BDR GOGL34 na B3/Nubank.",
            ticker_alvo="GOGL34",
            direcao="NEGATIVA" if eh_risco else "POSITIVA",
            justificativa="Pressões regulatórias podem gerar volatilidade de curto prazo, enquanto crescimento em cloud sustenta tese."
        )

    if _contem(texto, ["amazon", "aws", "jeff bezos", "andy jassy"]):
        eh_risco = _contem(texto, ["drop", "fall", "queda", "lawsuit", "decline", "miss", "tariff"])
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Notícia envolvendo varejo global, logística ou computação em nuvem (AWS) da Amazon.",
            consequencia_2a_ordem="Sensibilidade de margens de e-commerce e expansão de receita em cloud.",
            tese_3a_ordem="Reflexo direto no BDR AMZO34 na B3/Nubank.",
            ticker_alvo="AMZO34",
            direcao="NEGATIVA" if eh_risco else "POSITIVA",
            justificativa="AWS é o principal motor de lucro operacional da companhia."
        )

    if _contem(texto, ["meta", "facebook", "instagram", "whatsapp", "zuckerberg"]):
        eh_risco = _contem(texto, ["drop", "fall", "queda", "lawsuit", "antitrust", "decline", "miss"])
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Fato relevante sobre Meta Platforms (anúncios digitais, IA ou despesas de capital).",
            consequencia_2a_ordem="Impacto direto na eficiência de monetização publicitária e margens operacionais.",
            tese_3a_ordem="Reflexo no BDR M1TA34 na B3/Nubank.",
            ticker_alvo="M1TA34",
            direcao="NEGATIVA" if eh_risco else "POSITIVA",
            justificativa="Forte geração de caixa em publicidade digital frente a investimentos em IA."
        )

    if _contem(texto, ["tesla", "elon musk", "ev", "electric vehicle", "robotaxi"]):
        eh_risco = _contem(texto, ["drop", "fall", "queda", "recall", "decline", "miss", "slump"])
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Novidade ou variação relevante nas entregas, margens ou governança da Tesla.",
            consequencia_2a_ordem="Reprecificação de múltiplos de crescimento no setor de veículos elétricos e autonomia.",
            tese_3a_ordem="Alta volatilidade refletida no BDR TSLA34 na B3/Nubank.",
            ticker_alvo="TSLA34",
            direcao="NEGATIVA" if eh_risco else "POSITIVA",
            justificativa="Ativo com beta elevado e sensível a entregas trimestrais e notícias executivas."
        )

    if _contem(texto, ["tsmc", "taiwan semiconductor", "amd", "intel"]):
        eh_risco = _contem(texto, ["drop", "fall", "queda", "tariff", "sanction", "ban", "decline"])
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Movimentação na cadeia global de fabricação de semicondutores e fundição de chips.",
            consequencia_2a_ordem="Impacto na oferta de chips avançados e nos custos do setor de tecnologia global.",
            tese_3a_ordem="Exposição via BDR TSMC34 ou ETF NASD11 na B3/Nubank.",
            ticker_alvo="TSMC34",
            direcao="NEGATIVA" if eh_risco else "POSITIVA",
            justificativa="TSMC concentra a produção dos chips mais avançados do mundo (incluindo Nvidia e Apple)."
        )

    if _contem(texto, ["fed", "fomc", "powell", "nasdaq", "s&p 500", "wall street", "dow jones", "treasury", "rate cut", "rate hike", "us stocks"]):
        eh_aperto = _contem(texto, ["hike", "alta", "hawkish", "inflation", "hot", "drop", "fall", "selloff", "tumble", "tariffs"])
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Movimento macroeconômico nos EUA (Fed, Treasuries ou índices de Wall Street).",
            consequencia_2a_ordem="Alteração na taxa livre de risco global (Treasury 10Y) e apetite por ações americanas.",
            tese_3a_ordem="Impacto direto nos ETFs internacionais da B3: IVVB11 (S&P 500) e NASD11 (Nasdaq).",
            ticker_alvo="NASD11" if _contem(texto, ["nasdaq", "tech", "ai"]) else "IVVB11",
            direcao="NEGATIVA" if eh_aperto else "POSITIVA",
            justificativa="Juros americanos e liquidez global ditam os múltiplos das bolsas desenvolvidas."
        )

    if _contem(texto, ["saneamento", "marco legal do saneamento", "esgoto", "sabesp", "copasa", "sanepar"]):
        return TeseNoticia(
            titulo=noticia.get("titulo", ""),
            fonte=fonte,
            fato_1a_ordem="Avanços regulatórios e investimentos em saneamento básico e universalização.",
            consequencia_2a_ordem="Expansão da Base de Ativos Regulatórios (RAB) com retorno real garantido.",
            tese_3a_ordem="Concessionárias estaduais de saneamento fortalecem previsibilidade e fluxo de dividendos.",
            ticker_alvo="SBSP3",
            direcao="POSITIVA",
            justificativa="Receita recorrente, protegida por contratos de concessão de longo prazo."
        )

    # Caso padrão: notícia econômica sem cadeia setorial clara -> NÃO força tese em ativo específico
    return TeseNoticia(
        titulo=noticia.get("titulo", ""),
        fonte=fonte,
        fato_1a_ordem="Notícia econômica de caráter geral, sem gatilho setorial identificado.",
        consequencia_2a_ordem="Impacto difuso no mercado como um todo; sem transmissão clara para um setor específico.",
        tese_3a_ordem="Sem tese direcional. Acompanhar o índice amplo e manter a estratégia de aportes.",
        ticker_alvo="BOVA11",
        direcao="NEUTRA",
        justificativa="Evita conclusões forçadas: quando não há cadeia causal clara, o correto é não agir."
    )


def analisar_noticia_com_gemini(
    noticia: Dict[str, str],
    api_key: Optional[str] = None
) -> TeseNoticia:
    """Utiliza a API do Gemini com saída estruturada Pydantic se chave configurada."""
    chave = api_key or os.environ.get("GEMINI_API_KEY")
    if not chave:
        return inferir_tese_heuristica(noticia)

    try:
        from google import genai
        client = genai.Client(api_key=chave)

        prompt = f"""
        Você é um estrategista quantitativo e analista CNPI da B3.
        Analise a seguinte notícia e deduza rigorosamente o pensamento de segunda e terceira ordem:
        Título: {noticia['titulo']}
        Resumo: {noticia.get('resumo', '')}

        Regras:
        1. Fato de 1ª Ordem: O acontecimento objetivo.
        2. Consequência de 2ª Ordem: A transmissão econômica (juros, inflação, custos, câmbio).
        3. Tese de 3ª Ordem: Quem ganha/perde na bolsa brasileira (B3).
        4. Ticker Alvo: Um ticker real da B3 — Ações, FIIs, ETFs ou BDRs negociados no Brasil (ex: PETR4, TAEE11, NVDC34, AAPL34, NASD11, IVVB11).
        5. Direção: POSITIVA, NEGATIVA ou NEUTRA.
        """
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": TeseNoticia,
            },
        )
        if response.text:
            return TeseNoticia.model_validate_json(response.text)
    except Exception as e:
        print(f"[Aviso] Falha na chamada Gemini API: {e}. Alternando para heurística quant.")

    return inferir_tese_heuristica(noticia)


def processar_radar_noticias(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Rastreia notícias, infere teses de 2ª e 3ª ordem e cruza com a cotação em tempo real
    para detectar '🎯 JANELA ABERTA (Assimetria)' antes que o mercado precifique o movimento.
    """
    noticias_brutas = extrair_noticias_rss(limite_por_feed=4)
    # Filtro de relevância: só notícias com conteúdo econômico entram no radar
    noticias_brutas = [n for n in noticias_brutas if eh_noticia_economica(n)]
    teses_processadas = []

    for n in noticias_brutas:
        tese = analisar_noticia_com_gemini(n, api_key=api_key)
        ticker = tese.ticker_alvo.replace(".SA", "").strip().upper()

        info = obter_info_ativo(ticker)
        cotacao = info.get("cotacao", 0.0)
        variacao_dia = info.get("variacao_dia", 0.0)

        # Regra de Assimetria Quantitativa Reforçada:
        # Só confirma JANELA ABERTA se a tese é POSITIVA e a variação no dia é moderada (<= +1.5%)
        # evitando recomendar ativos que já dispararam no dia ou após euforia.
        if tese.direcao == "POSITIVA":
            if variacao_dia <= 0.8:
                status_assimetria = "🎯 JANELA ABERTA (Assimetria Favorável / Preço Seguro)"
                cor_status = "green"
            elif variacao_dia <= 2.0:
                status_assimetria = "🔵 EM ANDAMENTO (Janela Parcial)"
                cor_status = "blue"
            else:
                status_assimetria = "⚠️ JÁ ANDOU (Mercado absorveu a notícia)"
                cor_status = "orange"
        elif tese.direcao == "NEGATIVA":
            status_assimetria = "🛡️ ALERTA DE RISCO / HEDGE"
            cor_status = "red"
        else:
            status_assimetria = "⚪ NEUTRO / INFORMATIVO"
            cor_status = "gray"

        teses_processadas.append({
            "titulo": tese.titulo,
            "fonte": tese.fonte,
            "escopo": n.get("escopo", "Nacional"),
            "link": n.get("link", ""),
            "fato_1a_ordem": tese.fato_1a_ordem,
            "consequencia_2a_ordem": tese.consequencia_2a_ordem,
            "tese_3a_ordem": tese.tese_3a_ordem,
            "ticker_alvo": ticker,
            "cotacao_atual": cotacao,
            "variacao_dia_pct": variacao_dia,
            "direcao": tese.direcao,
            "justificativa": tese.justificativa,
            "status_assimetria": status_assimetria,
            "cor_status": cor_status
        })

    return teses_processadas
