"use client";

import gsap from "gsap";
import { Fragment, useCallback, useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import type { Edition, Story } from "@/lib/api";
import { useApi } from "@/lib/auth";

export const ASK_EVENT = "parhlo:ask";
/** Open the widget from anywhere (e.g. a story card): window.dispatchEvent(new CustomEvent(ASK_EVENT, { detail: { storyId } })) */
export function askAbout(storyId?: number) {
  window.dispatchEvent(new CustomEvent(ASK_EVENT, { detail: { storyId } }));
}

type Source = { id: number; headline: string; source: string; url: string };
type Answer = { answer: string; in_paper: boolean; sources: Source[]; follow_ups: string[]; route: { by: string; ms: number; focus: number[] } };
type Msg = { role: "user"; text: string } | { role: "assistant"; data: Answer; reveal: boolean } | { role: "error"; text: string };

const quote = (s: string) => (s.length > 60 ? `${s.slice(0, 57).trimEnd()}…` : s);

function starters(edition: Edition, story: Story | null): string[] {
  if (story) return ["Explain this simply", "Why does this matter to me?", "What are the key facts and numbers?", "What could happen next?"];
  const lead = edition.stories.find((s) => s.id === edition.lead_id);
  const core = edition.stories.find((s) => s.core && s.id !== edition.lead_id);
  return [
    "What are the most important stories today?",
    ...(lead ? [`Explain “${quote(lead.headline)}” simply`] : []),
    ...(core ? [`What's the background to “${quote(core.headline)}”?`] : []),
    `Which story matters most for someone in ${edition.reader.city}?`,
  ];
}

/** Minimal, safe markdown: paragraphs, "- " bullets, **bold**. No HTML injection. */
function Rich({ text }: { text: string }) {
  const inline = (line: string) => line.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={i} className="font-semibold text-ink">{part.slice(2, -2)}</strong> : <Fragment key={i}>{part}</Fragment>);
  const blocks: ReactNode[] = [];
  let list: string[] = [];
  const flush = () => {
    if (list.length) blocks.push(<ul key={`u${blocks.length}`} className="space-y-1.5">{list.map((l, i) => <li key={i} className="flex gap-2"><span className="text-primary">•</span><span>{inline(l)}</span></li>)}</ul>);
    list = [];
  };
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (/^[-•*]\s+/.test(line)) list.push(line.replace(/^[-•*]\s+/, ""));
    else { flush(); if (line) blocks.push(<p key={`p${blocks.length}`}>{inline(line)}</p>); }
  }
  flush();
  return <div className="space-y-2.5">{blocks}</div>;
}

