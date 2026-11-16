"""
Módulo de Camada de Dados: Banco Central do Brasil (SGS), yfinance e SanityGate
Tratamento robusto de MultiIndex, cache resiliente macro_cache.json / market_cache.json,
capitalização Base 252, escrita atômica para sincronização Google Drive e auditoria de qualidade.
"""
import os
import json
import shutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import numpy as np
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

from config import (
    BASE_DIR, STATE_FILE, DEMO_STATE_FILE, BACKUP_DIR, SGS_SELIC_META, SGS_CDI_DIARIO, SGS_IPCA_12M, SGS_PTAX_VENDA,
    IR_RENDA_FIXA_TABELA, TODOS_TICKERS, MACRO_CACHE_FILE, MARKET_CACHE_FILE,
    LEGACY_MACRO_CACHE_FILE, LEGACY_MARKET_CACHE_FILE, LOCAL_CACHE_DIR
)

# TTLs segregados: Cotações (30 min = 1800s) vs Fundamentos e Dividendos (24h = 86400s)
TTL_COTACAO_SEGUNDOS: int = 1800
TTL_FUNDAMENTOS_SEGUNDOS: int = 86400

# Cache em memória para evitar chamadas repetidas na mesma sessão
_CACHE_LOCK = threading.Lock()
_MACRO_CACHE: Dict[str, Any] = {"timestamp": 0.0, "data": None}
_YF_INFO_CACHE: Dict[str, Dict[str, Any]] = {}
_YF_HIST_CACHE: Dict[str, Any] = {}
_MARKET_CACHE_MEM: Optional[Dict[str, Any]] = None
_MARKET_CACHE_STATUS: Dict[str, Any] = {"usando_cache": False, "data_cache": "", "ativos_em_cache": 0}


def _atomic_write_json(target_path: Union[str, Path], payload: Any) -> Path:
    """
    Escreve JSON de forma atômica (.tmp + flush + os.fsync + os.replace) para impedir
    corrupção de arquivo ou PermissionError durante sincronização do Google Drive.
    """
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f"{target.name}.tmp")

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    # Retry progressivo caso cliente Google Drive mantenha leitura momentânea no arquivo destino
    for tentativa in range(8):
        try:
            os.replace(tmp_path, target)
            break
        except (PermissionError, OSError):
            if tentativa == 7:
                raise
            time.sleep(0.12 * (tentativa + 1))

    return target


def _criar_backup_rotativo_estado(target: Path, max_backups: int = 10) -> None:
    """Cria backup rotativo de user_state.json antes de sobrescrever, evitando perda por conflito de nuvem."""
    try:
        if not target.exists():
            return
        backup_root = Path(BACKUP_DIR)
        backup_root.mkdir(parents=True, exist_ok=True)
        conteudo_atual = target.read_bytes()
        backups_existentes = sorted(backup_root.glob("user_state_*.json"), key=lambda p: p.stat().st_mtime)
        if backups_existentes:
            try:
                if backups_existentes[-1].read_bytes() == conteudo_atual:
                    return
            except Exception:
                pass
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = backup_root / f"user_state_{ts}.json"
        shutil.copy2(target, destino)
        backups_atualizados = sorted(backup_root.glob("user_state_*.json"), key=lambda p: p.stat().st_mtime)
        while len(backups_atualizados) > max_backups:
            antigo = backups_atualizados.pop(0)
            try:
                antigo.unlink()
            except Exception:
                pass
    except Exception as e:
        print(f"[Aviso] Falha ao criar backup rotativo: {e}")


def save_user_state(data: Dict[str, Any], filepath: Union[str, Path] = STATE_FILE) -> Path:
    """
    Salva o estado do usuário (user_state.json) usando escrita atômica segura para nuvem:
    cria backup rotativo antes de sobrescrever e grava via .tmp + fsync() + os.replace().
    """
    target = Path(filepath)
    try:
        if target.resolve() == Path(STATE_FILE).resolve():
            _criar_backup_rotativo_estado(target, max_backups=10)
    except Exception:
        pass

    estado_norm = dict(data or {})
    orc_norm = dict(estado_norm.get("orcamento") or {})
    orc_norm.setdefault("receitas", [])
    orc_norm.setdefault("gastos_fixos", [])
    orc_norm.setdefault("gastos_variaveis", [])
    orc_norm.setdefault("despesas_anuais", [])
    estado_norm["orcamento"] = orc_norm
    estado_norm.setdefault("renda_fixa", [])
    estado_norm.setdefault("renda_variavel", [])
    estado_norm.setdefault("historico_patrimonial_mensal", [])
    estado_norm.setdefault("prejuizo_acumulado_acoes_etfs", 0.0)
    estado_norm.setdefault("prejuizo_acumulado_fiis", 0.0)
    cfg = dict(estado_norm.get("configuracoes") or {})
    cfg.setdefault("alerta_rsi_limite", 30.0)
    cfg.setdefault("meta_meses_reserva", 6)
    estado_norm["configuracoes"] = cfg
    return _atomic_write_json(filepath, estado_norm)


def obter_diretorio_cache() -> Path:
    """
    Retorna o diretório de cache garantindo compatibilidade cross-platform:
    - Windows: %LOCALAPPDATA%/AureaQuant/cache
    - Linux / macOS: ~/.cache/AureaQuant
    """
    localapp = os.getenv("LOCALAPPDATA")
    if localapp:
        d = Path(localapp) / "AureaQuant" / "cache"
    else:
        d = Path.home() / ".cache" / "AureaQuant"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        d = BASE_DIR / ".cache"
        d.mkdir(parents=True, exist_ok=True)
    return d


