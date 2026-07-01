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
  it("renders the title and source", () => {
    render(<ArticleCard article={{ ...base, url: "https://example.com/a" }} />);
    expect(screen.getByText("T")).toBeInTheDocument();
    expect(screen.getByText("hackernews")).toBeInTheDocument();
  });
  it("omits the score chip when score is null (never prints the literal 'null')", () => {
    render(<ArticleCard article={{ ...base, url: "https://example.com/a", score: null }} />);
    expect(screen.queryByText("412")).toBeNull();
    expect(screen.queryByText("null")).toBeNull();
  });
});
