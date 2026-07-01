# Frontend (Next.js) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Prerequisite:** Plan A (`2026-07-01-backend-contract-and-pipeline.md`) must be complete — this plan consumes `web/__fixtures__/digest.sample.json`.

**Goal:** A static Next.js site (bento neo-brutalism, mustard + graphite) that renders the latest digest — narrative + article grid + metadata + agent roster — from `web/public/latest.json` at build time.

**Architecture:** App Router, all Server Components (react-markdown renders at build → 0 client JS). `page.tsx` is a thin loader calling a synchronous `loadDigest()` and delegating to a pure `<DigestView digest={Digest|null}/>` that is unit-tested for both empty and populated states. Zod validates at the boundary. Security headers via `vercel.json`.

**Tech Stack:** Next.js (App Router) + TypeScript, Tailwind v4 (`@theme`), zod, react-markdown + rehype-sanitize, Vitest + React Testing Library, Playwright + axe.

## Global Constraints

- **Tailwind v4** — tokens via `@theme` in `globals.css`; no `tailwind.config.ts`.
- **All digest components are Server Components** — no `'use client'`; react-markdown must render at build time (keeps JS bundle < 150kb).
- **SSG on Vercel** — no `output: 'export'`; no dynamic APIs in the render path; `loadDigest` is synchronous (`readFileSync`).
- **Palette (semantic):** `--color-bg:#ece7dd`, `--color-surface:#faf7f0`, `--color-ink:#1c1c1c`, `--color-graphite:#2b2b2b`, `--color-accent:#e8b923`. Mustard is fill/border only — **never text on a light surface**. Score text is `--color-ink` (9.25:1).
- **Single `<h1>`** on the page (narrative headings demoted h1→h2).
- **Only `http:`/`https:` hrefs** rendered as links; anything else → inert text.
- Vercel Root Directory = `web/`. Commits in English, conventional format, no attribution trailer. Branch `feat/web-frontend`.

---

### Task 1: Scaffold Next.js + Tailwind v4 + test tooling

**Files:**
- Create: `web/` (via create-next-app), then `web/vitest.config.ts`, `web/vitest.setup.ts`
- Modify: `web/app/globals.css`, `web/package.json`

**Interfaces:**
- Produces: a buildable `web/` app; `npm run test` (Vitest) and `npm run build` wired.

- [ ] **Step 1: Scaffold (non-interactive)**

Run from repo root:
```bash
npx create-next-app@latest web --typescript --tailwind --app --no-src-dir --eslint --import-alias "@/*" --use-npm
```
Expected: `web/` created with App Router + Tailwind v4.

- [ ] **Step 2: Add runtime + test dependencies**

```bash
cd web
npm install zod react-markdown rehype-sanitize
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom @playwright/test @axe-core/playwright
```

- [ ] **Step 3: Configure Vitest**

Create `web/vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
  },
});
```
Create `web/vitest.setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
```
Add scripts to `web/package.json`:
```json
"scripts": {
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "test": "vitest run",
  "test:e2e": "playwright test"
}
```

- [ ] **Step 4: Replace `globals.css` with the design tokens**

Replace `web/app/globals.css` with:
```css
@import "tailwindcss";

@theme {
  --color-bg: #ece7dd;
  --color-surface: #faf7f0;
  --color-ink: #1c1c1c;
  --color-graphite: #2b2b2b;
  --color-accent: #e8b923;
  --font-display: "Space Grotesk", ui-sans-serif, sans-serif;
  --font-body: "Inter", ui-sans-serif, sans-serif;
}

body { background: var(--color-bg); color: var(--color-ink); font-family: var(--font-body); }

.brutal-card {
  border: 2.5px solid var(--color-ink);
  box-shadow: 4px 4px 0 var(--color-ink);
  transition: transform 150ms cubic-bezier(0.16, 1, 0.3, 1), box-shadow 150ms;
}
.brutal-card:hover { transform: translate(-2px, -2px); box-shadow: 6px 6px 0 var(--color-ink); }

@media (prefers-reduced-motion: reduce) {
  .brutal-card { transition: none; }
  .brutal-card:hover { transform: none; }  /* keep the instant shadow, drop the translate */
}
```

- [ ] **Step 5: Verify build + empty test run**

Run: `cd web && npm run build && npm run test`
Expected: build succeeds; Vitest runs (0 tests found is fine at this point).

