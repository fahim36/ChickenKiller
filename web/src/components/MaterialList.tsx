import {
  BookOpen,
  CreditCard,
  ExternalLink,
  FileText,
  GraduationCap,
  LayoutGrid,
  PlayCircle,
  ScrollText,
  Wrench,
} from "lucide-react";
import type { Material, MaterialType } from "@/lib/api";
import { materialLabel } from "@/lib/format";

const ICONS: Record<MaterialType, typeof BookOpen> = {
  docs: FileText,
  free: GraduationCap,
  video: PlayCircle,
  book: BookOpen,
  paper: ScrollText,
  tool: Wrench,
  paid: CreditCard,
  platform: LayoutGrid,
};

export function MaterialList({ materials }: { materials: Material[] }) {
  if (materials.length === 0) {
    return <p className="text-sm text-muted-foreground">No Materials for this Lesson.</p>;
  }
  return (
    <ul className="grid gap-2">
      {materials.map((m) => {
        const Icon = ICONS[m.type] ?? FileText;
        return (
          <li
            key={m.id}
            className="group relative flex items-center gap-3 rounded-xl border bg-card px-4 py-3 transition-colors hover:border-primary/50 hover:bg-accent/30"
          >
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary">
              <Icon aria-hidden className="size-4" />
            </span>
            <span className="min-w-0 flex-1">
              <a
                href={m.url}
                target="_blank"
                rel="noreferrer"
                className="block truncate text-sm font-medium after:absolute after:inset-0 after:rounded-xl"
              >
                {m.title}
              </a>
              <span className="text-xs text-muted-foreground">
                {materialLabel(m.type)}
              </span>
            </span>
            <ExternalLink
              aria-hidden
              className="size-4 shrink-0 text-muted-foreground group-hover:text-primary"
            />
          </li>
        );
      })}
    </ul>
  );
}
