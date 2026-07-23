"use client";

import { MessageSquare, Sparkles, Blocks } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/chat", label: "聊天", icon: MessageSquare },
  { href: "/skills", label: "Skill 管理", icon: Blocks },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-border bg-card/40">
      {/* 品牌 */}
      <Link
        href="/"
        className="flex items-center gap-2.5 px-5 py-5 text-foreground"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
          <Sparkles className="h-4 w-4" />
        </span>
        <span className="text-[15px] font-semibold tracking-tight">
          Skills 中心
        </span>
      </Link>

      {/* 导航 */}
      <nav className="flex flex-1 flex-col gap-1 px-3 py-2">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* 底部 */}
      <div className="flex items-center justify-between border-t border-border px-4 py-3">
        <span className="text-xs text-muted-foreground">v0.1 · MVP</span>
        <ThemeToggle />
      </div>
    </aside>
  );
}
