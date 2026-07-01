# Frontend web (Next.js) — Design

**Data:** 2026-07-01
**Autor:** Lucas Narita (com Claude Code)
**Status:** Revisado após review adversarial (5 lentes), pendente review final do usuário
**Escopo:** Adicionar um front-end estático que exibe o digest de notícias gerado pelo `news-agent`.

> **Nota de revisão:** este spec passou por um painel adversarial de 5 lentes (arquitetura, segurança, a11y/perf, testabilidade, escopo/DX), cada uma lendo o spec **e o código real**. Foram incorporados 1 achado crítico, 7 high e 5 medium/low. Ver §11.

---

## 1. Contexto e objetivo

O `news-agent` é um agent CLI multi-agent que agrega notícias de tech de 6 fontes, processa com a Claude API e produz um `DigestOutput` (narrativa em Markdown + artigos estruturados). Hoje a saída é consumível por CLI (`--format json`), mas não há superfície web.

**Objetivo:** construir uma peça de portfólio **ponta-a-ponta** — o agent Python produz o dado, um front Next.js o exibe — reforçando o posicionamento de AI Agent Engineer. O front expõe visualmente a fronteira `DigestOutput (Pydantic) → JSON → UI`, evidenciando design de contrato entre produtor e consumidor.

**Não-objetivo (v1):** histórico navegável de digests, API HTTP em tempo real, autenticação, personalização.

---

## 2. Decisões travadas

| Decisão | Escolha | Razão |
|---|---|---|
| Topologia | **Monorepo** — front em `web/` | Uma peça coesa; um link de portfólio conta a história inteira |
| Entrega de dados | **JSON pré-gerado + front estático** | Custo ~zero, sem key no client, deploy grátis |
| Stack front | **Next.js (App Router) + TypeScript + Tailwind v4** | Domínio de React/TS; SSG idiomático; tokens via `@theme` |
| Cadência de geração | **Cron diário (04:00 UTC) + `workflow_dispatch`** | Automação real visível; custo baixo |
| Escopo v1 | **Front mostra só o último digest**; pipeline **versiona por data** | YAGNI no front, porta aberta pra histórico em v2 |
| Deploy | **Vercel + SSG (build-time, sem `output: export`)** | Auto-deploy no push; headers via `vercel.json` |
| Estética | **Bento / Neo-brutalism, paleta mostarda + grafite** | Personalidade sem perder seriedade; cor semântica |
| Roster de agents | **Estender `DigestOutput` com `agents[]`** (roster completo + status) | Exibir status por agent é o diferencial multi-agent; e é honesto |

---

## 3. Arquitetura & fluxo de dados

```
GitHub Actions  (schedule: '0 4 * * *'  +  workflow_dispatch)
  │  pip install -e .
  │  news-agent run --format json --no-file       ← CLI existente (após fix de logging→stderr)
  │        └─ orchestrator.run_digest() → DigestOutput  (Claude + agents, asyncio.gather)
  │  valida o JSON (json.load)  ← FALHA o job se inválido, antes de qualquer commit
  │  grava  web/public/latest.json                (servido ao front)
  │      +  data/digests/digest-<AAAA-MM-DD>.json  (arquivo bruto, FORA do bundle Vercel)
  │  git pull --rebase --autostash → commit → push (com retry)
  └────────► Vercel detecta o push → next build (SSG lê latest.json) → deploy estático
```

**Princípio:** produtor (agent) e consumidor (front) se comunicam **apenas** pelo `latest.json`. O contrato é o `DigestOutput`. `data/digests/` fica **fora de `web/public/`** para a Vercel não empacotar um monte de JSON crescente (é seguro-de-dado bruto, não uma feature).

---

## 4. Backend: mudanças no Python (pré-requisito)

O review revelou que o front depende de correções no agent. Estas entram **antes** do front no plano.

