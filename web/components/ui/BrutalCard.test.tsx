import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrutalCard } from "./BrutalCard";

describe("BrutalCard", () => {
  it("renders children inside a .brutal-card element", () => {
    render(<BrutalCard>hello</BrutalCard>);
    const el = screen.getByText("hello");
    expect(el).toHaveClass("brutal-card");
  });
  it("respects the `as` prop", () => {
    render(<BrutalCard as="article">x</BrutalCard>);
    expect(screen.getByText("x").tagName).toBe("ARTICLE");
  });
});
