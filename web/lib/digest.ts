import { readFileSync } from "node:fs";
import path from "node:path";
import { z } from "zod";
import { isSafeHref } from "./url";

const AgentStatusSchema = z.object({
  name: z.string(),
  ok: z.boolean(),
  article_count: z.number().int(),
});

const ArticleSchema = z.object({
  title: z.string(),
  url: z.string().refine(isSafeHref, { message: "unsafe url scheme" }),
  source: z.string(),
  // NewsAPI always emits a real null score; other sources may too.
  score: z.number().int().nullable(),
  // Lobsters emits non-Z offsets like "-06:00"; offset:true accepts both.
  published_at: z.string().datetime({ offset: true }).nullable(),
  summary: z.string().nullable(),
});

export const DigestSchema = z.object({
  narrative: z.string(),
  // Can be empty on a fully-degraded run — no .nonempty()/.min(1).
  sources_used: z.array(z.string()),
  // Can be 0 on a fully-degraded run.
  total_articles: z.number().int(),
  generated_at: z.string().datetime({ offset: true }),
  // Can be empty on a fully-degraded run.
  articles: z.array(ArticleSchema),
  // Can be empty on a fully-degraded run.
  agents: z.array(AgentStatusSchema),
});

export type Digest = z.infer<typeof DigestSchema>;
export type Article = z.infer<typeof ArticleSchema>;

export function loadDigest(): Digest | null {
  const file = path.join(process.cwd(), "public", "latest.json");
  let raw: string;
  try {
    raw = readFileSync(file, "utf-8");
  } catch {
    return null; // absent → empty state (do not crash the build)
  }
  return DigestSchema.parse(JSON.parse(raw)); // invalid → throw (fail the build)
}
