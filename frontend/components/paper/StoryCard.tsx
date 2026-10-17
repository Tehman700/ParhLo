"use client";

import gsap from "gsap";
import { useEffect, useRef, useState } from "react";
import type { Story } from "@/lib/api";
import { timeAgo, topicLabel } from "@/lib/topics";

type Mark = "open" | "like" | "dislike" | "unreact" | "save" | "unsave" | "skip";
type Tracker = { track: (t: Mark, id: number) => void; observe: (el: HTMLElement | null, id: number) => (() => void) | void };

export function VerifiedBadge({ story }: { story: Story }) {
  if (story.verified === true) {
    const c = story.check;
    const pct = c?.confidence != null ? ` · ${Math.round(c.confidence * 100)}%` : "";
    const how = c?.by === "jev" ? "Jev, a decision model," : "a second AI pass";
    return <span className="t-caption font-semibold text-success" title={`Every point in this summary was checked against the original article by ${how}${c?.confidence != null ? ` (${Math.round(c.confidence * 100)}% confident)` : ""}.`}>✓ Checked against source{pct}</span>;
  }
  if (story.grounded_in && story.grounded_in !== "full article")
    return <span className="t-caption text-ink-48" title="The full article couldn't be loaded, so this summary uses the headline and excerpt.">Based on headline and excerpt</span>;
  return <span className="t-caption text-ink-48">AI summary</span>;
}

const Icon = {
  up: <path d="M7 11v8H4v-8h3Zm2 8h7.5a2 2 0 0 0 2-1.6l1.2-6A2 2 0 0 0 17.7 9H14V5.5A2.5 2.5 0 0 0 11.5 3L9 10v9Z" />,
  down: <path d="M7 13V5H4v8h3Zm2-8h7.5a2 2 0 0 1 2 1.6l1.2 6a2 2 0 0 1-2 2.4H14v3.5a2.5 2.5 0 0 1-2.5 2.5L9 14V5Z" />,
  save: <path d="M6 3h12v18l-6-4-6 4V3Z" />,
  hide: <path d="M6 6l12 12M18 6 6 18" />,
};

function IconButton({ label, active, onClick, kind, activeClass }: { label: string; active?: boolean; onClick: () => void; kind: keyof typeof Icon; activeClass: string }) {
  return (
    <button aria-label={label} title={label} onClick={onClick} data-react={kind}
      className={`flex h-8 w-8 items-center justify-center rounded-full transition-colors hover:bg-parchment ${active ? activeClass : "text-ink-48 hover:text-ink"}`}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill={active && kind !== "hide" ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{Icon[kind]}</svg>
    </button>
  );
}

export type StoryState = { reaction: "like" | "dislike" | null; saved: boolean };

export function StoryCard({ story, variant = "normal", tracker, initial }: { story: Story; variant?: "lead" | "normal"; tracker: Tracker; initial?: StoryState }) {
  const ref = useRef<HTMLElement>(null);
  const [reaction, setReaction] = useState<"like" | "dislike" | null>(initial?.reaction ?? null);
  const [saved, setSaved] = useState(initial?.saved ?? false);
  const [hidden, setHidden] = useState(false);
  const [open, setOpen] = useState(variant === "lead");
  const [imgFailed, setImgFailed] = useState(false);
  const lead = variant === "lead";

  useEffect(() => tracker.observe(ref.current, story.id) ?? undefined, [tracker, story.id]);

  function hide() {
    tracker.track("skip", story.id);
    gsap.to(ref.current, { height: 0, opacity: 0, marginTop: 0, paddingTop: 0, duration: 0.45, ease: "power2.inOut", onComplete: () => setHidden(true) });
  }
  function react(kind: "like" | "dislike") {
    // Pressing the active reaction again removes it.
    const next = reaction === kind ? null : kind;
    setReaction(next);
    tracker.track(next ?? "unreact", story.id);
    if (!next) return;
    gsap.fromTo(ref.current?.querySelector(`[data-react="${kind === "like" ? "up" : "down"}"]`) ?? null, { scale: 1.4 }, { scale: 1, duration: 0.4, ease: "back.out(3)" });
  }

  if (hidden) return null;

  return (
    <article ref={ref} className={`story-card overflow-hidden ${lead ? "" : "border-t border-hairline pt-5"}`}>
      <div className="flex items-center gap-2">
        <p className="kicker">{topicLabel(story.topics[0])}</p>
        {story.core && <span className="rounded-full bg-ink px-2 py-0.5 t-fine font-semibold text-white">Top story</span>}
        {story.discovery && <span className="rounded-full bg-parchment px-2 py-0.5 t-fine font-semibold text-ink-60">New for you</span>}
        {story.friend && <span className="rounded-full bg-[#e8f1fb] px-2 py-0.5 t-fine font-semibold text-primary">From {story.friend}</span>}
      </div>
      {story.image && !imgFailed && <img src={story.image} alt="" referrerPolicy="no-referrer" onError={() => setImgFailed(true)} className={`mt-3 w-full rounded-[12px] object-cover ${lead ? "aspect-[16/9]" : "aspect-[16/10]"}`} />}
      <h3 className={`headline mt-3 ${lead ? "text-[32px] sm:text-[40px]" : "text-[20px]"}`}>
        <a href={story.url} target="_blank" rel="noopener noreferrer" onClick={() => tracker.track("open", story.id)} className="hover:text-primary">
          {story.headline}
        </a>
      </h3>
      <p className={`deck mt-2 ${lead ? "!text-[19px]" : "!text-[16px]"}`}>{story.summary}</p>
      {open && story.points.length > 0 && (
        <ul className="mt-3 space-y-1.5 t-body text-ink-80">
          {story.points.map((p) => <li key={p} className="flex gap-2"><span className="text-primary">•</span>{p}</li>)}
        </ul>
      )}
      {story.why && <p className="mt-3 t-caption text-ink-60">Why this story: {story.why}</p>}
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
        <VerifiedBadge story={story} />
        {story.also_reported_by.length > 0 && <span className="t-caption text-ink-48">Also in {story.also_reported_by.slice(0, 3).join(", ")}</span>}
      </div>
      <div className="mt-3 flex items-center gap-1">
        <span className="mr-auto t-caption text-ink-48">{story.source} · {timeAgo(story.published_at)}</span>
        {!lead && story.points.length > 0 && <button className="mr-1 t-caption text-primary" onClick={() => setOpen(!open)}>{open ? "Less" : "Key points"}</button>}
        <IconButton label="More like this" kind="up" active={reaction === "like"} activeClass="text-primary" onClick={() => react("like")} />
        <IconButton label="Less like this" kind="down" active={reaction === "dislike"} activeClass="text-danger" onClick={() => react("dislike")} />
        <IconButton label={saved ? "Saved. Click to remove" : "Save"} kind="save" active={saved} activeClass="text-primary" onClick={() => { setSaved(!saved); tracker.track(saved ? "unsave" : "save", story.id); }} />
        <IconButton label="Hide this story" kind="hide" activeClass="" onClick={hide} />
      </div>
    </article>
  );
}
