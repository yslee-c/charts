"use client";

import { Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

interface Conversation {
  id: number;
  title: string;
  updated_at: string;
}

export function ConversationList({
  currentId,
  onSelect,
  onNew,
  refreshSignal,
}: {
  currentId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
  refreshSignal: number;
}) {
  const [items, setItems] = useState<Conversation[]>([]);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/conversations`, {
        cache: "no-store",
      });
      setItems(await res.json());
    } catch {
      /* 后端未启动时忽略 */
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshSignal]);

  async function remove(e: React.MouseEvent, id: number) {
    e.stopPropagation();
    if (!confirm("删除该会话？")) return;
    await fetch(`${API_BASE}/api/conversations/${id}`, { method: "DELETE" });
    if (id === currentId) onNew();
    load();
  }

  return (
    <div className="flex h-full w-64 shrink-0 flex-col border-r border-border bg-card/20">
      <div className="p-3">
        <button
          onClick={onNew}
          className="flex w-full items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium transition-colors hover:bg-accent"
        >
          <Plus className="h-4 w-4" />
          新对话
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {items.length === 0 ? (
          <p className="px-2 py-6 text-center text-xs text-muted-foreground">
            还没有会话
          </p>
        ) : (
          <div className="flex flex-col gap-0.5">
            {items.map((c) => (
              <button
                key={c.id}
                onClick={() => onSelect(c.id)}
                className={cn(
                  "group flex items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm transition-colors",
                  c.id === currentId
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                )}
              >
                <span className="min-w-0 flex-1 truncate">{c.title}</span>
                <span
                  role="button"
                  tabIndex={-1}
                  onClick={(e) => remove(e, c.id)}
                  className="shrink-0 rounded p-0.5 opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
                  aria-label="删除会话"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
