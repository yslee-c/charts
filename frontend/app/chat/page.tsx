import Link from "next/link";

export default function ChatPage() {
  return (
    <main
      style={{
        maxWidth: 720,
        margin: "0 auto",
        padding: "64px 24px",
      }}
    >
      <p style={{ marginBottom: 24 }}>
        <Link href="/">← 返回</Link>
      </p>
      <h1 style={{ fontSize: 28 }}>聊天窗口</h1>
      <p style={{ color: "var(--muted)" }}>
        占位页面。M1 将在此接入 Qwen 流式对话，M2 起 agent 可自主调用 skill。
      </p>

      <div
        style={{
          background: "var(--panel)",
          border: "1px dashed var(--border)",
          borderRadius: 12,
          padding: 24,
          marginTop: 24,
          color: "var(--muted)",
          textAlign: "center",
        }}
      >
        对话界面将在这里构建
      </div>
    </main>
  );
}