def bootstrap_demo_state(target_path: Union[str, Path] = STATE_FILE) -> Path:
    """
    Garante que o arquivo de estado exista na inicialização.
    Se user_state.json não existir, copia automaticamente user_state_demo.json.
    """
    target = Path(target_path)
    if not target.exists():
        demo_candidate = Path(DEMO_STATE_FILE) if Path(DEMO_STATE_FILE).exists() else target.parent / "user_state_demo.json"
        if not demo_candidate.exists():
            demo_candidate = BASE_DIR / "user_state_demo.json"
        if demo_candidate.exists():
            try:
                shutil.copy2(demo_candidate, target)
            except Exception as e:
                print(f"[Aviso] Falha ao copiar demo state para {target}: {e}")
                return demo_candidate
    return target


def load_user_state(filepath: Union[str, Path] = STATE_FILE) -> Dict[str, Any]:
    """Carrega user_state.json garantindo schema completo e campos fiscais/reserva/histórico."""
    padrao: Dict[str, Any] = {
        "orcamento": {"receitas": [], "gastos_fixos": [], "gastos_variaveis": [], "despesas_anuais": []},
        "renda_fixa": [],
        "renda_variavel": [],
        "historico_patrimonial_mensal": [],
        "prejuizo_acumulado_acoes_etfs": 0.0,
        "prejuizo_acumulado_fiis": 0.0,
        "configuracoes": {"alerta_rsi_limite": 30.0, "meta_meses_reserva": 6},
    }
    target = bootstrap_demo_state(filepath)

    if target.exists():
        for tentativa in range(5):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                if isinstance(dados, dict):
                    padrao.update(dados)
                    orc_loaded = dict(dados.get("orcamento") or {})
                    orc_loaded.setdefault("receitas", [])
                    orc_loaded.setdefault("gastos_fixos", [])
                    orc_loaded.setdefault("gastos_variaveis", [])
                    orc_loaded.setdefault("despesas_anuais", [])
                    padrao["orcamento"] = orc_loaded
                    padrao["historico_patrimonial_mensal"] = list(dados.get("historico_patrimonial_mensal") or [])
                    padrao["prejuizo_acumulado_acoes_etfs"] = float(dados.get("prejuizo_acumulado_acoes_etfs", 0.0) or 0.0)
                    padrao["prejuizo_acumulado_fiis"] = float(dados.get("prejuizo_acumulado_fiis", 0.0) or 0.0)
                    cfg = {"alerta_rsi_limite": 30.0, "meta_meses_reserva": 6}
                    if isinstance(dados.get("configuracoes"), dict):
                        cfg.update(dados["configuracoes"])
                    padrao["configuracoes"] = cfg
                    return padrao
            except (json.JSONDecodeError, PermissionError, OSError) as e:
                if tentativa == 4:
                    print(f"[Aviso] Falha ao ler estado do usuário em {target} após 5 tentativas: {e}")
                time.sleep(0.1 * (tentativa + 1))

        # Fallback de segurança: último backup válido se arquivo principal estiver inacessível
        try:
            backup_root = Path(BACKUP_DIR)
            if backup_root.exists():
                backups = sorted(backup_root.glob("user_state_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                for b in backups[:3]:
                    try:
                        with open(b, "r", encoding="utf-8") as fb:
                            dados_bkp = json.load(fb)
                        if isinstance(dados_bkp, dict) and (dados_bkp.get("renda_variavel") or dados_bkp.get("orcamento")):
                            padrao.update(dados_bkp)
                            return padrao
                    except Exception:
                        pass
        except Exception:
            pass
    return padrao


def obter_taxa_ir_renda_fixa(dias_corridos: int = 365) -> float:
    """Retorna a alíquota de IR regressivo com base no prazo em dias corridos."""
    for limite_dias, aliquota in IR_RENDA_FIXA_TABELA:
        if dias_corridos <= limite_dias:
            return float(aliquota)
    return 0.15


def validar_dados_yfinance(df_ativos: pd.DataFrame) -> pd.DataFrame:
    """
    Validador de Qualidade (SanityGate):
    Marca a coluna `status_auditoria` como 'Suspeito' se:
      - DY > 0.20 (20% na escala decimal ou > 20.0 na escala percentual)
      - OU P/L < 2.0 (para ações; FIIs não possuem P/L contábil)
      - OU P/VP < 0.30
    Ativos marcados como 'Suspeito' não podem assumir o Top 3 do ranking automaticamente.
    """
    if df_ativos is None or df_ativos.empty:
        if df_ativos is not None:
            df_vazio = df_ativos.copy()
            df_vazio["status_auditoria"] = pd.Series(dtype="str")
            return df_vazio
        return pd.DataFrame(columns=["status_auditoria"])

    df = df_ativos.copy()

    # Localiza colunas equivalentes de DY, P/L e P/VP
    col_dy = next((c for c in ["dy", "dy_anual_pct", "dy_projetado", "DY"] if c in df.columns), None)
    col_pl = next((c for c in ["pl", "P/L", "pe"] if c in df.columns), None)
    col_pvp = next((c for c in ["pvp", "P/VP", "p_vp"] if c in df.columns), None)
    col_tipo = next((c for c in ["tipo", "classe", "setor"] if c in df.columns), None)

    status_lista: List[str] = []

    for _, row in df.iterrows():
        suspeito = False

        # 1. Verificação de Dividend Yield > 20% (suporta fração 0.20 ou percentual 20.0)
        if col_dy is not None:
            val_dy = row.get(col_dy)
            try:
                dy_num = float(val_dy) if val_dy is not None and not pd.isna(val_dy) else 0.0
                # Se dy_num > 1.0, está em percentual (ex: 22.5 = 22.5%); caso contrário, fração (ex: 0.225)
                dy_frac = (dy_num / 100.0) if dy_num > 1.0 else dy_num
                if dy_frac > 0.20:
                    suspeito = True
            except (ValueError, TypeError):
                suspeito = True

        # Identifica se a linha é FII (FIIs não reportam LPA/PL tradicional)
        is_fii = False
        if col_tipo is not None and row.get(col_tipo) is not None:
            tipo_str = str(row.get(col_tipo)).upper()
            if "FII" in tipo_str or "IMOBILI" in tipo_str:
                is_fii = True

        # 2. Verificação de P/L < 2.0
        if col_pl is not None and not is_fii:
            val_pl = row.get(col_pl)
            if val_pl is not None and not pd.isna(val_pl):
                try:
                    pl_num = float(val_pl)
                    if pl_num < 2.0:
                        suspeito = True
                except (ValueError, TypeError):
                    suspeito = True

        # 3. Verificação de P/VP < 0.30
        if col_pvp is not None:
            val_pvp = row.get(col_pvp)
            if val_pvp is not None and not pd.isna(val_pvp):
                try:
                    pvp_num = float(val_pvp)
                    if pvp_num < 0.30:
                        suspeito = True
                except (ValueError, TypeError):
                    suspeito = True

        status_lista.append("Suspeito" if suspeito else "Validado")

    df["status_auditoria"] = status_lista
    return df


def _carregar_macro_cache_local() -> Optional[Dict[str, Any]]:
    """Carrega os últimos indicadores macroeconômicos salvos em macro_cache.json (local)."""
    for caminho in (MACRO_CACHE_FILE, LEGACY_MACRO_CACHE_FILE):
        try:
            if caminho.exists():
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    if isinstance(dados, dict) and "selic" in dados and "cdi" in dados:
                        return dados
        except Exception as e:
            print(f"[Aviso] Falha ao ler cache local {caminho}: {e}")
    return None


def _salvar_macro_cache_local(dados: Dict[str, Any]) -> None:
    """Persiste os indicadores macroeconômicos atualizados no cache local (%LOCALAPPDATA%)."""
    try:
        _atomic_write_json(MACRO_CACHE_FILE, dados)
    except Exception as e:
        print(f"[Aviso] Falha ao salvar cache local {MACRO_CACHE_FILE}: {e}")


_BCB_SESSION: Optional[requests.Session] = None


def _get_bcb_session() -> requests.Session:
    """Retorna uma sessão HTTP persistente com headers de browser para evitar timeouts na API do BCB."""
    global _BCB_SESSION
    if _BCB_SESSION is None:
        _BCB_SESSION = requests.Session()
        _BCB_SESSION.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        })
    return _BCB_SESSION


