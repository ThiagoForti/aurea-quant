"""
Módulo de Orçamento Pessoal e Capacidade de Aporte (CFP Standard)
Gerenciamento de receitas, gastos fixos, gastos variáveis, provisão de despesas anuais/sazonais
e desacoplamento inteligente entre Fixo/Variável e a Regra 50/30/20.
"""
from typing import Dict, List, Any

CATEGORIAS_CFP_VALIDAS = ("Essencial (50%)", "Estilo de Vida (30%)")

_KEYWORDS_ESTILO_VIDA = (
    "lazer", "restaurante", "delivery", "ifood", "streaming", "netflix",
    "spotify", "viagem", "viagens", "compras", "vestuário", "vestuario",
    "hobby", "bar", "festa", "estética", "estetica", "clube", "jogos", "cinema",
)

_KEYWORDS_ESSENCIAIS = (
    "moradia", "aluguel", "condomínio", "condominio", "saúde", "saude",
    "farmácia", "farmacia", "energia", "água", "agua", "luz", "gás", "gas",
    "internet", "utilidades", "alimentação", "alimentacao", "supermercado",
    "mercado", "feira", "transporte", "combustível", "combustivel",
    "seguro", "ipva", "iptu", "educação", "educacao", "escola", "faculdade",
)


def inferir_categoria_cfp(item: Dict[str, Any], eh_fixo: bool = True) -> str:
    """
    Infere ou normaliza a classificação CFP 50/30/20 de um item de despesa:
    - 'Essencial (50%)' (ex: Moradia, Saúde, Utilidades, Alimentação/Supermercado, Transporte, Educação)
    - 'Estilo de Vida (30%)' (ex: Lazer, Restaurantes, Delivery, Streaming, Viagens, Compras)
    Permite que um gasto variável (como Supermercado ou Luz) seja classificado como Essencial (50%),
    e um gasto fixo (como Streaming/Clube) seja classificado como Estilo de Vida (30%).
    """
    cat_explicit = str(item.get("categoria_cfp", "") or "").strip()
    if cat_explicit:
        if "essencial" in cat_explicit.lower() or "50" in cat_explicit:
            return "Essencial (50%)"
        if "estilo" in cat_explicit.lower() or "desejo" in cat_explicit.lower() or "30" in cat_explicit:
            return "Estilo de Vida (30%)"

    texto = f"{item.get('nome', '')} {item.get('categoria', '')}".strip().lower()
    if any(k in texto for k in _KEYWORDS_ESTILO_VIDA):
        return "Estilo de Vida (30%)"
    if any(k in texto for k in _KEYWORDS_ESSENCIAIS):
        return "Essencial (50%)"

    return "Essencial (50%)" if eh_fixo else "Estilo de Vida (30%)"


