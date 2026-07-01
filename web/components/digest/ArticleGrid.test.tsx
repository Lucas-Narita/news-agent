import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ArticleGrid } from "./ArticleGrid";
import type { Article } from "@/lib/digest";

const makeArticle = (i: number): Article => ({
  title: `Article ${i}`,
  url: `https://example.com/${i}`,
  source: "hackernews",
  score: i,
  published_at: null,
  summary: null,
});

describe("ArticleGrid", () => {
  it("renders one card per article", () => {
    const articles = [makeArticle(1), makeArticle(2), makeArticle(3)];
    render(<ArticleGrid articles={articles} />);
    expect(screen.getAllByRole("link")).toHaveLength(3);
    expect(screen.getByText("Article 1")).toBeInTheDocument();
    expect(screen.getByText("Article 2")).toBeInTheDocument();
    expect(screen.getByText("Article 3")).toBeInTheDocument();
  });
});
