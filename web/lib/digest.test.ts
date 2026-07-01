import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { DigestSchema } from "./digest";

const FIXTURE = path.join(process.cwd(), "__fixtures__", "digest.sample.json");

describe("DigestSchema", () => {
  it("parses the Python-generated fixture", () => {
    const raw = JSON.parse(readFileSync(FIXTURE, "utf-8"));
    const parsed = DigestSchema.parse(raw);
    // Fixture has 3 fetched articles + 1 fully-failed agent (github, ok:false).
    expect(parsed.agents.length).toBe(4);
    expect(parsed.articles.length).toBe(3);
    expect(parsed.articles[0].url).toMatch(/^https?:/);
  });

  it("accepts a guaranteed-real null score (NewsAPI-shaped article)", () => {
    const raw = JSON.parse(readFileSync(FIXTURE, "utf-8"));
    const parsed = DigestSchema.parse(raw);
    const lobsters = parsed.articles.find((a) => a.source === "lobsters");
    expect(lobsters?.score).toBeNull();
  });

  it("accepts a non-UTC offset published_at (Lobsters-shaped article)", () => {
    const raw = JSON.parse(readFileSync(FIXTURE, "utf-8"));
    const parsed = DigestSchema.parse(raw);
    const lobsters = parsed.articles.find((a) => a.source === "lobsters");
    expect(lobsters?.published_at).toMatch(/-06:00$/);
  });

  it("accepts an empty sources_used/articles/agents run (fully degraded)", () => {
    const raw = JSON.parse(readFileSync(FIXTURE, "utf-8"));
    const degraded = {
      ...raw,
      sources_used: [],
      articles: [],
      agents: [],
      total_articles: 0,
    };
    expect(() => DigestSchema.parse(degraded)).not.toThrow();
  });

  it("rejects an article with an unsafe url", () => {
    const raw = JSON.parse(readFileSync(FIXTURE, "utf-8"));
    raw.articles[0].url = "javascript:alert(1)";
    expect(() => DigestSchema.parse(raw)).toThrow();
  });
});
