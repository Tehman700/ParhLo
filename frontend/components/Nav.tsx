"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useConfig } from "@/lib/hooks";

// Add a page: create app/<route>/page.tsx, then add it here.
const LINKS: { href: string; label: string; feature?: "rag" | "ml" | "vision" }[] = [
  { href: "/", label: "Workspace" },
];

export function Nav() {
  const pathname = usePathname();
  const { data: config, error } = useConfig();

  const status = error
    ? { text: "Backend offline", color: "bg-danger" }
    : !config
      ? { text: "Connecting…", color: "bg-ink-48" }
      : config.llm.configured
        ? { text: config.llm.model, color: "bg-success" }
        : { text: "No LLM key", color: "bg-[#d29922]" };

  return (
    <header className="sticky top-0 z-30">
      <nav className="bg-black text-white">
        <div className="mx-auto flex h-11 max-w-[1440px] items-center gap-6 overflow-x-auto px-4 text-[12px] tracking-[-0.12px] sm:px-6">
          <Link href="/" className="shrink-0 text-[14px] font-semibold tracking-tight">
            NaSCon AI
          </Link>
          <div className="flex flex-1 items-center gap-5">
            {LINKS.map((l) => {
              const disabled = l.feature && config && !config.features[l.feature];
              const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`shrink-0 transition-opacity ${active ? "opacity-100" : "opacity-70 hover:opacity-100"} ${disabled ? "line-through opacity-40" : ""}`}
                >
                  {l.label}
                </Link>
              );
            })}
          </div>
          <span className="flex shrink-0 items-center gap-2 text-white/80" title={error ?? config?.llm.base_url}>
            <span className={`h-2 w-2 rounded-full ${status.color}`} />
            {status.text}
          </span>
        </div>
      </nav>
    </header>
  );
}
