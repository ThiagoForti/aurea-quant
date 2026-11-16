# 🏛️ Aurea Quant — Private Wealth & B3
## Documentação Técnica Completa de Arquitetura, Metodologias e Engenharia de Software

> **Data de Atualização:** Novembro de 2026  
> **Versão do Sistema:** 2.5 (Edição Desktop & Nuvem Resiliente)  
> **Ambiente de Execução:** Local / Sincronizado em Nuvem (Multiplataforma)  
> **Finalidade deste Documento:** Servir como base de conhecimento integral e contexto exaustivo para desenvolvedores, analistas quantitativos e agentes de Inteligência Artificial (Gemini / Claude / GPT).

---

## SUMÁRIO EXECUTIVO

1. [Visão Geral e Filosofia de Gestão](#1-visão-geral-e-filosofia-de-gestão)
2. [Stack Tecnológica e Dependências](#2-stack-tecnológica-e-dependências)
3. [Arquitetura de Nuvem e Sincronização (Google Drive)](#3-arquitetura-de-nuvem-e-sincronização-google-drive)
4. [Estrutura de Diretórios e Mapeamento de Arquivos](#4-estrutura-de-diretórios-e-mapeamento-de-arquivos)
5. [Detalhamento Técnico Módulo por Módulo](#5-detalhamento-técnico-módulo-por-módulo)
   - [5.1. config.py](#51-configpy--parâmetros-globais-e-segmentação)
   - [5.2. data_engine.py](#52-data_enginepy--camada-de-dados-bcb-e-sanitygate)
   - [5.3. budget_engine.py](#53-budget_enginepy--motor-de-orçamento-cfp-e-fire)
   - [5.4. portfolio_engine.py](#54-portfolio_enginepy--carteira-gatekeeper-e-tributação-b3)
   - [5.5. scanner.py](#55-scannerpy--metodologias-quantitativas-e-valuation)
   - [5.6. news_intelligence.py](#56-news_intelligencepy--second-order-thinking)
   - [5.7. educational_engine.py](#57-educational_enginepy--estudos-diários-e-glossário)
   - [5.8. export_excel.py](#58-export_excelpy--planilha-executiva-em-7-abas)
   - [5.9. dashboard.py](#59-dashboardpy--interface-visual-streamlit)
   - [5.10. test_system.py](#510-test_systempy--suíte-de-testes-em-8-etapas)
   - [5.11. iniciar.bat e Iniciar_Aurea_Quant.exe](#511-iniciarbat-e-iniciar_aurea_quantexe--launchers)
6. [Formulário Matemático Consolidado](#6-formulário-matemático-consolidado)
7. [Manual Operacional: Como Rodar no Computador e no Notebook](#7-manual-operacional-como-rodar-no-computador-e-no-notebook)

---

## 1. VISÃO GERAL E FILOSOFIA DE GESTÃO

O **Aurea Quant** é um ecossistema quantitativo e terminal financeiro desktop desenvolvido para investidores individuais aplicarem a governança de gestão patrimonial no padrão **CFP® (Certified Financial Planner)** e metodologias clássicas de **Value Investing** adaptadas às idiossincrasias do mercado de capitais brasileiro (B3, Banco Central do Brasil e Receita Federal).

### Pilares Fundamentais:
1. **Governança Orçamentária e Cash Flow:** Aplicação estrita da regra 50/30/20, monitoramento da capacidade de poupança e cálculo da sobra líquida mensal para investimentos.
2. **Reserva de Emergência com Trava Ativa (Regra Gatekeeper):** Proteção patrimonial algorítmica que bloqueia ou reduz aportes em renda variável enquanto a reserva de liquidez imediata estiver abaixo da meta (em meses de custo de vida).
3. **Independência Financeira com Juro Real (Equação de Fisher):** Eliminação da "ilusão monetária" em renda fixa pós-fixada (CDI) e fundos imobiliários de papel, descontando a inflação (IPCA) para projetar renda passiva perpétua real.
4. **Valuation Fundamentalista Segmentado:** Abandono de métricas universais simplistas em prol de modelos matemáticos específicos por setor (Graham para industriais/concessões, Gordon com trava de payout para bancos/seguradoras, bandas P/VP para FIIs e momentum MM200/RSI para ETFs de acumulação).
5. **Inteligência Fiscal Automatizada:** Segregação de apuração de ganho de capital, isenção de R$ 20.000 exclusiva para ações, retenção de imposto dedo-duro (0,005%), emissão de DARF código 6015 e compensação estanque de prejuízos fiscais acumulados (Ações/ETFs vs. FIIs).
6. **Portabilidade e Sincronização em Nuvem (Google Drive):** Arquitetura distribuída para permitir uso sincronizado entre desktop e notebook sem conflitos de concorrência ou corrupção de arquivos.

---

## 2. STACK TECNOLÓGICA E DEPENDÊNCIAS

- **Linguagem:** Python 3.10+ (compatível com 3.11, 3.12, 3.13, 3.15)
- **Frontend / Interface:** `streamlit` (v1.35+)
- **Manipulação de Dados e Vetorização:** `pandas`, `numpy`
- **Visualização Gráfica Interativa:** `plotly` (Graph Objects e Express)
- **Engenharia de Planilhas:** `openpyxl` (formatação executiva com Segoe UI, paleta corporativa Navy/Emerald e cards de KPI)
- **Fontes de Dados de Mercado e Notícias:** `yfinance`, `requests`, `feedparser`
- **Validação de Schema:** `pydantic`
- **Inteligência Artificial Opcional:** `google-genai` (Gemini 2.5 Flash estruturado)
- **Launcher e Execução Silenciosa:** Shell Script Windows (`iniciar.bat`) e runtime nativo compilado em C#/.NET (`Iniciar_Aurea_Quant.exe`)

---

## 3. ARQUITETURA DE NUVEM E SINCRONIZAÇÃO RESILIENTE

O projeto é estruturado para suportar execução local isolada ou sincronizada em serviços de armazenamento em nuvem (ex: Google Drive, OneDrive, etc.), garantindo sincronização em tempo real entre computadores através de caminhos relativos e resolução dinâmica de diretórios.

### Mecanismos de Proteção contra Bloqueios e Conflitos de Nuvem:
1. **Isolamento de Caches Voláteis fora da Nuvem:**
   - Caches de cotações (`market_cache.json`) e séries macroeconômicas (`macro_cache.json`) são gravados exclusivamente em `%LOCALAPPDATA%\AureaQuant\cache\`.
   - *Motivo:* Evita que requisições contínuas a cotações gerem conflitos de escrita, bloqueios de leitura (`PermissionError`) ou lentidão na fila de sincronização de pastas em nuvem.
2. **Escrita Atômica com Retry Progressivo (`_atomic_write_json`):**
   - Ao salvar `user_state.json`, os dados são gravados num arquivo temporário `.tmp`, descarregados com `f.flush()`, garantidos em disco via `os.fsync()` e substituídos com `os.replace()`.
   - Possui retry com **8 tentativas progressivas** de até 2,5 segundos para absorver momentos em que o cliente de nuvem trava o arquivo para cálculo de hash/upload.
3. **Leitura Resiliente com Fallback (`load_user_state`):**
   - Na leitura, tenta abrir o arquivo até 5 vezes. Se o arquivo estiver ausente ou bloqueado temporariamente, inicializa automaticamente a partir de `user_state_demo.json` ou busca o último backup íntegro em `backups/user_state_*.json`.
4. **Recarregamento Dinâmico em Tempo Real (`Hot-Reload Protection`):**
   - No topo de `dashboard.py`, é executado um loop com `importlib.reload()` em todos os 8 módulos de lógica. Ao sincronizar e recarregar a tela, o Python recarrega imediatamente as funções na memória sem lançar `ImportError`.
5. **Exportação Excel Atômica:**
   - Em `export_excel.py`, a geração da planilha `Gestao_Completa_Patrimonio_B3.xlsx` também utiliza substituição atômica via `.tmp` com retry, evitando corrupção caso o arquivo esteja sendo sincronizado ou visualizado no Excel.

---

## 4. ESTRUTURA DE DIRETÓRIOS E MAPEAMENTO DE ARQUIVOS

```text
aurea-quant/
├── .streamlit\
│   ├── config.toml                     # Configurações de tema, porta 8501 e telemetria
│   ├── aurea_quant.png                 # Monograma e ícone oficial do sistema
│   └── aurea_quant.ico                 # Ícone da janela desktop
├── backups\                            # Backups rotativos automáticos de user_state.json
├── config.py                           # Parâmetros globais, universos de ativos e feeds RSS
├── data_engine.py                      # SGS/BCB, Base 252, escrita atômica e SanityGate
├── budget_engine.py                    # Orçamento CFP, 50/30/20 e simulador corte FIRE
├── portfolio_engine.py                 # Carteira, Gatekeeper, Fisher FIRE e IR/DARF B3
├── scanner.py                          # Graham, Bazin c/ JCP, Gordon, FIIs, ETFs e Magic Number
├── news_intelligence.py                # Second-Order Thinking e Janelas de Assimetria
├── educational_engine.py               # 31 estudos diários curados e glossário financeiro
├── export_excel.py                     # Motor de exportação para Excel (7 abas)
├── dashboard.py                        # Interface principal em Streamlit com 5 abas
├── test_system.py                      # Suíte de testes de integração ponta a ponta (8/8)
├── user_state.json                     # Estado principal do usuário (Single Source of Truth)
├── user_state_demo.json                # Carteira de demonstração auditada
├── Gestao_Completa_Patrimonio_B3.xlsx  # Planilha executiva gerada e sincronizada
├── requirements.txt                    # Dependências do ecossistema Python
├── iniciar.bat                         # Inicializador em lote com resolução de portas
└── Iniciar_Aurea_Quant.exe             # Launcher C#/.NET para inicialização sem console
```

---

## 5. DETALHAMENTO TÉCNICO MÓDULO POR MÓDULO

### 5.1. `config.py` — Parâmetros Globais e Segmentação
- **Diretórios Dinâmicos:** Usa `Path(__file__).resolve().parent` para que funcione em qualquer computador ou letra de drive.
- **Segmentação Setorial:**
  - `BANCOS_JCP`: `["ITUB4", "BBDC4", "BBAS3", "SANB11"]` (Haircut ponderado de 10% no provento de Bazin por misturarem JCP tributado a 15% com dividendos).
  - `SEGURADORAS_ISENTAS`: `["BBSE3", "CXSE3"]` (Haircut 0% — dividendos praticamente 100% isentos).
  - `FIIS_PAPEL`: `["KNCR11", "KNIP11"]` vs. `FIIS_TIJOLO`: `["HGLG11", "BTLG11", "XPML11"]`.
- **Universos de Ativos:**
  - **BESST Tradicional:** `TAEE11`, `EGIE3`, `ISAE4`, `CPFE3`, `CMIG4`, `SBSP3`, `SAPR11`, `CSMG3`, `ITUB4`, `BBAS3`, `BBDC4`, `BBSE3`, `CXSE3`, `VIVT3`.
  - **Crescimento:** `WEGE3`, `VALE3`, `PETR4`, `PRIO3`, `SUZB3`, `RADL3`, `SLCE3`, `SMTO3`, `RENT3`, `TOTS3`, `GGBR4`.
  - **ETFs de Acumulação:** `BOVA11`, `DIVO11`, `IVVB11`, `NASD11`, `WRLD11`, `SMAL11`, `GOLD11`.
  - **BDRs Internacionais:** `NVDC34`, `AAPL34`, `MSFT34`, `GOGL34`, `AMZO34`, `M1TA34`, `TSLA34`, `TSMC34`, `MELI34`, `BERK34`.
- **Códigos Oficiais SGS do Banco Central:**
  - Série 432: Taxa Selic Meta (% a.a.)
  - Série 4389: Taxa CDI Diário Anualizada (% a.a.)
  - Série 13522: IPCA acumulado em 12 meses (% a.a.)
  - Série 1: Taxa de Câmbio PTAX Venda (R$)
- **Tabela de IR Regressivo de Renda Fixa:**
  - Até 180 dias: 22,5% | 181 a 360 dias: 20,0% | 361 a 720 dias: 17,5% | Acima de 720 dias: 15,0%

---

### 5.2. `data_engine.py` — Camada de Dados, BCB e SanityGate
- **Sessão Persistente SGS (`_get_bcb_session`):** Cria um pool de conexões HTTP `requests.Session` com headers reais de browser desktop e retry automático. Reduz o tempo de resposta das 4 séries do Banco Central para **0,33 segundos**.
- **Cálculo de Renda Fixa em Base Oficial de 252 Dias Úteis (`calcular_rendimento_nubank`):**
  - Converte dias corridos em dias úteis: $\text{DU} = \text{round}(\text{DC} \times \frac{252}{365})$.
  - Calcula o Fator Diário composto:
    $$\text{Fator Diário} = 1 + \left( (1 + \text{CDI}_{\text{anual}})^{1/252} - 1 \right) \times \frac{\%\text{CDI}}{100}$$
  - Aplica o fator no prazo: $\text{Fator Bruto} = (\text{Fator Diário})^{\text{DU}}$.
  - O Imposto de Renda incide estritamente sobre o rendimento bruto auferido, garantindo o efeito real do diferimento fiscal nos juros compostos.
  - Converte para taxas equivalentes líquidas mensais (21 DU) e anuais (252 DU) para permitir comparação direta de yield com ações e FIIs.
- **SanityGate (`validar_dados_yfinance`):**
  - Executa uma auditoria algorítmica sobre os dados brutos recebidos da B3:
    1. Se $\text{DY} > 20\%$ (anomalia decorrente de dividendos extraordinários ou erro de provedor).
    2. Se $P/L < 2.0$ (para ações não-financeiras, apontando distorção contábil).
    3. Se $P/VP < 0.30$ (empresas em estresse severo ou risco de liquidação).
  - Classifica a linha como `'Suspeito'` e bloqueia que esse ativo assuma automaticamente as primeiras posições do ranking de compras recomendadas.

---

### 5.3. `budget_engine.py` — Motor de Orçamento CFP e FIRE
- **Consolidação Financeira (`calcular_orcamento`):**
  - Agrupa Receitas Líquidas, Gastos Fixos e Gastos Variáveis.
  - Calcula a **Sobra Líquida Mensal para Aportes**: $\text{Sobra} = \text{Receitas} - (\text{Fixos} + \text{Variáveis})$.
  - Avalia o enquadramento na regra **50/30/20** (Essenciais $\le 50\%$, Estilo de Vida $\le 30\%$, Poupança/Investimento $\ge 20\%$).
- **Simulador de Corte de Gastos com Juros Compostos (`simular_corte_gastos_fire`):**
  - Modela matematicamente o **efeito duplo** da redução de despesas supérfluas:
    1. *Efeito 1:* Eleva diretamente o aporte mensal em $X$ reais.
    2. *Efeito 2:* Reduz o custo de vida perpétuo, encolhendo a meta de patrimônio total necessária pela regra dos dividendos perpétuos reais:
       $$\text{Meta FIRE} = \frac{\text{Custo de Vida Anual}}{\text{Taxa de Retorno Real}}$$
  - Calcula a quantidade exata de meses e anos antecipados até a independência financeira com base na equação de anuidade de juros compostos.

---

### 5.4. `portfolio_engine.py` — Carteira, Gatekeeper e Tributação B3
- **Gatekeeper da Reserva de Emergência (`calcular_cobertura_reserva`):**
  - Calcula a cobertura da reserva em meses: $\text{Cobertura} = \frac{\text{Saldo Reserva RF}}{\text{Custo de Vida Mensal Total}}$.
  - Se $\text{Cobertura} < \text{Meta em Meses}$ (ex.: 6 meses):
    - Ativa o modo `'Gatekeeper Ativo'`.
    - Determina o percentual mínimo de retenção da sobra mensal (entre 50% e 100%) direcionado compulsoriamente para a Caixinha Nubank/Tesouro Selic antes de liberar aportes em ações ou fundos imobiliários.
- **Renda Passiva Sustentável Real via Equação de Fisher (`calcular_renda_passiva_real_e_fire`):**
  - A renda nominal dos títulos atrelados ao CDI e dos FIIs de recebíveis (papel) embute a recomposição inflacionária do principal. Para não descapitalizar o patrimônio, o sistema expurga o IPCA via Fisher:
    $$r_{\text{real}} = \frac{1 + r_{\text{nominal}}}{1 + \text{IPCA}} - 1$$
  - Calcula a cobertura percentual dos custos fixos mensais com proventos reais.
- **Simulador Fiscal e DARF da B3 (`simular_venda_e_ir`):**
  - **Ações:** Monitora o volume total de vendas no mês civil.
    - Se $\sum \text{Vendas} \le \text{R\$} 20.000,00$: Isenção legal do imposto sobre ganho de capital (alíquota zero).
    - Se $\sum \text{Vendas} > \text{R\$} 20.000,00$: Tributação de 15% sobre o lucro líquido (preço de venda menos preço médio menos taxas de corretagem e B3).
  - **FIIs:** Sem qualquer isenção. Tributação de 20% sobre o ganho de capital em 100% dos casos.
  - **Direitos de Subscrição de FIIs (Final 12):** Preço médio contábil tratado como R$ 0,00; IR de 20% incide sobre 100% do valor bruto da alienação.
  - **ETFs e BDRs:** Tributação fixa de 15% sobre o lucro líquido, **sem consumir a cota de isenção de R$ 20.000 exclusiva das ações**.
  - **Imposto Retido na Fonte (Dedo-Duro):** Calcula a alíquota oficial de 0,005% sobre o valor da alienação e desconta do IR devido.
  - **Compensação Segregada de Prejuízos:**
    - `prejuizo_acumulado_acoes_etfs`: Utilizado para abater ganhos exclusivamente de Ações, ETFs e BDRs.
    - `prejuizo_acumulado_fiis`: Utilizado para abater ganhos exclusivamente de Fundos Imobiliários.
- **Mercado Fracionário Inteligente (`formatar_ticker_fracionario`):**
  - Se a classe for `'Ações'` e a sugestão de compra estiver entre 1 e 99 unidades, adiciona automaticamente a letra `F` ao ticker (ex.: `BBAS3` $\rightarrow$ `BBAS3F`). Mantém inalterado para lotes padrão de 100 cotas ou para FIIs, ETFs e BDRs.
- **Algoritmo de Aporte com Trava de Teto (`calcular_rebalanceamento_aportes`):**
  - Se a cotação de mercado estiver acima do **Preço Teto** calculado (Bazin ou Gordon), o algoritmo bloqueia a compra do ativo, reclassifica-o como `'Bloqueado por Preço Teto'` e redireciona o capital para ativos subavaliados ou para o **Caixa de Oportunidade (Renda Fixa)**.

---

### 5.5. `scanner.py` — Metodologias Quantitativas e Valuation
- **Benjamin Graham Tradicional:**
  $$V_I = \sqrt{22,5 \times \text{LPA} \times \text{VPA}}$$
  *Trava matemática:* Se $\text{LPA} \le 0$ ou $\text{VPA} \le 0$, retorna `None`.
- **Preço Teto de Décio Bazin com Haircut Seletivo de JCP:**
  - Fórmula básica:
    $$\text{Preço Teto} = \frac{\text{Dividendo Mediano por Ação (3 a 5 anos)}}{0,06}$$
  - Haircut seletivo:
    - Seguradoras (`BBSE3`, `CXSE3`): Multiplica por 1,00 (0% de desconto).
    - Bancos (`ITUB4`, `BBDC4`, `BBAS3`, `SANB11`): Multiplica por 0,90 (10% de haircut médio ponderado pelo imposto retido sobre o JCP).
- **Modelo de Gordon Dinâmico com Trava de Solvência:**
  - Aplicado a instituições financeiras onde $P/L$ e Graham não capturam o custo regulatório de capital:
    $$P_0 = \text{VPA} \times \frac{\text{ROE} \times \text{Payout}_{\text{prudencial}}}{K_e - g}$$
  - Onde:
    - $K_e = \max(12\%, \text{CDI} + 4\%)$ (custo de capital próprio dinâmico).
    - $\text{Payout}_{\text{prudencial}} = \min(\text{Payout Histórico}, 60\%)$ (preserva capital de Basileia).
    - $g = 4\%$ (crescimento nominal conservador de longo prazo).
- **Segmentação Estrutural de FIIs:**
  - *FIIs de Papel (CRIs):* Avalia a paridade patrimonial ($P/VP \approx 1,00$). Penaliza severamente ágio ($P/VP > 1,03$) e emite `'Alerta de Risco de Crédito no Portfólio de CRIs'` quando $P/VP < 0,85$.
  - *FIIs de Tijolo (Imóveis Físicos):* Aplica banda elástica entre 0,85 e 1,05, interpolando linearmente a pontuação entre 0,80 e 0,85.
- **Score de Saúde de Balanço e Dívida:**
  - Setor Industrial / Concessões: Penaliza empresas com Dívida Líquida / Ebitda $> 3,0x$ ou Liquidez Corrente $< 1,0$.
  - Bancos: Isenta o cálculo de Dívida/Ebitda e pontua por ROE ($> 18\%$), estabilidade de lucros e margem líquida.
  - ETFs: Isenta dívida e múltiplos contábeis, pontuando por liquidez diária e aderência ao índice de referência.
- **Magic Number Dual (Efeito Bola de Neve):**
  - *FIIs:* $\text{Cotas Necessárias} = \frac{\text{Cotação Atual}}{\text{Dividendo Mensal por Cota}}$ (cotas para comprar 1 nova cota **todo mês**).
  - *Ações:* $\text{Cotas Necessárias} = \frac{\text{Cotação Atual}}{\text{Dividendo Anual por Cota}}$ (cotas para comprar 1 nova cota **todo ano**).
- **Scanner Técnico de Sobrevenda (RSI 14) com Qualificação de Risco:**
  - Calcula o RSI de 14 períodos sobre preços ajustados (`Adj Close`).
  - *Sobrevenda de Elite:* Ativo com $RSI \le 35$, saúde de balanço $> 75$ e dentro do preço teto.
  - *Sobrevenda de Alto Risco:* Ativo com $RSI \le 35$, mas com balanço fragilizado ou endividamento crítico.

---

### 5.6. `news_intelligence.py` — Second-Order Thinking
- **Cadeia Causal de 3 Níveis:**
  1. *Fato de 1ª Ordem:* O acontecimento objetivo da manchete.
  2. *Consequência de 2ª Ordem:* O mecanismo de transmissão macroeconômica (juros, câmbio, custos, inflação).
  3. *Tese de 3ª Ordem na B3:* O ativo mais beneficiado ou prejudicado na bolsa.
- **Janela de Assimetria Aberta:**
  - Cruza a tese com a cotação intradiária. Se a tese for positiva e a cotação no dia tiver oscilado até $+0,8\%$, classifica como `'🎯 JANELA ABERTA (Assimetria Favorável)'`. Se a ação já subiu mais de $2\%$, classifica como `'⚠️ JÁ ANDOU (Mercado absorveu)'`.
- **Modo Híbrido:** Opera 100% autônomo offline via regex semântico; se a chave `GEMINI_API_KEY` estiver configurada, consome a API do Gemini 2.5 Flash estruturada via Pydantic (`TeseNoticia`).

---

### 5.7. `educational_engine.py` — Estudos Diários e Glossário
- Catálogo de **31 estudos diários** (um para cada dia do mês), com conceitos práticos, lições operacionais e links oficiais verificados para aprofundamento (Graham, Bazin, Howard Marks, Peter Lynch, B3 Educação, InfoMoney).
- Glossário completo de conceitos e métodos (Margem de Segurança, Equação de Fisher, Preço Teto, RSI, Gatekeeper).

---

### 5.8. `export_excel.py` — Planilha Executiva em 7 Abas
Gera atomicamente o arquivo **`Gestao_Completa_Patrimonio_B3.xlsx`** contendo 7 abas formatadas em padrão corporativo (paleta Navy `#0F172A`, Esmeralda `#059669`, tipografia Segoe UI, tabelas zebradas e cards KPI com auto-ajuste de colunas):
1. `1_Orcamento_Mensal`: Receitas, fixos, variáveis, diagnósticos CFP e meta 50/30/20.
2. `2_Minha_Carteira`: Renda Fixa detalhada, Renda Variável com cotações ao vivo, Preço Teto, Spread vs. CDI e cálculos de rebalanceamento inteligente.
3. `3_Setores_Mais_Seguros`: Universos BESST e Crescimento auditados com Graham, Gordon e Bazin.
4. `4_Teses_Futuras_Noticias`: Radar de pensamentos de 2ª e 3ª ordem e status de assimetria.
5. `5_Radar_Intradiario_e_FIIs`: Scanner técnico de sobrecompra/sobrevenda e análise de FIIs de Papel e Tijolo.
6. `6_Risco_e_Correlacao`: Matriz de risco, volatilidade e diversificação patrimonial.
7. `7_Calendario_Sazonal`: Mapeamento mês a mês dos dividendos históricos esperados ao longo dos 12 meses do ano.

---

### 5.9. `dashboard.py` — Interface Visual Streamlit
- Interface desenvolvida em Streamlit estruturada em **5 abas principais** sem scroll horizontal:
  - **Aba 1 (Cockpit):** Resumo executivo em 1 minuto, 4 cards de KPIs com micro-barras nativas de progresso, monitoramento de cobertura de gastos fixos por renda real e alarme do Gatekeeper.
  - **Aba 2 (Minha Carteira & IR):** Gestão cadastral de ativos, simulador de vendas e DARF com cálculo de isenção de 20k, apurador de prejuízos e gerador de ordens de compra fracionárias (`F`).
  - **Aba 3 (Meu Orçamento):** Cockpit financeiro pessoal com simulador de corte de gastos FIRE.
  - **Aba 4 (Radar de Oportunidades):** Classificação fundamentalista BESST, ranking de FIIs, ETFs, BDRs, scanner de assimetria de notícias e calendário sazonal de dividendos.
  - **Aba 5 (Guia Educacional):** Acervo do estudo do dia e biblioteca de conceitos.
- **Top Ticker Ribbon:** Fita de cotações macroeconômicas no topo (Selic Meta, CDI Líquido, IPCA 12m, Juro Real Ex-Post, PTAX Dólar e Sobra Mensal).
- **Barra Lateral Executiva Proporcional:** Controles de metas de meses de reserva, botão de sincronização global com limpeza de cache, download imediato da planilha Excel, backup/limpeza/demo e rodapé de status de rede (`Banco Central SGS: Online 🟢` e `Mercado B3: 47 ativos 🟢`).
- **Tema Híbrido:** Suporte instantâneo a tema **Diurno Orgânico (Quiet Luxury)** e tema **Noturno Mineral (Slate/Carvão Macio)**, além de **Modo Apresentação / Privacidade** (oculta todos os valores em R$ da tela para compartilhamento de tela ou prints).

---

### 5.10. `test_system.py` — Suíte de Testes em 8 Etapas
Testa de forma autônoma 8 blocos funcionais do sistema:
1. `[1/8]` Persistência atômica, integridade do schema de `user_state.json` e isolamento dos caches locais fora do Drive.
2. `[2/8]` Resiliência da API do Banco Central (SGS/BCB) e validação matemática de Renda Fixa na base 252 DU.
3. `[3/8]` Motor de orçamento CFP, regra 50/30/20 e matemática de antecipação do FIRE com corte de gastos.
4. `[4/8]` Gatekeeper da reserva, equação de Fisher para FIRE Real, simulador fiscal (isenção 20k, dedos-duros, FIIs 20%, ETFs 15%, BDRs 15% e buckets estanques de prejuízos acumulados) e roteador fracionário (`F`).
5. `[5/8]` Valuation segmentado (Graham, Gordon, Bazin c/ haircut JCP, FIIs papel vs. tijolo, ETFs MM200/RSI e SanityGate).
6. `[6/8]` Heurística de notícias (Second-Order Thinking nacional e internacional) e estudos diários.
7. `[7/8]` Geração e integridade estrutural das 7 abas do arquivo Excel `Gestao_Completa_Patrimonio_B3.xlsx`.
8. `[8/8]` Consistência e estabilidade global.

---

### 5.11. `iniciar.bat` e `Iniciar_Aurea_Quant.exe` — Launchers
- **`iniciar.bat`:** Script batch com codificação UTF-8 (`chcp 65001`), resolução de caminhos dinâmicos (`%~dp0`), encerramento de processos órfãos na porta 8501 via `netstat` e `taskkill`, validação do `requirements.txt` e inicialização do executável.
- **`Iniciar_Aurea_Quant.exe`:** Executável nativo compilado em C#/.NET que inicializa o processo do Python em segundo plano (`WindowStyle.Hidden`) e monitora a porta `8501` via `TcpClient`. Assim que o servidor responde HTTP 200, ele abre o navegador padrão do Windows diretamente no endereço local `http://localhost:8501`.

---

## 6. FORMULÁRIO MATEMÁTICO CONSOLIDADO

$$\begin{aligned}
\textbf{Base 252 (Renda Fixa):} & \quad \text{Fator Diário} = 1 + \left( (1 + \text{CDI})^{1/252} - 1 \right) \cdot \frac{\%\text{CDI}}{100} \\
\textbf{Fisher FIRE Real:} & \quad r_{\text{real}} = \frac{1 + r_{\text{nominal}}}{1 + \text{IPCA}} - 1 \\
\textbf{Benjamin Graham:} & \quad V_I = \sqrt{22,5 \cdot \text{LPA} \cdot \text{VPA}} \quad (\text{com } \text{LPA} > 0, \, \text{VPA} > 0) \\
\textbf{Décio Bazin (Bancos):} & \quad \text{Teto} = \frac{\text{Mediana Div (3 a 5 anos)} \cdot 0,90}{0,06} \\
\textbf{Décio Bazin (Seguradoras):} & \quad \text{Teto} = \frac{\text{Mediana Div (3 a 5 anos)} \cdot 1,00}{0,06} \\
\textbf{Gordon Dinâmico:} & \quad P_0 = \text{VPA} \cdot \frac{\text{ROE} \cdot \min(\text{Payout}, 0,60)}{K_e - 0,04}, \quad K_e = \max(0,12, \, \text{CDI} + 0,04) \\
\textbf{SanityGate:} & \quad \text{Suspeito se: } (\text{DY} > 0,20) \lor (P/L < 2,0 \text{ em ações}) \lor (P/VP < 0,30) \\
\textbf{Gatekeeper Reserva:} & \quad \text{Se } \frac{\text{Reserva RF}}{\text{Custo de Vida}} < \text{Meta Meses} \implies \text{Trava 50\% a 100\% do aporte em RF}
\end{aligned}$$

---

## 7. MANUAL OPERACIONAL: COMO EXECUTAR O SISTEMA

1. **Instalação e Dependências:** Clone ou extraia o repositório em uma pasta local. Certifique-se de que o Python 3.10+ está instalado e execute `pip install -r requirements.txt`.
2. **Execução:** Execute o script `iniciar.bat` ou inicie diretamente via terminal com `streamlit run dashboard.py`.
3. **Uso:** O sistema abre automaticamente no navegador padrão (`http://localhost:8501`). Se for a primeira execução, o sistema carrega automaticamente os dados de demonstração de `user_state_demo.json`. Qualquer novo aporte cadastrado, alteração de despesas ou ajuste de metas é salvo atomicamente no arquivo `user_state.json`.
4. **Fechamento:** Para encerrar o servidor e liberar a porta 8501, utilize o botão **"Encerrar Aplicativo"** na barra lateral.
