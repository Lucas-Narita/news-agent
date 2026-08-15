# CLAUDE.md — news-agent

Este arquivo é lido automaticamente pelo Claude Code ao abrir o terminal neste projeto.
Contém todas as decisões de arquitetura tomadas antes da criação do repo.

---

## O que é esse projeto

**news-agent** — API Orchestration Agent com arquitetura multi-agent.

Agent CLI que agrega notícias e tendências de tech em tempo real (HackerNews, GitHub Trending, NewsAPI, Reddit, Dev.to, Lobsters, arXiv), processa com Claude API, e gera um digest narrativo em Markdown + terminal.

**Objetivo:** projeto de portfólio público para posicionamento como AI Agent Engineer.
**Proprietário:** Lucas Narita
**Status:** seções 1–8 implementadas e testadas, mais evoluções (7 fontes, dedupe por URL canônica, ranking determinístico, retry com backoff, cache com TTL, modelo/categoria/timeout configuráveis, `--limit`/`--verbose`/`--format json`/`--cache`/`--output-dir`, comando `sources`) — 188 testes (cobertura ≥80%), CI no GitHub Actions (lint + format + testes), LICENSE MIT. Pronto como peça de portfólio.

---

## Stack decidida

| Componente | Tecnologia | Justificativa |
|---|---|---|
| Linguagem | Python 3.11+ | Melhor ecossistema LLM |
| CLI | Typer | Tipado, auto-documenta --help |
| Schemas/validação | Pydantic v2 | Contratos entre agents |
| LLM | Claude API (Anthropic) | Coerente com posicionamento |
| Paralelismo | asyncio | Agents rodam em paralelo |
| Config | pydantic-settings | Variáveis de ambiente tipadas |
| Output terminal | rich | Formatação profissional |
| Packaging | pyproject.toml | Padrão moderno (PEP 517/518) |
| Testes | pytest + pytest-asyncio | Async-first |

---

## Arquitetura: multi-agent com orquestrador

```
CLI (Typer)
 └─► Orchestrator
       ├─► HackerNewsAgent  ─┐
       ├─► GitHubAgent       ├─► asyncio.gather() → AgentResult[]
       └─► NewsAPIAgent     ─┘
             │
             ▼
        LLM Client (Claude API)
             │
             ▼
     console (rich) + output/digest-YYYY-MM-DD-HH.md
```

**Princípio central:** cada agent é independente. O orquestrador não sabe qual API cada agent usa — só chama `.fetch()` e recebe `AgentResult`. Adicionar um novo agent = criar o arquivo + registrar. O orquestrador não muda.

---

## Estrutura de pastas

```
news-agent/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── news_agent/
│   ├── __init__.py
│   ├── cli.py               # entry point Typer
│   ├── config.py            # pydantic-settings
│   ├── orchestrator.py      # lógica de orquestração
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py          # BaseAgent ABC
│   │   ├── hackernews.py
│   │   ├── github.py
│   │   └── newsapi.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── models.py        # Article, AgentResult, DigestOutput
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py        # wrapper Claude API
│   │   └── prompts.py       # templates de prompt
│   │
│   └── output/
│       ├── __init__.py
│       ├── markdown.py
│       └── console.py
│
├── output/                  # digests gerados (.gitignore)
└── tests/
    ├── __init__.py
    ├── test_agents.py
    └── test_orchestrator.py
```

---

## Contratos de dados (Pydantic schemas)

```python
# news_agent/schemas/models.py

class Article(BaseModel):
    title: str
    url: str
    source: str          # "hackernews" | "github" | "newsapi"
    score: int | None = None
    published_at: datetime | None = None
    summary: str | None = None

class AgentResult(BaseModel):
    source: str
    articles: list[Article]
    fetched_at: datetime
    error: str | None = None  # falha graceful — sistema continua sem esse agent

class DigestOutput(BaseModel):
    narrative: str
    sources_used: list[str]
    total_articles: int
    generated_at: datetime
```

**Regra importante:** agents nunca levantam exceção. Erros vão em `AgentResult.error`. O sistema degrada graciosamente — se NewsAPI cair, o digest é gerado com HackerNews + GitHub.

---

## Base agent

```python
# news_agent/agents/base.py

from abc import ABC, abstractmethod
from news_agent.schemas.models import AgentResult

class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> AgentResult:
        """Busca e normaliza dados. Nunca levanta exceção."""
        ...
```

---

## Decisões arquiteturais importantes (para entrevista)

