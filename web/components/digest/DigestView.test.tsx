import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DigestView } from "./DigestView";

const digest = {
  narrative: "## Today\n\nStuff happened.",
  sources_used: ["hackernews"],
  total_articles: 1,
  generated_at: "2026-07-01T04:00:00+00:00",
  articles: [
    {
      title: "A",
      url: "https://example.com/a",
      source: "hackernews",
      score: 1,
      published_at: null,
      summary: null,
    },
  ],
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
