"use client";

import { ArrowLeft, Save } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Markdown } from "@/components/markdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

interface Skill {
  id: number;
  name: string;
  description: string;
  kind: string;
  source: string;
  version: number;
  skill_md: string;
}

export default function SkillDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [skill, setSkill] = useState<Skill | null>(null);
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [meta, src] = await Promise.all([
        fetch(`${API_BASE}/api/skills/${id}`, { cache: "no-store" }).then((r) =>
          r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))
        ),
        fetch(`${API_BASE}/api/skills/${id}/source`, { cache: "no-store" }).then(
          (r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
        ),
      ]);
      setSkill(meta);
      setSource(src.content);
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : String(e) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function save() {
    setSaving(true);
    setMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/skills/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: source }),
      });
      if (res.ok) {
        const updated = await res.json();
        setSkill(updated);
        setMsg({ ok: true, text: `已保存（v${updated.version}）` });
      } else {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        setMsg({ ok: false, text: err.detail });
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <header className="flex h-14 items-center gap-3 border-b border-border px-6">
        <Link
          href="/skills"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Skill
        </Link>
      </header>

      <div className="mx-auto max-w-5xl px-6 py-8">
        {loading ? (
          <div className="flex flex-col gap-4">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-80 w-full" />
          </div>
        ) : (
          skill && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-semibold tracking-tight">{skill.name}</h1>
                <Badge variant={skill.kind === "http" ? "secondary" : "outline"}>
                  {skill.kind}
                </Badge>
                <Badge variant="outline">{skill.source}</Badge>
                <Badge variant="outline">v{skill.version}</Badge>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{skill.description}</p>

              <div className="mt-6 grid gap-5 lg:grid-cols-2">
                {/* 编辑器 */}
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-sm font-medium">SKILL.md</label>
                    <span className="text-xs text-muted-foreground">
                      Claude Skills 规范
                    </span>
                  </div>
                  <Textarea
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    rows={22}
                    className="font-mono text-xs leading-relaxed"
                  />
                  <div className="mt-3 flex items-center gap-3">
                    <Button onClick={save} disabled={saving || !source.trim()} className="gap-2">
                      <Save className="h-4 w-4" />
                      {saving ? "保存中…" : "保存"}
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

                {/* 正文预览 */}
                <div>
                  <div className="mb-2 text-sm font-medium">正文预览</div>
                  <Card>
                    <CardHeader className="pb-0">
                      <CardTitle className="text-sm text-muted-foreground">
                        当前生效的指令（保存后更新）
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-3">
                      {skill.skill_md ? (
                        <Markdown content={skill.skill_md} />
                      ) : (
                        <p className="text-sm text-muted-foreground">（无正文）</p>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </div>
            </>
          )
        )}
      </div>
    </div>
  );
}
