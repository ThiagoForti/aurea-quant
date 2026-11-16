"""
Motor Educacional e Metodologias do Sistema - Terminal Quant B3
Carrega sob demanda o acervo de 31 estudos diários e o glossário de metodologias
a partir do arquivo estruturado `estudos_diarios.json`, reduzindo drasticamente
a pegada de memória na inicialização do aplicativo.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

ESTUDOS_JSON_FILE = Path(__file__).resolve().parent / "estudos_diarios.json"
_ACERVO_CACHE: Optional[Dict[str, List[Dict[str, Any]]]] = None


def carregar_acervo_educacional() -> Dict[str, List[Dict[str, Any]]]:
    """Carrega e mantém em cache leve o conteúdo de `estudos_diarios.json` sob demanda."""
    global _ACERVO_CACHE
    if _ACERVO_CACHE is not None:
        return _ACERVO_CACHE

    try:
        with open(ESTUDOS_JSON_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(dados, dict):
            _ACERVO_CACHE = {
                "estudos_diarios": list(dados.get("estudos_diarios", [])),
                "glossario": list(dados.get("glossario", [])),
            }
            return _ACERVO_CACHE
    except Exception as e:
        print(f"[Aviso] Falha ao carregar {ESTUDOS_JSON_FILE}: {e}")

    _ACERVO_CACHE = {"estudos_diarios": [], "glossario": []}
    return _ACERVO_CACHE


def obter_lista_estudos_diarios() -> List[Dict[str, Any]]:
    """Retorna a lista completa dos 31 estudos diários."""
    return carregar_acervo_educacional().get("estudos_diarios", [])


def obter_estudo_do_dia(dia_especifico: Optional[int] = None) -> Dict[str, Any]:
    """
    Retorna a pílula de conhecimento correspondente ao dia do mês (1 a 31)
    ou ao dia específico selecionado pelo usuário.
    """
    estudos = obter_lista_estudos_diarios()
    if not estudos:
        return {
            "dia": 1,
            "titulo": "Estudo Indisponível",
            "autor": "Aurea Quant",
            "categoria": "Educação",
            "tempo_leitura": "1 min",
            "resumo": "Acervo educacional não encontrado.",
            "texto_completo": "Verifique o arquivo estudos_diarios.json.",
            "licao_pratica": "",
            "link": "https://www.b3.com.br/",
        }

    if dia_especifico is not None and 1 <= int(dia_especifico) <= len(estudos):
        return estudos[int(dia_especifico) - 1]

    dia_atual = datetime.now().day
    indice = (dia_atual - 1) % len(estudos)
    return estudos[indice]


def obter_glossario_conceitos() -> List[Dict[str, str]]:
    """
    Retorna um dicionário estruturado explicando passo a passo TODAS as metodologias
    e fórmulas matemáticas utilizadas no sistema.
    """
    return carregar_acervo_educacional().get("glossario", [])


def __getattr__(name: str) -> Any:
    """Compatibilidade retroativa lazy para `ESTUDOS_DIARIOS`."""
    if name == "ESTUDOS_DIARIOS":
        return obter_lista_estudos_diarios()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
