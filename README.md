# Dunder Auditor

Projeto: Chatbot/Agentes de Auditoria para Dunder Mifflin (Scranton).

Arquivos de dados (fornecidos):
- `data/politica_compliance.txt`. :contentReference[oaicite:4]{index=4}
- `data/emails.txt`. :contentReference[oaicite:5]{index=5}
- `/mnt/data/transacoes_bancarias.csv` -> copie para `data/`.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# editar .env com sua chave GOOGLE_API_KEY
```

## Arquitetura de Agentes

O sistema Dunder Auditor implementa uma arquitetura multi-agente especializada para auditoria de compliance, onde cada agente possui responsabilidades específicas e trabalha de forma coordenada para detectar violações, conspirações e correlacionar evidências.

### Visão Geral

```
┌─────────────────────────────────────────────────────────────┐
│                    DUNDER AUDITOR SYSTEM                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ RAG Policy   │  │   Email      │  │ Transaction  │     │
│  │    Agent     │  │   Agent      │  │    Agent     │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            ▼                                 │
│                   ┌─────────────────┐                       │
│                   │  Correlation    │                       │
│                   │     Agent       │                       │
│                   └─────────────────┘                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Core

#### **Embeddings (`core/embeddings.py`)**
- Gera embeddings vetoriais usando Gemini (`text-embedding-004`)
- Converte texto em vetores de 1536 dimensões para busca semântica
- Base para todos os agentes que utilizam RAG

#### **VectorStore (`core/vectorstore.py`)**
- Implementa indexação e busca vetorial usando FAISS (Facebook AI Similarity Search)
- Armazena embeddings e metadados de chunks
- Operações: build, add, query com distância L2
- Persistência em arquivos `.index` e `.meta.pkl`

#### **LLM (`core/llm.py`)**
- Interface para Gemini (`gemini-1.5-flash`)
- Gera respostas contextualizadas baseadas em evidências
- Suporta controle de temperatura e max_tokens

### Agentes Especializados

#### 1. **RAGPolicyAgent** (`agents/rag_policy_agent.py`)
**Propósito:** Responder perguntas sobre a política de compliance usando RAG

**Funcionamento:**
1. Recebe uma pergunta em linguagem natural
2. Gera embedding da pergunta
3. Busca os top-k chunks mais relevantes no vectorstore de política
4. Constrói prompt com evidências
5. Usa LLM para gerar resposta estruturada (RESPOSTA, RAZÃO, EVIDÊNCIAS)

**Dados:**
- `vectorstore/policy/` - Índice FAISS da política
- `data/politica_compliance.txt` - Documento fonte

**Casos de uso:**
- "Qual o limite para despesas sem PO?"
- "Itens proibidos pela política?"

---

#### 2. **EmailAgent** (`agents/email_agent.py`)
**Propósito:** Buscar e analisar e-mails suspeitos, detectar conspirações

**Funcionalidades:**

**a) Busca por Palavras-chave (`search_keyword`)**
- Procura palavras suspeitas no corpo dos e-mails
- Lista: "conta alternativa", "mascarar", "destruir evidências", etc.

**b) Busca Semântica (`semantic_search`)**
- Busca por similaridade vetorial
- Agrupa chunks por email_id
- Retorna e-mails ranqueados por relevância

**c) Detecção de Conspiração (`detect_conspiracy`)**
- Combina busca por palavras-chave + busca semântica
- Procura menções a "Toby", "operação fênix", "destruir"
- Retorna veredito ("Sim"/"Não") + evidências

**Dados:**
- `vectorstore/emails/` - Índice FAISS de e-mails
- `data/emails_parsed.jsonl` - E-mails parseados estruturados

---

#### 3. **TransactionAgent** (`agents/transaction_agent.py`)
**Propósito:** Aplicar regras de compliance diretas nas transações bancárias

**Regras Implementadas:**

| ID | Regra | Severidade | Descrição |
|----|-------|------------|-----------|
| R1 | `rule_large_expense` | HIGH | Despesas > $500 requerem PO e aprovação CFO |
| R2 | `rule_event_category_above_5` | MEDIUM | Categoria "Outros" não aceita > $5 |
| R3 | `rule_prohibited_item` | CRITICAL | Detecta itens da lista negra (algemas, armas, kit mágica) |

**Funcionamento:**
1. Carrega CSV normalizado de transações
2. Itera sobre cada linha
3. Aplica todas as regras
4. Retorna lista de violações com: data, beneficiário, valor, regra, severidade

**Dados:**
- `data/transacoes_bancarias.csv` - Transações normalizadas

---

