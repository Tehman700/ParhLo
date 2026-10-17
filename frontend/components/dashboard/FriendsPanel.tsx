"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { FriendsInfo } from "@/lib/api";
import { useApi } from "@/lib/auth";
import { Spinner } from "../ui";
import { Section } from "./Section";

/** Invite link, friends list and the one "Learn from friends" switch. */
export function FriendsPanel({ isDemo, onChanged }: { isDemo: boolean; onChanged?: (msg: string) => void }) {
  const api = useApi();
  const [info, setInfo] = useState<FriendsInfo | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isDemo) api.get<FriendsInfo>("/api/me/friends").then(setInfo).catch(() => {});
  }, [api, isDemo]);

  if (isDemo) return (
    <Section id="friends" title="Friends" note="Invite friends and let what they like shape your paper.">
      <p className="t-body text-ink-60"><Link href="/sign-in" className="link">Create an account</Link> to invite friends.</p>
    </Section>
  );

  const link = info ? `${window.location.origin}/invite/${info.invite_code}` : "";

  async function copy() {
    try {
      if (navigator.share && window.matchMedia("(pointer: coarse)").matches) {
        await navigator.share({ title: "ParhLo", text: "Join me on ParhLo: your news, in one paper.", url: link });
        return;
      }
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  }

  async function toggle() {
    if (!info) return;
    const on = !info.learn_from_friends;
    setBusy(true);
    setInfo({ ...info, learn_from_friends: on });
    try {
      await api.patch("/api/me", { learn_from_friends: on });
      onChanged?.(on ? "Your friends can now shape your paper" : "Friends no longer shape your paper");
    } catch {
      setInfo({ ...info, learn_from_friends: !on });
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string, name: string) {
    setInfo(await api.del<FriendsInfo>(`/api/me/friends/${id}`));
    onChanged?.(`Removed ${name}`);
  }

  return (
    <Section id="friends" title="Friends" note="Invite friends to ParhLo. You'll get a notification when they join.">
      {!info ? <Spinner label="Loading" /> : (
        <>
          <div className="flex items-start gap-4 rounded-[12px] bg-parchment p-4">
            <div className="flex-1">
              <p className="t-body font-semibold">Learn from friends</p>
              <p className="mt-1 t-caption text-ink-60">
                When on, up to 2 stories your friends liked appear in your paper, and your interests drift slightly toward theirs.
                Your likes can shape their papers too, if they turn this on. Turning it off stops this from then on. Nothing already learned is undone.
              </p>
            </div>
            <button type="button" role="switch" aria-checked={info.learn_from_friends} aria-label="Learn from friends"
              className="switch mt-1" disabled={busy} onClick={toggle} />
          </div>

          <p className="mt-6 t-caption font-semibold text-ink-60">Your invite link</p>
          <div className="mt-2 flex gap-2">
            <input className="input flex-1 !text-[15px]" readOnly value={link} aria-label="Your invite link" onFocus={(e) => e.target.select()} />
            <button className="btn btn-primary" onClick={copy}>{copied ? "Copied" : "Copy link"}</button>
          </div>

          <p className="mt-6 t-caption font-semibold text-ink-60">Your friends</p>
          {info.friends.length === 0 ? (
            <p className="mt-2 t-body text-ink-60">No friends yet. Share your link to add some.</p>
          ) : (
            <ul className="mt-2 divide-y divide-divider">
              {info.friends.map((f) => (
                <li key={f.id} className="flex items-center gap-3 py-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-ink text-[14px] font-semibold text-white">{f.name.charAt(0).toUpperCase()}</span>
                  <div className="flex-1">
                    <p className="t-body">{f.name}</p>
                    <p className="t-fine text-ink-48">{f.sharing && info.learn_from_friends ? "Shaping your paper" : f.sharing ? "Shares likes · turn on Learn from friends to use them" : "Not sharing likes"}</p>
                  </div>
                  <button className="t-caption text-ink-48 hover:text-danger" onClick={() => remove(f.id, f.name)}>Remove</button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Section>
  );
}
