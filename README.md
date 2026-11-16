# 🏛️ Aurea Quant — Private Wealth & Quantitative Terminal

Terminal quantitativo e motor de inteligência patrimonial desenvolvido para alocação estratégica de capital, rebalanceamento inteligente de carteiras na B3 (Ações, FIIs, ETFs e BDRs), renda fixa de alta liquidez (Base 252) e planejamento orçamentário com foco em independência financeira (FIRE).

---

## ⚡ Guia Rápido de Execução (Cross-Platform)

O sistema foi projetado para execução imediata em qualquer sistema operacional (Windows, macOS e Linux) com dependências padrão do ecossistema Python.

### Pré-requisitos
- **Python 3.10 ou superior** instalado e adicionado ao `PATH`.
- Instalação dos pacotes necessários:
  ```bash
  pip install -r requirements.txt
  ```

---

### Formas de Inicialização

#### 1. Windows (1 Clique)
Na raiz do projeto, utilize uma das opções de inicialização rápida:
- Duplo clique em **`iniciar.bat`**: Script batch que encerra processos pendentes na porta 8501, valida as dependências e inicia o terminal.
- Ou execute **`Iniciar_Aurea_Quant.exe`**: Launcher nativo que dispara o servidor em segundo plano e abre o navegador padrão automaticamente.

#### 2. Qualquer Sistema Operacional (Terminal / Linux / macOS)
Abra o terminal na pasta do projeto e execute:
```bash
streamlit run dashboard.py
```
O Streamlit iniciará o servidor local e abrirá a interface no endereço padrão:
```text
http://localhost:8501
```

---

## 🚀 Bootstrap Automático & Modo Demonstração

- **Zero Configuração Inicial:** O repositório vem sanitizado para publicação pública. Na primeira execução (quando `user_state.json` não existir), o sistema detecta a ausência e **copia automaticamente `user_state_demo.json`** para `user_state.json`.
- **Dados Fictícios e Auditados:** A carteira de exemplo inclui alocações realistas em empresas do universo BESST, FIIs de tijolo e papel, ETFs internacionais (IVVB11), caixinhas de renda fixa e orçamento mensal estruturado na metodologia CFP (50/30/20).
- **Sem Necessidade de Chaves de API:** O radar de inteligência de notícias opera 100% no **modo heurístico quantitativo offline** por padrão. Se desejar usar o modo LLM generativo, basta definir a variável de ambiente `GEMINI_API_KEY` (opcional).
- **Isolamento de Cache Multiplataforma:** Arquivos de cache intradiário e macroeconômico são mantidos fora do versionamento:
  - **Windows:** `%LOCALAPPDATA%\AureaQuant\cache`
  - **Linux / macOS:** `~/.cache/AureaQuant`

---

## 🧠 Arquitetura e Motores do Sistema

```text
aurea-quant/
├── .streamlit/                     # Configurações visuais e tema executivo
├── budget_engine.py                # Planejamento CFP (50/30/20) e simulador de corte FIRE
├── config.py                       # Parâmetros macroeconômicos, universos e caches
├── dashboard.py                    # Terminal visual em Streamlit (5 visões integradas)
├── data_engine.py                  # Integração SGS/BCB, yfinance, Base 252 e SanityGate
├── educational_engine.py           # Base com 31 estudos diários e glossário financeiro
├── export_excel.py                 # Exportador de relatório executivo em Excel (7 abas)
├── news_intelligence.py            # Radar de assimetrias e pensamento de 2ª e 3ª ordem
├── portfolio_engine.py             # Rebalanceamento, Gatekeeper de reserva e tributação B3
├── scanner.py                      # Valuation (Graham, Bazin c/ JCP, Gordon) e Magic Number
├── test_system.py                  # Suíte de testes de integração ponta a ponta (8 etapas)
├── user_state_demo.json            # Estado demonstrativo sanitizado
├── requirements.txt                # Dependências Python
├── iniciar.bat                     # Inicializador rápido para ambiente Windows
└── Iniciar_Aurea_Quant.exe         # Launcher executável sem terminal
```

### 1. Camada de Dados & Resiliência (`data_engine.py`)
- Coleta automática de indicadores macroeconômicos via webservice oficial do Banco Central (SGS): Selic Meta, CDI, IPCA 12M e Dólar PTAX.
- Tratamento quantitativo de Renda Fixa em convenção **Base 252** dias úteis com dedução regressiva de Imposto de Renda.
- **SanityGate:** Filtro algorítmico contra anomalias de dados públicos (dividend yield > 20%, P/L negativo ou distorções de grupamentos).

### 2. Motor de Carteira & Alocação Inteligente (`portfolio_engine.py`)
- **Gatekeeper da Reserva de Emergência:** Trava aportes em ativos de risco quando a liquidez de segurança estiver abaixo da meta (meses de custo de vida).
- **Algoritmo de Rebalanceamento por Aporte:** Direciona novos recursos para os ativos mais para trás em relação à meta percentual, sem forçar vendas desnecessárias e geradoras de IR.
- **Tributação B3 Completa:** Cálculo segregado de IR para ações (com isenção de R$ 20k no mês), FIIs (alíquota fixa de 20%), ETFs e BDRs, incluindo compensação automática de prejuízos acumulados e emissão do código DARF 6015.

### 3. Scanner Quantitativo & Valuation (`scanner.py`)
- **Preço Justo de Benjamin Graham:** $V_I = \sqrt{22{,}5 \times \text{LPA} \times \text{VPA}}$ para empresas com histórico de lucros e patrimônio positivo.
- **Método de Décio Bazin com Haircut de JCP:** Aplicação de haircut tributário seletivo sobre proventos de bancos e seguradoras antes da exigência de Dividend Yield mínimo de 6%.
- **Gordon Dinâmico:** Modelo de desconto de dividendos com custo de oportunidade ancorado no CDI real.
- **Efeito Bola de Neve (Magic Number):** Determinação exata da quantidade de cotas necessárias para que os proventos mensais comprem uma nova cota automaticamente.

### 4. Inteligência de Notícias & 2ª Ordem (`news_intelligence.py`)
- Mapeamento de desdobramentos de **Primeira, Segunda e Terceira Ordem** a partir de fatos relevantes e notícias financeiras globais e locais.
- Detecção de **Janelas de Assimetria Favorável**: Identifica quando um ativo ainda não precificou um evento positivo no pregão.

---

## 🧪 Testes Automatizados e Validação

Para validar a integridade de todas as fórmulas matemáticas, persistência atômica e conexões de rede, execute a suíte de testes:

```bash
python test_system.py
```

A suíte executa 8 etapas de validação rigorosa:
1. Persistência atômica e cache offline
2. Banco Central SGS e convenção Base 252
3. Orçamento CFP (50/30/20) e projeções FIRE
4. Carteira, Gatekeeper e motor tributário B3
5. Modelos de Valuation e Scanner intradiário
6. Motor Educacional e Heurísticas de Notícias
7. Geração da planilha Excel com fórmulas vivas e auto-filtro
8. Integridade dos schemas de dados

---

## 📄 Licença & Finalidade

Projeto desenvolvido para fins de estudo, portfólio técnico e demonstração de engenharia de software e análise quantitativa. Sinta-se livre para explorar, clonar e adaptar o código.
