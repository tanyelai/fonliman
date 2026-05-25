import { Link } from "react-router-dom";

import { Sparkline } from "@/components/Sparkline";
import {
  formatNumber,
  formatPercent,
  formatTL,
  returnColor,
  riskColor,
} from "@/lib/format";
import type { FundCard } from "@/lib/types";

interface Props {
  fund: FundCard;
}

// One row of a group card. Heavy on the sparkline (the user said
// "görsel-ağırlıklı"), with returns as compact pills so they don't crowd
// the chart. Click anywhere to drill into the fund detail page.
export function FundRow({ fund }: Props) {
  const showRank = fund.category_rank !== null && fund.category_total !== null;

  return (
    <Link
      to={`/fon/${fund.code}`}
      className="grid grid-cols-12 gap-3 items-center px-4 py-3
                 hover:bg-ink-100/50 dark:hover:bg-ink-800/30
                 transition-colors group rounded-xl"
    >
      {/* Identity: code + name + risk pill */}
      <div className="col-span-4 sm:col-span-3 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="font-mono font-semibold text-sm tracking-tight">{fund.code}</span>
          {fund.risk_score !== null && (
            <span className={`pill ${riskColor(fund.risk_score)}`}>R{fund.risk_score}</span>
          )}
        </div>
        <div className="text-xs text-ink-500 dark:text-ink-400 truncate mt-0.5" title={fund.name}>
          {fund.name}
        </div>
      </div>

      {/* Sparkline — the visual centre of gravity */}
      <div className="col-span-4 sm:col-span-3 flex justify-center">
        <Sparkline points={fund.sparkline} width={170} height={42} />
      </div>

      {/* Price + daily change — the single most "what's happening now" datum */}
      <div className="col-span-4 sm:col-span-2 text-right">
        <div className="tabular font-medium text-sm">{formatTL(fund.latest_price)}</div>
        <div className={`tabular text-xs ${returnColor(fund.daily_return_pct)}`}>
          {formatPercent(fund.daily_return_pct, { signed: true })}
        </div>
      </div>

      {/* Return windows — compact grid so they read as a single block */}
      <div className="hidden sm:flex col-span-3 justify-end gap-1 text-xs tabular">
        <ReturnChip label="1A" value={fund.return_1m} />
        <ReturnChip label="YBD" value={fund.return_ytd} />
        <ReturnChip label="1Y" value={fund.return_1y} />
      </div>

      {/* Rank — only when we have it */}
      <div className="hidden sm:block col-span-1 text-right">
        {showRank ? (
          <div className="text-xs tabular text-ink-500 dark:text-ink-400">
            <span className="font-medium text-ink-900 dark:text-ink-100">{fund.category_rank}</span>
            <span className="text-ink-400">/{fund.category_total}</span>
          </div>
        ) : (
          <span className="text-ink-300 dark:text-ink-700">—</span>
        )}
      </div>
    </Link>
  );
}

function ReturnChip({ label, value }: { label: string; value: number | null }) {
  if (value === null) {
    return (
      <div className="flex flex-col items-end min-w-[3.5rem] opacity-40">
        <div className="text-[10px] text-ink-400">{label}</div>
        <div className="text-ink-400">—</div>
      </div>
    );
  }
  return (
    <div className="flex flex-col items-end min-w-[3.5rem]">
      <div className="text-[10px] text-ink-400 dark:text-ink-500">{label}</div>
      <div className={returnColor(value)}>{formatPercent(value, { signed: true, digits: 1 })}</div>
    </div>
  );
}

// Helper for empty-state — exposed for tests later.
export function fundAumLabel(fund: FundCard) {
  if (fund.investor_count === null && fund.aum === null) return null;
  const parts = [];
  if (fund.investor_count !== null) parts.push(`${formatNumber(fund.investor_count, { compact: true })} yatırımcı`);
  if (fund.aum !== null) parts.push(formatTL(fund.aum, { compact: true, digits: 0 }));
  return parts.join(" • ");
}
