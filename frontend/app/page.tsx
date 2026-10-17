"use client";

import { useEffect, useRef, useState } from "react";
import { post, streamChat, type AgentResult, type AgentStep, type ChatMessage, type ToolInfo } from "@/lib/api";
import { useApi, useConfig, useStoredState } from "@/lib/hooks";
import { Badge, ErrorNote, JsonView, PageHeader, Segmented, Spinner } from "@/components/ui";
import { ToolSteps } from "@/components/ToolSteps";

type Mode = "agent" | "chat";
type Turn = ChatMessage & { steps?: AgentStep[]; durationMs?: number; mode?: Mode };

const SUGGESTIONS = [
  "What is (1899 * 3 + 449) * 1.17?",
  "Which tables are in the database?",
];

export default function Workspace() {
  const { data: config } = useConfig();
  const { data: tools } = useApi<ToolInfo[]>("/api/agent/tools");
  const [mode, setMode] = useStoredState<Mode>("ws.mode", "agent");
  const [turns, setTurns] = useStoredState<Turn[]>("ws.turns", []);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<AgentResult | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, busy]);

  const lastAgentTurn = [...turns].reverse().find((t) => t.steps);

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    setInput("");
    setError(null);
    setBusy(true);
    const history: ChatMessage[] = turns.map(({ role, content }) => ({ role, content }));
    setTurns((t) => [...t, { role: "user", content: message }]);

    try {
      if (mode === "agent") {
        const res = await post<AgentResult>("/api/agent/run", { message, history });
        setLastResult(res);
        setTurns((t) => [...t, { role: "assistant", content: res.answer, steps: res.steps, durationMs: res.duration_ms, mode }]);
      } else {
        abortRef.current = new AbortController();
        setTurns((t) => [...t, { role: "assistant", content: "", mode }]);
        await streamChat([...history, { role: "user", content: message }], (delta) => {
          setTurns((t) => {
            const copy = [...t];
            const last = copy[copy.length - 1];
            copy[copy.length - 1] = { ...last, content: last.content + delta };
            return copy;
          });
        }, { signal: abortRef.current.signal });
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
      // Drop an empty streamed assistant bubble if the request failed.
      setTurns((t) => (t.at(-1)?.role === "assistant" && !t.at(-1)?.content ? t.slice(0, -1) : t));
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  return (
    <>
      <PageHeader
        title="Workspace"
        subtitle="Chat with the model, or let the agent call tools. Every tool call shows up on the right."
        actions={
          <>
            <Segmented<Mode>
              value={mode}
              onChange={setMode}
              options={[{ value: "agent", label: "Agent" }, { value: "chat", label: "Chat" }]}
            />
            <button className="btn btn-ghost" onClick={() => { setTurns([]); setLastResult(null); setError(null); }} disabled={busy || !turns.length}>
              Clear
            </button>
          </>
        }
      />

      {config && !config.llm.configured && (
        <div className="mb-6">
          <ErrorNote error="No LLM key configured. Set LLM_API_KEY in the repo-root .env and restart the backend. Tools, files, documents search and ML work without it." />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_420px]">
        {/* Conversation */}
        <section className="card flex min-h-[560px] flex-col !p-0">
          <div className="flex-1 space-y-5 overflow-y-auto p-6" style={{ maxHeight: "calc(100vh - 300px)" }}>
            {!turns.length && (
              <div className="py-10 text-center">
                <p className="display text-[28px]">What should we work on?</p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} className="btn btn-secondary !text-[14px]" onClick={() => send(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {turns.map((t, i) => (
              <Bubble key={i} turn={t} />
            ))}
            {busy && mode === "agent" && <Spinner label="Agent is thinking and calling tools…" />}
            <div ref={endRef} />
          </div>

          <div className="border-t border-divider p-4">
            <ErrorNote error={error} onDismiss={() => setError(null)} />
            <form
              className="mt-2 flex items-end gap-3"
              onSubmit={(e) => {
                e.preventDefault();
                send(input);
              }}
            >
              <textarea
                className="input min-h-[48px] flex-1 !rounded-[24px] !py-3"
                rows={1}
                placeholder={mode === "agent" ? "Ask the agent… (Enter to send, Shift+Enter for newline)" : "Message the model…"}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send(input);
                  }
                }}
              />
              {busy && mode === "chat" ? (
                <button type="button" className="btn btn-dark !rounded-full !py-3" onClick={() => abortRef.current?.abort()}>Stop</button>
              ) : (
                <button className="btn btn-primary !py-3" disabled={busy || !input.trim()}>Send</button>
              )}
            </form>
          </div>
        </section>

        {/* Tool execution + results */}
        <aside className="flex flex-col gap-6">
          <section className="tile-dark">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-[17px] font-semibold">Tool execution</h2>
              {lastAgentTurn?.durationMs !== undefined && <Badge tone="blue">{lastAgentTurn.steps?.length ?? 0} steps</Badge>}
            </div>
            <ToolSteps steps={lastAgentTurn?.steps ?? []} totalMs={lastAgentTurn?.durationMs} />
          </section>

          <section className="card">
            <h2 className="mb-3 text-[17px] font-semibold">Last result</h2>
            {lastResult ? (
              <JsonView data={{ ...lastResult, answer: lastResult.answer.slice(0, 300) }} maxHeight={280} />
            ) : (
              <p className="caption text-ink-48">The raw agent response (JSON) appears here.</p>
            )}
          </section>

          <section className="card">
            <h2 className="mb-3 text-[17px] font-semibold">Available tools</h2>
            <ul className="space-y-3">
              {(tools ?? []).map((t) => (
                <li key={t.name}>
                  <div className="mono text-ink">{t.name}</div>
                  <div className="caption text-ink-48">{t.description}</div>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </>
  );
}

function Bubble({ turn }: { turn: Turn }) {
  const isUser = turn.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] whitespace-pre-wrap rounded-[18px] px-4 py-3 text-[16px] ${
          isUser ? "bg-primary text-white" : "bg-parchment text-ink"
        }`}
      >
        {turn.content || <Spinner />}
        {!isUser && turn.steps && turn.steps.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {turn.steps.map((s, i) => (
              <Badge key={i} tone={s.error ? "red" : "blue"}>{s.tool}</Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
