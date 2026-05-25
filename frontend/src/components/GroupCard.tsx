import { useState } from "react";

import { FundRow } from "@/components/FundRow";
import { formatNumber, formatTL } from "@/lib/format";
import type { FundCard, Group } from "@/lib/types";

interface Props {
  group: Group | null; // null = ungrouped bucket
  funds: FundCard[];
  onEdit?: (group: Group) => void;
}

// Group card aggregates its funds and exposes the per-group totals — total
// AUM exposure across the group's funds, average daily return weighted by
// NAV. These are the "what does this slice of my portfolio look like"
// numbers the user wants visible without opening anything.
export function GroupCard({ group, funds, onEdit }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const totals = aggregate(funds);
  const accent = group?.color ?? "#71717a";

  return (
    <section className="card overflow-hidden">
      <header
        className="flex items-center justify-between px-4 py-3
                   border-b border-ink-100 dark:border-ink-800"
      >
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="w-6 h-6 flex items-center justify-center
                       rounded-md hover:bg-ink-100 dark:hover:bg-ink-800"
            title={collapsed ? "Aç" : "Kapat"}
          >
            <Chevron rotated={!collapsed} />
          </button>
          <span
            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
            style={{ backgroundColor: accent }}
          />
          <h2 className="font-semibold tracking-tight">
            {group?.name ?? "Gruplandırılmamış"}
          </h2>
          <span className="text-xs text-ink-400">{funds.length} fon</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-ink-500 dark:text-ink-400 tabular">
          {totals.investorCount !== null && (
            <span title="Toplam yatırımcı sayısı">
              {formatNumber(totals.investorCount, { compact: true })} yat.
            </span>
          )}
          {totals.aum !== null && (
            <span title="Bu gruptaki fonların toplam büyüklüğü">
              {formatTL(totals.aum, { compact: true, digits: 0 })}
            </span>
          )}
          {group && onEdit && (
            <button
              onClick={() => onEdit(group)}
              className="btn btn-ghost h-7 px-2"
              title="Grubu düzenle"
            >
              <PencilIcon />
            </button>
          )}
        </div>
      </header>

      {!collapsed && (
        <div className="divide-y divide-ink-100 dark:divide-ink-800/60 p-1">
          {funds.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-ink-400">
              Bu grupta fon yok
            </div>
          ) : (
            funds.map((f) => <FundRow key={f.code} fund={f} />)
          )}
        </div>
      )}
    </section>
  );
}

function aggregate(funds: FundCard[]) {
  let totalInvestor = 0;
  let hasInvestor = false;
  let totalAum = 0;
  let hasAum = false;
  for (const f of funds) {
    if (f.investor_count !== null) {
      totalInvestor += f.investor_count;
      hasInvestor = true;
    }
    if (f.aum !== null) {
      totalAum += f.aum;
      hasAum = true;
    }
  }
  return {
    investorCount: hasInvestor ? totalInvestor : null,
    aum: hasAum ? totalAum : null,
  };
}

function Chevron({ rotated }: { rotated: boolean }) {
  return (
    <svg
      className={`w-4 h-4 transition-transform ${rotated ? "" : "-rotate-90"}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function PencilIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z" />
    </svg>
  );
}
