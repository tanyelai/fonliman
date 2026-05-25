import { useMemo } from "react";

import { formatPercent } from "@/lib/format";
import type { AllocationItem } from "@/lib/types";

interface Props {
  items: AllocationItem[];
}

// Curated colour cycle — picked so adjacent slices stay visually distinct
// even when many small ones cluster. We re-use across many funds; consistent
// colour for "Hisse Senedi" would be nice but TEFAS gives us arbitrary mixes
// per fund, so we go ordinal instead.
const COLOURS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
  "#8b5cf6", "#ec4899", "#14b8a6", "#f97316",
  "#84cc16", "#6366f1", "#06b6d4", "#a855f7",
];

// Bar-stack visual rather than a donut — for asset-class breakdowns the
// horizontal proportions read more naturally than a pie chart, especially
// when a single class dominates (e.g. AOY is 97% yabancı hisse).
export function AllocationChart({ items }: Props) {
  const total = useMemo(() => items.reduce((s, i) => s + i.pct, 0), [items]);
  const normalized = useMemo(() => {
    // Sometimes TEFAS percentages add to >100 (rounding) or <100 (residual).
    // Display as-is; only normalise the bar widths.
    if (total <= 0) return [];
    return items.map((it, i) => ({ ...it, ratio: it.pct / total, colour: COLOURS[i % COLOURS.length] }));
  }, [items, total]);

  return (
    <div className="space-y-3">
      {/* Stacked bar */}
      <div className="h-2 rounded-full overflow-hidden flex bg-ink-100 dark:bg-ink-800">
        {normalized.map((it) => (
          <div
            key={it.label}
            className="h-full transition-all"
            style={{ width: `${it.ratio * 100}%`, backgroundColor: it.colour }}
            title={`${it.label}: ${formatPercent(it.pct, { digits: 2 })}`}
          />
        ))}
      </div>

      {/* Legend */}
      <ul className="space-y-1.5">
        {normalized.map((it) => (
          <li key={it.label} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                style={{ backgroundColor: it.colour }}
              />
              <span className="text-ink-600 dark:text-ink-300 truncate">{it.label}</span>
            </div>
            <span className="tabular font-medium ml-2 flex-shrink-0">
              {formatPercent(it.pct, { digits: 2 })}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
