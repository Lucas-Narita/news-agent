import type { Digest } from "@/lib/digest";
import { DigestHero } from "./DigestHero";
import { ArticleGrid } from "./ArticleGrid";
import { MetaBlock } from "./MetaBlock";
import { AgentsBlock } from "./AgentsBlock";
import { HowItWorks } from "./HowItWorks";
import { SiteFooter } from "./SiteFooter";

const REPO_URL = "https://github.com/Lucas-Narita/news-agent";

export function DigestView({ digest }: { digest: Digest | null }) {
  return (
    <main className="mx-auto max-w-[1600px] px-6 py-14 lg:px-12 lg:py-20 2xl:px-20">
      <header className="mb-12 flex flex-col gap-6 lg:mb-16 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="font-display text-xs font-black uppercase tracking-widest text-ink/70 2xl:text-sm">
            Daily Tech Digest
          </p>
          <h1 className="mt-1 font-display text-5xl font-black leading-none text-ink sm:text-7xl 2xl:text-8xl">
            news-agent
          </h1>
          <p className="mt-4 max-w-xl text-lg text-ink/70 2xl:text-xl">
            An AI agent reads Hacker News, Dev.to, Lobsters and more — then writes one daily
            briefing on what matters in tech.
          </p>
        </div>
        <a
          href={REPO_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="brutal-card inline-flex w-fit shrink-0 items-center gap-2 bg-ink px-5 py-3 font-display text-sm font-black uppercase tracking-wide text-surface"
        >
          View source ↗
        </a>
      </header>

      {digest === null ? (
        <p className="text-lg text-ink/70">No digest yet — the agent runs daily at 04:00 UTC.</p>
      ) : (
        <>
          <div className="grid gap-5 lg:grid-cols-3 lg:gap-6">
            <div className="lg:col-span-2">
              <DigestHero narrative={digest.narrative} />
            </div>
            <div className="grid gap-5 lg:gap-6">
              <MetaBlock total={digest.total_articles} generatedAt={digest.generated_at} />
              <AgentsBlock agents={digest.agents} />
            </div>
          </div>

          <section aria-labelledby="stories-heading" className="mt-12 lg:mt-16">
            <h2
              id="stories-heading"
              className="mb-5 font-display text-sm font-black uppercase tracking-widest text-ink/70"
            >
              Top Stories
            </h2>
            <ArticleGrid articles={digest.articles} />
          </section>

          <HowItWorks />
        </>
      )}

      <SiteFooter />
    </main>
  );
}
