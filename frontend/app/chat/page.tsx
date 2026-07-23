"use client";

import { ArrowUp, ChevronDown, Sparkles, Square, Wrench } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ConversationList } from "@/components/conversation-list";
import { CopyButton } from "@/components/copy-button";
import { Markdown } from "@/components/markdown";
import { ToolOutput } from "@/components/tool-output";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Role = "user" | "assistant" | "activity";
interface Message {
  role: Role;
  content: string;
  skill?: string;
  output?: string; // 工具调用的原始输出（活动消息，仅本次会话可展开）
}

const SUGGESTIONS = [
  "把「今天天气真好」改写成文言文",
  "用 emoji 总结一下什么是 REST API",
  "你能帮我做什么？",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [cid, setCid] = useState<number | null>(null);
  const [refreshSignal, setRefreshSignal] = useState(0);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  function scrollToBottom() {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
    });
  }

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [input]);

  function newConversation() {
    if (streaming) return;
    setCid(null);
    setMessages([]);
    setError(null);
  }

  async function selectConversation(id: number) {
    if (streaming) return;
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/conversations/${id}`, {
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const detail = await res.json();
      setMessages(
        detail.messages.map((m: { role: Role; content: string }) => ({
          role: m.role,
          content: m.content,
        }))
      );
      setCid(id);
      scrollToBottom();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function stop() {
    abortRef.current?.abort();
  }

  function toggleExpand(i: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  async function send(text: string) {
    text = text.trim();
    if (!text || streaming) return;

    setError(null);
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setStreaming(true);
    scrollToBottom();

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: cid, message: text }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        const detail = await res.text().catch(() => "");
        throw new Error(detail || `HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

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
              conversation?: { id: number; title: string; is_new: boolean };
              tool_call?: { skill: string };
              tool_result?: { skill: string; ok: boolean; output?: string };
            };
            if (obj.conversation) {
              setCid(obj.conversation.id);
              if (obj.conversation.is_new) setRefreshSignal((n) => n + 1);
            } else if (obj.error) {
              setError(obj.error);
            } else if (obj.tool_call) {
              const skill = obj.tool_call.skill;
              setMessages((prev) => [
                ...prev,
                { role: "activity", content: `调用 skill：${skill}`, skill },
              ]);
              scrollToBottom();
            } else if (obj.tool_result) {
              const tr = obj.tool_result;
              setMessages((prev) => {
                const next = [...prev];
                for (let i = next.length - 1; i >= 0; i--) {
                  if (next[i].role === "activity" && next[i].skill === tr.skill) {
                    next[i] = {
                      ...next[i],
                      content: next[i].content + (tr.ok ? " · 完成" : " · 失败"),
                      output: tr.output,
                    };
                    break;
                  }
                }
                return next;
              });
            } else if (obj.delta) {
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
            /* 忽略无法解析的分片 */
          }
        }
      }
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
      setRefreshSignal((n) => n + 1); // 刷新会话列表（标题/排序）
      scrollToBottom();
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  const empty = messages.length === 0;

  return (
    <div className="flex h-full">
      <ConversationList
        currentId={cid}
        onSelect={selectConversation}
        onNew={newConversation}
        refreshSignal={refreshSignal}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center border-b border-border px-6">
          <h1 className="text-sm font-medium">聊天</h1>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-6 py-6">
            {empty ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/15 text-primary">
                  <Sparkles className="h-6 w-6" />
                </span>
                <h2 className="mt-4 text-xl font-semibold">有什么可以帮你？</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  agent 会根据你的需求，自主决定是否调用已启用的 skill。
                </p>
                <div className="mt-6 flex flex-col gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="rounded-lg border border-border bg-card px-4 py-2.5 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                {messages.map((m, i) =>
                  m.role === "activity" ? (
                    <div key={i} className="flex flex-col items-center gap-1.5">
                      <button
                        onClick={() => m.output && toggleExpand(i)}
                        disabled={!m.output}
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground animate-fade-in",
                          m.output && "hover:text-foreground"
                        )}
                      >
                        <Wrench className="h-3 w-3" />
                        {m.content}
                        {m.output && (
                          <ChevronDown
                            className={cn(
                              "h-3 w-3 transition-transform",
                              expanded.has(i) && "rotate-180"
                            )}
                          />
                        )}
                      </button>
                      {m.output && expanded.has(i) && (
                        <div className="w-full max-w-xl">
                          <ToolOutput output={m.output} />
                        </div>
                      )}
                    </div>
                  ) : m.role === "user" ? (
                    <div key={i} className="flex animate-fade-in justify-end">
                      <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground">
                        {m.content}
                      </div>
                    </div>
                  ) : (
                    <div
                      key={i}
                      className="group flex animate-fade-in flex-col items-start"
                    >
                      <div className="max-w-[85%] break-words rounded-2xl border border-border bg-card px-4 py-1 text-card-foreground">
                        <Markdown content={m.content} />
                      </div>
                      {m.content && (
                        <div className="mt-1 pl-1 opacity-0 transition-opacity group-hover:opacity-100">
                          <CopyButton text={m.content} label="复制" />
                        </div>
                      )}
                    </div>
                  )
                )}
                {streaming &&
                  messages[messages.length - 1]?.role !== "assistant" && (
                    <div className="flex justify-start">
                      <div className="flex items-center gap-1 rounded-2xl border border-border bg-card px-4 py-3">
                        {[0, 1, 2].map((i) => (
                          <span
                            key={i}
                            className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-pulse-soft"
                            style={{ animationDelay: `${i * 0.2}s` }}
                          />
                        ))}
                      </div>
                    </div>
                  )}
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-border px-6 py-4">
          <div className="mx-auto max-w-3xl">
            {error && (
              <div className="mb-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                出错：{error}
              </div>
            )}
            <div className="flex items-end gap-2 rounded-2xl border border-input bg-card p-2 shadow-sm focus-within:ring-2 focus-within:ring-ring">
              <textarea
                ref={taRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                rows={1}
                placeholder="输入消息，Enter 发送，Shift+Enter 换行"
                className="max-h-[200px] flex-1 resize-none bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-muted-foreground"
              />
              {streaming ? (
                <button
                  onClick={stop}
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border text-foreground transition-colors hover:bg-accent"
                  aria-label="停止生成"
                >
                  <Square className="h-3.5 w-3.5 fill-current" />
                </button>
              ) : (
                <button
                  onClick={() => send(input)}
                  disabled={!input.trim()}
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-opacity disabled:opacity-40"
                  aria-label="发送"
                >
                  <ArrowUp className="h-4 w-4" />
                </button>
              )}
            </div>
            <p className="mt-2 text-center text-xs text-muted-foreground">
              由通义千问驱动 · agent 可自主调用 skill
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
