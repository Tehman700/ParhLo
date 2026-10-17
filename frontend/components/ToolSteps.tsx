"use client";

import { useState } from "react";
import type { AgentStep } from "@/lib/api";

/** Agent tool executions, shown on a dark tile. */
export function ToolSteps({ steps, totalMs }: { steps: AgentStep[]; totalMs?: number }) {
  if (!steps.length) {
    return <p className="caption text-muted-on-dark/70">No tools used yet. Ask something that needs a calculation, the database, or a CSV.</p>;
  }
  const toolMs = steps.reduce((s, x) => s + x.duration_ms, 0);
  return (
    <div className="flex flex-col gap-2">
      {steps.map((s, i) => (
        <StepRow key={i} step={s} index={i + 1} />
      ))}
      <div className="mt-2 flex justify-between caption text-muted-on-dark/70">
        <span>{steps.length} tool call{steps.length > 1 ? "s" : ""} · {toolMs.toFixed(0)} ms in tools</span>
        {totalMs !== undefined && <span>{(totalMs / 1000).toFixed(2)} s total</span>}
      </div>
    </div>
  );
}

function StepRow({ step, index }: { step: AgentStep; index: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-[11px] bg-tile-2">
      <button className="flex w-full items-center gap-3 px-4 py-3 text-left" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-[12px]">{index}</span>
        <span className="mono flex-1 truncate text-white">{step.tool}</span>
        <span className={`h-2 w-2 shrink-0 rounded-full ${step.error ? "bg-[#ff6b5e]" : "bg-[#30d158]"}`} />
        <span className="shrink-0 caption text-muted-on-dark/70">{step.duration_ms.toFixed(1)} ms</span>
        <span className="shrink-0 text-muted-on-dark/70">{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div className="space-y-2 px-4 pb-4">
          <div className="label !text-muted-on-dark/60">Arguments</div>
          <pre className="mono overflow-auto rounded-[8px] bg-tile-3 p-3 text-muted-on-dark">{JSON.stringify(step.arguments, null, 2)}</pre>
          <div className="label !text-muted-on-dark/60">{step.error ? "Error" : "Result"}</div>
          <pre className={`mono max-h-64 overflow-auto rounded-[8px] bg-tile-3 p-3 ${step.error ? "text-[#ff6b5e]" : "text-muted-on-dark"}`}>
            {step.error ?? JSON.stringify(step.result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