- [ ] **Step 6: Commit**

```bash
git add web/ && git commit -m "chore(web): scaffold Next.js app with Tailwind v4 tokens and Vitest"
```

---

### Task 2: Contract layer — `isSafeHref`, Zod schema, `loadDigest`

**Files:**
- Create: `web/lib/url.ts`, `web/lib/digest.ts`
- Test: `web/lib/url.test.ts`, `web/lib/digest.test.ts`

**Interfaces:**
- Produces: `isSafeHref(url: string): boolean`; `DigestSchema` (zod), `type Digest`, `type Article`, `loadDigest(): Digest | null`.
- Consumes: `web/__fixtures__/digest.sample.json` (from Plan A).

- [ ] **Step 1: Write failing tests for `isSafeHref`**

Create `web/lib/url.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { isSafeHref } from "./url";

describe("isSafeHref", () => {
  it("allows http and https", () => {
    expect(isSafeHref("https://example.com")).toBe(true);
    expect(isSafeHref("http://example.com")).toBe(true);
  });
  it("rejects dangerous schemes and garbage", () => {
    for (const u of ["javascript:alert(1)", "data:text/html,x", "vbscript:x", "file:///etc", "not a url"]) {
      expect(isSafeHref(u)).toBe(false);
    }
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run lib/url.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `isSafeHref`**

Create `web/lib/url.ts`:
```ts
export function isSafeHref(url: string): boolean {
  try {
    const { protocol } = new URL(url);
    return protocol === "http:" || protocol === "https:";
  } catch {
    return false;
  }
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd web && npx vitest run lib/url.test.ts`
Expected: PASS

- [ ] **Step 5: Write failing tests for the schema + loader**

Create `web/lib/digest.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { DigestSchema } from "./digest";

const FIXTURE = path.join(process.cwd(), "__fixtures__", "digest.sample.json");

describe("DigestSchema", () => {
  it("parses the Python-generated fixture", () => {
    const raw = JSON.parse(readFileSync(FIXTURE, "utf-8"));
    const parsed = DigestSchema.parse(raw);
    expect(parsed.agents.length).toBe(3);
    expect(parsed.articles[0].url).toMatch(/^https?:/);
  });
  it("rejects an article with an unsafe url", () => {
    const raw = JSON.parse(readFileSync(FIXTURE, "utf-8"));
    raw.articles[0].url = "javascript:alert(1)";
    expect(() => DigestSchema.parse(raw)).toThrow();
  });
});
```

- [ ] **Step 6: Run to verify it fails**

Run: `cd web && npx vitest run lib/digest.test.ts`
Expected: FAIL — `DigestSchema` not found.

- [ ] **Step 7: Implement the schema + loader**

Create `web/lib/digest.ts`:
```ts
import { readFileSync } from "node:fs";
import path from "node:path";
import { z } from "zod";
import { isSafeHref } from "./url";

const AgentStatusSchema = z.object({
  name: z.string(),
  ok: z.boolean(),
  article_count: z.number().int(),
});

const ArticleSchema = z.object({
  title: z.string(),
  url: z.string().refine(isSafeHref, { message: "unsafe url scheme" }),
  source: z.string(),
  score: z.number().int().nullable().optional(),
  published_at: z.string().datetime({ offset: true }).nullable().optional(),
  summary: z.string().nullable().optional(),
});

export const DigestSchema = z.object({
  narrative: z.string(),
  sources_used: z.array(z.string()),
  total_articles: z.number().int(),
  generated_at: z.string().datetime({ offset: true }),
  articles: z.array(ArticleSchema),
  agents: z.array(AgentStatusSchema),
});

export type Digest = z.infer<typeof DigestSchema>;
export type Article = z.infer<typeof ArticleSchema>;

export function loadDigest(): Digest | null {
  const file = path.join(process.cwd(), "public", "latest.json");
  let raw: string;
  try {
    raw = readFileSync(file, "utf-8");
  } catch {
    return null; // absent → empty state (do not crash the build)
  }
  return DigestSchema.parse(JSON.parse(raw)); // invalid → throw (fail the build)
}
```

- [ ] **Step 8: Run to verify both test files pass**

Run: `cd web && npx vitest run lib/`
Expected: PASS (all)

- [ ] **Step 9: Commit**

```bash
git add web/lib/ && git commit -m "feat(web): add zod contract, safe-href guard, and digest loader"
```

---

### Task 3: `BrutalCard` primitive

**Files:**
- Create: `web/components/ui/BrutalCard.tsx`
- Test: `web/components/ui/BrutalCard.test.tsx`

**Interfaces:**
- Produces: `BrutalCard({ as?, className?, children })` — renders the given element with the `.brutal-card` class.

- [ ] **Step 1: Write the failing test**

Create `web/components/ui/BrutalCard.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrutalCard } from "./BrutalCard";