1. **Por que multi-agent em vez de script linear?**
   Cada fonte tem rate limit, latência e formato diferentes. Paralelismo real com asyncio reduz tempo de resposta de ~9s (3×3s) para ~3s. E o contrato via BaseAgent permite extensão sem modificar o orquestrador (Open/Closed Principle).

2. **Por que Pydantic nos schemas?**
   Validação na borda de cada agent — se a API externa mudar o formato, o erro aparece com mensagem clara no AgentResult, não como KeyError silencioso no meio do sistema.

3. **Por que `AgentResult.error` em vez de try/except no orquestrador?**
   O orquestrador não precisa conhecer os tipos de falha de cada API. A degradação graceful é parte do contrato do agent, não uma responsabilidade do orquestrador.

4. **Por que prompts separados do código?**
   Prompt é configuração, não lógica. Muda frequentemente durante tuning sem justificar um commit de código.

5. **Por que LLM só na etapa de geração do narrative?**
   Coleta, normalização e filtragem são feitas por código determinístico. LLM só entra onde precisa de linguagem natural. Isso reduz custo de API e torna o pipeline testável sem mock de LLM.

---

## Status de implementação

Todas as seções de design foram implementadas e testadas:

- [x] Seção 1: Arquitetura geral (fluxo, stack, APIs)
- [x] Seção 2: Estrutura de pastas e contratos de dados
- [x] Seção 3: Config + CLI (`pyproject.toml`, `config.py`, `cli.py`)
- [x] Seção 4: BaseAgent + implementação dos 3 agents
- [x] Seção 5: Orchestrator (`asyncio.gather`, degradação graceful)
- [x] Seção 6: LLM client + prompt strategy (com prompt caching)
- [x] Seção 7: Output (markdown formatter + console rich)
- [x] Seção 8: Testes + README

**Evoluções pós-design (mantendo a arquitetura base):**

- [x] Qualidade de dados: deduplicação por URL + ranking por score (`processing.py`) + flag `--limit`
- [x] Resiliência: retry com backoff exponencial (`retry.py`), timeout configurável (`REQUEST_TIMEOUT`), logging estruturado (`logging_config.py`, `--verbose`)
- [x] Fontes adicionais: Reddit, Dev.to, Lobsters, arXiv (total de 7, todas via `BaseAgent`)
- [x] Output composável: `--format json` (digest serializado, stdout limpo para pipe)
- [x] Determinismo: seções ordenadas pela ordem declarada das fontes e desempate de ranking
  por recência + URL — a mesma entrada gera sempre o mesmo Markdown
- [x] Configuração: `CACHE_TTL`, `ANTHROPIC_MODEL`, `MAX_TOKENS` e `ARXIV_CATEGORY` em `Settings`
- [x] Resiliência de parsing: todo agent descarta itens malformados individualmente
  (`_parse_*`), nunca perdendo a fonte inteira por causa de um item

**Qualidade:** 188 testes (mockados, sem rede), cobertura ≥80% com gate no pytest,
CI no GitHub Actions (lint + format + testes em Python 3.11/3.12/3.13), LICENSE MIT.

---

## Como continuar

O design base está completo. A partir daqui, evoluções típicas:

- **Adicionar uma nova fonte:** criar `news_agent/agents/<fonte>.py` (subclasse de
  `BaseAgent`) e registrá-la em `agents/registry.py`. `Settings.default_sources` e a CLI
  derivam dali. Também adicionar a fonte em `llm/prompts.py::SOURCE_GUIDANCE` e em
  `output/markdown.py::SOURCE_LABELS` — há teste garantindo que o prompt cobre todas as
  fontes registradas.
- **Ajustar a estratégia de prompt:** editar `news_agent/llm/prompts.py`.

---

## APIs utilizadas

| API | Auth | Limite free |
|---|---|---|
| HackerNews | Nenhuma | Sem limite |
| GitHub | Token opcional | 60 req/h sem token, 5000 com |
| NewsAPI | API key obrigatória | 100 req/dia (dev tier) |
| Claude API | API key obrigatória | Pago por token |

## Variáveis de ambiente necessárias

```
ANTHROPIC_API_KEY=
NEWSAPI_KEY=
GITHUB_TOKEN=          # opcional, aumenta rate limit
```

---

## Regras desse projeto

- Não adicionar dependências sem justificativa técnica explícita
- Não usar `print()` — usar `logging` ou `rich`
- Não commitar `.env` — apenas `.env.example`
- Não usar `dict` onde Pydantic resolve — schemas são o contrato
- Código em inglês, comentários e README em inglês
- Commits em inglês, mensagens descritivas
