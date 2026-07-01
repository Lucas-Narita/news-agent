import type { ElementType, ReactNode } from "react";

type Props = { as?: ElementType; className?: string; children: ReactNode };

export function BrutalCard({ as: Tag = "div", className = "", children }: Props) {
  return <Tag className={`brutal-card ${className}`.trim()}>{children}</Tag>;
}