describe("BrutalCard", () => {
  it("renders children inside a .brutal-card element", () => {
    render(<BrutalCard>hello</BrutalCard>);
    const el = screen.getByText("hello");
    expect(el).toHaveClass("brutal-card");
  });
  it("respects the `as` prop", () => {
    render(<BrutalCard as="article">x</BrutalCard>);
    expect(screen.getByText("x").tagName).toBe("ARTICLE");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run components/ui/BrutalCard.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `web/components/ui/BrutalCard.tsx`:
```tsx
import type { ElementType, ReactNode } from "react";

type Props = { as?: ElementType; className?: string; children: ReactNode };

export function BrutalCard({ as: Tag = "div", className = "", children }: Props) {
  return <Tag className={`brutal-card ${className}`.trim()}>{children}</Tag>;
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd web && npx vitest run components/ui/BrutalCard.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/components/ui/ && git commit -m "feat(web): add BrutalCard primitive"
```

---

### Task 4: `Narrative` (sanitized markdown, single h1)

**Files:**
- Create: `web/components/digest/Narrative.tsx`
- Test: `web/components/digest/Narrative.test.tsx`

**Interfaces:**
- Produces: `Narrative({ markdown: string })` — sanitized HTML; any `#`/h1 in the markdown becomes `<h2>`.

- [ ] **Step 1: Write the failing test**

Create `web/components/digest/Narrative.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Narrative } from "./Narrative";

describe("Narrative", () => {
  it("strips dangerous HTML", () => {
    const { container } = render(<Narrative markdown={"hi <img src=x onerror=alert(1)>"} />);
    expect(container.querySelector("img[onerror]")).toBeNull();
  });
  it("demotes markdown h1 so the page keeps a single authored h1", () => {
    const { container } = render(<Narrative markdown={"# Tech Digest\n\ntext"} />);
    expect(container.querySelector("h1")).toBeNull();
    expect(container.querySelector("h2")?.textContent).toBe("Tech Digest");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run components/digest/Narrative.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `web/components/digest/Narrative.tsx`:
```tsx
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

export function Narrative({ markdown }: { markdown: string }) {
  return (
    <ReactMarkdown
      rehypePlugins={[rehypeSanitize]}
      components={{ h1: "h2", h2: "h3" }}
    >
      {markdown}
    </ReactMarkdown>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd web && npx vitest run components/digest/Narrative.test.tsx`
Expected: PASS (rehype-sanitize is passed explicitly; without it these would fail)

- [ ] **Step 5: Commit**

```bash
git add web/components/digest/Narrative.tsx web/components/digest/Narrative.test.tsx
git commit -m "feat(web): add sanitized Narrative with h1 demotion"
```

---

### Task 5: `ArticleCard` + `ArticleGrid`

**Files:**
- Create: `web/components/digest/ArticleCard.tsx`, `web/components/digest/ArticleGrid.tsx`
- Test: `web/components/digest/ArticleCard.test.tsx`

**Interfaces:**
- Consumes: `Article` (from `@/lib/digest`), `BrutalCard`, `isSafeHref`.
- Produces: `ArticleCard({ article })`, `ArticleGrid({ articles })`.

- [ ] **Step 1: Write the failing test**

Create `web/components/digest/ArticleCard.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ArticleCard } from "./ArticleCard";

const base = { title: "T", source: "hackernews", score: 412, published_at: null, summary: null };

describe("ArticleCard", () => {
  it("renders a safe link with security rel", () => {
    render(<ArticleCard article={{ ...base, url: "https://example.com/a" }} />);
    const link = screen.getByRole("link", { name: "T" });
    expect(link).toHaveAttribute("href", "https://example.com/a");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });
  it("neutralizes an unsafe url to inert text (no link)", () => {
    render(<ArticleCard article={{ ...base, url: "javascript:alert(1)" }} />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText("T")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run components/digest/ArticleCard.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement both components**

Create `web/components/digest/ArticleCard.tsx`:
```tsx
import { BrutalCard } from "@/components/ui/BrutalCard";
import { isSafeHref } from "@/lib/url";
import type { Article } from "@/lib/digest";

export function ArticleCard({ article }: { article: Article }) {
  const safe = isSafeHref(article.url);
  return (
    <BrutalCard as="article" className="bg-surface p-4">
      {safe ? (
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-display font-black text-ink hover:underline"
        >
          {article.title}
        </a>
      ) : (
        <span className="font-display font-black text-ink">{article.title}</span>
      )}
      <div className="mt-2 text-sm text-ink/70">
        {article.source}
        {article.score != null && <span className="ml-2 font-bold text-ink">{article.score}</span>}
      </div>
      {article.summary && <p className="mt-1 text-sm text-ink/80">{article.summary}</p>}
    </BrutalCard>
  );
}
```
Create `web/components/digest/ArticleGrid.tsx`:
```tsx
import type { Article } from "@/lib/digest";
import { ArticleCard } from "./ArticleCard";

export function ArticleGrid({ articles }: { articles: Article[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {articles.map((a) => (
        <ArticleCard key={a.url} article={a} />
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd web && npx vitest run components/digest/ArticleCard.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/components/digest/ArticleCard.tsx web/components/digest/ArticleGrid.tsx web/components/digest/ArticleCard.test.tsx
git commit -m "feat(web): add ArticleCard (safe links) and ArticleGrid"
```

---

### Task 6: `MetaBlock` + `AgentsBlock`

**Files:**
- Create: `web/components/digest/MetaBlock.tsx`, `web/components/digest/AgentsBlock.tsx`
- Test: `web/components/digest/AgentsBlock.test.tsx`

**Interfaces:**
- Consumes: `Digest["agents"]`, `BrutalCard`.
- Produces: `MetaBlock({ total, generatedAt })`, `AgentsBlock({ agents })`.

- [ ] **Step 1: Write the failing test for AgentsBlock**

Create `web/components/digest/AgentsBlock.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentsBlock } from "./AgentsBlock";

describe("AgentsBlock", () => {
  it("shows the honest count of succeeded vs total agents", () => {
    render(
      <AgentsBlock
        agents={[
          { name: "hackernews", ok: true, article_count: 4 },
          { name: "github", ok: true, article_count: 2 },
          { name: "newsapi", ok: false, article_count: 0 },
        ]}
      />,
    );
    expect(screen.getByText(/2 \/ 3/)).toBeInTheDocument(); // 2 of 3 agents delivered
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run components/digest/AgentsBlock.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement both**

Create `web/components/digest/AgentsBlock.tsx`:
```tsx
import { BrutalCard } from "@/components/ui/BrutalCard";
import type { Digest } from "@/lib/digest";

export function AgentsBlock({ agents }: { agents: Digest["agents"] }) {
  const ok = agents.filter((a) => a.ok).length;
  return (
    <BrutalCard className="bg-graphite p-4">
      <div className="font-display text-xs font-black uppercase tracking-wide text-[var(--color-accent)]">
        Agents · {ok} / {agents.length}
      </div>
      <ul className="mt-2 space-y-1 text-sm text-white">
        {agents.map((a) => (
          <li key={a.name}>
            <span className={a.ok ? "text-[var(--color-accent)]" : "text-white/50"}>
              {a.ok ? "✓" : "✗"}
            </span>{" "}
            {a.name} · {a.article_count}
          </li>
        ))}
      </ul>
    </BrutalCard>
  );
}
```
Create `web/components/digest/MetaBlock.tsx`:
```tsx
import { BrutalCard } from "@/components/ui/BrutalCard";

export function MetaBlock({ total, generatedAt }: { total: number; generatedAt: string }) {
  const when = new Date(generatedAt).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  });
  return (
    <BrutalCard className="bg-surface p-4">
      <div className="font-display text-2xl font-black text-ink">{total}</div>
      <div className="text-xs uppercase tracking-wide text-ink/70">articles</div>
      <div className="mt-2 text-xs text-ink/60">{when} UTC</div>
    </BrutalCard>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd web && npx vitest run components/digest/AgentsBlock.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/components/digest/MetaBlock.tsx web/components/digest/AgentsBlock.tsx web/components/digest/AgentsBlock.test.tsx
git commit -m "feat(web): add MetaBlock and honest AgentsBlock roster"
```

---

### Task 7: `DigestView` (empty + populated) and `DigestHero`

**Files:**
- Create: `web/components/digest/DigestHero.tsx`, `web/components/digest/DigestView.tsx`
- Test: `web/components/digest/DigestView.test.tsx`

**Interfaces:**
- Consumes: `Digest | null`, all digest components.
- Produces: `DigestView({ digest })` — the single `<h1>` lives here; renders empty state on `null`.

- [ ] **Step 1: Write the failing test (both states)**

Create `web/components/digest/DigestView.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DigestView } from "./DigestView";

const digest = {
  narrative: "## Today\n\nStuff happened.",
  sources_used: ["hackernews"],
  total_articles: 1,
  generated_at: "2026-07-01T04:00:00+00:00",
  articles: [{ title: "A", url: "https://example.com/a", source: "hackernews", score: 1, published_at: null, summary: null }],
  agents: [{ name: "hackernews", ok: true, article_count: 1 }],
};

describe("DigestView", () => {
  it("renders an empty state when digest is null", () => {
    render(<DigestView digest={null} />);
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/nenhum digest ainda/i)).toBeInTheDocument();
  });
  it("renders exactly one h1 when populated", () => {
    const { container } = render(<DigestView digest={digest} />);
    expect(container.querySelectorAll("h1")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "A" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run components/digest/DigestView.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `DigestHero` then `DigestView`**

Create `web/components/digest/DigestHero.tsx`:
```tsx
import { BrutalCard } from "@/components/ui/BrutalCard";
import { Narrative } from "./Narrative";

export function DigestHero({ narrative }: { narrative: string }) {
  return (
    <BrutalCard className="bg-[var(--color-accent)] p-6">
      <div className="prose prose-sm max-w-none text-ink">
        <Narrative markdown={narrative} />
      </div>
    </BrutalCard>
  );
}
```
Create `web/components/digest/DigestView.tsx`:
```tsx
import type { Digest } from "@/lib/digest";
import { DigestHero } from "./DigestHero";
import { ArticleGrid } from "./ArticleGrid";
import { MetaBlock } from "./MetaBlock";
import { AgentsBlock } from "./AgentsBlock";

export function DigestView({ digest }: { digest: Digest | null }) {
  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <header className="mb-8">
        <p className="font-display text-xs font-black uppercase tracking-widest text-ink/60">
          Daily Tech Digest
        </p>
        <h1 className="font-display text-4xl font-black text-ink sm:text-6xl">news-agent</h1>
      </header>

      {digest === null ? (
        <p className="text-lg text-ink/70">
          Nenhum digest ainda — o agent roda diariamente às 04:00 UTC.
        </p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <DigestHero narrative={digest.narrative} />
          </div>
          <div className="grid gap-4">
            <MetaBlock total={digest.total_articles} generatedAt={digest.generated_at} />
            <AgentsBlock agents={digest.agents} />
          </div>
          <div className="lg:col-span-3">
            <ArticleGrid articles={digest.articles} />
          </div>
        </div>
      )}
    </main>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd web && npx vitest run components/digest/DigestView.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/components/digest/DigestHero.tsx web/components/digest/DigestView.tsx web/components/digest/DigestView.test.tsx
git commit -m "feat(web): add DigestView with empty state and single h1"
```

---

### Task 8: Wire the page, fonts, metadata, and security headers

**Files:**
- Modify: `web/app/page.tsx`, `web/app/layout.tsx`
- Create: `web/app/not-found.tsx`, `web/vercel.json`

**Interfaces:**
- Consumes: `loadDigest()`, `DigestView`.
- Produces: the built site + response headers.

- [ ] **Step 1: Thin loader page**

Replace `web/app/page.tsx` with:
```tsx
import { loadDigest } from "@/lib/digest";
import { DigestView } from "@/components/digest/DigestView";

export default function Page() {
  return <DigestView digest={loadDigest()} />;
}
```

- [ ] **Step 2: Layout with fonts + metadata**

Replace `web/app/layout.tsx` with:
```tsx
import type { Metadata } from "next";
import { Space_Grotesk, Inter } from "next/font/google";
import "./globals.css";

const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-display", display: "swap" });
const body = Inter({ subsets: ["latin"], variable: "--font-body", display: "swap" });

export const metadata: Metadata = {
  title: "news-agent — Daily Tech Digest",
  description: "A multi-agent tech news digest, written by Claude.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: not-found**

Create `web/app/not-found.tsx`:
```tsx
export default function NotFound() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="font-display text-4xl font-black">404</h1>
    </main>
  );
}
```

- [ ] **Step 4: Security headers**

Create `web/vercel.json`:
```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "Strict-Transport-Security", "value": "max-age=31536000; includeSubDomains; preload" },
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" },
        { "key": "Content-Security-Policy", "value": "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'" }
      ]
    }
  ]
}
```

- [ ] **Step 5: Seed a local `latest.json` and build**

```bash
cp web/__fixtures__/digest.sample.json web/public/latest.json
cd web && npm run build
```
Expected: build succeeds; the page renders the fixture at build time (SSG).

- [ ] **Step 6: Commit**

```bash
git add web/app/ web/vercel.json && git commit -m "feat(web): wire page loader, fonts, metadata, and security headers"
```

---

### Task 9: E2E, accessibility, reduced-motion, bundle gate

**Files:**
- Create: `web/playwright.config.ts`, `web/e2e/home.spec.ts`

**Interfaces:**
- Consumes: the built site.

- [ ] **Step 1: Playwright config**

Create `web/playwright.config.ts`:
```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  webServer: { command: "npm run build && npm run start", url: "http://localhost:3000", timeout: 120_000 },
  use: { baseURL: "http://localhost:3000" },
});
```

- [ ] **Step 2: E2E spec — populated, a11y, screenshots**

Create `web/e2e/home.spec.ts`:
```ts
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("home renders one h1 and article links", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toHaveCount(1);
  await expect(page.getByRole("link").first()).toBeVisible();
});

test("no accessibility violations", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

for (const width of [320, 768, 1024, 1440]) {
  test(`screenshot @ ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page).toHaveScreenshot(`home-${width}.png`, { fullPage: true });
  });
}
```

- [ ] **Step 3: Run E2E (populated, with the fixture copied in Task 8 Step 5)**

Run: `cd web && npx playwright install --with-deps && npm run test:e2e`
Expected: PASS; screenshots created on first run (baseline).

- [ ] **Step 4: Verify empty-state build does not crash**

```bash
rm web/public/latest.json && cd web && npm run build
```
Expected: build succeeds (empty state); then restore: `cp web/__fixtures__/digest.sample.json web/public/latest.json`.

- [ ] **Step 5: Check the JS bundle budget**

Run: `cd web && npm run build`
Expected: the route's First Load JS is well under 150kb (Server Components ship ~0 app JS; react-markdown renders at build). If a component accidentally became a Client Component, the number spikes — investigate before committing.

- [ ] **Step 6: Commit**

```bash
git add web/playwright.config.ts web/e2e/ && git commit -m "test(web): add E2E, axe, responsive screenshots"
```

---

## Deploy (manual, post-merge)

- [ ] Import the repo in Vercel; set **Root Directory = `web/`**.
- [ ] Confirm the Actions bot commit to `web/public/latest.json` triggers a Vercel redeploy.
- [ ] Verify headers with `curl -I <deploy-url>` (CSP, HSTS, nosniff present).

---

## Self-review notes (author)

- **Spec coverage:** §6.1→T1, §6.5 (zod/url/loader)→T2, §6.4/BrutalCard→T1+T3, §6.5 Narrative→T4, §5.3 ArticleCard/Grid→T5, MetaBlock/AgentsBlock→T6, §6.2 page seam→T7+T8, §6.6 headers→T8, §7 E2E/a11y/reduced-motion + §8 bundle gate→T9.
- **Type consistency:** `Digest`/`Article` come from `@/lib/digest` and are used unchanged in every component; `AgentsBlock` consumes `Digest["agents"]`.
- **Testability seam:** `DigestView` (pure, sync) carries both null/populated tests; `page.tsx` (loader) is covered by the E2E build. No async Server Component is unit-tested (correct — those are E2E-only).
- **Reduced-motion:** mechanism is the `@media` block in `globals.css` (Task 1); the hover lift is CSS-only, so it degrades without JS.
