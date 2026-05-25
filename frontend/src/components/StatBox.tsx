import { ResponsiveContainer, Area, AreaChart, Tooltip } from "recharts";

import { formatDate, formatPercent, returnColor } from "@/lib/format";

// Threshold below which we consider a series "effectively flat" and skip
// the sparkline. A line that goes "—————" reads as visual noise; we'd
// rather just show the headline number cleanly.
const FLAT_VARIATION_THRESHOLD_PCT = 1.5;

interface StatBoxProps {
  label: string;
  // Pre-formatted headline value, e.g. "37,39 B" or "3 / 190".
  value: string;
  // Optional caption shown directly under the value — overrides the
  // change indicator when set.
  caption?: string;
  // Optional change indicator. Hidden when caption is set.
  change?: {
    pct: number;
    label?: string; // e.g. "son 28 günde"
    /** When true (e.g. rank), down is good and we flip the colour. */
    invert?: boolean;
  };
  // Optional series for sparkline. Component decides whether to render
  // based on variation.
  series?: { date: string; v: number }[];
  accent?: string;
  /** When the parent fund just got created and no metric has landed yet. */
  isPending?: boolean;
}

export function StatBox({
  label,
  value,
  caption,
  change,
  series,
  accent = "#3b82f6",
  isPending,
}: StatBoxProps) {
  const showChart = shouldShowChart(series);
  const changeColour = change
    ? returnColor((change.invert ? -1 : 1) * change.pct)
    : "";

  return (
    <div className="rounded-2xl border border-ink-200/70 dark:border-ink-800
                    bg-white dark:bg-ink-900/70 px-4 py-3.5">
      <div className="text-xs font-medium text-ink-500 dark:text-ink-400">
        {label}
      </div>

      <div className="mt-1 flex items-baseline gap-2">
        {isPending ? (
          <div className="h-7 w-24 rounded-md bg-ink-100 dark:bg-ink-800
                          animate-pulse-soft" />
        ) : (
          <div className="tabular text-2xl font-semibold tracking-tight
                          text-ink-900 dark:text-ink-50">
            {value}
          </div>
        )}
      </div>

      {(caption || change) && !isPending && (
        <div className="mt-0.5 text-xs">
          {caption ? (
            <span className="text-ink-500 dark:text-ink-400">{caption}</span>
          ) : change ? (
            <span className={`tabular ${changeColour}`}>
              {formatPercent(change.pct, { signed: true, digits: 1 })}
              {change.label && (
                <span className="text-ink-500 dark:text-ink-400 ml-1.5">
                  {change.label}
                </span>
              )}
            </span>
          ) : null}
        </div>
      )}

      {showChart && (
        <div className="mt-2 h-10 -mx-1">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={series} margin={{ top: 2, right: 4, left: 4, bottom: 2 }}>
              <Area
                type="monotone"
                dataKey="v"
                stroke={accent}
                strokeWidth={1.5}
                fill={accent}
                fillOpacity={0.12}
                isAnimationActive={false}
              />
              <Tooltip content={<SparkTooltip />} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function shouldShowChart(series?: { date: string; v: number }[]): boolean {
  if (!series || series.length < 6) return false;
  const values = series.map((s) => s.v);
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min <= 0) return Math.abs(max - min) > 0;
  const variationPct = ((max - min) / min) * 100;
  return variationPct >= FLAT_VARIATION_THRESHOLD_PCT;
}

function SparkTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const { date, v } = payload[0].payload;
  return (
    <div className="px-2 py-1 rounded-md bg-ink-900 dark:bg-ink-50
                    text-white dark:text-ink-900 text-[10px] shadow-lg">
      <div className="tabular font-medium">{formatNumberCompact(v)}</div>
      <div className="opacity-60">{formatDate(date)}</div>
    </div>
  );
}

function formatNumberCompact(v: number): string {
  if (Math.abs(v) >= 1_000_000) return v.toLocaleString("tr-TR", { notation: "compact", maximumFractionDigits: 2 });
  return v.toLocaleString("tr-TR", { maximumFractionDigits: 2 });
}
