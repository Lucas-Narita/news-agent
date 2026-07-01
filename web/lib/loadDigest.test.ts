import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { loadDigest } from "./digest";
import fixture from "../__fixtures__/digest.sample.json";

// loadDigest() hardcodes its read path as `${process.cwd()}/public/latest.json`
// (see lib/digest.ts), so exercising its real IO branches means pointing
// process.cwd() at a scratch directory we fully control — not the repo's own
// public/latest.json (which may or may not exist depending on whether the
// pipeline has run, and which we don't want tests to depend on).
//
// Vitest isolates each test file in its own process/worker by default, and
// these tests run sequentially (no `.concurrent`), so mutating process.cwd()
// here is safe: it can't race with other test files or other tests in this
// file.
describe("loadDigest", () => {
  const originalCwd = process.cwd();
  let tempDir: string;

  beforeEach(() => {
    tempDir = mkdtempSync(path.join(tmpdir(), "news-agent-web-"));
  });

  afterEach(() => {
    process.chdir(originalCwd);
    rmSync(tempDir, { recursive: true, force: true });
  });

  it("returns null when public/latest.json is absent", () => {
    process.chdir(tempDir);

    expect(loadDigest()).toBeNull();
  });

  it("returns a validated Digest matching the committed fixture shape when the file is present", () => {
    mkdirSync(path.join(tempDir, "public"), { recursive: true });
    // Same fixture seeded at web/public/latest.json: 3 fetched articles
    // + 1 fully-failed agent (github, ok:false).
    writeFileSync(path.join(tempDir, "public", "latest.json"), JSON.stringify(fixture));
    process.chdir(tempDir);

    const digest = loadDigest();

    expect(digest).not.toBeNull();
    expect(digest?.articles).toHaveLength(3);
    expect(digest?.agents).toHaveLength(4);
  });

  it("throws when the file contains invalid JSON", () => {
    mkdirSync(path.join(tempDir, "public"), { recursive: true });
    writeFileSync(path.join(tempDir, "public", "latest.json"), "{ not valid json");
    process.chdir(tempDir);

    expect(() => loadDigest()).toThrow();
  });

  it("throws when the JSON is well-formed but schema-invalid", () => {
    mkdirSync(path.join(tempDir, "public"), { recursive: true });
    writeFileSync(
      path.join(tempDir, "public", "latest.json"),
      JSON.stringify({ narrative: "missing every other required field" }),
    );
    process.chdir(tempDir);

    expect(() => loadDigest()).toThrow();
  });
});
