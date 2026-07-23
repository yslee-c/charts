import { ArrowRight, Blocks, MessageSquare } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function getBackendHealth(): Promise<{ ok: boolean; detail: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
    if (!res.ok) return { ok: false, detail: `HTTP ${res.status}` };
    const data = await res.json();
    return { ok: data.status === "ok", detail: `数据库 ${data.database}` };
  } catch {
    return { ok: false, detail: "无法连接后端（后端是否已启动？）" };
  }
}

export default async function Home() {
  const health = await getBackendHealth();

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-8 py-16">
        <Badge variant="outline" className="mb-4">
          MVP · M2
        </Badge>
        <h1 className="text-4xl font-semibold tracking-tight">
          Agent 化的 Skills 中心
        </h1>
        <p className="mt-3 text-lg text-muted-foreground">
          用自然语言表达需求，agent 会根据对话自主调用你启用的 skill 来完成任务。
          skill 可编辑、导入、订阅。
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/chat" className={buttonVariants()}>
            <MessageSquare className="h-4 w-4" />
            进入聊天
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/skills" className={buttonVariants({ variant: "outline" })}>
            <Blocks className="h-4 w-4" />
            管理 Skill
          </Link>
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">后端连接</CardTitle>
              <CardDescription>{API_BASE}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <span
                  className={`inline-block h-2.5 w-2.5 rounded-full ${
                    health.ok ? "bg-success" : "bg-destructive"
                  }`}
                />
                <span className="text-sm text-muted-foreground">
                  {health.ok ? "已连接" : "未连接"} · {health.detail}
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">工作原理</CardTitle>
              <CardDescription>渐进式披露 + tool calling</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              平时只把 skill 的名称与描述提供给模型；当模型判断某 skill
              相关时，才展开它的完整指令并执行。
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
