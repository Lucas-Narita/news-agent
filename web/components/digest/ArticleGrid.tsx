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
