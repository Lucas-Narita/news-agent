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