/** Reveals an answer word by word the first time it is shown. */
function Typewriter({ text, animate, onDone }: { text: string; animate: boolean; onDone: () => void }) {
  const words = text.split(/(\s+)/);
  const [n, setN] = useState(animate ? 0 : words.length);
  useEffect(() => {
    if (!animate) return;
    const step = Math.max(1, Math.ceil(words.length / 45));
    const t = setInterval(() => setN((k) => {
      if (k + step >= words.length) { clearInterval(t); onDone(); return words.length; }
      return k + step;
    }), 22);
    return () => clearInterval(t);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return <Rich text={words.slice(0, n).join("")} />;
}

function scrollToStory(id: number) {
  const el = document.getElementById(`story-${id}`);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  gsap.fromTo(el, { backgroundColor: "rgba(0,113,227,0.10)" }, { backgroundColor: "rgba(0,113,227,0)", duration: 2, delay: 0.4, ease: "power2.out" });
}

/** "Ask your paper": a floating assistant that answers only from this edition, with sources. */
export function AskPaper({ edition }: { edition: Edition }) {
  const api = useApi();
  const [open, setOpen] = useState(false);
  const [story, setStory] = useState<Story | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);
  const fab = useRef<HTMLButtonElement>(null);
  const storyRef = useRef<number | null>(null);

  // Opened from a story card
  useEffect(() => {
    const onAsk = (e: Event) => {
      const id = (e as CustomEvent<{ storyId?: number }>).detail?.storyId ?? null;
      // A different story starts a fresh conversation about it.
      if (id !== null && id !== storyRef.current) setMsgs([]);
      storyRef.current = id;
      setStory(edition.stories.find((s) => s.id === id) ?? null);
      setOpen(true);
    };
    window.addEventListener(ASK_EVENT, onAsk);
    return () => window.removeEventListener(ASK_EVENT, onAsk);
  }, [edition]);

  useEffect(() => {
    if (!open) return;
    gsap.fromTo(panel.current, { opacity: 0, y: 24, scale: 0.96, transformOrigin: "bottom right" }, { opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "power3.out" });
    gsap.fromTo(".ask-starter", { opacity: 0, y: 10 }, { opacity: 1, y: 0, stagger: 0.05, duration: 0.35, delay: 0.1, ease: "power3.out" });
    setTimeout(() => field.current?.focus(), 150);
    const esc = (e: globalThis.KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [open]);

  useEffect(() => {
    const id = Number(new URLSearchParams(window.location.search).get("ask"));
    if (!id || !edition.stories.some((s) => s.id === id)) return;
    const t = setTimeout(() => askAbout(id), 600);
    window.history.replaceState(null, "", window.location.pathname + window.location.hash);
    return () => clearTimeout(t);
  }, [edition]);

  useEffect(() => {
    gsap.fromTo(fab.current, { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, delay: 1.2, ease: "back.out(1.6)" });
  }, []);

  const scrollDown = useCallback(() => requestAnimationFrame(() => scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" })), []);

  async function send(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    const history = msgs.flatMap((m) => m.role === "user" ? [{ role: "user", content: m.text }] : m.role === "assistant" ? [{ role: "assistant", content: m.data.answer }] : []);
    setMsgs((m) => [...m, { role: "user", text: q }]);
    setInput("");
    setBusy(true);
    scrollDown();
    try {
      const data = await api.post<Answer>("/api/ask", { question: q, date: edition.edition_date, story_id: story?.id ?? null, history });
      setMsgs((m) => [...m, { role: "assistant", data, reveal: true }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "error", text: (e as Error).message }]);
    } finally {
      setBusy(false);
      scrollDown();
    }
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(input); }
  }

  const list = starters(edition, story);

  return (
    <>
      {!open && (
        <button ref={fab} onClick={() => { if (storyRef.current !== null) setMsgs([]); storyRef.current = null; setStory(null); setOpen(true); }} aria-label="Ask your paper" data-tour="ask"
          className="fixed bottom-5 right-5 z-50 flex items-center gap-2 rounded-full bg-ink py-3 pl-4 pr-5 text-[15px] font-medium text-white shadow-[0_12px_32px_-8px_rgba(0,0,0,.45)] transition-transform hover:scale-[1.03] active:scale-95">
          <Sparkle /> Ask your paper
        </button>
      )}

      {open && (
        <div ref={panel} role="dialog" aria-label="Ask your paper"
          className="fixed inset-0 z-50 flex flex-col overflow-hidden bg-canvas sm:inset-auto sm:bottom-5 sm:right-5 sm:h-[min(680px,calc(100vh-88px))] sm:w-[420px] sm:rounded-[24px] sm:border sm:border-hairline sm:shadow-[0_24px_64px_-16px_rgba(0,0,0,.35)]">
          {/* header */}
          <div className="flex items-center gap-3 border-b border-divider px-5 py-4">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-ink text-white"><Sparkle /></span>
            <div className="flex-1">
              <p className="text-[17px] font-semibold leading-tight">Ask your paper</p>
              <p className="t-fine text-ink-48">Answers come only from your {edition.stories.length} stories</p>
            </div>
            {msgs.length > 0 && <button className="t-caption text-primary" onClick={() => { setMsgs([]); setStory(null); storyRef.current = null; }}>New</button>}
            <button aria-label="Close" onClick={() => setOpen(false)} className="flex h-8 w-8 items-center justify-center rounded-full bg-parchment text-ink-60 hover:text-ink">✕</button>
          </div>

          {story && (
            <div className="flex items-center gap-2 border-b border-divider bg-pearl px-5 py-2.5">
              <span className="t-fine font-semibold text-primary">About</span>
              <span className="flex-1 truncate t-caption">{story.headline}</span>
              <button aria-label="Ask about the whole paper" className="t-caption text-ink-48 hover:text-ink" onClick={() => { setStory(null); storyRef.current = null; }}>✕</button>
            </div>
          )}

          {/* messages */}
          <div ref={scroller} className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
            {msgs.length === 0 && (
              <div>
                <p className="t-body text-ink-80">{story ? "What would you like to know about this story?" : "Ask anything about today's paper. Every answer shows the stories it came from."}</p>
                <div className="mt-4 flex flex-col items-start gap-2">
                  {list.map((q) => (
                    <button key={q} onClick={() => send(q)} className="ask-starter rounded-[14px] border border-hairline px-3.5 py-2.5 text-left t-caption text-ink hover:border-primary hover:text-primary">{q}</button>
                  ))}
                </div>
              </div>
            )}

            {msgs.map((m, i) => m.role === "user" ? (
              <div key={i} className="flex justify-end">
                <p className="max-w-[85%] rounded-[18px] rounded-br-[6px] bg-primary px-4 py-2.5 t-body !text-[15px] text-white">{m.text}</p>
              </div>
            ) : m.role === "error" ? (
              <p key={i} className="rounded-[14px] bg-[#fff2f2] px-4 py-3 t-caption text-danger">{m.text}</p>
            ) : (
              <div key={i} className="max-w-[95%]">
                <div className="rounded-[18px] rounded-bl-[6px] bg-parchment px-4 py-3 text-[15px] leading-[1.5] text-ink-80">
                  <Typewriter text={m.data.answer} animate={m.reveal} onDone={() => { setMsgs((all) => all.map((x, k) => (k === i && x.role === "assistant" ? { ...x, reveal: false } : x))); scrollDown(); }} />
                </div>
                {!m.reveal && (
                  <>
                    {m.data.sources.length > 0 && (
                      <div className="mt-2.5">
                        <p className="t-fine text-ink-48">{m.data.in_paper ? "From your paper" : "Closest stories in your paper"}</p>
                        <div className="mt-1.5 flex flex-col gap-1.5">
                          {m.data.sources.map((s, k) => (
                            <div key={s.id} className="flex items-center gap-2 rounded-[12px] border border-hairline px-3 py-2">
                              <span className="flex h-5 w-5 flex-none items-center justify-center rounded-full bg-[#e8f1fb] text-[11px] font-semibold text-primary">{k + 1}</span>
                              <button className="flex-1 truncate text-left t-caption hover:text-primary" title="Show in the paper" onClick={() => { scrollToStory(s.id); if (window.innerWidth < 640) setOpen(false); }}>{s.headline}</button>
                              <a href={s.url} target="_blank" rel="noopener noreferrer" className="flex-none t-fine text-ink-48 hover:text-primary" aria-label={`Read the original on ${s.source}`}>{s.source} ↗</a>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {i === msgs.length - 1 && m.data.follow_ups.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {m.data.follow_ups.map((f) => (
                          <button key={f} onClick={() => send(f)} className="rounded-full bg-[#e8f1fb] px-3 py-1.5 text-left t-fine font-medium text-primary hover:bg-[#d6e6f8]">{f}</button>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}

            {busy && (
              <div className="flex items-center gap-2 t-caption text-ink-60" role="status">
                <span className="flex gap-1">
                  <span className="dot h-1.5 w-1.5 rounded-full bg-primary" /><span className="dot h-1.5 w-1.5 rounded-full bg-primary" /><span className="dot h-1.5 w-1.5 rounded-full bg-primary" />
                </span>
                Reading your paper…
              </div>
            )}
          </div>

          {/* input */}
          <div className="border-t border-divider p-3">
            <div className="flex items-end gap-2 rounded-[20px] border border-[#d2d2d7] bg-canvas py-1.5 pl-4 pr-1.5 focus-within:border-primary-focus focus-within:shadow-[0_0_0_3px_rgba(0,113,227,.15)]">
              <textarea ref={field} rows={1} value={input} maxLength={500} placeholder={story ? "Ask about this story" : "Ask about today's paper"}
                onChange={(e) => { setInput(e.target.value); e.target.style.height = "auto"; e.target.style.height = `${Math.min(e.target.scrollHeight, 96)}px`; }}
                onKeyDown={onKey} aria-label="Your question"
                className="max-h-24 flex-1 resize-none bg-transparent py-1.5 text-[15px] outline-none placeholder:text-ink-48" />
              <button onClick={() => send(input)} disabled={!input.trim() || busy} aria-label="Send"
                className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-primary text-white transition-opacity disabled:opacity-30">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 19V5M5 12l7-7 7 7" /></svg>
              </button>
            </div>
            <p className="mt-1.5 text-center t-fine text-ink-48">AI answers can be wrong. Check the original stories.</p>
          </div>
        </div>
      )}
    </>
  );
}

function Sparkle() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 2l1.9 5.6L19.5 9.5l-5.6 1.9L12 17l-1.9-5.6L4.5 9.5l5.6-1.9L12 2Z" />
      <path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z" opacity=".7" />
    </svg>
  );
}
