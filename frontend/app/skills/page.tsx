"use client";

import { Plus, Trash2, Upload } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

interface Skill {
  id: number;
  name: string;
  description: string;
  kind: string;
  source: string;
  is_active: boolean;
  version: number;
}

const SAMPLE = `---
name: my-skill
description: 一句话说明「什么时候」该用这个 skill（agent 据此决定是否调用）
---

# 指令正文
当被调用时，agent 应遵循的步骤……`;

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function load() {
    try {
      const res = await fetch(`${API_BASE}/api/skills`, { cache: "no-store" });
      setSkills(await res.json());
    } catch {
      setMsg({ ok: false, text: "无法连接后端" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function toggle(s: Skill) {
    setSkills((prev) =>
      prev.map((x) => (x.id === s.id ? { ...x, is_active: !x.is_active } : x))
    );
    await fetch(`${API_BASE}/api/skills/${s.id}/active`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: !s.is_active }),
    });
    load();
  }

  async function remove(s: Skill) {
    if (!confirm(`删除 skill「${s.name}」？`)) return;
    await fetch(`${API_BASE}/api/skills/${s.id}`, { method: "DELETE" });
    load();
  }

  async function doImport() {
    setMsg(null);
    const res = await fetch(`${API_BASE}/api/skills/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: draft }),
    });
    if (res.ok) {
      const s = await res.json();
      setMsg({ ok: true, text: `已导入：${s.name}（v${s.version}）` });
      setDraft("");
      load();
    } else {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      setMsg({ ok: false, text: err.detail });
    }
  }

  const activeCount = skills.filter((s) => s.is_active).length;

  return (
    <div className="h-full overflow-y-auto">
      <header className="flex h-14 items-center border-b border-border px-6">
        <h1 className="text-sm font-medium">Skill 管理</h1>
      </header>

      <div className="mx-auto max-w-3xl px-6 py-8">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Skill 库</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              启用的 skill 会作为工具提供给 agent；对话时由 agent 自主决定是否调用。
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline">{activeCount} 个已启用</Badge>
            <Link href="/skills/new" className={buttonVariants({ size: "sm" })}>
              <Plus className="h-4 w-4" />
              新建 skill
            </Link>
          </div>
        </div>

        {/* 列表 */}
        <div className="mt-6 flex flex-col gap-2.5">
          {loading &&
            [0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-[68px] w-full rounded-lg" />
            ))}
          {!loading && skills.length === 0 && (
            <Card className="p-8 text-center text-sm text-muted-foreground">
              还没有 skill，用下面的表单导入一个。
            </Card>
          )}
          {skills.map((s) => (
            <Card
              key={s.id}
              className="flex items-center gap-4 px-4 py-3.5 transition-colors hover:border-border/80"
            >
              <Switch
                checked={s.is_active}
                onCheckedChange={() => toggle(s)}
                aria-label={`启用 ${s.name}`}
              />
              <Link href={`/skills/${s.id}`} className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium hover:underline">{s.name}</span>
                  <Badge variant={s.kind === "http" ? "secondary" : "outline"}>
                    {s.kind}
                  </Badge>
                  {s.source === "builtin" && (
                    <Badge variant="outline">内置</Badge>
                  )}
                  <span className="text-xs text-muted-foreground">v{s.version}</span>
                </div>
                <p className="mt-0.5 truncate text-sm text-muted-foreground">
                  {s.description}
                </p>
              </Link>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => remove(s)}
                aria-label="删除"
                className="text-muted-foreground hover:text-destructive"
              >
                <Trash2 />
              </Button>
            </Card>
          ))}
        </div>

        {/* 导入 */}
        <div className="mt-10">
          <h3 className="text-lg font-semibold">导入 skill</h3>
          <p className="mb-3 mt-1 text-sm text-muted-foreground">
            粘贴一段符合 Claude Skills 规范的 SKILL.md（同名会更新并升版本）。
          </p>
          <Textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={SAMPLE}
            rows={10}
            className="font-mono text-xs"
          />
          <div className="mt-3 flex items-center gap-3">
            <Button onClick={doImport} disabled={!draft.trim()} className="gap-2">
              <Upload className="h-4 w-4" />
              导入
            </Button>
            {msg && (
              <span
                className={
                  msg.ok ? "text-sm text-success" : "text-sm text-destructive"
                }
              >
                {msg.text}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