def buscar_sgs_bcb(codigo_serie: int, fallback: float) -> Tuple[float, bool]:
    """
    Busca o valor mais recente de uma série temporal do SGS/BCB.
    Retorna tupla (valor, sucesso_online). Em caso de Timeout ou falha de rede,
    sinaliza sucesso_online=False para acionamento do cache local.
    """
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados/ultimos/1?formato=json"
    session = _get_bcb_session()
    for tentativa in range(2):
        try:
            resp = session.get(url, timeout=10)
            if resp.status_code == 200 and resp.text:
                dados = resp.json()
                if dados and isinstance(dados, list) and len(dados) > 0:
                    val_str = str(dados[0].get("valor", "")).replace(",", ".")
                    return float(val_str), True
        except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            if tentativa == 0:
                time.sleep(0.3)
                continue
            print(f"[Aviso] Conexão SGS {codigo_serie} falhou na tentativa {tentativa + 1}: {e}")
        except Exception as e:
            print(f"[Aviso] Erro inesperado ao processar SGS {codigo_serie}: {e}")
            break
    return fallback, False


def limpar_cache_macro() -> None:
    """Limpa o cache em memória dos dados macroeconômicos e cotações intradiárias."""
    global _MACRO_CACHE, _YF_INFO_CACHE, _YF_HIST_CACHE
    with _CACHE_LOCK:
        _MACRO_CACHE = {"timestamp": 0.0, "data": None}
        _YF_INFO_CACHE.clear()
        _YF_HIST_CACHE.clear()


