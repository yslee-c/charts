import type { Metadata } from "next";

import { Sidebar } from "@/components/sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Skills 中心",
  description: "Agent 化的 AI 聊天窗口 —— 可编辑、导入、订阅 skill",
};

// 首帧就确定主题，避免闪烁；默认深色。
const themeScript = `
(function(){try{var t=localStorage.getItem('theme');
if(t==='light'){document.documentElement.classList.remove('dark');}
else{document.documentElement.classList.add('dark');}}catch(e){
document.documentElement.classList.add('dark');}})();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="h-screen overflow-hidden">
        <div className="flex h-full">
          <Sidebar />
          <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
