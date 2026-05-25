import { useMemo, useState } from "react";

import { formatDate, formatTL } from "@/lib/format";
import type { SparklinePoint } from "@/lib/types";

interface Props {
  points: SparklinePoint[];
  width?: number;
  height?: number;
  // When false, the sparkline is rendered colour-coded by net change over
  // the window; when true, the strokes are a static accent colour (used
  // inside fund-row tables where colour means daily-change instead).
  staticColor?: boolean;
}

// Hand-rolled SVG sparkline. Recharts overkill for a 30-point series and
// adds DOM weight to the dashboard, which renders one of these per fund.
// The hover crosshair shows the underlying NAV in a tooltip — that's the
// "günlük fiyatlara hover ile erişebilmeli" requirement.
export function Sparkline({ points, width = 180, height = 44, staticColor = false }: Props) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const path = useMemo(() => {
    if (points.length < 2) return null;
    const prices = points.map((p) => p.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;
    const padX = 1;
    const padY = 3;
    const usableW = width - padX * 2;
    const usableH = height - padY * 2;

    const coords = points.map((p, i) => {
      const x = padX + (i / (points.length - 1)) * usableW;
      const y = padY + (1 - (p.price - min) / range) * usableH;
      return { x, y, ...p };
    });

    const linePath = coords
      .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(2)} ${c.y.toFixed(2)}`)
      .join(" ");
    const fillPath = `${linePath} L ${coords[coords.length - 1].x.toFixed(2)} ${height - padY} L ${coords[0].x.toFixed(2)} ${height - padY} Z`;

    const first = points[0].price;
    const last = points[points.length - 1].price;
    const trend = last - first;

    return { coords, linePath, fillPath, trend, min, max };
  }, [points, width, height]);

  if (!path) {
    return (
      <div
        style={{ width, height }}
        className="rounded-md bg-ink-100 dark:bg-ink-900 animate-pulse-soft"
      />
    );
  }

  const positive = path.trend >= 0;
  const stroke = staticColor
    ? "stroke-ink-500"
    : positive
      ? "stroke-positive"
      : "stroke-negative";
  const fill = staticColor
    ? "fill-ink-400/10"
    : positive
      ? "fill-positive/10"
      : "fill-negative/10";

  function onMove(e: React.PointerEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const ratio = x / rect.width;
    const idx = Math.round(ratio * (points.length - 1));
    if (idx >= 0 && idx < points.length) setHoverIdx(idx);
  }

  const hovered = hoverIdx !== null ? path.coords[hoverIdx] : null;

  return (
    <div className="relative inline-block" style={{ width, height }}>
      <svg
        width={width}
        height={height}
        onPointerMove={onMove}
        onPointerLeave={() => setHoverIdx(null)}
        className="overflow-visible"
      >
        <path d={path.fillPath} className={fill} />
        <path
          d={path.linePath}
          className={stroke}
          fill="none"
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {hovered && (
          <>
            <line
              x1={hovered.x}
              x2={hovered.x}
              y1={0}
              y2={height}
              className="stroke-ink-300 dark:stroke-ink-700"
              strokeWidth="1"
              strokeDasharray="2 2"
            />
            <circle
              cx={hovered.x}
              cy={hovered.y}
              r="3"
              className={`${positive ? "fill-positive" : "fill-negative"} stroke-white dark:stroke-ink-950`}
              strokeWidth="1.5"
            />
          </>
        )}
      </svg>
      {hovered && (
        <div
          className="absolute pointer-events-none z-10 px-2 py-1
                     rounded-md bg-ink-900 dark:bg-ink-100
                     text-white dark:text-ink-900 text-xs whitespace-nowrap"
          style={{
            left: Math.min(width - 110, Math.max(0, hovered.x - 50)),
            top: -36,
          }}
        >
          <div className="tabular font-medium">{formatTL(hovered.price, { digits: 6 })}</div>
          <div className="text-ink-400 dark:text-ink-600 text-[10px]">
            {formatDate(hovered.date)}
          </div>
        </div>
      )}
    </div>
  );
}
