import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import { CopyButton } from "@/components/copy-button";

/** 从 react 子节点里抽出纯文本（用于代码块复制）。 */
function toText(node: React.ReactNode): string {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(toText).join("");
  if (typeof node === "object" && "props" in (node as any)) {
    return toText((node as any).props?.children);
  }
  return "";
}

export function Markdown({ content }: { content: string }) {
  return (
    <div className="markdown-body text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
        components={{
          a: ({ children, ...props }) => (
            <a
              {...props}
              target="_blank"
              rel="noreferrer"
              className="text-primary underline underline-offset-2"
            >
              {children}
            </a>
          ),
          pre: ({ children }) => {
            const code = toText(children);
            return (
              <div className="group/code relative my-3">
                <div className="absolute right-2 top-2 opacity-0 transition-opacity group-hover/code:opacity-100">
                  <CopyButton
                    text={code}
                    className="bg-card/80 backdrop-blur"
                  />
                </div>
                <pre className="overflow-x-auto rounded-lg border border-border bg-card p-3.5 text-[13px]">
                  {children}
                </pre>
              </div>
            );
          },
          code: ({ className, children, ...props }) => {
            const isBlock =
              /language-/.test(className || "") || toText(children).includes("\n");
            if (isBlock) {
              return (
                <code className={className} {...props}>
                  {children}
                </code>
              );
            }
            return (
              <code
                className="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.85em]"
                {...props}
              >
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
