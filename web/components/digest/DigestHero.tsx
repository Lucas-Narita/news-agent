import { BrutalCard } from "@/components/ui/BrutalCard";
import { Narrative } from "./Narrative";

// Tailwind arbitrary variants style the rendered markdown children. Utilities recompile
// reliably from the class scan, unlike custom CSS in globals.css under Turbopack.
const proseClass =
  "text-base leading-relaxed lg:text-lg " +
  "[&>*:first-child]:mt-0 [&_p]:mt-4 [&_strong]:font-bold " +
  "[&_a]:font-semibold [&_a]:underline [&_a]:underline-offset-2 " +
  "[&_h2]:mt-5 [&_h2]:font-display [&_h2]:text-2xl [&_h2]:font-black " +
  "[&_h3]:mt-5 [&_h3]:font-display [&_h3]:text-xl [&_h3]:font-black " +
  "[&_ul]:mt-4 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:mt-4 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:mt-1";

export function DigestHero({ narrative }: { narrative: string }) {
  return (
    <BrutalCard className="flex h-full flex-col bg-[var(--color-accent)] p-6 lg:p-8">
      <p className="font-display text-xs font-black uppercase tracking-widest text-ink/70">
        AI Summary
      </p>
      <div className={`mt-4 flex-1 text-ink ${proseClass}`}>
        <Narrative markdown={narrative} />
      </div>
    </BrutalCard>
  );
}