### 4.1 [CRÍTICO] Logging para stderr — senão o `latest.json` é envenenado
Hoje `configure_logging()` anexa `RichHandler()` sem `console=`, mandando logs pro **stdout**. `orchestrator.py:47` faz `logger.warning(...)` em nível WARNING (default) sempre que uma fonte falha — rotina no design graceful. Isso polui o stdout **antes** do JSON → `> latest.json` grava JSON inválido → commitado → build quebra.
- `news_agent/logging_config.py`: `RichHandler(console=Console(stderr=True), ...)`.
- `news_agent/cli.py` (branches de erro de config, ~l.124/130): `console.print` → `err_console.print`.
- **Teste de regressão:** rodar o CLI com uma fonte forçada a falhar e afirmar que `json.loads(stdout)` tem sucesso.

### 4.2 [HIGH] `published_at` timezone-aware em TODOS os agents
`hackernews.py:47` e `reddit.py:29` usam `datetime.fromtimestamp(t)` → **naive** (sem offset). Pydantic serializa sem `Z`/offset → o Zod (`datetime({offset:true})`) rejeitaria → build quebra no 1º digest com artigo de HN/Reddit.
- HN/Reddit: `datetime.fromtimestamp(t, tz=timezone.utc)`.
- Auditar devto/github/newsapi/lobsters (usam `fromisoformat`) e garantir tz-aware UTC.
- `orchestrator.py`: os dois `datetime.now()` → `datetime.now(timezone.utc)` (para `generated_at`).
- **Teste:** cada agent produz `published_at` tz-aware; um fixture inclui artigo com timestamp de HN.

### 4.3 [HIGH · decisão A] Roster de agents no contrato
```python
class AgentStatus(BaseModel):
    name: str
    ok: bool
    article_count: int

class DigestOutput(BaseModel):
    narrative: str
    sources_used: list[str]
    total_articles: int
    generated_at: datetime
    articles: list[Article] = []
    agents: list[AgentStatus] = []          # NOVO — roster completo das fontes tentadas
```
- `orchestrator.run_digest`: no loop sobre `results`, montar um `AgentStatus` por fonte **tentada** (`ok = result.error is None`, `article_count = len(result.articles)`).
- O `AgentsBlock` exibe esse roster **fielmente** ("N agents · M com dados"), sem hardcodar "6". Sobrevive a adicionar uma 7ª fonte (Open/Closed).
- **Teste:** roster reflete sucessos e falhas (uma fonte com `error` aparece com `ok=false`).

### 4.4 Fixture de contrato (gerado pelo Python)
- Um pytest serializa um `DigestOutput` canônico (incluindo um artigo com timestamp naive-de-origem já normalizado, um agent `ok=false`) para `web/__fixtures__/digest.sample.json`.
- Em CI Python, regenerar e `git diff --exit-code` — um schema que muda sem atualizar o fixture **falha o job** (detecta drift de verdade; um fixture escrito à mão mascararia).

---

## 5. Pipeline de geração (`.github/workflows/digest.yml`)

**Abordagem A: orquestração no shell** (o CLI já entrega o JSON; o workflow redireciona e versiona). Zero código Python de publicação. Mantém o CLI agnóstico (Single Responsibility).

```yaml
name: Generate digest
on:
  schedule: [{ cron: '0 4 * * *' }]   # 04:00 UTC diário
  workflow_dispatch: {}
permissions:
  contents: write
concurrency: { group: digest, cancel-in-progress: false }
jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with: { python-version: '3.12' }
      - run: pip install -e .
      - name: Generate + validate JSON
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          NEWSAPI_KEY: ${{ secrets.NEWSAPI_KEY }}       # opcional
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}     # opcional; token automático do Actions (rate limit da API do GitHub). config.py lê a env var GITHUB_TOKEN
        run: |
          mkdir -p web/public data/digests
          news-agent run --format json --no-file > web/public/latest.json
          python -c "import json,sys; json.load(open('web/public/latest.json'))"   # falha se inválido
          cp web/public/latest.json "data/digests/digest-$(date -u +%F).json"
      - name: Commit (rebase + retry)
        run: |
          git config user.name  "news-agent-bot"
          git config user.email "bot@users.noreply.github.com"
          git add web/public/latest.json data/digests/
          git diff --cached --quiet && exit 0
          git commit -m "chore: update digest $(date -u +%F)"
          for i in 1 2 3; do
            git pull --rebase --autostash origin main && git push && break
            sleep 5
          done
```

