"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

interface SkillRun {
  id: number;
  skill_id: number | null;
  skill_name: string;
  arguments: Record<string, unknown> | null;
  output: string;
  status: string;
  error: string | null;
  latency_ms: number;
  created_at: string;
}

function fmtTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("zh-CN", { hour12: false });
}

export default function RunsPage() {
  const [runs, setRuns] = useState<SkillRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<Set<number>>(new Set());

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/skill-runs?limit=200`, {
          cache: "no-store",
        });
        setRuns(await res.json());
      } catch {
        /* ignore */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  function toggle(id: number) {
    setOpen((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  return (
    <div className="h-full overflow-y-auto">
      <header className="flex h-14 items-center border-b border-border px-6">
        <h1 className="text-sm font-medium">调用记录</h1>
      </header>

      <div className="mx-auto max-w-3xl px-6 py-8">
        <h2 className="text-2xl font-semibold tracking-tight">Skill 调用审计</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          每次 agent 调用 skill 的输入、输出、耗时与状态。最近 200 条。
        </p>

        <div className="mt-6 flex flex-col gap-2.5">
          {loading &&
            [0, 1, 2].map((i) => <Skeleton key={i} className="h-14 w-full rounded-lg" />)}

          {!loading && runs.length === 0 && (
            <Card className="p-8 text-center text-sm text-muted-foreground">
              还没有调用记录。去聊天页触发一次 skill 调用试试。
            </Card>
          )}

          {runs.map((r) => {
            const expanded = open.has(r.id);
            return (
              <Card key={r.id} className="overflow-hidden">
                <button
                  onClick={() => toggle(r.id)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-accent/40"
                >
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
                      expanded && "rotate-180"
                    )}
                  />
                  <span className="font-medium">{r.skill_name}</span>
                  <Badge variant={r.status === "ok" ? "success" : "outline"}>
                    {r.status === "ok" ? "成功" : "失败"}
                  </Badge>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {r.latency_ms}ms · {fmtTime(r.created_at)}
                  </span>
                </button>

                {expanded && (
                  <div className="space-y-3 border-t border-border px-4 py-3">
                    <Field label="输入参数">
                      {JSON.stringify(r.arguments ?? {}, null, 2)}
                    </Field>
                    {r.error && (
                      <Field label="错误" tone="error">
                        {r.error}
                      </Field>
                    )}
                    <Field label="输出">{r.output || "（空）"}</Field>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
  tone,
}: {
  label: string;
  children: React.ReactNode;
  tone?: "error";
}) {
  return (
    <div>
      <div className="mb-1 text-xs font-medium text-muted-foreground">{label}</div>
      <pre
        className={cn(
          "max-h-60 overflow-auto rounded-md border border-border bg-background p-2.5 text-xs",
          tone === "error" && "border-destructive/40 text-destructive"
        )}
      >
        {children}
      </pre>
    </div>
  );
}
