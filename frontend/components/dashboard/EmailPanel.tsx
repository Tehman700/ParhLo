"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useApi } from "@/lib/auth";
import { Spinner } from "../ui";
import { Section } from "./Section";

type Status = { last: { status: string; kind: string; sent_at: string | null; created_at: string } | null };

/** Morning email on/off, "send me today's email", and when the last one went out. */
export function EmailPanel({ on, email, isDemo, onChanged }: { on: boolean; email: string | null; isDemo: boolean; onChanged?: (msg: string) => void }) {
  const api = useApi();
  const [enabled, setEnabled] = useState(on);
  const [busy, setBusy] = useState<"toggle" | "send" | null>(null);
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null);
  const [status, setStatus] = useState<Status | null>(null);

  useEffect(() => {
    if (!isDemo) api.get<Status>("/api/me/email").then(setStatus).catch(() => {});
  }, [api, isDemo]);

  if (isDemo || !email) return (
    <Section id="email" title="Morning email" note="Get your paper in your inbox every morning.">
      <p className="t-body text-ink-60"><Link href="/sign-in" className="link">Create an account</Link> to get your paper by email.</p>
    </Section>
  );

  async function toggle() {
    const next = !enabled;
    setBusy("toggle");
    setEnabled(next);
    try {
      await api.patch("/api/me", { email_morning: next });
      onChanged?.(next ? "Morning email is on" : "Morning email is off");
    } catch {
      setEnabled(!next);
    } finally {
      setBusy(null);
    }
  }

  async function sendNow() {
    setBusy("send");
    setNote(null);
    try {
      const r = await api.post<{ to: string }>("/api/me/email/send");
      setNote({ ok: true, text: `Sent to ${r.to}. It should arrive in a minute.` });
      api.get<Status>("/api/me/email").then(setStatus).catch(() => {});
    } catch (e) {
      setNote({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(null);
    }
  }

  const last = status?.last;
  return (
    <Section id="email" title="Morning email" note="Your paper in your inbox at about 6:00 AM, with a link to read it and download the PDF.">
      <div className="flex items-start gap-4 rounded-[12px] bg-parchment p-4">
        <div className="flex-1">
          <p className="t-body font-semibold">Send my paper every morning</p>
          <p className="mt-1 t-caption text-ink-60">To {email}. Every email has a one-click unsubscribe link.</p>
        </div>
        <button type="button" role="switch" aria-checked={enabled} aria-label="Morning email" className="switch mt-1"
          disabled={busy === "toggle"} onClick={toggle} />
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-4">
        <button className="btn btn-secondary" onClick={sendNow} disabled={!!busy}>
          {busy === "send" ? <Spinner label="Sending" /> : "Send me today's email now"}
        </button>
        {last?.sent_at && <span className="t-caption text-ink-60">Last sent {new Date(last.sent_at).toLocaleString("en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" })}</span>}
      </div>
      {note && <p className={`mt-3 t-caption ${note.ok ? "text-success" : "text-danger"}`} role="status">{note.ok ? "✓ " : ""}{note.text}</p>}
    </Section>
  );
}
