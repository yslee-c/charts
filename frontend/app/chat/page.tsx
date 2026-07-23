"use client";

import Link from "next/link";
import { useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Role = "user" | "assistant" | "activity";
interface Message {
  role: Role;
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  function scrollToBottom() {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
    });
  }

  async function send() {
    const text = input.trim();
    if (!text || streaming) return;

    setError(null);
    setInput("");

    // 发给后端的历史：只保留 user/assistant 文本消息（剔除工具活动行）
    const payload = messages
      .filter((m) => m.role !== "activity" && m.content)
      .map((m) => ({ role: m.role, content: m.content }));
    payload.push({ role: "user", content: text });

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setStreaming(true);
    scrollToBottom();

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: payload }),
      });

      if (!res.ok || !res.body) {
        const detail = await res.text().catch(() => "");
        throw new Error(detail || `HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // 逐块读取 SSE，事件以空行分隔
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const evt of events) {
          const line = evt.trim();
          if (!line.startsWith("data:")) continue;
          const data = line.slice(5).trim();
          if (data === "[DONE]") continue;

          try {
            const obj = JSON.parse(data) as {
              delta?: string;
              error?: string;
              tool_call?: { skill: string };
              tool_result?: { skill: string; ok: boolean };
            };
            if (obj.error) {
              setError(obj.error);
            } else if (obj.tool_call) {
              // 工具调用：新增一行活动提示（后续 delta 会开一个新的助手气泡）
              setMessages((prev) => [
                ...prev,
                { role: "activity", content: `🛠 调用 skill：${obj.tool_call!.skill}` },
              ]);
              scrollToBottom();
            } else if (obj.tool_result) {
              // 给最近一条匹配的活动行补上结果标记
              setMessages((prev) => {
                const next = [...prev];
                for (let i = next.length - 1; i >= 0; i--) {
                  if (
                    next[i].role === "activity" &&
                    next[i].content.includes(obj.tool_result!.skill)
                  ) {
                    next[i] = {
                      ...next[i],
                      content:
                        next[i].content + (obj.tool_result!.ok ? " ✅" : " ❌"),
                    };
                    break;
                  }
                }
                return next;
              });
            } else if (obj.delta) {
              // 追加到最后一个助手气泡；若最后一条不是助手气泡则新开一个
              const piece = obj.delta;
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last && last.role === "assistant") {
                  next[next.length - 1] = { ...last, content: last.content + piece };
                } else {
                  next.push({ role: "assistant", content: piece });
                }
                return next;
              });
              scrollToBottom();
            }
          } catch {
            // 忽略无法解析的分片
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setStreaming(false);
      scrollToBottom();
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <main
      style={{
        maxWidth: 760,
        margin: "0 auto",
        padding: "24px",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ marginBottom: 12 }}>
        <Link href="/">← 返回</Link>
      </div>
      <h1 style={{ fontSize: 22, margin: "0 0 12px" }}>聊天窗口</h1>

      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: "auto",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: 16,
          background: "var(--panel)",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {messages.length === 0 && (
          <div style={{ color: "var(--muted)", textAlign: "center", marginTop: 40 }}>
            开始对话吧 —— agent 会按需调用已启用的 skill。
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "activity" ? (
            <div
              key={i}
              style={{
                alignSelf: "center",
                fontSize: 12,
                color: "var(--muted)",
                background: "var(--bg)",
                border: "1px solid var(--border)",
                borderRadius: 999,
                padding: "3px 12px",
              }}
            >
              {m.content}
            </div>
          ) : (
            <div
              key={i}
              style={{
                alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                maxWidth: "82%",
                padding: "10px 14px",
                borderRadius: 12,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                background: m.role === "user" ? "var(--accent)" : "var(--bg)",
                color: m.role === "user" ? "#fff" : "var(--text)",
                border: m.role === "user" ? "none" : "1px solid var(--border)",
              }}
            >
              {m.content}
            </div>
          )
        )}
        {streaming &&
          messages[messages.length - 1]?.role !== "assistant" && (
            <div style={{ alignSelf: "flex-start", color: "var(--muted)", fontSize: 13 }}>
              思考中…
            </div>
          )}
      </div>

      {error && (
        <div style={{ color: "var(--err)", fontSize: 13, marginTop: 8 }}>
          出错：{error}
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="输入消息，Enter 发送，Shift+Enter 换行"
          rows={2}
          style={{
            flex: 1,
            resize: "none",
            padding: "10px 12px",
            borderRadius: 10,
            border: "1px solid var(--border)",
            background: "var(--panel)",
            color: "var(--text)",
            fontFamily: "inherit",
            fontSize: 14,
          }}
        />
        <button
          onClick={send}
          disabled={streaming || !input.trim()}
          style={{
            padding: "0 20px",
            borderRadius: 10,
            border: "none",
            background: "var(--accent)",
            color: "#fff",
            fontSize: 14,
            cursor: streaming || !input.trim() ? "not-allowed" : "pointer",
            opacity: streaming || !input.trim() ? 0.5 : 1,
          }}
        >
          {streaming ? "…" : "发送"}
        </button>
      </div>
    </main>
  );
}