def obter_dados_macro(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Retorna os principais indicadores macroeconômicos do BCB:
    - Selic Meta (% a.a.)
    - CDI Anualizado (% a.a.)
    - IPCA 12m (% a.a.)
    - PTAX Venda (R$)
    - CDI Líquido de referência (IR de 15% - longo prazo > 720 dias)
    - Flag `is_cached` (True apenas se offline sem conexão alguma com a API)
    """
    global _MACRO_CACHE
    agora = time.time()
    if force_refresh:
        limpar_cache_macro()

    if _MACRO_CACHE["data"] is not None and (agora - _MACRO_CACHE["timestamp"]) < 1800:
        return _MACRO_CACHE["data"]

    cache_disco = _carregar_macro_cache_local()
    fb_selic = float(cache_disco.get("selic", 13.75)) if cache_disco else 13.75
    fb_cdi = float(cache_disco.get("cdi", 13.65)) if cache_disco else 13.65
    fb_ipca = float(cache_disco.get("ipca_12m", 4.58)) if cache_disco else 4.58
    fb_ptax = float(cache_disco.get("ptax", 5.46)) if cache_disco else 5.46

    selic, ok_selic = buscar_sgs_bcb(SGS_SELIC_META, fallback=fb_selic)
    cdi, ok_cdi = buscar_sgs_bcb(SGS_CDI_DIARIO, fallback=fb_cdi)
    ipca, ok_ipca = buscar_sgs_bcb(SGS_IPCA_12M, fallback=fb_ipca)
    ptax, ok_ptax = buscar_sgs_bcb(SGS_PTAX_VENDA, fallback=fb_ptax)

    # Conexão online se ao menos Selic ou CDI responderam
    conexao_online = (ok_selic or ok_cdi)

    if not conexao_online and cache_disco is not None:
        # Se nenhuma taxa principal respondeu e temos cache local salvo, restaura e marca is_cached=True
        dados_cached = dict(cache_disco)
        dados_cached["is_cached"] = True
        _MACRO_CACHE["data"] = dados_cached
        _MACRO_CACHE["timestamp"] = agora
        return dados_cached

    aliquota_padrao = 0.15
    cdi_liquido_anual = cdi * (1.0 - aliquota_padrao)
    cdi_liquido_mensal = ((1.0 + (cdi_liquido_anual / 100.0)) ** (1.0 / 12.0) - 1.0) * 100.0
    juro_real_anual = (((1.0 + cdi_liquido_anual / 100.0) / (1.0 + ipca / 100.0)) - 1.0) * 100.0

    dados = {
        "selic": round(selic, 2),
        "cdi": round(cdi, 2),
        "ipca_12m": round(ipca, 2),
        "ptax": round(ptax, 4),
        "aliquota_ir_padrao": aliquota_padrao,
        "cdi_liquido_anual": round(cdi_liquido_anual, 2),
        "cdi_liquido_mensal": round(cdi_liquido_mensal, 4),
        "juro_real_anual": round(juro_real_anual, 2),
        "data_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "is_cached": not conexao_online
    }

    _salvar_macro_cache_local(dados)
    _MACRO_CACHE["data"] = dados
    _MACRO_CACHE["timestamp"] = agora
    return dados


def cdi_liquido_por_prazo(cdi_bruto_anual: float, dias_corridos: int, percentual_cdi: float = 100.0) -> float:
    """CDI líquido anual (%) aplicando a alíquota regressiva correta para o prazo."""
    aliquota = obter_taxa_ir_renda_fixa(dias_corridos)
    return round(cdi_bruto_anual * (percentual_cdi / 100.0) * (1.0 - aliquota), 2)


def calcular_rendimento_nubank(
    saldo_atual: float,
    percentual_cdi: float = 100.0,
    dias_corridos: int = 365,
    cdi_anual: Optional[float] = None,
    valor_aplicado: Optional[float] = None
) -> Dict[str, float]:
    """
    Calcula o rendimento das Caixinhas Nubank / Títulos CDI na convenção oficial B3 de 252 dias úteis:
    - Fator_Diario = (1 + CDI_Bruto_Anual) ** (1 / 252) (ajustado pelo % do CDI contratado)
    - IR regressivo (22,5% a 15%) incide exclusivamente sobre o rendimento bruto acumulado
      (modelando o diferimento fiscal real dos juros compostos).
    - Retorna também taxa equivalente mensal líquida (base 21 DU/mês) para comparação com dividendos.
    """
    if cdi_anual is None:
        macro = obter_dados_macro()
        cdi_anual = float(macro["cdi"])

    saldo_f = max(0.0, float(saldo_atual or 0.0))
    pct_cdi_f = max(0.0, float(percentual_cdi or 0.0))
    dias_c = max(1, int(dias_corridos or 1))
    dias_uteis = max(1, int(round(dias_c * (252.0 / 365.0))))

    cdi_bruto_anual = max(0.0, float(cdi_anual) / 100.0)
    fator_diario_base = (1.0 + cdi_bruto_anual) ** (1.0 / 252.0)
    fator_diario = 1.0 + (fator_diario_base - 1.0) * (pct_cdi_f / 100.0)

    aliquota_ir = obter_taxa_ir_renda_fixa(dias_c)

    # Capitalização composta em base 252 até o prazo e incidência de IR apenas sobre o rendimento bruto acumulado
    fator_bruto_periodo = fator_diario ** dias_uteis
    ganho_bruto_unitario = max(0.0, fator_bruto_periodo - 1.0)
    ganho_liquido_unitario = ganho_bruto_unitario * (1.0 - aliquota_ir)
    fator_liquido_periodo = 1.0 + ganho_liquido_unitario

    # Taxas equivalentes líquidas (anual 252 DU e mensal 21 DU) incorporando o diferimento fiscal
    taxa_liquida_anual = (fator_liquido_periodo ** (252.0 / float(dias_uteis))) - 1.0
    taxa_liquida_mensal = (fator_liquido_periodo ** (21.0 / float(dias_uteis))) - 1.0

    # Rendimento bruto acumulado efetivo (se houver valor_aplicado < saldo_atual, usa ganho já acumulado)
    if valor_aplicado is not None and float(valor_aplicado) > 0 and saldo_f > float(valor_aplicado):
        rendimento_bruto_acumulado = round(saldo_f - float(valor_aplicado), 2)
        ir_acumulado = round(rendimento_bruto_acumulado * aliquota_ir, 2)
        rendimento_liquido_acumulado = round(rendimento_bruto_acumulado - ir_acumulado, 2)
        saldo_liquido_resgate = round(saldo_f - ir_acumulado, 2)
    else:
        rendimento_bruto_acumulado = round(saldo_f * ganho_bruto_unitario, 2)
        ir_acumulado = round(rendimento_bruto_acumulado * aliquota_ir, 2)
        rendimento_liquido_acumulado = round(rendimento_bruto_acumulado - ir_acumulado, 2)
        saldo_liquido_resgate = round(saldo_f + rendimento_liquido_acumulado, 2)

    taxa_bruta_mensal = (fator_diario ** 21.0) - 1.0
    rendimento_mensal_bruto = saldo_f * taxa_bruta_mensal
    rendimento_mensal_liquido = saldo_f * taxa_liquida_mensal

    return {
        "saldo_atual": round(saldo_f, 2),
        "percentual_cdi": pct_cdi_f,
        "cdi_anual": float(cdi_anual),
        "dias_corridos": dias_c,
        "dias_uteis": dias_uteis,
        "fator_diario": round(fator_diario, 8),
        "aliquota_ir": aliquota_ir,
        "taxa_liquida_anual_pct": round(taxa_liquida_anual * 100.0, 2),
        "taxa_liquida_mensal_pct": round(taxa_liquida_mensal * 100.0, 4),
        "rendimento_mensal_bruto": round(rendimento_mensal_bruto, 2),
        "rendimento_mensal_liquido": round(rendimento_mensal_liquido, 2),
        "rendimento_bruto_acumulado": rendimento_bruto_acumulado,
        "ir_acumulado": ir_acumulado,
        "rendimento_liquido_acumulado": rendimento_liquido_acumulado,
        "saldo_liquido_resgate": saldo_liquido_resgate,
    }


def _carregar_market_cache_local() -> Dict[str, Any]:
    """Carrega o snapshot offline de cotações, dividendos e múltiplos do market_cache.json (local)."""
    global _MARKET_CACHE_MEM
    if _MARKET_CACHE_MEM is not None:
        return _MARKET_CACHE_MEM
    for caminho in (MARKET_CACHE_FILE, LEGACY_MARKET_CACHE_FILE):
        try:
            if caminho.exists():
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                if isinstance(dados, dict):
                    dados.setdefault("assets", {})
                    dados.setdefault("histories", {})
                    dados.setdefault("updated_at", "")
                    _MARKET_CACHE_MEM = dados
                    return dados
        except Exception as e:
            print(f"[Aviso] Falha ao ler cache local {caminho}: {e}")
    _MARKET_CACHE_MEM = {"updated_at": "", "assets": {}, "histories": {}}
    return _MARKET_CACHE_MEM


def _salvar_market_cache_local(cache_data: Dict[str, Any]) -> None:
    """Persiste atomicamente o snapshot de mercado em market_cache.json."""
    global _MARKET_CACHE_MEM
    try:
        cache_data["updated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        _MARKET_CACHE_MEM = cache_data
        _atomic_write_json(MARKET_CACHE_FILE, cache_data)
    except Exception as e:
        print(f"[Aviso] Falha ao salvar cache local {MARKET_CACHE_FILE}: {e}")


def obter_status_market_cache() -> Dict[str, Any]:
    """Informa à UI se dados de mercado vieram do cache offline (market_cache.json) e a data do snapshot."""
    cache = _carregar_market_cache_local()
    return {
        "usando_cache": bool(_MARKET_CACHE_STATUS.get("usando_cache", False)),
        "data_cache": _MARKET_CACHE_STATUS.get("data_cache") or cache.get("updated_at", ""),
        "ativos_em_cache": len(cache.get("assets", {})),
    }


def sanitizar_dataframe_yf(df: pd.DataFrame) -> pd.DataFrame:
    """
    Corrige colunas MultiIndex do yfinance moderno e garante a presença
    da coluna 'Adj Close' (Preços Ajustados por Proventos) para cálculo do RSI.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df_limpo = df.copy()
    if isinstance(df_limpo.columns, pd.MultiIndex):
        try:
            df_limpo.columns = df_limpo.columns.get_level_values(0)
        except Exception:
            pass

    mapa_colunas = {}
    for c in df_limpo.columns:
        c_str = str(c).strip()
        if c_str.lower() in ("adj close", "adj_close", "adjclose"):
            mapa_colunas[c] = "Adj Close"
        else:
            mapa_colunas[c] = c_str.capitalize()

    df_limpo = df_limpo.rename(columns=mapa_colunas)

    if "Adj Close" not in df_limpo.columns and "Close" in df_limpo.columns:
        df_limpo["Adj Close"] = df_limpo["Close"]

    return df_limpo


def baixar_historico_multiplo(
    tickers: List[str],
    periodo: str = "1y",
    intervalo: str = "1d"
) -> Dict[str, pd.DataFrame]:
    """
    Baixa histórico de múltiplos ativos em lote vetorizado (`yf.download(..., period="1y", group_by="ticker", threads=True)`)
    com auto_adjust=False para preservar explicitamente a coluna 'Adj Close' (ajustada por dividendos/JCP),
    e fallback automático offline via market_cache.json em caso de falha ou rate-limit.
    """
    if not tickers:
        return {}

    tickers_formatados = list(dict.fromkeys([t if t.endswith(".SA") or "^" in t else f"{t}.SA" for t in tickers]))
    agora = time.time()
    chave_hist = (tuple(sorted(tickers_formatados)), periodo, intervalo)

    with _CACHE_LOCK:
        cached_mem = _YF_HIST_CACHE.get(chave_hist)
        if cached_mem and (agora - float(cached_mem.get("timestamp", 0.0))) < TTL_COTACAO_SEGUNDOS:
            return cached_mem["data"]

    resultado: Dict[str, pd.DataFrame] = {}

    try:
        dados_brutos = yf.download(
            tickers=tickers_formatados,
            period=periodo,
            interval=intervalo,
            group_by="ticker",
            threads=True,
            progress=False,
            auto_adjust=False
        )

        if dados_brutos is not None and not dados_brutos.empty:
            for ticker in tickers_formatados:
                ticker_curto = ticker.replace(".SA", "")
                if isinstance(dados_brutos.columns, pd.MultiIndex):
                    if ticker in dados_brutos.columns.levels[0]:
                        df_ticker = dados_brutos[ticker].dropna(how="all").copy()
                    elif ticker_curto in dados_brutos.columns.levels[0]:
                        df_ticker = dados_brutos[ticker_curto].dropna(how="all").copy()
                    else:
                        df_ticker = dados_brutos.copy()
                        if isinstance(df_ticker.columns, pd.MultiIndex):
                            df_ticker.columns = df_ticker.columns.get_level_values(0)
                else:
                    df_ticker = dados_brutos.copy()

                df_ticker = sanitizar_dataframe_yf(df_ticker)
                if not df_ticker.empty and ("Adj Close" in df_ticker.columns or "Close" in df_ticker.columns):
                    resultado[ticker] = df_ticker
                    resultado[ticker_curto] = df_ticker

    except Exception as e:
        print(f"[Erro] Falha no download em lote do yfinance: {e}")

    cache = _carregar_market_cache_local()
    histories_cache = cache.setdefault("histories", {})

    if resultado:
        houve_novo_hist = False
        for ticker in tickers_formatados:
            ticker_curto = ticker.replace(".SA", "")
            df_t = resultado.get(ticker_curto)
            if df_t is not None and not df_t.empty:
                try:
                    df_tail = df_t.tail(260)
                    col_adj = "Adj Close" if "Adj Close" in df_tail.columns else "Close"
                    col_cls = "Close" if "Close" in df_tail.columns else col_adj
                    dates_list = [idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx) for idx in df_tail.index]
                    adj_vals = [round(float(x), 4) if pd.notna(x) else None for x in df_tail[col_adj]]
                    cls_vals = [round(float(x), 4) if pd.notna(x) else None for x in df_tail[col_cls]]
                    histories_cache[ticker_curto] = {
                        "dates": dates_list,
                        "adj_close": adj_vals,
                        "close": cls_vals,
                        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "quote_ts": agora,
                    }
                    houve_novo_hist = True
                except Exception:
                    pass
        if houve_novo_hist:
            _salvar_market_cache_local(cache)

    # Fallback para ativos que falharam no download em lote ou quando totalmente offline
    for ticker in tickers_formatados:
        ticker_curto = ticker.replace(".SA", "")
        if ticker_curto not in resultado and ticker_curto in histories_cache:
            h_item = histories_cache[ticker_curto]
            try:
                idx = pd.to_datetime(h_item.get("dates", []))
                df_rec = pd.DataFrame({
                    "Adj Close": h_item.get("adj_close", []),
                    "Close": h_item.get("close", []),
                }, index=idx).dropna()
                if not df_rec.empty:
                    resultado[ticker] = df_rec
                    resultado[ticker_curto] = df_rec
                    _MARKET_CACHE_STATUS["usando_cache"] = True
                    _MARKET_CACHE_STATUS["data_cache"] = h_item.get("updated_at") or cache.get("updated_at", "")
            except Exception:
                pass

    if resultado:
        with _CACHE_LOCK:
            _YF_HIST_CACHE[chave_hist] = {"timestamp": agora, "data": resultado}

    return resultado