def calcular_orcamento(dados_orcamento: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula os totais e indicadores de saúde financeira do orçamento pessoal:
    - Desacopla Gastos Fixos/Variáveis da Regra 50/30/20 via `categoria_cfp`.
    - Calcula o Carimbo Mensal de Provisão (`Valor Anual / 12`) para Despesas Anuais & Sazonais
      e deduz antes de apurar a Sobra Líquida para investimentos.
    """
    receitas = dados_orcamento.get("receitas", [])
    gastos_fixos_raw = dados_orcamento.get("gastos_fixos", [])
    gastos_variaveis_raw = dados_orcamento.get("gastos_variaveis", [])
    despesas_anuais_raw = dados_orcamento.get("despesas_anuais", [])

    gastos_fixos: List[Dict[str, Any]] = []
    for item in gastos_fixos_raw:
        it_copy = dict(item)
        it_copy["categoria_cfp"] = inferir_categoria_cfp(it_copy, eh_fixo=True)
        gastos_fixos.append(it_copy)

    gastos_variaveis: List[Dict[str, Any]] = []
    for item in gastos_variaveis_raw:
        it_copy = dict(item)
        it_copy["categoria_cfp"] = inferir_categoria_cfp(it_copy, eh_fixo=False)
        gastos_variaveis.append(it_copy)

    despesas_anuais: List[Dict[str, Any]] = []
    total_despesas_anuais = 0.0
    for item in despesas_anuais_raw:
        it_copy = dict(item)
        val_anual = float(it_copy.get("valor_anual", it_copy.get("valor", 0.0)) or 0.0)
        it_copy["valor_anual"] = round(val_anual, 2)
        it_copy["provisao_mensal"] = round(val_anual / 12.0, 2)
        it_copy.setdefault("vencimento", "Anual/Sazonal")
        total_despesas_anuais += val_anual
        despesas_anuais.append(it_copy)

    total_despesas_anuais = round(total_despesas_anuais, 2)
    provisao_mensal_anual = round(total_despesas_anuais / 12.0, 2)

    total_receitas = sum(float(item.get("valor", 0.0) or 0.0) for item in receitas)
    total_fixos = sum(float(item.get("valor", 0.0) or 0.0) for item in gastos_fixos)
    total_variaveis = sum(float(item.get("valor", 0.0) or 0.0) for item in gastos_variaveis)

    # Desacoplamento 50/30/20 real por categoria_cfp
    todos_gastos_mensais = gastos_fixos + gastos_variaveis
    total_essenciais_cfp = sum(
        float(item.get("valor", 0.0) or 0.0)
        for item in todos_gastos_mensais
        if item.get("categoria_cfp") == "Essencial (50%)"
    )
    total_estilo_cfp = sum(
        float(item.get("valor", 0.0) or 0.0)
        for item in todos_gastos_mensais
        if item.get("categoria_cfp") == "Estilo de Vida (30%)"
    )

    custo_vida_corrente = round(total_fixos + total_variaveis, 2)
    total_despesas = round(custo_vida_corrente + provisao_mensal_anual, 2)
    sobra_antes_provisao_anual = round(total_receitas - custo_vida_corrente, 2)
    sobra_para_investir = round(total_receitas - total_despesas, 2)
    sobra_efetiva = max(0.0, sobra_para_investir)

    # Métricas percentuais
    taxa_poupanca = (sobra_efetiva / total_receitas * 100.0) if total_receitas > 0 else 0.0
    pct_fixos = (total_fixos / total_receitas * 100.0) if total_receitas > 0 else 0.0
    pct_variaveis = (total_variaveis / total_receitas * 100.0) if total_receitas > 0 else 0.0
    pct_essenciais_cfp = (total_essenciais_cfp / total_receitas * 100.0) if total_receitas > 0 else 0.0
    pct_estilo_cfp = (total_estilo_cfp / total_receitas * 100.0) if total_receitas > 0 else 0.0
    pct_provisao_anual = (provisao_mensal_anual / total_receitas * 100.0) if total_receitas > 0 else 0.0

    # Diagnóstico CFP
    if taxa_poupanca >= 30.0:
        diagnostico = "🟢 Excelente! Capacidade de aporte superior a 30% da renda líquida (já deduzindo provisões anuais)."
    elif taxa_poupanca >= 20.0:
        diagnostico = "🔵 Saudável! Alinhado à regra 50/30/20 clássica."
    elif taxa_poupanca >= 10.0:
        diagnostico = "🟡 Atenção. Sobra modesta. Otimize gastos de Estilo de Vida para acelerar a carteira."
    elif sobra_para_investir > 0:
        diagnostico = "🟠 Aperto financeiro. Margem de segurança de fluxo de caixa estreita."
    else:
        diagnostico = "🔴 Déficit orçamentário! Gastos + provisões superam a receita. Risco de resgate na carteira."

    meta_essenciais_rs = round(total_receitas * 0.50, 2)
    meta_estilo_rs = round(total_receitas * 0.30, 2)
    meta_investimentos_rs = round(total_receitas * 0.20, 2)

    regra_50_30_20 = {
        "meta_essenciais_rs": meta_essenciais_rs,
        "meta_estilo_rs": meta_estilo_rs,
        "meta_investimentos_rs": meta_investimentos_rs,
        "essenciais_real_rs": round(total_essenciais_cfp, 2),
        "estilo_real_rs": round(total_estilo_cfp, 2),
        "provisao_anual_mensal_rs": provisao_mensal_anual,
        "pct_essenciais": round(pct_essenciais_cfp, 1),
        "pct_estilo": round(pct_estilo_cfp, 1),
        "pct_provisao_anual": round(pct_provisao_anual, 1),
        "essenciais_ok": bool(total_receitas > 0 and pct_essenciais_cfp <= 50.0),
        "estilo_ok": bool(total_receitas > 0 and pct_estilo_cfp <= 30.0),
        "investimentos_ok": bool(total_receitas > 0 and taxa_poupanca >= 20.0),
        "desvio_essenciais_rs": round(total_essenciais_cfp - meta_essenciais_rs, 2),
        "desvio_estilo_rs": round(total_estilo_cfp - meta_estilo_rs, 2),
        "desvio_investimentos_rs": round(sobra_efetiva - meta_investimentos_rs, 2),
    }

    return {
        "total_receitas": round(total_receitas, 2),
        "total_fixos": round(total_fixos, 2),
        "total_variaveis": round(total_variaveis, 2),
        "total_essenciais_cfp": round(total_essenciais_cfp, 2),
        "total_estilo_cfp": round(total_estilo_cfp, 2),
        "total_despesas_anuais": total_despesas_anuais,
        "provisao_mensal_anual": provisao_mensal_anual,
        "custo_vida_corrente": custo_vida_corrente,
        "total_despesas": round(total_despesas, 2),
        "total_gastos": round(total_despesas, 2),
        "custo_vida_mensal": round(total_despesas, 2),
        "sobra_antes_provisao_anual": sobra_antes_provisao_anual,
        "sobra_para_investir": sobra_para_investir,
        "sobra_efetiva": sobra_efetiva,
        "taxa_poupanca_pct": round(taxa_poupanca, 1),
        "pct_fixos": round(pct_fixos, 1),
        "pct_variaveis": round(pct_variaveis, 1),
        "pct_essenciais_cfp": round(pct_essenciais_cfp, 1),
        "pct_estilo_cfp": round(pct_estilo_cfp, 1),
        "pct_provisao_anual": round(pct_provisao_anual, 1),
        "diagnostico": diagnostico,
        "regra_50_30_20": regra_50_30_20,
        "receitas": receitas,
        "gastos_fixos": gastos_fixos,
        "gastos_variaveis": gastos_variaveis,
        "despesas_anuais": despesas_anuais,
    }


def _meses_para_meta_fire(
    patrimonio_inicial: float,
    aporte_mensal: float,
    meta_patrimonio: float,
    taxa_mensal: float,
    max_meses: int = 1200,
) -> int:
    """Calcula quantos meses leva para atingir a meta FIRE com juros compostos reais."""
    if meta_patrimonio <= 0 or patrimonio_inicial >= meta_patrimonio:
        return 0
    if aporte_mensal <= 0 and taxa_mensal <= 0:
        return max_meses

    patrimonio = max(0.0, float(patrimonio_inicial))
    for mes in range(1, max_meses + 1):
        patrimonio = patrimonio * (1.0 + taxa_mensal) + max(0.0, float(aporte_mensal))
        if patrimonio >= meta_patrimonio:
            return mes
    return max_meses


def simular_corte_gastos_fire(
    corte_mensal_rs: float,
    patrimonio_atual_rs: float,
    aporte_mensal_atual_rs: float,
    custo_vida_mensal_atual_rs: float,
    retorno_real_anual_pct: float = 5.5,
    yield_medio_real_pct: float = 6.0,
) -> Dict[str, Any]:
    """
    Simula o efeito duplo de reduzir despesas variáveis em R$/mês:
    1) Aumenta diretamente a capacidade mensal de aporte;
    2) Reduz o patrimônio FIRE necessário para sustentar o custo de vida real.
    """
    corte = max(0.0, float(corte_mensal_rs))
    patrimonio = max(0.0, float(patrimonio_atual_rs))
    aporte_atual = max(0.0, float(aporte_mensal_atual_rs))
    custo_atual = max(0.0, float(custo_vida_mensal_atual_rs))

    taxa_yield_anual = max(0.01, float(yield_medio_real_pct) / 100.0)
    taxa_retorno_anual = max(0.0, float(retorno_real_anual_pct) / 100.0)
    taxa_mensal = (1.0 + taxa_retorno_anual) ** (1.0 / 12.0) - 1.0

    novo_custo = max(0.0, custo_atual - corte)
    novo_aporte = aporte_atual + corte

    meta_fire_atual = (custo_atual * 12.0) / taxa_yield_anual
    meta_fire_nova = (novo_custo * 12.0) / taxa_yield_anual

    meses_atuais = _meses_para_meta_fire(patrimonio, aporte_atual, meta_fire_atual, taxa_mensal)
    meses_novos = _meses_para_meta_fire(patrimonio, novo_aporte, meta_fire_nova, taxa_mensal)
    meses_antecipados = max(0, meses_atuais - meses_novos)

    if taxa_mensal > 0:
        fator_10a = ((1.0 + taxa_mensal) ** 120 - 1.0) / taxa_mensal
    else:
        fator_10a = 120.0
    patrimonio_extra_10a = corte * fator_10a
    dividendos_anuais_extras_ano1 = (corte * 12.0) * taxa_yield_anual
    dividendos_anuais_extras_10a = patrimonio_extra_10a * taxa_yield_anual

    return {
        "corte_mensal_rs": round(corte, 2),
        "novo_custo_vida_mensal": round(novo_custo, 2),
        "nova_sobra_mensal": round(novo_aporte, 2),
        "meta_fire_atual": round(meta_fire_atual, 2),
        "meta_fire_nova": round(meta_fire_nova, 2),
        "reducao_meta_fire": round(max(0.0, meta_fire_atual - meta_fire_nova), 2),
        "meses_ate_fire_atual": meses_atuais,
        "meses_ate_fire_novo": meses_novos,
        "meses_antecipados": meses_antecipados,
        "anos_antecipados": round(meses_antecipados / 12.0, 1),
        "dividendos_anuais_extras_ano1": round(dividendos_anuais_extras_ano1, 2),
        "dividendos_anuais_extras_10a": round(dividendos_anuais_extras_10a, 2),
        "patrimonio_extra_10_anos": round(patrimonio_extra_10a, 2),
    }
