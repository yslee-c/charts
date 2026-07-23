"use client";

import { FuturesAnalysis, type FuturesData } from "@/components/futures-analysis";

/** 展开显示某次 skill 调用的原始输出：能识别为期货分析则渲染卡片，否则显示原文。 */
export function ToolOutput({ output }: { output: string }) {
  let parsed: unknown = null;
  try {
    parsed = JSON.parse(output);
  } catch {
    parsed = null;
  }

  const isFutures =
    parsed &&
    typeof parsed === "object" &&
    "ok" in parsed &&
    ("trend" in parsed || "summary" in parsed) &&
    ("pivots" in parsed || "bearish" in parsed || (parsed as FuturesData).ok === false);

  return (
    <div className="mt-2 w-full rounded-lg border border-border bg-card p-3 text-left">
      {isFutures ? (
        <FuturesAnalysis data={parsed as FuturesData} />
      ) : (
        <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs text-muted-foreground">
          {output}
        </pre>
      )}
    </div>
  );
}
