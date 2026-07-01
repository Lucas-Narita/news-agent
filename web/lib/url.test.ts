import { describe, it, expect } from "vitest";
import { isSafeHref } from "./url";

describe("isSafeHref", () => {
  it("allows http and https", () => {
    expect(isSafeHref("https://example.com")).toBe(true);
    expect(isSafeHref("http://example.com")).toBe(true);
  });
  it("rejects dangerous schemes and garbage", () => {
    for (const u of ["javascript:alert(1)", "data:text/html,x", "vbscript:x", "file:///etc", "not a url"]) {
      expect(isSafeHref(u)).toBe(false);
    }
  });
});