**Requisitos:** secret `ANTHROPIC_API_KEY` (obrigatório; o usuário configurará). `NEWSAPI_KEY`/`GH_READ_TOKEN` opcionais.
**Sem loop de CI:** `digest.yml` roda por schedule/dispatch (não por push); `ci.yml` roda por push mas não commita. O push do bot dispara só o deploy da Vercel.
**Validação pré-commit** (`json.load`) garante que um run degradado falha **ruidosamente** em vez de envenenar a `main`.

---

## 6. Front-end (Next.js)

### 6.1 Stack
- **Next.js App Router + TypeScript**, **Tailwind v4** (tokens via `@theme` em `globals.css`; `@tailwindcss/postcss`; **sem** `tailwind.config.ts`).
- **`react-markdown` + `rehype-sanitize`** para a narrativa (wiring explícito — ver 6.5).
- **`zod`** para validar/derivar tipos do `latest.json`.
- **`next/font`** (Space Grotesk display + Inter corpo) — self-hosted.
- Página **SSG na Vercel** (Server Components lendo `fs` no build; **sem** `output: export`; nenhuma dynamic API).

### 6.2 Estrutura de arquivos
```
web/
├── app/
│   ├── layout.tsx          # root: fontes, <html lang>, metadata/SEO
│   ├── page.tsx            # loader fino: loadDigest() → <DigestView/>
│   ├── globals.css         # @theme (tokens) + @media reduced-motion
│   └── not-found.tsx
├── components/
│   ├── digest/
│   │   ├── DigestView.tsx      # apresentacional puro: recebe Digest | null (a costura testável)
│   │   ├── DigestHero.tsx      # bloco dominante: narrativa da IA
│   │   ├── Narrative.tsx       # react-markdown + sanitize (Server Component)
│   │   ├── ArticleGrid.tsx     # grade bento (Server Component)
│   │   ├── ArticleCard.tsx     # card de artigo (link validado, fonte, score, summary)
│   │   ├── MetaBlock.tsx       # total + generated_at
│   │   └── AgentsBlock.tsx     # roster de agents (agents[] com ✓/✗ + contagem)
│   └── ui/
│       └── BrutalCard.tsx      # primitivo: borda grossa + sombra dura
├── lib/
│   ├── digest.ts           # Zod schema + type + loadDigest() (readFileSync, síncrono)
│   └── url.ts              # isSafeHref(): allowlist http/https
├── public/latest.json      # ← pipeline grava aqui (o único dado servido)
├── __fixtures__/digest.sample.json   # gerado pelo Python (§4.4)
├── package.json · tsconfig.json · next.config.mjs · postcss.config.mjs · vercel.json
```
(`data/digests/` fica na **raiz do repo**, fora de `web/`.)

### 6.3 Componentes (unidades isoladas)

| Componente | Responsabilidade | Server/Client |
|---|---|---|
| `BrutalCard` | Primitivo: borda + sombra dura | Server |
| `DigestView` | Layout bento; recebe `Digest \| null`; decide populated/empty | Server |
| `DigestHero` | Narrativa da IA | Server |
| `Narrative` | Markdown sanitizado (build-time) | **Server (obrigatório)** |
| `ArticleGrid` / `ArticleCard` | Grade + card de artigo | Server |
| `MetaBlock` | `total_articles` + `generated_at` | Server |
| `AgentsBlock` | Roster `agents[]` com status | Server |

`Narrative`/`ArticleGrid`/cards **têm de ser Server Components** — react-markdown + a árvore unified/micromark (~40–60kb) renderizam no build e enviam **0 JS** ao cliente. Um `'use client'` acidental estoura o budget.

