// Inline SVG charts for the Monday board. No chart library, per the Graphed
// dashboard conventions. Colors come from Tailwind stroke/fill classes so the
// charts follow the light/dark theme.

export function compact(value: number): string {
  const abs = Math.abs(value);
  const digits = abs >= 1000 ? 1 : 0;
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(digits)}m`;
  if (abs >= 1_000) return `${(value / 1_000).toFixed(digits)}k`;
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

export function money(value: number, digits = 0): string {
  return `$${value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
}

export function shortDay(day: string): string {
  const date = new Date(`${day.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return day;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}

function smoothLine(points: { x: number; y: number }[]): string {
  const first = points[0];
  if (!first) return "";
  if (points.length === 1) return `M${first.x},${first.y}`;
  let path = `M${first.x},${first.y}`;
  for (let index = 0; index < points.length - 1; index += 1) {
    const from = points[index];
    const to = points[index + 1];
    if (!from || !to) continue;
    const mid = (from.x + to.x) / 2;
    path += ` C${mid},${from.y} ${mid},${to.y} ${to.x},${to.y}`;
  }
  return path;
}

function clipLabel(label: string | null): string {
  const text = label == null || label === "" ? "(none)" : label;
  return text.length > 34 ? `${text.slice(0, 33)}…` : text;
}

export type Tone = "primary" | "muted" | "warn" | "info";

const STROKE: Record<Tone, string> = {
  primary: "stroke-emerald-400",
  muted: "stroke-slate-400",
  warn: "stroke-amber-400",
  info: "stroke-sky-400",
};
const DOT: Record<Tone, string> = {
  primary: "bg-emerald-400",
  muted: "bg-slate-400",
  warn: "bg-amber-400",
  info: "bg-sky-400",
};
const FILL_COLOR: Record<Tone, string> = {
  primary: "#34d399",
  muted: "#94a3b8",
  warn: "#fbbf24",
  info: "#38bdf8",
};

export interface Series {
  label: string;
  tone: Tone;
  data: { x: string; y: number | null }[];
  dashed?: boolean;
}

export interface Marker {
  x: string;
  label: string;
}

/**
 * Multi-series smooth line chart with an area fill under the first series,
 * optional dashed vertical markers (dated events), and a legend.
 */
export function TrendChart({
  series,
  label,
  markers = [],
  format = compact,
  gradientId,
}: {
  series: Series[];
  label: string;
  markers?: Marker[];
  format?: (value: number) => string;
  gradientId: string;
}) {
  const xs = [...new Set(series.flatMap((s) => s.data.map((d) => d.x)))].sort();
  if (xs.length === 0) {
    return (
      <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
        No rows in this window.
      </div>
    );
  }

  const width = 720;
  const height = 300;
  const pad = { top: 20, right: 20, bottom: 36, left: 52 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const values = series.flatMap((s) => s.data.map((d) => d.y)).filter((v): v is number => v != null);
  const minValue = Math.min(0, ...values);
  const maxValue = Math.max(0, ...values) || 1;
  const span = maxValue - minValue || 1;
  const xFor = (x: string) => {
    const index = xs.indexOf(x);
    return pad.left + (xs.length === 1 ? innerW / 2 : (index / (xs.length - 1)) * innerW);
  };
  const yFor = (value: number) => pad.top + innerH - ((value - minValue) / span) * innerH;
  const zeroY = yFor(Math.max(0, minValue));

  const tickValues = [0, maxValue / 2, maxValue];
  const dateIndexes = [0, Math.floor((xs.length - 1) / 2), xs.length - 1];

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
        {series.map((s) => (
          <span key={s.label} className="inline-flex items-center gap-1.5">
            <span className={`inline-block h-2 w-2 rounded-full ${DOT[s.tone]}`} />
            {s.label}
          </span>
        ))}
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-72 w-full" role="img" aria-label={label}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={FILL_COLOR[series[0]?.tone ?? "primary"]} stopOpacity="0.35" />
            <stop offset="100%" stopColor={FILL_COLOR[series[0]?.tone ?? "primary"]} stopOpacity="0" />
          </linearGradient>
        </defs>
        {tickValues.map((value) => (
          <g key={`tick-${value}`}>
            <line
              x1={pad.left}
              x2={width - pad.right}
              y1={yFor(value)}
              y2={yFor(value)}
              stroke="currentColor"
              className="text-border"
              strokeDasharray="3 6"
            />
            <text x={pad.left - 10} y={yFor(value) + 4} textAnchor="end" className="fill-muted-foreground text-[11px]">
              {format(value)}
            </text>
          </g>
        ))}
        {markers
          .filter((m) => xs.includes(m.x) || (m.x >= (xs[0] ?? "") && m.x <= (xs[xs.length - 1] ?? "")))
          .map((m) => {
            const nearest = xs.includes(m.x) ? m.x : (xs.find((x) => x >= m.x) ?? xs[xs.length - 1]!);
            const x = xFor(nearest);
            return (
              <g key={`marker-${m.x}`}>
                <line x1={x} x2={x} y1={pad.top} y2={pad.top + innerH} className="stroke-amber-400/70" strokeDasharray="4 4" strokeWidth="1.5" />
                <text x={x + 5} y={pad.top + 11} className="fill-amber-500 text-[10px] font-medium">
                  {m.label}
                </text>
              </g>
            );
          })}
        {series.map((s, seriesIndex) => {
          const points = s.data
            .filter((d) => d.y != null)
            .sort((a, b) => (a.x < b.x ? -1 : 1))
            .map((d) => ({ x: xFor(d.x), y: yFor(d.y as number), row: d }));
          if (points.length === 0) return null;
          const line = smoothLine(points);
          const area = `${line} L${points[points.length - 1]?.x ?? pad.left},${zeroY} L${points[0]?.x ?? pad.left},${zeroY} Z`;
          const last = points[points.length - 1]!;
          return (
            <g key={s.label}>
              {seriesIndex === 0 ? <path d={area} fill={`url(#${gradientId})`} /> : null}
              {seriesIndex === 0 ? (
                <path d={line} fill="none" className={`${STROKE[s.tone]} opacity-30`} strokeWidth="8" strokeLinecap="round" />
              ) : null}
              <path
                d={line}
                fill="none"
                className={STROKE[s.tone]}
                strokeWidth={seriesIndex === 0 ? 2.5 : 2}
                strokeLinecap="round"
                strokeDasharray={s.dashed ? "6 5" : undefined}
              />
              <circle cx={last.x} cy={last.y} r="3.5" className={`fill-card ${STROKE[s.tone]}`} strokeWidth="2" />
              <text x={Math.min(last.x + 6, width - 4)} y={last.y - 6} textAnchor={last.x > width - 60 ? "end" : "start"} className="fill-foreground text-[11px] font-medium tabular-nums">
                {format(last.row.y as number)}
              </text>
            </g>
          );
        })}
        {dateIndexes.map((index) => {
          const x = xs[index];
          if (x === undefined) return null;
          const anchor = index === 0 ? "start" : index === xs.length - 1 ? "end" : "middle";
          return (
            <text key={`date-${x}`} x={xFor(x)} y={height - 10} textAnchor={anchor} className="fill-muted-foreground text-[11px]">
              {shortDay(x)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

/** Horizontal bars with a muted track and the value at the right. */
export function BreakdownChart({
  data,
  label,
  format = compact,
  highlight,
}: {
  data: { label: string | null; value: number; note?: string }[];
  label: string;
  format?: (value: number) => string;
  highlight?: (row: { label: string | null; value: number }) => boolean;
}) {
  if (data.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
        No breakdown rows in this window.
      </div>
    );
  }
  const rows = data.slice(0, 10);
  const width = 720;
  const rowH = 40;
  const height = rows.length * rowH + 8;
  const labelW = 240;
  const valueW = 70;
  const barX = labelW;
  const barMax = width - labelW - valueW - 12;
  const maxValue = Math.max(...rows.map((row) => Math.abs(row.value)), 1);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img" aria-label={label}>
      <defs>
        <linearGradient id="bar-fill" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#34d399" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#34d399" stopOpacity="1" />
        </linearGradient>
        <linearGradient id="bar-fill-warn" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#fbbf24" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#fbbf24" stopOpacity="1" />
        </linearGradient>
      </defs>
      {rows.map((row, index) => {
        const y = 8 + index * rowH;
        const magnitude = Math.abs(row.value);
        const barW = magnitude === 0 ? 0 : Math.max((magnitude / maxValue) * barMax, 10);
        const warn = highlight?.(row) ?? false;
        return (
          <g key={`${clipLabel(row.label)}-${index}`}>
            <text x={0} y={y + 14} className="fill-foreground text-[12px]">
              {clipLabel(row.label)}
            </text>
            {row.note ? (
              <text x={0} y={y + 27} className="fill-muted-foreground text-[10px]">
                {row.note}
              </text>
            ) : null}
            <rect x={barX} y={y + 6} width={barMax} height={16} rx={8} className="fill-muted" />
            <rect x={barX} y={y + 6} width={barW} height={16} rx={8} fill={warn ? "url(#bar-fill-warn)" : "url(#bar-fill)"} />
            <text x={width} y={y + 18} textAnchor="end" className="fill-foreground text-[12px] tabular-nums">
              {format(row.value)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** Tiny sparkline for scorecards. */
export function Sparkline({ data, tone = "primary", id }: { data: number[]; tone?: Tone; id: string }) {
  if (data.length < 2) return null;
  const width = 120;
  const height = 36;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const points = data.map((v, i) => ({ x: (i / (data.length - 1)) * width, y: height - 4 - ((v - min) / span) * (height - 8) }));
  const line = smoothLine(points);
  const area = `${line} L${width},${height} L0,${height} Z`;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-10 w-28" aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={FILL_COLOR[tone]} stopOpacity="0.4" />
          <stop offset="100%" stopColor={FILL_COLOR[tone]} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id})`} />
      <path d={line} fill="none" className={STROKE[tone]} strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
