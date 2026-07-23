"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

/** 深/浅色切换。首帧主题由 layout 中的内联脚本决定，避免 FOUC。 */
export function ThemeToggle() {
  const [dark, setDark] = useState(true);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      /* ignore */
    }
  }

  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label="切换主题">
      {dark ? <Sun /> : <Moon />}
    </Button>
  );
}
