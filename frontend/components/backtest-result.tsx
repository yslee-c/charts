"use client";

import { Badge } from "@/components/ui/badge";

interface Metrics {
  trades: number;
  win_rate: number;
  total_return: number;
  avg_return: number;
  profit_factor: number | null;
  avg_win: number;
  avg_loss: number;
  max_drawdown: number;
}
interface Trade {
  side: "long" | "short";
  entry_date?: string;
  exit_date?: string;
  entry: number;
  exit: number;
  reason: string;
  return_pct: number;
}
export interface BacktestData {
  ok: boolean;
  kind?: string;
  symbol?: string;
  resolved?: string;
  bars_count?: number;
  params?: { entry_conf: number; max_hold: number };
  metrics?: Metrics;
  equity?: number[];
  trades?: Trade[];
  notes?: string[];
  summary?: string;
}

export function BacktestResult({ data }: { data: BacktestData }) {
  if (!data.ok || !data.metrics) {
    return <p className="text-sm text-muted-foreground">{data.summary}</p>;
  }
  const m = data.metrics;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">
          {data.symbol}
          {data.resolved && data.resolved !== data.symbol ? `（${data.resolved}）` : ""}
        </span>
        <Badge variant="secondary">回测</Badge>
        <span className="text-xs text-muted-foreground">
          {data.bars_count} 根 · 阈值 {data.params?.entry_conf} · 最长持仓{" "}
          {data.params?.max_hold} 日
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <Stat label="交易数" value={m.trades} />
        <Stat label="胜率" value={`${m.win_rate}%`} tone={m.win_rate >= 50 ? "pos" : undefined} />
        <Stat
          label="盈亏比"
          value={m.profit_factor ?? "—"}
          tone={m.profit_factor != null && m.profit_factor >= 1 ? "pos" : "neg"}
        />
        <Stat
          label="累计收益"
          value={`${m.total_return}%`}
          tone={m.total_return >= 0 ? "pos" : "neg"}
        />
        <Stat label="单笔均收益" value={`${m.avg_return}%`} tone={m.avg_return >= 0 ? "pos" : "neg"} />
        <Stat label="最大回撤" value={`${m.max_drawdown}%`} tone="neg" />
      </div>

      {data.equity && data.equity.length > 1 && <EquityCurve equity={data.equity} />}

      {data.trades && data.trades.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="text-muted-foreground">
              <tr>
                <th className="px-2 py-1 text-left">方向</th>
                <th className="px-2 py-1 text-right">进场</th>
                <th className="px-2 py-1 text-right">出场</th>
                <th className="px-2 py-1 text-left">原因</th>
                <th className="px-2 py-1 text-right">收益</th>
              </tr>
            </thead>
            <tbody>
              {data.trades.slice(-8).map((t, i) => (
                <tr key={i} className="border-t border-border">
                  <td className="px-2 py-1">{t.side === "long" ? "多" : "空"}</td>
                  <td className="px-2 py-1 text-right">{t.entry}</td>
                  <td className="px-2 py-1 text-right">{t.exit}</td>
                  <td className="px-2 py-1 text-muted-foreground">{t.reason}</td>
                  <td
                    className={
                      "px-2 py-1 text-right " +
                      (t.return_pct >= 0 ? "text-success" : "text-destructive")
                    }
                  >
                    {t.return_pct}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-[11px] text-muted-foreground">
        简化模型（次日开盘进出、摆动点止损，未计滑点手续费）。历史回测不代表未来，非投资建议。
      </p>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone?: "pos" | "neg";
}) {
  return (
    <div className="rounded-md border border-border p-2">
      <div className="text-[11px] text-muted-foreground">{label}</div>
      <div
        className={
          "text-sm font-semibold " +
          (tone === "pos" ? "text-success" : tone === "neg" ? "text-destructive" : "")
        }
      >
        {value}
      </div>
    </div>
  );
}

function EquityCurve({ equity }: { equity: number[] }) {
  const W = 600;
  const H = 90;
  const pad = 6;
  const min = Math.min(0, ...equity);
  const max = Math.max(0, ...equity);
  const span = max - min || 1;
  const x = (k: number) => pad + (k / (equity.length - 1)) * (W - 2 * pad);
  const y = (v: number) => pad + (1 - (v - min) / span) * (H - 2 * pad);
  const pts = equity.map((v, k) => `${x(k).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const up = equity[equity.length - 1] >= 0;

  return (
    <div className="rounded-md border border-border bg-background p-1">
      <div className="px-1 pt-1 text-[11px] text-muted-foreground">资金曲线（累计收益 %）</div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: H }}>
        <line
          x1={pad}
          x2={W - pad}
          y1={y(0)}
          y2={y(0)}
          stroke="hsl(var(--border))"
          strokeWidth={1}
        />
        <polyline
          points={pts}
          fill="none"
          stroke={up ? "hsl(var(--success))" : "hsl(var(--destructive))"}
          strokeWidth={1.5}
        />
      </svg>
    </div>
  );
}
