import { BrutalCard } from "@/components/ui/BrutalCard";

const STEPS = [
  {
    n: "1",
    title: "Collect",
    body: "Independent agents pull from Hacker News, Dev.to, Lobsters, GitHub and more — in parallel, each degrading gracefully if a source is down.",
  },
  {
    n: "2",
    title: "Synthesize",
    body: "Claude reads every item and writes one narrative briefing — not a link dump, a summary of what actually matters today.",
  },
  {
    n: "3",
    title: "Publish",
    body: "The digest is baked into a static site and rebuilt every day at 04:00 UTC. Fast, cacheable, and ships zero client-side JavaScript.",
  },
];

export function HowItWorks() {
  return (
    <section aria-labelledby="how-heading" className="mt-12 lg:mt-16">
      <h2
        id="how-heading"
        className="mb-5 font-display text-sm font-black uppercase tracking-widest text-ink/70"
      >
        How it works
      </h2>
      <div className="grid gap-5 lg:grid-cols-3 lg:gap-6">
        {STEPS.map((s) => (
          <BrutalCard key={s.n} className="bg-surface p-6 lg:p-7">
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center bg-ink font-display text-base font-black text-[var(--color-accent)]">
                {s.n}
              </span>
              <h3 className="font-display text-xl font-black text-ink">{s.title}</h3>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-ink/80">{s.body}</p>
          </BrutalCard>
        ))}
      </div>
    </section>
  );
}