def _extrair_dividendos_anuais_3_5_anos(ativo: yf.Ticker, div_12m_fallback: float) -> Tuple[List[float], Dict[str, Any]]:
    """
    Extrai a soma anual de proventos pagos nos últimos 3 a 5 anos para cálculo
    da Mediana de Bazin e analisa a estabilidade dos últimos 12 meses (para FIIs).
    """
    metricas_12m: Dict[str, Any] = {"qtd_pagamentos_12m": 0, "cv_12m": None, "estabilidade_score": 70.0}
    try:
        divs = ativo.dividends
        if divs is not None and not divs.empty:
            df_div = divs.to_frame(name="valor")
            df_div["ano"] = df_div.index.year
            ano_atual = datetime.now().year

            # Análise de consistência dos últimos 12 meses (365 dias)
            try:
                ultimo_ts = df_div.index.max()
                corte_12m = ultimo_ts - pd.Timedelta(days=366)
                divs_12m = df_div[df_div.index >= corte_12m]["valor"].astype(float)
                divs_12m = divs_12m[divs_12m > 0]
                qtd_12m = int(len(divs_12m))
                metricas_12m["qtd_pagamentos_12m"] = qtd_12m
                if qtd_12m >= 3 and divs_12m.mean() > 0:
                    cv = float(divs_12m.std(ddof=0) / divs_12m.mean())
                    metricas_12m["cv_12m"] = round(cv, 3)
                    # Quanto menor a oscilação e mais próximo de 12 pagamentos/ano, maior a estabilidade
                    nota_freq = min(50.0, (min(qtd_12m, 12) / 12.0) * 50.0)
                    nota_cv = max(0.0, 50.0 * (1.0 - min(cv, 0.80) / 0.80))
                    metricas_12m["estabilidade_score"] = round(nota_freq + nota_cv, 1)
                elif qtd_12m >= 1:
                    metricas_12m["estabilidade_score"] = 55.0
            except Exception:
                pass

            # Filtra os últimos 5 anos (incluindo anos fechados recentes)
            df_recente = df_div[(df_div["ano"] >= ano_atual - 5) & (df_div["ano"] <= ano_atual)]
            if not df_recente.empty:
                somas_anuais = df_recente.groupby("ano")["valor"].sum().tolist()
                if len(somas_anuais) >= 3:
                    return [round(float(x), 4) for x in somas_anuais[-5:]], metricas_12m
    except Exception:
        pass
    return ([round(float(div_12m_fallback), 4)] if div_12m_fallback > 0 else []), metricas_12m


