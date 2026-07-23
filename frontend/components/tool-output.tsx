"use client";

import { BacktestResult, type BacktestData } from "@/components/backtest-result";
import { FuturesAnalysis, type FuturesData } from "@/components/futures-analysis";

/** 展开显示某次 skill 调用的原始输出：识别为回测/期货分析则渲染卡片，否则显示原文。 */
export function ToolOutput({ output }: { output: string }) {
  let parsed: Record<string, unknown> | null = null;
  try {
    const p = JSON.parse(output);
    parsed = p && typeof p === "object" ? p : null;
  } catch {
    parsed = null;
  }

  const isBacktest = parsed !== null && (parsed.kind === "backtest" || "metrics" in parsed);
  const isFutures =
    parsed !== null &&
    "ok" in parsed &&
    ("trend" in parsed || "pivots" in parsed || "bearish" in parsed);

  return (
    <div className="mt-2 w-full rounded-lg border border-border bg-card p-3 text-left">
      {isBacktest ? (
        <BacktestResult data={parsed as unknown as BacktestData} />
      ) : isFutures ? (
        <FuturesAnalysis data={parsed as unknown as FuturesData} />
      ) : (
        <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs text-muted-foreground">
          {output}
        </pre>
      )}
    </div>
  );
}
