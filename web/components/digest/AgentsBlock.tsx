import { BrutalCard } from "@/components/ui/BrutalCard";
import type { Digest } from "@/lib/digest";

export function AgentsBlock({ agents }: { agents: Digest["agents"] }) {
  const ok = agents.filter((a) => a.ok).length;
  return (
    <BrutalCard className="bg-graphite p-4">
      <div className="font-display text-xs font-black uppercase tracking-wide text-[var(--color-accent)]">
        Agents · {ok} / {agents.length}
      </div>
      <ul className="mt-2 space-y-1 text-sm text-white">
        {agents.map((a) => (
          <li key={a.name}>
            <span className={a.ok ? "text-[var(--color-accent)]" : "text-white/50"}>
              {a.ok ? "✓" : "✗"}
            </span>{" "}
            {a.name} · {a.article_count}
          </li>
        ))}
      </ul>
    </BrutalCard>
  );
}