def obter_info_ativo(ticker: str, persist_cache: bool = True) -> Dict[str, Any]:
    """
    Obtém indicadores fundamentalistas, cotação e histórico de proventos (3-5 anos)
    de um ativo da B3 via yfinance, com cache persistente em market_cache.json e TTL separado:
    - Cotações expiram em 30 minutos (`TTL_COTACAO_SEGUNDOS` = 1800s).
    - Múltiplos fundamentalistas e histórico de dividendos expiram em 24 horas (`TTL_FUNDAMENTOS_SEGUNDOS` = 86400s).
    """
    ticker_str = str(ticker or "").strip().upper()
    ticker_yf = ticker_str if ticker_str.endswith(".SA") or "^" in ticker_str else f"{ticker_str}.SA"
    agora = time.time()

    with _CACHE_LOCK:
        if ticker_yf in _YF_INFO_CACHE and (agora - _YF_INFO_CACHE[ticker_yf]["timestamp"]) < TTL_COTACAO_SEGUNDOS:
            return _YF_INFO_CACHE[ticker_yf]["data"]

    cache = _carregar_market_cache_local()
    cached_entry = cache.get("assets", {}).get(ticker_yf)

    # Verifica se tanto a cotação (< 30m) quanto os fundamentos (< 24h) estão válidos no market_cache.json
    quote_fresca = False
    fundamentos_frescos = False
    if cached_entry and float(cached_entry.get("cotacao", 0.0) or 0.0) > 0.0:
        q_ts = float(cached_entry.get("quote_ts", 0.0) or 0.0)
        f_ts = float(cached_entry.get("fundamentals_ts", 0.0) or 0.0)
        quote_fresca = (agora - q_ts) < TTL_COTACAO_SEGUNDOS
        fundamentos_frescos = (agora - f_ts) < TTL_FUNDAMENTOS_SEGUNDOS
        if quote_fresca and fundamentos_frescos:
            dados_ok = dict(cached_entry)
            dados_ok["is_cached"] = False
            with _CACHE_LOCK:
                _YF_INFO_CACHE[ticker_yf] = {"timestamp": agora, "data": dados_ok}
            return dados_ok

    dados_padrao: Dict[str, Any] = {
        "ticker": ticker_str.replace(".SA", ""),
        "ticker_yf": ticker_yf,
        "cotacao": 0.0,
        "variacao_dia": 0.0,
        "pl": 0.0,
        "pvp": 0.0,
        "dy": 0.0,
        "lpa": 0.0,
        "vpa": 0.0,
        "roe": 0.0,
        "liquidez_corrente": 0.0,
        "margem_liquida": 0.0,
        "divida_liquida_ebitda": None,
        "payout_ratio": None,
        "crescimento_lucro_pct": None,
        "volume_medio_diario": 0.0,
        "estabilidade_dividendos_score": 70.0,
        "qtd_pagamentos_12m": 0,
        "dividendos_anuais_3_5a": [],
        "nome": ticker_str.replace(".SA", ""),
        "setor": "Indefinido",
        "min_52sem": 0.0,
        "max_52sem": 0.0,
        "is_cached": False,
        "data_atualizacao": "",
        "quote_ts": 0.0,
        "fundamentals_ts": 0.0,
    }

    def limpa_num(v: Any) -> float:
        if v is None:
            return 0.0
        try:
            f = float(v)
            if np.isnan(f) or np.isinf(f):
                return 0.0
            return f
        except (ValueError, TypeError):
            return 0.0

    sucesso_online = False
    try:
        ativo = yf.Ticker(ticker_yf)
        fast_info = getattr(ativo, "fast_info", None)

        # Se os fundamentos (< 24h) já estão frescos no cache, atualiza apenas a cotação intradiária!
        if fundamentos_frescos and cached_entry:
            cotacao_fast = (fast_info.last_price if fast_info and hasattr(fast_info, "last_price") else 0.0) or 0.0
            fech_ant_fast = (fast_info.previous_close if fast_info and hasattr(fast_info, "previous_close") else 0.0) or 0.0
            cotacao_limpa = round(limpa_num(cotacao_fast), 2)
            if cotacao_limpa > 0.0:
                sucesso_online = True
                variacao = ((cotacao_limpa / float(fech_ant_fast)) - 1.0) * 100.0 if fech_ant_fast and float(fech_ant_fast) > 0 else float(cached_entry.get("variacao_dia", 0.0))
                dados_padrao.update(cached_entry)
                dados_padrao.update({
                    "cotacao": cotacao_limpa,
                    "variacao_dia": round(limpa_num(variacao), 2),
                    "is_cached": False,
                    "data_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "quote_ts": agora,
                })
                with _CACHE_LOCK:
                    cache.setdefault("assets", {})[ticker_yf] = dict(dados_padrao)
                    _YF_INFO_CACHE[ticker_yf] = {"timestamp": agora, "data": dados_padrao}
                if persist_cache:
                    _salvar_market_cache_local(cache)
                return dados_padrao

        info = ativo.info or {}

        cotacao = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or (fast_info.last_price if fast_info and hasattr(fast_info, "last_price") else 0.0)
            or 0.0
        )

        cotacao_limpa = round(limpa_num(cotacao), 2)
        if cotacao_limpa > 0.0:
            sucesso_online = True

            fech_anterior = info.get("regularMarketPreviousClose") or info.get("previousClose") or 0.0
            if fech_anterior and float(fech_anterior) > 0:
                variacao = ((float(cotacao_limpa) / float(fech_anterior)) - 1.0) * 100.0
            else:
                variacao = float(info.get("regularMarketChangePercent") or 0.0)

            pl = info.get("trailingPE") or info.get("forwardPE") or 0.0
            pvp = info.get("priceToBook") or 0.0

            div_12m = float(info.get("trailingAnnualDividendRate") or 0.0)
            if div_12m and cotacao_limpa > 0:
                dy = (div_12m / float(cotacao_limpa)) * 100.0
            elif info.get("trailingAnnualDividendYield"):
                dy = float(info.get("trailingAnnualDividendYield")) * 100.0
            else:
                dy = float(info.get("dividendYield") or 0.0)

            if dy < 0 or dy > 45.0:
                dy = 0.0

            if div_12m <= 0 and dy > 0 and cotacao_limpa > 0:
                div_12m = float(cotacao_limpa) * (dy / 100.0)

            lpa = info.get("trailingEps") or 0.0
            vpa = info.get("bookValue") or 0.0

            divs_historico, metricas_12m = _extrair_dividendos_anuais_3_5_anos(ativo, div_12m)

            ebitda_val = limpa_num(info.get("ebitda"))
            debt_val = limpa_num(info.get("totalDebt"))
            cash_val = limpa_num(info.get("totalCash"))
            dl_ebitda = round((debt_val - cash_val) / ebitda_val, 2) if ebitda_val > 0 else None

            payout_raw = info.get("payoutRatio")
            payout_ratio = round(limpa_num(payout_raw), 4) if payout_raw is not None and limpa_num(payout_raw) > 0 else None

            eg_raw = info.get("earningsGrowth") if info.get("earningsGrowth") is not None else info.get("earningsQuarterlyGrowth")
            crescimento_lucro_pct = round(limpa_num(eg_raw) * 100.0, 2) if eg_raw is not None else None

            avg_vol_shares = limpa_num(info.get("averageVolume") or info.get("averageDailyVolume10Day") or 0.0)
            volume_fin_diario = round(avg_vol_shares * cotacao_limpa, 2)

            ts_agora = datetime.now().strftime("%d/%m/%Y %H:%M")

            dados_padrao.update({
                "cotacao": cotacao_limpa,
                "variacao_dia": round(limpa_num(variacao), 2),
                "pl": round(limpa_num(pl), 2),
                "pvp": round(limpa_num(pvp), 2),
                "dy": round(limpa_num(dy), 2),
                "lpa": round(limpa_num(lpa), 2),
                "vpa": round(limpa_num(vpa), 2),
                "nome": info.get("shortName") or info.get("longName") or ticker_str.replace(".SA", ""),
                "setor": info.get("sector") or "B3",
                "min_52sem": round(limpa_num(info.get("fiftyTwoWeekLow")), 2),
                "max_52sem": round(limpa_num(info.get("fiftyTwoWeekHigh")), 2),
                "roe": round(limpa_num((info.get("returnOnEquity") or 0.0) * 100.0), 2),
                "liquidez_corrente": round(limpa_num(info.get("currentRatio")), 2),
                "margem_liquida": round(limpa_num((info.get("profitMargins") or 0.0) * 100.0), 2),
                "divida_patrimonio": round(limpa_num(info.get("debtToEquity")), 2),
                "ebitda": ebitda_val,
                "total_debt": debt_val,
                "total_cash": cash_val,
                "divida_liquida_ebitda": dl_ebitda,
                "payout_ratio": payout_ratio,
                "crescimento_lucro_pct": crescimento_lucro_pct,
                "volume_medio_diario": volume_fin_diario,
                "estabilidade_dividendos_score": metricas_12m.get("estabilidade_score", 70.0),
                "qtd_pagamentos_12m": metricas_12m.get("qtd_pagamentos_12m", 0),
                "dividendos_anuais_3_5a": divs_historico,
                "is_cached": False,
                "data_atualizacao": ts_agora,
                "quote_ts": agora,
                "fundamentals_ts": agora,
            })

            with _CACHE_LOCK:
                cache.setdefault("assets", {})[ticker_yf] = dict(dados_padrao)
            if persist_cache:
                _salvar_market_cache_local(cache)

    except Exception as e:
        print(f"[Aviso] Não foi possível obter info completa de {ticker_yf}: {e}")

    if not sucesso_online:
        if cached_entry and float(cached_entry.get("cotacao", 0.0) or 0.0) > 0.0:
            dados_fallback = dict(cached_entry)
            dados_fallback["is_cached"] = True
            ts_cache = cached_entry.get("data_atualizacao") or cache.get("updated_at", "")
            _MARKET_CACHE_STATUS["usando_cache"] = True
            _MARKET_CACHE_STATUS["data_cache"] = ts_cache
            with _CACHE_LOCK:
                _YF_INFO_CACHE[ticker_yf] = {"timestamp": agora, "data": dados_fallback}
            return dados_fallback

    with _CACHE_LOCK:
        _YF_INFO_CACHE[ticker_yf] = {"timestamp": agora, "data": dados_padrao}
    return dados_padrao


def obter_infos_multiplos(tickers: List[str], max_workers: int = 8) -> Dict[str, Dict[str, Any]]:
    """
    Busca em paralelo (`ThreadPoolExecutor(max_workers=8)`) os dados fundamentalistas e cotações
    de uma lista de ativos, persistindo `market_cache.json` uma única vez ao final do lote.
    """
    if not tickers:
        return {}

    tickers_limpos = list(dict.fromkeys([str(t or "").replace(".SA", "").strip().upper() for t in tickers if t]))
    resultados: Dict[str, Dict[str, Any]] = {}

    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(tickers_limpos)))) as executor:
        futuros = {executor.submit(obter_info_ativo, t, False): t for t in tickers_limpos}
        for fut in as_completed(futuros):
            t_key = futuros[fut]
            try:
                info_res = fut.result()
                resultados[t_key] = info_res
                resultados[f"{t_key}.SA"] = info_res
            except Exception as e:
                print(f"[Aviso] Erro no worker paralelo para {t_key}: {e}")

    try:
        cache = _carregar_market_cache_local()
        _salvar_market_cache_local(cache)
    except Exception:
        pass

    return resultados
