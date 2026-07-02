import { BrutalCard } from "@/components/ui/BrutalCard";
import type { Digest } from "@/lib/digest";

export function AgentsBlock({ agents }: { agents: Digest["agents"] }) {
  const ok = agents.filter((a) => a.ok).length;
  return (
    <BrutalCard className="bg-graphite p-6">
      <div className="font-display text-xs font-black uppercase tracking-wide text-[var(--color-accent)]">
        Agents · {ok} / {agents.length}
      </div>
      <ul className="mt-3 space-y-1.5 text-sm text-white">
        {agents.map((a) => (
          <li key={a.name}>
            <span
              aria-hidden="true"
              className={a.ok ? "text-[var(--color-accent)]" : "text-white/50"}
            >
              {a.ok ? "✓" : "✗"}
            </span>
            <span className="sr-only">{a.ok ? "OK" : "Failed"}</span>{" "}
            {a.name} · {a.article_count}
          </li>
        ))}
      </ul>
    </BrutalCard>
  );
}
