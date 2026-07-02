# news-agent · web

Static [Next.js 16](https://nextjs.org) (App Router) frontend for the **news-agent** daily tech
digest. The page is **prerendered at build time** from `public/latest.json` — the same
`DigestOutput` JSON the CLI emits — so the live site is a plain CDN-served static document with no
runtime API or LLM calls.

## How the data gets here

```
news-agent run --format json  ─►  web/public/latest.json  ─►  next build (static)  ─►  CDN
     (GitHub Action, daily)            (committed)            (Vercel, per commit)
```

- `lib/digest.ts` reads `public/latest.json` and validates it against a zod schema that mirrors the
  backend's `DigestOutput` Pydantic contract. Invalid data fails the build; an absent file renders
  the empty state instead of crashing.
- `.github/workflows/digest.yml` regenerates and commits `latest.json` daily; each commit triggers a
  fresh Vercel build, so the static page stays current without a server.

## Develop

```bash
npm install
npm run dev        # http://localhost:3000
npm run build      # production build (static prerender)
npm test           # Vitest unit tests
npm run test:e2e   # Playwright E2E + axe a11y + responsive screenshots
```

## Stack

Next.js 16 · React 19 · Tailwind CSS v4 · zod · react-markdown + rehype-sanitize · Vitest · Playwright

## Deploy

Deployed on **Vercel (Hobby / free)**. Because this app lives in a subdirectory of a Python-root
repo, the Vercel project's **Root Directory must be set to `web`**, and no build-time environment
variables are required. Full steps: [`../DEPLOY.md`](../DEPLOY.md).
