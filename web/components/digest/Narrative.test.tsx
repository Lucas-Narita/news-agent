import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Narrative } from "./Narrative";

describe("Narrative", () => {
  it("strips dangerous HTML", () => {
    const { container } = render(<Narrative markdown={"hi <img src=x onerror=alert(1)>"} />);
    expect(container.querySelector("img[onerror]")).toBeNull();
  });
  it("demotes markdown h1 so the page keeps a single authored h1", () => {
    const { container } = render(<Narrative markdown={"# Tech Digest\n\ntext"} />);
    expect(container.querySelector("h1")).toBeNull();
    expect(container.querySelector("h2")?.textContent).toBe("Tech Digest");
  });
});
