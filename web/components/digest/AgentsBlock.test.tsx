import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentsBlock } from "./AgentsBlock";

describe("AgentsBlock", () => {
  it("shows the honest count of succeeded vs total agents", () => {
    render(
      <AgentsBlock
        agents={[
          { name: "hackernews", ok: true, article_count: 4 },
          { name: "github", ok: true, article_count: 2 },
          { name: "newsapi", ok: false, article_count: 0 },
        ]}
      />,
    );
    expect(screen.getByText(/2 \/ 3/)).toBeInTheDocument(); // 2 of 3 agents delivered
  });

  it("renders one row per agent, including a failed agent shown as failed (not hidden)", () => {
    render(
      <AgentsBlock
        agents={[
          { name: "hackernews", ok: true, article_count: 4 },
          { name: "newsapi", ok: false, article_count: 0 },
        ]}
      />,
    );
    expect(screen.getByText(/hackernews/)).toBeInTheDocument();
    const failedRow = screen.getByText(/newsapi/).closest("li");
    expect(failedRow).not.toBeNull();
    // Honesty requirement: a failed agent must render a distinct failed indicator, not be silently dropped.
    expect(failedRow).toHaveTextContent("✗");
    expect(failedRow).toHaveTextContent("0");
  });

  it("renders without crashing when agents is empty, with a sensible empty state", () => {
    render(<AgentsBlock agents={[]} />);
    expect(screen.getByText(/0 \/ 0/)).toBeInTheDocument();
    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
  });
});
