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
