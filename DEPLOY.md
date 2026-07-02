# Deploying the web frontend to Vercel (free)

The [`web/`](web/) directory is a static Next.js 16 site that renders the daily digest from
`web/public/latest.json`. It deploys to **Vercel's Hobby (free) tier** with **no build-time
secrets** — the Anthropic / NewsAPI calls happen only in the `digest.yml` GitHub Action, never in
the Vercel build.

## One-time setup

1. **Import the repo** at [vercel.com/new](https://vercel.com/new) and pick
   `Lucas-Narita/news-agent`.
2. **Set the Root Directory to `web`.** This is the one step that "connect the repo" does *not*
   cover, and it is mandatory: the git root is a Python project with no `package.json`, so with the
   default root Vercel cannot detect Next.js (**the build fails**) *and* never reads
   `web/vercel.json` (**the security headers are silently dropped**). On the *Configure Project*
   screen click **Edit** next to *Root Directory* → type `web` → confirm the Framework Preset flips
   to **Next.js**.
3. Leave everything else at its default:

   | Setting | Value |
   |---|---|
   | Framework Preset | Next.js (auto-detected) |
   | Build Command | `next build` (default) |
   | Install Command | `npm install` (default) |
   | Output Directory | default |
   | Node.js Version | 22.x (also pinned via `web/package.json` `engines`) |
   | Production Branch | `main` |
   | Environment Variables | **none** |

4. Click **Deploy**.

## Verify the deploy

```bash
curl -sI https://<your-project>.vercel.app \
  | grep -i -E 'content-security-policy|strict-transport-security|x-frame-options'
```

Seeing these headers confirms the Root Directory is correctly scoped to `web` — they come from
`web/vercel.json`, which Vercel only reads when the root points at `web/`.

## Keeping it fresh (free)

`.github/workflows/digest.yml` runs daily at 04:00 UTC (and on manual dispatch): it regenerates
`web/public/latest.json`, validates it against the `DigestOutput` contract, and commits it to
`main`. Because that file lives inside the Root Directory, each commit triggers a fresh production
build — the static page updates with no server and no cost.

> **First impression:** the committed seed `latest.json` uses placeholder article links. Right after
> the first deploy, trigger one real run so visitors see live data:
> `gh workflow run "Generate digest"` (requires `ANTHROPIC_API_KEY` in the repo's Actions secrets).
