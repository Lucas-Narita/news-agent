import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DigestView } from "./DigestView";

const digest = {
  // Top-level markdown heading (h1) so this fixture actually exercises the
  // Narrative h1->h2 demotion — a "## Today" (h2) fixture would never touch
  // that code path and would mask a regression there.
  narrative: "# Today\n\nStuff happened.",
  sources_used: ["hackernews"],
  total_articles: 1,
  generated_at: "2026-07-01T04:00:00+00:00",
  articles: [
    {
      title: "A",
      url: "https://example.com/a",
      source: "hackernews",
      // Distinct from total_articles (1) so the two "1"s in the DOM
      // (MetaBlock's total and this score) don't collide in text queries.
      score: 5,
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

  it("renders exactly one h1 when populated, with meta and agents wired", () => {
    const { container } = render(<DigestView digest={digest} />);
    // Invariant: hero h1 + Narrative's demoted h1->h2 = exactly one h1 on the page.
    expect(container.querySelectorAll("h1")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "A" })).toBeInTheDocument();
    // MetaBlock wiring: total_articles must actually reach the DOM, not just
    // an empty/blank section if the prop got dropped or mis-wired.
    expect(screen.getByText("1")).toBeInTheDocument();
    // AgentsBlock wiring: the agent roster (name + article_count) must render,
    // not just an empty section.
    expect(screen.getByText(/hackernews · 1/)).toBeInTheDocument();
  });
});
