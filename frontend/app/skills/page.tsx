"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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
  const [importMsg, setImportMsg] = useState<{ ok: boolean; text: string } | null>(
    null
  );

  async function load() {
    try {
      const res = await fetch(`${API_BASE}/api/skills`, { cache: "no-store" });
      setSkills(await res.json());
    } catch {
      setImportMsg({ ok: false, text: "无法连接后端" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function toggle(s: Skill) {
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
    setImportMsg(null);
    const res = await fetch(`${API_BASE}/api/skills/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: draft }),
    });
    if (res.ok) {
      const s = await res.json();
      setImportMsg({ ok: true, text: `已导入：${s.name}（v${s.version}）` });
      setDraft("");
      load();
    } else {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      setImportMsg({ ok: false, text: err.detail });
    }
  }

  return (
    <main style={{ maxWidth: 820, margin: "0 auto", padding: "32px 24px" }}>
      <div style={{ marginBottom: 12 }}>
        <Link href="/">← 返回</Link>
        {"　"}
        <Link href="/chat">进入聊天 →</Link>
      </div>
      <h1 style={{ fontSize: 24 }}>Skill 管理</h1>
      <p style={{ color: "var(--muted)", marginTop: 0 }}>
        启用的 skill 会作为工具提供给 agent；对话时由 agent 自主决定是否调用。
      </p>

      {/* 列表 */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 20 }}>
        {loading && <div style={{ color: "var(--muted)" }}>加载中…</div>}
        {!loading && skills.length === 0 && (
          <div style={{ color: "var(--muted)" }}>还没有 skill，用下面的表单导入一个。</div>
        )}
        {skills.map((s) => (
          <div
            key={s.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              background: "var(--panel)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: "12px 16px",
            }}
          >
            <label style={{ display: "flex", alignItems: "center", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={s.is_active}
                onChange={() => toggle(s)}
                style={{ width: 18, height: 18 }}
              />
            </label>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <strong>{s.name}</strong>
                <Badge>{s.kind}</Badge>
                <Badge>{s.source}</Badge>
                <span style={{ color: "var(--muted)", fontSize: 12 }}>v{s.version}</span>
              </div>
              <div style={{ color: "var(--muted)", fontSize: 13, marginTop: 2 }}>
                {s.description}
              </div>
            </div>
            <button onClick={() => remove(s)} style={ghostBtn}>
              删除
            </button>
          </div>
        ))}
      </div>

      {/* 导入 */}
      <h2 style={{ fontSize: 18, marginTop: 32 }}>导入 skill（Claude Skills 规范）</h2>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder={SAMPLE}
        rows={10}
        style={{
          width: "100%",
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
          fontSize: 13,
          padding: 12,
          borderRadius: 10,
          border: "1px solid var(--border)",
          background: "var(--panel)",
          color: "var(--text)",
          resize: "vertical",
        }}
      />
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8 }}>
        <button onClick={doImport} disabled={!draft.trim()} style={primaryBtn}>
          导入
        </button>
        {importMsg && (
          <span style={{ color: importMsg.ok ? "var(--ok)" : "var(--err)", fontSize: 13 }}>
            {importMsg.text}
          </span>
        )}
      </div>
    </main>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        fontSize: 11,
        color: "var(--muted)",
        border: "1px solid var(--border)",
        borderRadius: 6,
        padding: "1px 6px",
      }}
    >
      {children}
    </span>
  );
}

const primaryBtn: React.CSSProperties = {
  padding: "8px 18px",
  borderRadius: 8,
  border: "none",
  background: "var(--accent)",
  color: "#fff",
  fontSize: 14,
  cursor: "pointer",
};

const ghostBtn: React.CSSProperties = {
  padding: "6px 12px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "transparent",
  color: "var(--muted)",
  fontSize: 13,
  cursor: "pointer",
};
