import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function getBackendHealth(): Promise<{ ok: boolean; detail: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
    if (!res.ok) return { ok: false, detail: `HTTP ${res.status}` };
    const data = await res.json();
    return { ok: data.status === "ok", detail: JSON.stringify(data) };
  } catch (e) {
    return { ok: false, detail: "无法连接后端（后端是否已启动？）" };
  }
}

export default async function Home() {
  const health = await getBackendHealth();

  return (
    <main
      style={{
        maxWidth: 720,
        margin: "0 auto",
        padding: "64px 24px",
      }}
    >
      <h1 style={{ fontSize: 32, marginBottom: 8 }}>Skills 中心</h1>
      <p style={{ color: "var(--muted)", marginTop: 0 }}>
        Agent 化的 AI 聊天窗口 —— agent 根据对话自主调用 skill。你可以编辑、导入、订阅
        skill。
      </p>

      <div
        style={{
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: 20,
          marginTop: 24,
        }}
      >
        <div style={{ fontSize: 14, color: "var(--muted)", marginBottom: 6 }}>
          后端连接状态
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              display: "inline-block",
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: health.ok ? "var(--ok)" : "var(--err)",
            }}
          />
          <code style={{ fontSize: 13 }}>{health.detail}</code>
        </div>
      </div>

      <p style={{ marginTop: 32, display: "flex", gap: 20 }}>
        <Link href="/chat">进入聊天 →</Link>
        <Link href="/skills">管理 Skill →</Link>
      </p>
    </main>
  );
}
