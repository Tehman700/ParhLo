"use client";

import type { ReactNode } from "react";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="flex flex-col gap-4 pb-8 pt-10 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="display text-[34px] sm:text-[40px]">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-[17px] text-ink-48">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ title, actions, children, className = "" }: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-[17px] font-semibold">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-ink-48 caption" role="status">
      <span className="flex gap-1">
        <span className="dot h-1.5 w-1.5 rounded-full bg-current" />
        <span className="dot h-1.5 w-1.5 rounded-full bg-current" />
        <span className="dot h-1.5 w-1.5 rounded-full bg-current" />
      </span>
      {label}
    </span>
  );
}

export function ErrorNote({ error, onDismiss }: { error: string | null | undefined; onDismiss?: () => void }) {
  if (!error) return null;
  return (
    <div className="flex items-start justify-between gap-3 rounded-[11px] bg-[#fff1f0] px-4 py-3 caption text-danger" role="alert">
      <span className="break-words">{error}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="shrink-0 text-ink-48 hover:text-ink" aria-label="Dismiss">
          ✕
        </button>
      )}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="rounded-[11px] bg-parchment px-4 py-8 text-center caption text-ink-48">{children}</div>;
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "blue" | "green" | "red" }) {
  const tones = {
    neutral: "bg-parchment text-ink-80",
    blue: "bg-[#e8f1fb] text-primary",
    green: "bg-[#e9f6ec] text-success",
    red: "bg-[#fff1f0] text-danger",
  };
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[12px] font-semibold ${tones[tone]}`}>{children}</span>;
}

export function Segmented<T extends string>({ value, options, onChange }: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex rounded-full bg-parchment p-1" role="tablist">
      {options.map((o) => (
        <button key={o.value} role="tab" aria-selected={value === o.value} data-active={value === o.value}
          className="chip" onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-[11px] bg-parchment px-4 py-3">
      <div className="label">{label}</div>
      <div className="mt-1 text-[24px] font-semibold tracking-tight">{value}</div>
    </div>
  );
}

export function JsonView({ data, dark = false, maxHeight = 420 }: { data: unknown; dark?: boolean; maxHeight?: number }) {
  return (
    <pre
      className={`mono overflow-auto rounded-[11px] p-4 leading-relaxed ${dark ? "bg-tile-3 text-muted-on-dark" : "bg-parchment text-ink-80"}`}
      style={{ maxHeight }}
    >
      {typeof data === "string" ? data : JSON.stringify(data, null, 2)}
    </pre>
  );
}

/** Generic table for arrays of records (CSV previews, SQL results, predictions...). */
export function DataTable({ rows, maxRows = 50 }: { rows: Record<string, unknown>[]; maxRows?: number }) {
  if (!rows.length) return <Empty>No rows</Empty>;
  const cols = Array.from(new Set(rows.flatMap((r) => Object.keys(r))));
  return (
    <div className="overflow-auto rounded-[11px] border border-hairline">
      <table className="w-full text-left caption">
        <thead className="bg-parchment">
          <tr>
            {cols.map((c) => (
              <th key={c} className="whitespace-nowrap px-3 py-2 font-semibold">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, maxRows).map((r, i) => (
            <tr key={i} className="border-t border-divider">
              {cols.map((c) => (
                <td key={c} className="whitespace-nowrap px-3 py-1.5 text-ink-80">{formatCell(r[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > maxRows && <div className="px-3 py-2 caption text-ink-48">Showing {maxRows} of {rows.length} rows</div>}
    </div>
  );
}

function formatCell(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(4).replace(/0+$/, "");
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 ** 2).toFixed(1)} MB`;
}
