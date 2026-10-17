import type { ReactNode } from "react";

export function Section({ title, note, children, id, right }: { title: string; note?: string; children: ReactNode; id?: string; right?: ReactNode }) {
  return (
    <section id={id} className="panel scroll-mt-16 rounded-[18px] bg-canvas p-6 sm:p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="t-tagline">{title}</h2>
          {note && <p className="mt-1 t-caption text-ink-60">{note}</p>}
        </div>
        {right}
      </div>
      <div className="mt-6">{children}</div>
    </section>
  );
}

export function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 border-t border-divider py-4 first:border-t-0 first:pt-0 sm:flex-row sm:items-center sm:justify-between">
      <span className="t-body">{label}</span>
      <div className="sm:w-[320px]">{children}</div>
    </div>
  );
}
