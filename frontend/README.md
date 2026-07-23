# Frontend — Skills Hub (Next.js)

Next.js（App Router）+ TypeScript。

## 快速开始

```bash
cd frontend
npm install
cp .env.local.example .env.local   # 设置 NEXT_PUBLIC_API_BASE 指向后端
npm run dev
```

打开 http://localhost:3000 —— 首页会显示后端 `/api/health` 的连接状态。

> 需要后端在 http://localhost:8000 运行（见 `../backend/README.md`）才能看到「绿灯」。

## 页面

- `app/page.tsx` — 首页，展示后端连接状态
- `app/chat/page.tsx` — 聊天窗口占位（M1 接入 Qwen 流式对话）

## 脚本

- `npm run dev` — 开发服务器
- `npm run build` — 生产构建
- `npm run start` — 运行生产构建
