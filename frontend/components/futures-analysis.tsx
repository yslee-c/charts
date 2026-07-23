"use client";

import { Badge } from "@/components/ui/badge";

interface Pivot {
  i: number;
  date: string;
  price: number;
}
interface Cond {
  code: string;
  label: string;
  met: boolean;
}
export interface FuturesData {
  ok: boolean;
  symbol?: string;
  resolved?: string;
  as_of?: string;
  trend?: "up" | "down" | "range";
  last_close?: number;
  bars_count?: number;
  atr?: number;
  confidence?: { bearish: number; bullish: number };
  pivots?: { highs: Pivot[]; lows: Pivot[] };
  bearish?: { count: number; twoB: boolean; ordered?: boolean; confidence?: number; conditions: Cond[] };
  bullish?: { count: number; twoB: boolean; ordered?: boolean; confidence?: number; conditions: Cond[] };
  stops?: { short_ref: number | null; long_ref: number | null };
  notes?: string[];
  series?: [string, number][];
  summary?: string;
}

const TREND_CN: Record<string, string> = { up: "上升", down: "下降", range: "盘整/震荡" };

export function FuturesAnalysis({ data }: { data: FuturesData }) {
  if (!data.ok) {
    return <p className="text-sm text-muted-foreground">{data.summary}</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">
          {data.symbol}
          {data.resolved && data.resolved !== data.symbol ? `（${data.resolved}）` : ""}
        </span>
        <Badge variant={data.trend === "range" ? "outline" : "secondary"}>
          {TREND_CN[data.trend ?? "range"]}
        </Badge>
        <span className="text-xs text-muted-foreground">
          收盘 {data.last_close} · 截至 {data.as_of} · {data.bars_count} 根
        </span>
      </div>

      {data.series && data.series.length > 1 && (
        <PriceChart
          series={data.series}
          highs={data.pivots?.highs ?? []}
          lows={data.pivots?.lows ?? []}
          stops={data.stops}
        />
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        <ConditionList
          title="看跌 123"
          count={data.bearish?.count ?? 0}
          twoB={data.bearish?.twoB ?? false}
          ordered={data.bearish?.ordered ?? false}
          confidence={data.bearish?.confidence ?? data.confidence?.bearish ?? 0}
          conds={data.bearish?.conditions ?? []}
        />
        <ConditionList
          title="看涨 123"
          count={data.bullish?.count ?? 0}
          twoB={data.bullish?.twoB ?? false}
          ordered={data.bullish?.ordered ?? false}
          confidence={data.bullish?.confidence ?? data.confidence?.bullish ?? 0}
          conds={data.bullish?.conditions ?? []}
        />
      </div>

      {data.stops && (
        <div className="text-xs text-muted-foreground">
          参考位：做空止损 {data.stops.short_ref ?? "—"} · 做多止损 {data.stops.long_ref ?? "—"}
        </div>
      )}

      {data.notes && data.notes.length > 0 && (
        <div className="rounded-md border border-border bg-background px-2.5 py-1.5 text-xs text-muted-foreground">
          {data.notes.map((n, i) => (
            <div key={i}>· {n}</div>
          ))}
        </div>
      )}

      <p className="text-[11px] text-muted-foreground">技术分析仅供参考，非投资建议。</p>
    </div>
  );
}

function ConditionList({
  title,
  count,
  twoB,
  ordered,
  confidence,
  conds,
}: {
  title: string;
  count: number;
  twoB: boolean;
  ordered: boolean;
  confidence: number;
  conds: Cond[];
}) {
  return (
    <div className="rounded-md border border-border p-2.5">
      <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
        <span className="text-sm font-medium">{title}</span>
        <Badge variant={count >= 2 ? "success" : "outline"}>{count}/3</Badge>
        {ordered && <Badge variant="outline">时序</Badge>}
        {twoB && <Badge variant="success">2B</Badge>}
        <Badge variant={confidence >= 50 ? "success" : "outline"}>
          置信 {confidence}
        </Badge>
      </div>
      <ul className="space-y-1">
        {conds.map((c) => (
          <li key={c.code} className="flex items-center gap-1.5 text-xs">
            <span className={c.met ? "text-success" : "text-muted-foreground/50"}>
              {c.met ? "✓" : "○"}
            </span>
            <span className={c.met ? "" : "text-muted-foreground"}>
              {c.code} {c.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function PriceChart({
  series,
  highs,
  lows,
  stops,
}: {
  series: [string, number][];
  highs: Pivot[];
  lows: Pivot[];
  stops?: { short_ref: number | null; long_ref: number | null };
}) {
  const W = 600;
  const H = 150;
  const pad = { l: 6, r: 6, t: 10, b: 10 };
  const closes = series.map((s) => s[1]);
  let min = Math.min(...closes);
  let max = Math.max(...closes);
  const levels = [stops?.short_ref, stops?.long_ref].filter(
    (v): v is number => typeof v === "number"
  );
  for (const v of levels) {
    min = Math.min(min, v);
    max = Math.max(max, v);
  }
  const span = max - min || 1;
  const x = (k: number) => pad.l + (k / (series.length - 1)) * (W - pad.l - pad.r);
  const y = (v: number) => pad.t + (1 - (v - min) / span) * (H - pad.t - pad.b);

  const dateIndex = (d: string) => series.findIndex((s) => s[0] === d);
  const linePts = series.map((s, k) => `${x(k).toFixed(1)},${y(s[1]).toFixed(1)}`).join(" ");

  return (
    <div className="overflow-x-auto rounded-md border border-border bg-background p-1">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: H }}>
        {/* 止损参考位 */}
        {stops?.short_ref != null && (
          <line
            x1={pad.l}
            x2={W - pad.r}
            y1={y(stops.short_ref)}
            y2={y(stops.short_ref)}
            stroke="hsl(var(--destructive))"
            strokeWidth={1}
            strokeDasharray="4 4"
            opacity={0.5}
          />
        )}
        {stops?.long_ref != null && (
          <line
            x1={pad.l}
            x2={W - pad.r}
            y1={y(stops.long_ref)}
            y2={y(stops.long_ref)}
            stroke="hsl(var(--success))"
            strokeWidth={1}
            strokeDasharray="4 4"
            opacity={0.5}
          />
        )}
        {/* 收盘价线 */}
        <polyline
          points={linePts}
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth={1.5}
        />
        {/* 摆动高点（红） */}
        {highs.map((h, idx) => {
          const k = dateIndex(h.date);
          if (k < 0) return null;
          return (
            <circle
              key={`h${idx}`}
              cx={x(k)}
              cy={y(h.price)}
              r={3}
              fill="hsl(var(--destructive))"
            />
          );
        })}
        {/* 摆动低点（绿） */}
        {lows.map((l, idx) => {
          const k = dateIndex(l.date);
          if (k < 0) return null;
          return (
            <circle
              key={`l${idx}`}
              cx={x(k)}
              cy={y(l.price)}
              r={3}
              fill="hsl(var(--success))"
            />
          );
        })}
      </svg>
    </div>
  );
}
