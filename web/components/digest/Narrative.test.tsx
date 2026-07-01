import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Narrative } from "./Narrative";

describe("Narrative", () => {
  it("strips dangerous HTML (defense-in-depth; react-markdown already escapes raw HTML)", () => {
    const { container } = render(<Narrative markdown={"hi <img src=x onerror=alert(1)>"} />);
    expect(container.querySelector("img[onerror]")).toBeNull();
  });
  it("blocks a javascript: markdown link (defense-in-depth; react-markdown's own urlTransform already does this)", () => {
    // react-markdown v10 has a built-in `defaultUrlTransform` that runs
    // unconditionally on every href/src produced from markdown syntax, using
    // the same protocol allowlist (http(s), irc(s), mailto, xmpp) that
    // rehype-sanitize uses for `href`. That built-in transform already strips
    // this href even with rehype-sanitize removed, so this case is NOT a
    // rehype-sanitize gate (verified empirically) — see the img[src] test
    // below for the case that actually depends on rehype-sanitize.
    const { container } = render(<Narrative markdown={"[click](javascript:alert(1))"} />);
    const anchor = container.querySelector("a");
    const href = anchor?.getAttribute("href") ?? "";
    expect(href.toLowerCase().startsWith("javascript:")).toBe(false);
  });
  it("strips a mailto: image src via rehype-sanitize's per-tag protocol allowlist", () => {
    // This is the actual rehype-sanitize gate. react-markdown's own built-in
    // urlTransform applies ONE shared protocol regex (http(s), irc(s), mailto,
    // xmpp) to both href and src, so it lets `mailto:` through on an <img src>
    // even though that makes no sense for images. rehype-sanitize's schema is
    // stricter and tag-aware: img.protocols.src is only ['http', 'https'], so
    // it drops the `src` attribute entirely for any other protocol. Removing
    // rehypeSanitize from Narrative.tsx makes this test fail (src survives as
    // "mailto:test@test.com" instead of being stripped) — confirmed via RED
    // run in the task report.
    const { container } = render(<Narrative markdown={"![img](mailto:test@test.com)"} />);
    const img = container.querySelector("img");
    const src = img?.getAttribute("src") ?? "";
    expect(src.toLowerCase().startsWith("mailto:")).toBe(false);
  });
  it("demotes markdown h1 so the page keeps a single authored h1", () => {
    const { container } = render(<Narrative markdown={"# Tech Digest\n\ntext"} />);
    expect(container.querySelector("h1")).toBeNull();
    expect(container.querySelector("h2")?.textContent).toBe("Tech Digest");
  });
});
