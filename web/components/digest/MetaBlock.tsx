import { BrutalCard } from "@/components/ui/BrutalCard";

export function MetaBlock({ total, generatedAt }: { total: number; generatedAt: string }) {
  // Fixed locale ("en-US") + fixed timeZone ("UTC") make this deterministic regardless
  // of where it runs — the SSG server and the hydrating browser always agree, so there's
  // no hydration mismatch (unlike a bare toLocaleString() that follows the runtime's locale/TZ).
  const when = new Date(generatedAt).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  });
  return (
    <BrutalCard className="bg-surface p-4">
      <div className="font-display text-2xl font-black text-ink">{total}</div>
      <div className="text-xs uppercase tracking-wide text-ink/70">articles</div>
      <div className="mt-2 text-xs text-ink/60">{when} UTC</div>
    </BrutalCard>
  );
}