### 6.4 Design tokens (`globals.css`, Tailwind v4 `@theme`)
```css
@theme {
  --color-bg: #ece7dd;         /* creme base */
  --color-surface: #faf7f0;    /* cards claros */
  --color-ink: #1c1c1c;        /* texto/bordas (grafite quase-preto) */
  --color-graphite: #2b2b2b;   /* blocos escuros */
  --color-accent: #e8b923;     /* mostarda (assinatura) */
  --duration-fast: 150ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}
/* borda/sombra brutalist como utilitários/classe .brutal-card */
@media (prefers-reduced-motion: reduce) {
  .brutal-card { transition: none }
  .brutal-card:hover { transform: none }   /* mantém a troca de sombra/cor, remove o translate */
}
```
**Cor semântica com contraste correto:** mostarda é **fill/borda/underline**, nunca texto sobre superfície clara (mostarda em creme = 1.5:1, reprova). Números de **score** vão em tinta `#1c1c1c` (9.25:1) **ou** num chip grafite `#2b2b2b` (mostarda-em-grafite = 7.68:1).

### 6.5 Dados, validação & segurança (borda)
- `lib/digest.ts`: `AgentStatusSchema`, `ArticleSchema`, `DigestSchema` em **Zod**; tipo = `z.infer` (fonte única).
  - `generated_at`/`published_at`: `z.string().datetime({ offset: true })` (tolera offset; casa com o Python tz-aware).
  - `url`: validado por `isSafeHref` (não só `.url()`) — só `http:`/`https:`.
- `loadDigest(): Digest | null` — **síncrona** (`readFileSync`), roda no build: ausente → `null`; presente e inválido → `throw` (falha o build; fail fast).
- **`lib/url.ts` `isSafeHref(u)`**: parseia e retorna `true` só se protocolo ∈ {`http:`,`https:`}; barra `javascript:`,`data:`,`vbscript:`,`blob:`,`file:`. Aplicado em **todo** href de artigo; se falhar, renderiza texto inerte (sem `<a>`).
- **Narrativa (`Narrative.tsx`)**: `<ReactMarkdown rehypePlugins={[rehypeSanitize]}>` — **sanitize explícito**; `rehype-raw` **OFF**. `components` demovendo `h1→h2` (a narrativa LLM começa com `# …` → garantir **um único `<h1>`** autoral na página).
- **Links de artigo**: `target="_blank"` + `rel="noopener noreferrer"`.
- **Nenhum secret no front**; o `latest.json` é público e não contém nada sensível (só dados de notícia).

### 6.6 Headers HTTP (`vercel.json`)
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy: default-src 'self'; img-src 'self' data: https:;
  style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';
  object-src 'none'; base-uri 'self'; frame-ancestors 'none'
