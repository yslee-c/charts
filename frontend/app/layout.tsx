import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Skills 中心",
  description: "Agent 化的 AI 聊天窗口 —— 可编辑、导入、订阅 skill",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
