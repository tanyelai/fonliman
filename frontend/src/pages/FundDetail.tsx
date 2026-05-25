import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import useSWR, { mutate } from "swr";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AllocationChart } from "@/components/AllocationChart";
import { StatBox } from "@/components/StatBox";
import { deleteResource, patchJSON } from "@/lib/api";
import {
  formatDate,
  formatNumber,
  formatPercent,
  formatTL,
  returnColor,
  riskColor,
} from "@/lib/format";
import type { FundDetail as FundDetailPayload, Group } from "@/lib/types";

type Window = "1A" | "3A" | "6A" | "1Y" | "Hepsi";

const WINDOWS: { label: Window; days: number | null }[] = [
  { label: "1A", days: 30 },
  { label: "3A", days: 90 },
  { label: "6A", days: 180 },
  { label: "1Y", days: 365 },
  { label: "Hepsi", days: null },
];

export function FundDetail() {
  const { code = "" } = useParams<{ code: string }>();
  const upperCode = code.toUpperCase();
  const { data, isLoading, error } = useSWR<FundDetailPayload>(
    `/api/funds/${upperCode}/detail`,
    {
      // Freshly added funds need a moment for backfill to land. Poll every
      // 2.5 s while NAV is still empty; back off once the chart has data.
      refreshInterval: (latest) =>
        latest && latest.nav && latest.nav.length > 0 ? 0 : 2500,
    },
  );
  const { data: groups } = useSWR<Group[]>("/api/groups");
  const [chartWindow, setChartWindow] = useState<Window>("3A");

  const nav = data?.nav ?? [];
  const rank = data?.rank ?? [];

  const navWindowed = useMemo(() => {
    const win = WINDOWS.find((w) => w.label === chartWindow)!;
    if (win.days === null) return nav;
    return nav.slice(-win.days);
  }, [nav, chartWindow]);

  const navTrend = useMemo(() => {
    if (navWindowed.length < 2) return null;
    const first = navWindowed[0].price;
    const last = navWindowed[navWindowed.length - 1].price;
    return ((last - first) / first) * 100;
  }, [navWindowed]);

  const investorSeries = useMemo(
    () => nav.filter((n) => n.investor_count !== null)
              .map((n) => ({ date: n.date, v: n.investor_count! })),
    [nav],
  );
  const aumSeries = useMemo(
    () => nav.filter((n) => n.aum !== null)
              .map((n) => ({ date: n.date, v: n.aum! })),
    [nav],
  );
  const rankSeries = useMemo(
    () => rank.filter((r) => r.category_rank !== null)
              .map((r) => ({ date: r.date, v: r.category_rank! })),
    [rank],
  );

  if (isLoading && !data) return <DetailSkeleton />;
  if (error || !data) {
    return (
      <div className="card p-8 text-center">
        <h2 className="font-semibold mb-2">Fon bulunamadı</h2>
        <Link to="/" className="text-sm text-ink-500 underline">
          Panele dön
        </Link>
      </div>
    );
  }

  const { fund, returns, allocation } = data;
  const latest = nav[nav.length - 1];
  const isBackfilling = nav.length === 0;

  // Helper for derived stats.
  const seriesChange = (s: { date: string; v: number }[]) => {
    if (s.length < 2) return null;
    const first = s[0].v;
    if (!first) return null;
    return ((s[s.length - 1].v - first) / first) * 100;
  };

  const latestRank = rank.length ? rank[rank.length - 1] : null;
  const rankPercentile = latestRank && latestRank.category_total
    ? (latestRank.category_rank! / latestRank.category_total) * 100
    : null;

  async function changeGroup(groupId: number | null) {
    await patchJSON(`/api/funds/${fund.code}`, { group_id: groupId });
    mutate(`/api/funds/${fund.code}/detail`);
    mutate("/api/dashboard");
  }

  async function onDelete() {
    if (!confirm(`${fund.code} fonunu izlemekten kaldırmak istediğine emin misin?`)) return;
    await deleteResource(`/api/funds/${fund.code}`);
    mutate("/api/dashboard");
    window.location.href = "/";
  }

  return (
    <div className="space-y-4">
      {/* Identity */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Link to="/" className="text-xs text-ink-500 hover:text-ink-900 dark:hover:text-ink-100">
            ← Panel
          </Link>
          <div className="flex items-baseline gap-3 mt-1 flex-wrap">
            <h1 className="font-mono font-bold text-2xl tracking-tight">{fund.code}</h1>
            {fund.risk_score !== null && (
              <span className={`pill ${riskColor(fund.risk_score)}`}>R{fund.risk_score}</span>
            )}
            {fund.tefas_category && (
              <span className="text-xs text-ink-500">{fund.tefas_category}</span>
            )}
          </div>
          <h2 className="text-sm text-ink-600 dark:text-ink-400 mt-0.5">{fund.name}</h2>
        </div>
        <div className="flex flex-col items-end gap-2">
          <select
            value={fund.group_id ?? ""}
            onChange={(e) => changeGroup(e.target.value ? Number(e.target.value) : null)}
            className="text-xs px-2.5 py-1.5 rounded-lg
                       bg-ink-100 dark:bg-ink-800
                       border border-ink-200 dark:border-ink-700
                       text-ink-900 dark:text-ink-50
                       focus:outline-none focus:ring-2
                       focus:ring-ink-300 dark:focus:ring-ink-600"
          >
            <option value="">Gruplandırılmamış</option>
            {(groups ?? []).map((g) => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
          <button onClick={onDelete} className="text-xs text-negative hover:underline">
            Listemden çıkar
          </button>
        </div>
      </div>

      {/* Big NAV chart */}
      <section className="card p-4">
        <div className="flex items-start justify-between mb-3 flex-wrap gap-2">
          <div>
            <div className="tabular text-3xl font-semibold tracking-tight">
              {isBackfilling ? "—" : formatTL(latest?.price, { digits: 6 })}
            </div>
            <div className="flex items-baseline gap-2 mt-1">
              {navTrend !== null && (
                <span className={`tabular text-sm ${returnColor(navTrend)}`}>
                  {formatPercent(navTrend, { signed: true })}
                </span>
              )}
              <span className="text-xs text-ink-400">
                {isBackfilling
                  ? "Veri yükleniyor…"
                  : `${chartWindow} • son ${formatDate(latest?.date)}`}
              </span>
            </div>
          </div>
          <div className="flex bg-ink-100 dark:bg-ink-800 rounded-lg p-0.5">
            {WINDOWS.map((w) => (
              <button
                key={w.label}
                onClick={() => setChartWindow(w.label)}
                className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                  chartWindow === w.label
                    ? "bg-white dark:bg-ink-700 shadow-sm text-ink-900 dark:text-ink-50"
                    : "text-ink-500 dark:text-ink-400"
                }`}
              >
                {w.label}
              </button>
            ))}
          </div>
        </div>

        <div className="h-64 -ml-2">
          {isBackfilling ? (
            <BackfillingChart />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={navWindowed} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                <defs>
                  <linearGradient id="navFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={(navTrend ?? 0) >= 0 ? "#10b981" : "#ef4444"} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={(navTrend ?? 0) >= 0 ? "#10b981" : "#ef4444"} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke="#a1a1aa" strokeOpacity={0.18} vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(d) => formatChartDate(d)}
                  minTickGap={40}
                />
                <YAxis
                  domain={["auto", "auto"]}
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v) => v.toLocaleString("tr-TR", { maximumFractionDigits: 2 })}
                  width={56}
                />
                <Tooltip content={<NavTooltip />} />
                <Area
                  type="monotone"
                  dataKey="price"
                  stroke={(navTrend ?? 0) >= 0 ? "#10b981" : "#ef4444"}
                  strokeWidth={2}
                  fill="url(#navFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      {/* Return windows */}
      {returns && (
        <section className="card p-4">
          <h3 className="text-xs font-semibold text-ink-500 dark:text-ink-400 mb-3">
            Getiriler
          </h3>
          <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
            <ReturnTile label="1 Ay" value={returns.return_1m} />
            <ReturnTile label="3 Ay" value={returns.return_3m} />
            <ReturnTile label="6 Ay" value={returns.return_6m} />
            <ReturnTile label="YBD" value={returns.return_ytd} />
            <ReturnTile label="1 Yıl" value={returns.return_1y} />
            <ReturnTile label="3 Yıl" value={returns.return_3y} />
            <ReturnTile label="5 Yıl" value={returns.return_5y} />
          </div>
        </section>
      )}

      {/* Bottom grid: allocation + metric stat boxes */}
      <div className="grid md:grid-cols-2 gap-4">
        {allocation && allocation.items.length > 0 && (
          <section className="card p-4">
            <div className="flex items-baseline justify-between mb-3">
              <h3 className="text-xs font-semibold text-ink-500 dark:text-ink-400">
                Portföy dağılımı
              </h3>
              <span className="text-[11px] text-ink-400">{formatDate(allocation.date)}</span>
            </div>
            <AllocationChart items={allocation.items} />
          </section>
        )}

        <section className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:auto-rows-min">
          <StatBox
            label="Yatırımcı sayısı"
            value={
              latest?.investor_count !== null && latest?.investor_count !== undefined
                ? formatNumber(latest.investor_count, { compact: true })
                : "—"
            }
            change={
              investorSeries.length > 1
                ? { pct: seriesChange(investorSeries) ?? 0, label: `${investorSeries.length} günde` }
                : undefined
            }
            series={investorSeries}
            accent="#3b82f6"
            isPending={isBackfilling}
          />

          <StatBox
            label="Fon büyüklüğü"
            value={
              latest?.aum !== null && latest?.aum !== undefined
                ? formatTL(latest.aum, { compact: true, digits: 0 })
                : "—"
            }
            change={
              aumSeries.length > 1
                ? { pct: seriesChange(aumSeries) ?? 0, label: `${aumSeries.length} günde` }
                : undefined
            }
            series={aumSeries}
            accent="#8b5cf6"
            isPending={isBackfilling}
          />

          <StatBox
            label="Kategori sıralaması"
            value={
              latestRank
                ? `${latestRank.category_rank} / ${latestRank.category_total}`
                : "—"
            }
            caption={
              rankPercentile !== null
                ? rankPercentile <= 50
                  ? `Kategorinin üst %${rankPercentile.toFixed(1).replace(".", ",")}'lık diliminde`
                  : `Kategorinin alt %${(100 - rankPercentile).toFixed(1).replace(".", ",")}'lık diliminde`
                : undefined
            }
            series={rankSeries}
            accent="#f59e0b"
            isPending={isBackfilling}
          />

          <StatBox
            label="Risk skoru (KIID)"
            value={fund.risk_score !== null ? `${fund.risk_score} / 7` : "—"}
            caption={fund.risk_score !== null ? riskCaption(fund.risk_score) : undefined}
            isPending={false}
          />
        </section>
      </div>
    </div>
  );
}

// Helpers --------------------------------------------------------------------

function riskCaption(score: number): string {
  if (score <= 2) return "Düşük risk";
  if (score <= 4) return "Orta-düşük risk";
  if (score <= 5) return "Orta risk";
  if (score === 6) return "Yüksek risk";
  return "Çok yüksek risk";
}

function formatChartDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("tr-TR", { day: "2-digit", month: "short" });
}

function NavTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const { date, price } = payload[0].payload;
  return (
    <div className="px-2.5 py-1.5 rounded-lg bg-ink-900 dark:bg-ink-50
                    text-white dark:text-ink-900 text-xs shadow-lg">
      <div className="tabular font-semibold">{formatTL(price, { digits: 6 })}</div>
      <div className="opacity-60">{formatDate(date)}</div>
    </div>
  );
}

function ReturnTile({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="bg-ink-50 dark:bg-ink-900/60 rounded-xl px-3 py-2.5 text-center
                    border border-ink-100 dark:border-ink-800">
      <div className="text-[10px] text-ink-500 dark:text-ink-400 font-medium">{label}</div>
      <div className={`tabular text-sm font-semibold mt-1 ${returnColor(value)}`}>
        {formatPercent(value, { signed: true, digits: 1 })}
      </div>
    </div>
  );
}

function BackfillingChart() {
  return (
    <div className="h-full flex flex-col items-center justify-center gap-2">
      <div className="w-6 h-6 rounded-full border-2 border-ink-300 dark:border-ink-700
                      border-t-positive animate-spin" />
      <div className="text-xs text-ink-500 dark:text-ink-400">
        TEFAS'tan geçmiş çekiliyor…
      </div>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-4 animate-pulse-soft">
      <div className="h-8 w-40 bg-ink-100 dark:bg-ink-800 rounded" />
      <div className="card p-4 h-80" />
      <div className="card p-4 h-24" />
    </div>
  );
}
