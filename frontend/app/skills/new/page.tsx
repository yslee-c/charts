"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Kind = "instruction" | "http";

export default function NewSkillPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [kind, setKind] = useState<Kind>("instruction");
  const [body, setBody] = useState("");
  const [method, setMethod] = useState("GET");
  const [url, setUrl] = useState("");
  const [paramsText, setParamsText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);

    const payload: Record<string, unknown> = {
      name: name.trim(),
      description: description.trim(),
      kind,
      skill_md: body,
    };

    if (kind === "http") {
      if (!url.trim()) {
        setError("HTTP 型需要填写 URL");
        return;
      }
      payload.http_action = { method, url: url.trim() };
      if (paramsText.trim()) {
        try {
          payload.parameters_schema = JSON.parse(paramsText);
        } catch {
          setError("参数 JSON Schema 格式不正确");
          return;
        }
      }
    }

    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/skills`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const s = await res.json();
        router.push(`/skills/${s.id}`);
      } else {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        setError(
          Array.isArray(err.detail)
            ? err.detail.map((d: { msg: string }) => d.msg).join("；")
            : err.detail
        );
      }
    } finally {
      setSaving(false);
    }
  }

  const canSubmit = name.trim() && description.trim() && !saving;

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

      <div className="mx-auto max-w-2xl px-6 py-8">
        <h1 className="text-2xl font-semibold tracking-tight">新建 Skill</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          填写字段即可创建；也可以在 Skill 管理页粘贴 SKILL.md 导入。
        </p>

        <div className="mt-6 space-y-5">
          <Field label="名称" hint="小写字母/数字/连字符，如 weather-lookup">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-skill"
            />
          </Field>

          <Field label="描述" hint="决定 agent 是否选用它 —— 说明「什么时候」该用">
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="当用户想…… 时使用"
            />
          </Field>

          <Field label="类型">
            <div className="flex gap-2">
              {(["instruction", "http"] as Kind[]).map((k) => (
                <button
                  key={k}
                  onClick={() => setKind(k)}
                  className={cn(
                    "rounded-md border px-3 py-1.5 text-sm transition-colors",
                    kind === k
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border text-muted-foreground hover:text-foreground"
                  )}
                >
                  {k === "instruction" ? "指令型" : "HTTP 型"}
                </button>
              ))}
            </div>
          </Field>

          {kind === "http" && (
            <div className="space-y-5 rounded-lg border border-border bg-card/40 p-4">
              <Field label="请求">
                <div className="flex gap-2">
                  <select
                    value={method}
                    onChange={(e) => setMethod(e.target.value)}
                    className="h-9 rounded-md border border-input bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {["GET", "POST", "PUT", "DELETE"].map((m) => (
                      <option key={m}>{m}</option>
                    ))}
                  </select>
                  <Input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://api.example.com/{param}"
                    className="flex-1"
                  />
                </div>
              </Field>
              <Field
                label="参数 JSON Schema（可选）"
                hint="供模型填参；URL 里的 {占位符} 会被同名参数替换"
              >
                <Textarea
                  value={paramsText}
                  onChange={(e) => setParamsText(e.target.value)}
                  rows={6}
                  placeholder={
                    '{\n  "type": "object",\n  "properties": { "q": { "type": "string" } },\n  "required": ["q"]\n}'
                  }
                  className="font-mono text-xs"
                />
              </Field>
            </div>
          )}

          <Field label="指令正文（SKILL.md 正文）" hint="被调用时 agent 遵循的步骤">
            <Textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={8}
              placeholder={"# 指令\n当被调用时，请……"}
              className="font-mono text-xs"
            />
          </Field>

          <div className="flex items-center gap-3">
            <Button onClick={submit} disabled={!canSubmit}>
              {saving ? "创建中…" : "创建"}
            </Button>
            {error && <span className="text-sm text-destructive">{error}</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline gap-2">
        <label className="text-sm font-medium">{label}</label>
        {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
      </div>
      {children}
    </div>
  );
}