#### 4. **CorrelationAgent** (`agents/correlation_agent.py`)
**Propósito:** Correlacionar transações com evidências em e-mails usando sistema de pontuação sofisticado

**Sistema de Pontuação (Máx: 115pts, normalizado para 100):**

| Componente | Pontos | Descrição |
|------------|--------|-----------|
| **Temporal** | 0-40 | Mesmo dia (40), ±1 dia (35), ±2-3 dias (25), ±4-7 dias (15) |
| **Beneficiário** | 0-30 | Match de beneficiário/descrição no e-mail |
| **Valor** | 0-20 | Menção exata ou aproximada (±10%) do valor |
| **Palavras-chave** | 0-30 | Presença de termos suspeitos |
| **Remetente** | 0-15 | VIPs (Michael Scott, Jan Levinson, David Wallace, etc.) |
| **Assunto** | 0-10 | Relevância do assunto (urgente, confidencial, pagamento) |

**Algoritmo:**
```python
Para cada transação:
  Para cada e-mail na janela temporal (±7 dias):
    score_temporal = calcular proximidade temporal
    score_valor = verificar menção de valor no corpo
    score_keywords = contar palavras suspeitas
    score_remetente = verificar se é VIP
    score_beneficiario = match de nomes/descrições
    score_assunto = verificar relevância do assunto
    
    score_total = soma de todos os scores
    score_normalizado = (score_total / 115) * 100
    
  Retorna melhor match para cada transação
```

**Classificação de Risco:**
- **Alto Risco:** Score ≥ 60
- **Médio Risco:** 45 ≤ Score < 60
- **Baixo Risco:** Score < 45

**Dados:**
- Usa `TransactionAgent` e `EmailAgent` internamente
- Janela temporal configurável (padrão: 7 dias)

---

### Fluxo de Trabalho Típico

#### 1. **Ingestão de Dados**
```bash
# Executar scripts de ingestão
python scripts/ingest_policy.py      # Indexa política
python scripts/ingest_emails.py      # Parseia e indexa e-mails
python scripts/ingest_transactions.py # Normaliza transações
```

#### 2. **Análise Individual**
```python
# Verificar política
agent = RAGPolicyAgent()
resposta = agent.answer("Qual o limite de despesas?")

# Detectar conspiração
agent = EmailAgent()
resultado = agent.detect_conspiracy()

# Verificar violações diretas
agent = TransactionAgent()
violacoes = agent.run_rules()
```

#### 3. **Correlação Cruzada**
```python
# Conectar transações com e-mails
agent = CorrelationAgent()
correlacoes = agent.correlate_all()
# Retorna: transações ranqueadas por score de correlação
```

### Casos de Uso

**Cenário 1: Auditoria Completa**
1. `TransactionAgent` identifica despesa de $800 em "WUPHF Tech"
2. `CorrelationAgent` encontra e-mail de Michael Scott no mesmo dia mencionando "mascarar custos"
3. `RAGPolicyAgent` confirma que despesas > $500 requerem PO
4. **Resultado:** Violação HIGH + Correlação 85/100 + Política violada

**Cenário 2: Investigação de Conspiração**
1. `EmailAgent` detecta palavras-chave suspeitas ("operação fênix", "destruir evidências")
2. Busca semântica encontra múltiplos e-mails relacionados a Toby
3. **Resultado:** Conspiração detectada com evidências

**Cenário 3: Consulta de Compliance**
1. Usuário pergunta: "Posso comprar algemas?"
2. `RAGPolicyAgent` busca na política
3. **Resultado:** "Não. Item proibido na Lista Negra (Seção 3)"

### Interface CLI

O sistema oferece menu interativo via `cli/run.py`:

```bash
python cli/run.py
# ou
./cli/menu.sh
```

**Comandos disponíveis:**
- `ingest` - Ingestar todos os dados
- `rag` - Perguntar sobre política
- `emails` - Scan de e-mails (conspiração)
- `transactions` - Scan de transações (regras)
- `correlate` - Análise de correlação completa

### Tecnologias Utilizadas

- **Embeddings:** Google Gemini `text-embedding-004`
- **LLM:** Google Gemini `gemini-1.5-flash`
- **Vector DB:** FAISS (Facebook AI Similarity Search)
- **Data Processing:** Pandas, LangChain Text Splitters
- **CLI:** Typer + Rich (interface bonita no terminal)

### Segurança e Privacidade

- Dados processados localmente (exceto chamadas API)
- Embeddings e índices armazenados em `vectorstore/`
- Nenhum dado bruto enviado para APIs (apenas chunks relevantes)
- Chaves API em `.env` (não comitadas)

---

## Uso
