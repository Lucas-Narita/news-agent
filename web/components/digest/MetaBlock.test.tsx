import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetaBlock } from "./MetaBlock";

describe("MetaBlock", () => {
  it("shows the total article count", () => {
    render(<MetaBlock total={12} generatedAt="2026-07-01T04:00:00Z" />);
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText(/articles/i)).toBeInTheDocument();
  });

  it("formats generatedAt deterministically in UTC (SSR/hydration safe)", () => {
    render(<MetaBlock total={12} generatedAt="2026-07-01T04:00:00Z" />);
    // Fixed locale + fixed timeZone: the same string renders on server and client
    // regardless of the host machine's local timezone, so hydration cannot mismatch.
    expect(screen.getByText(/Jul 1, 2026/)).toBeInTheDocument();
    expect(screen.getByText(/UTC/)).toBeInTheDocument();
  });

  it("renders without crashing when total is 0", () => {
    render(<MetaBlock total={0} generatedAt="2026-07-01T04:00:00Z" />);
    expect(screen.getByText("0")).toBeInTheDocument();
  });
});