```
CSP **pragmático pra estático**: Next injeta script/style inline de hydration, então `'unsafe-inline'` é aceito (o nonce ideal exigiria middleware → rendering dinâmico, o que contradiz SSG). Validar contra um `next build` real.

### 6.7 Acessibilidade & performance
- HTML semântico (`<header>`, `<main>`, `<article>` nos cards), **um único `<h1>`** (garantido pelo demote no Narrative).
- Contraste verificado — **pares reais**: preto/mostarda 9.25:1 ✓; branco/grafite 14.16:1 ✓; mostarda/grafite 7.68:1 ✓; score em tinta/creme 9.25:1 ✓. Mostarda/creme **evitado**.
- Hover/focus/active desenhados: sombra cresce + `transform` (compositor-friendly); `@media (prefers-reduced-motion: reduce)` remove o translate (§6.4).
- Foco de teclado visível; SSG + `next/font` → LCP baixo, CLS ~0; budget < 150kb garantido por Server Components + **gate de bundle size** no CI (§8).

---

## 7. Estratégia de testes (TDD: RED → GREEN → REFACTOR)

**Python (pytest):**
- Regressão de logging: CLI com fonte falha → `json.loads(stdout)` sucede (§4.1).
- `published_at` tz-aware em todos os agents (§4.2).
- Roster `agents[]` reflete ok/falha (§4.3).
- Fixture gerado + `git diff --exit-code` em CI (§4.4).

**Front unit (Vitest + RTL):**
- `DigestView` **RED-first** com `null` (empty state) e populado — a costura de §6.2 torna isso testável sem mock de `fs`.
- `loadDigest`: válido → objeto; ausente → `null`; inválido → lança.
- `isSafeHref` / `ArticleCard`: `javascript:`/`data:` → href neutralizado (texto inerte); `http(s)` → link.
- `Narrative`: payload malicioso renderiza **inerte**; zero `<h1>` na narrativa + ordem de headings monotônica.
- `DigestSchema.parse(fixture)` sucede (contrato Python↔Zod via o fixture de §4.4).

**E2E / visual (Playwright):**
- Screenshots em 320/768/1024/1440.
- Build **com `latest.json` ausente** → empty state renderiza (sem crash).
- axe sem violações; assert de reduced-motion (mock `matchMedia`).

---

## 8. Critérios de sucesso (Definition of Done do v1)
- [ ] Correções §4 aplicadas; `ci.yml` do Python verde (logging→stderr, datetime UTC, roster, fixture).
- [ ] `digest.yml` gera+**valida** `latest.json`, versiona em `data/digests/`, commita com rebase/retry, Vercel deploya.
- [ ] `web/` builda estático (`next build`) com o digest embutido; **bundle < 150kb** (gate no CI).
- [ ] Testes Python + front unit + E2E passam; axe sem violações; Lighthouse LCP < 2.5s.
- [ ] Estética fiel ao mockup (bento brutalist, mostarda + grafite); todos os pares de contraste ≥ AA.
- [ ] `AgentsBlock` mostra o roster real (não "6" fixo); XSS de link/narrativa coberto por teste.

---

## 9. Fora de escopo (candidatos a v2)
- Histórico navegável (`/digests/[data]`) consumindo os JSONs de `data/digests/`.
- Busca/filtro por fonte; feed RSS/Atom; dark mode (variante "carvão" fica como opção futura).

---

## 10. Riscos & mitigações
| Risco | Mitigação |
|---|---|
| Cron do GitHub atrasa/pula em pico | `workflow_dispatch` manual; `generated_at` comunica frescor |
| Drift de schema Python↔Zod | Fixture gerado pelo Python + `git diff` em CI + Zod carrega o mesmo arquivo |
| JSON envenenado por log/erro | Logging→stderr (§4.1) + validação `json.load` pré-commit (§5) |
| `datetime` naive quebra o build | Normalização UTC nos agents + Zod `{offset:true}` (§4.2) |
| Race no push do bot | `git pull --rebase --autostash` + retry (§5) |
| Custo da Claude API | 1 geração/dia + prompt caching → centavos/mês |
| `use client` acidental estoura budget | Server Components fixados + gate de bundle no CI |

---

## 11. Apêndice — achados do review adversarial (incorporados)
| # | Sev | Achado | Onde tratei |
|---|---|---|---|
| 1 | CRÍTICO | Logs no stdout envenenam o `latest.json` | §4.1, §5 (validação) |
| 2 | HIGH | `published_at` naive quebra o Zod; contrato não wired | §4.2, §4.4, §6.5 |
| 3 | HIGH | URL de artigo sem allowlist → XSS | §6.5 (`isSafeHref`), §7 |
| 4 | HIGH | react-markdown não sanitiza sozinho; múltiplos `<h1>` | §6.5, §7 |
| 5 | HIGH | Headers incompletos; CSP quebra hydration | §6.6 |
| 6 | HIGH | Mostarda no score ilegível (1.5:1) | §6.4, §6.7 |
| 7 | HIGH | "6 agents" não derivável do contrato | §2, §4.3 (decisão A) |
| 8 | HIGH | `page.tsx` sem costura pra teste do empty state | §6.2 (`DigestView`), §7 |
| 9 | MED | `git push` sem rebase/retry | §5 |
| 10 | MED | reduced-motion sem mecanismo | §6.4, §7 |
| 11 | MED | Tailwind versão não fixada | §2, §6.1 (v4) |
| 12 | LOW | Budget depende de Server Components | §6.3, §8 (gate) |
| 13 | LOW | `digests/` acumula no bundle Vercel | §3 (movido p/ `data/`) |
