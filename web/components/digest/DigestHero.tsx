import { BrutalCard } from "@/components/ui/BrutalCard";
import { Narrative } from "./Narrative";

export function DigestHero({ narrative }: { narrative: string }) {
  return (
    <BrutalCard className="bg-[var(--color-accent)] p-6">
      <div className="prose prose-sm max-w-none text-ink">
        <Narrative markdown={narrative} />
      </div>
    </BrutalCard>
  );
}
