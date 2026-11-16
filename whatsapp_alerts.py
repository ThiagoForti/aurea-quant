"""
Módulo de Disparos de Alertas via WhatsApp (pywhatkit + webhook/simulador)
Envia notificações estruturadas quando oportunidades de RSI ou assimetrias de notícias são detectadas.
"""
import time
import requests
from typing import Dict, Any, Optional

try:
    import pywhatkit as pwk
    PYWHATKIT_AVAILABLE = True
except Exception:
    PYWHATKIT_AVAILABLE = False


def formatar_mensagem_alerta(
    tipo: str,
    dados: Dict[str, Any]
) -> str:
    """Formata o texto do alerta com emojis, métricas e instruções claras."""
    if tipo == "scanner":
        msg = (
            f"🚨 *[ALERTA QUANT INVESTIMENTO B3]* 🚨\n\n"
            f"🎯 *Oportunidade Técnica Detectada!*\n"
            f"• *Ativo:* {dados.get('ticker')} ({dados.get('nome', '')})\n"
            f"• *Setor:* {dados.get('tipo_setor', 'B3')}\n"
            f"• *Cotação Atual:* R$ {dados.get('cotacao', 0.0):.2f}\n"
            f"• *Variação no Dia:* {dados.get('variacao_dia_pct', 0.0):+.2f}%\n"
            f"• *RSI (14):* {dados.get('rsi_14', 0.0):.1f} (Sobrevenda)\n"
            f"• *Distância MM200:* {dados.get('distancia_mm200_pct', 0.0):+.1f}%\n"
            f"• *Severidade:* {dados.get('severidade', '⚠️ MÉDIA')}\n"
            f"• *Motivos:* {dados.get('motivos', '')}\n\n"
            f"💡 *Ação Sugerida:* Avaliar aporte no rebalanceamento inteligente da carteira."
        )
    elif tipo == "noticia":
        msg = (
            f"🧠 *[RADAR SECOND-ORDER THINKING]* 🧠\n\n"
            f"🎯 *Janela de Assimetria Aberta!*\n"
            f"• *Notícia:* {dados.get('titulo', '')}\n"
            f"• *Fato (1ª Ordem):* {dados.get('fato_1a_ordem', '')}\n"
            f"• *Transmissão (2ª Ordem):* {dados.get('consequencia_2a_ordem', '')}\n"
            f"• *Tese B3 (3ª Ordem):* {dados.get('tese_3a_ordem', '')}\n"
            f"• *Ativo Alvo:* {dados.get('ticker_alvo', '')} (Cotação: R$ {dados.get('cotacao_atual', 0.0):.2f})\n"
            f"• *Variação no Dia:* {dados.get('variacao_dia_pct', 0.0):+.2f}%\n"
            f"• *Status:* {dados.get('status_assimetria', '')}\n\n"
            f"💡 *Oportunidade:* O ativo ainda não precificou os desdobramentos de segunda ordem."
        )
    else:
        msg = f"🔔 *[NOTIFICAÇÃO CARTEIRA B3]*\n\n{str(dados)}"

    return msg


def enviar_alerta_whatsapp(
    numero_destino: str,
    mensagem: str,
    modo_simulacao: bool = False,
    webhook_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Envia a notificação via WhatsApp.
    - Se houver webhook cadastrado, envia payload via HTTP POST.
    - Se modo_simulacao=False e pywhatkit disponível, dispara via pywhatkit.
    - Se em modo simulação, apenas valida o número e formata a mensagem com sucesso.
    """
    if not numero_destino or len(numero_destino.replace(" ", "").replace("-", "")) < 10:
        return {
            "sucesso": False,
            "mensagem": "Número de WhatsApp inválido ou não informado. Use o formato internacional (ex: +5511999999999)."
        }

    # Limpar formatação
    numero_limpo = numero_destino.strip()
    if not numero_limpo.startswith("+"):
        numero_limpo = f"+{numero_limpo}"

    # Envio via Webhook (se configurado, ex: Zapier, n8n, Evolution API, Twilio)
    if webhook_url:
        try:
            resp = requests.post(webhook_url, json={"numero": numero_limpo, "mensagem": mensagem}, timeout=8)
            if resp.status_code in [200, 201, 202]:
                return {"sucesso": True, "canal": "Webhook", "mensagem": "Alerta enviado via Webhook com sucesso!"}
        except Exception as e:
            print(f"[Aviso] Falha ao disparar webhook: {e}")

    if modo_simulacao or not PYWHATKIT_AVAILABLE:
        return {
            "sucesso": True,
            "canal": "Simulador / Log",
            "numero": numero_limpo,
            "preview_mensagem": mensagem,
            "mensagem": f"✅ Mensagem simulada e validada com sucesso para {numero_limpo}."
        }

    # Envio real via pywhatkit
    try:
        # Envia instantaneamente (abre aba rápida ou com delay controlado de 15 segundos)
        pwk.sendwhatmsg_instantly(
            phone_no=numero_limpo,
            message=mensagem,
            wait_time=15,
            tab_close=True,
            close_time=4
        )
        return {
            "sucesso": True,
            "canal": "pywhatkit",
            "numero": numero_limpo,
            "mensagem": f"Disparo executado via pywhatkit para {numero_limpo}."
        }
    except Exception as e:
        return {
            "sucesso": False,
            "canal": "pywhatkit",
            "erro": str(e),
            "mensagem": f"Falha no envio via pywhatkit: {e}. (Verifique se o WhatsApp Web está conectado no navegador)."
        }
