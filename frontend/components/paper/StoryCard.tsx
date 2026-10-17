"use client";

import gsap from "gsap";
import { useEffect, useRef, useState } from "react";
import type { Story } from "@/lib/api";
import { timeAgo, topicLabel } from "@/lib/topics";

type Tracker = { track: (t: "open" | "like" | "dislike" | "save" | "skip", id: number) => void; observe: (el: HTMLElement | null, id: number) => (() => void) | void };

export function VerifiedBadge({ story }: { story: Story }) {
  if (story.verified === true)
    return <span className="inline-flex items-center gap-1 text-[12px] font-semibold text-success" title="A second AI pass checked every claim against the original article.">✓ Verified against {story.grounded_in === "full article" ? "full article" : "source"}</span>;
  if (story.grounded_in && story.grounded_in !== "full article")
    return <span className="text-[12px] text-ink-48" title="The full article couldn't be fetched, so this summary is based on the headline and excerpt.">◐ From headline &amp; excerpt</span>;
  return <span className="text-[12px] text-ink-48">AI summary · check the original</span>;
}

export function StoryCard({ story, variant = "normal", tracker }: { story: Story; variant?: "lead" | "normal" | "compact"; tracker: Tracker }) {
  const ref = useRef<HTMLElement>(null);
  const [reaction, setReaction] = useState<"like" | "dislike" | null>(null);
  const [saved, setSaved] = useState(false);
  const [skipped, setSkipped] = useState(false);
  const [open, setOpen] = useState(variant === "lead");

  useEffect(() => tracker.observe(ref.current, story.id) ?? undefined, [tracker, story.id]);

  function skip() {
    tracker.track("skip", story.id);
    gsap.to(ref.current, { height: 0, opacity: 0, paddingTop: 0, paddingBottom: 0, marginTop: 0, duration: 0.45, ease: "power2.inOut",
      onComplete: () => setSkipped(true) });
  }
  function react(kind: "like" | "dislike") {
    setReaction(kind);
    tracker.track(kind, story.id);
    gsap.fromTo(ref.current?.querySelector(`[data-react="${kind}"]`) ?? null, { scale: 1.5 }, { scale: 1, duration: 0.4, ease: "back.out(3)" });
  }

  if (skipped) return null;
  const lead = variant === "lead";
  const compact = variant === "compact";

  return (
    <article ref={ref} className={`story-card group overflow-hidden ${lead ? "" : "border-t border-rule pt-4"}`}>
      <p className="kicker text-sun-deep">
        {topicLabel(story.topics[0])}
        {story.discovery && <span className="ml-2 rounded-full bg-ink px-2 py-0.5 text-[10px] text-sun">Discovery</span>}
        {story.region === "pakistan" && story.topics[0] !== "pakistan" && <span className="ml-2 text-ink-48">· Pakistan</span>}
      </p>
      {lead && story.image && <img src={story.image} alt="" className="mt-3 aspect-[16/9] w-full rounded-[4px] object-cover grayscale-[15%]" />}
      <h3 className={`headline mt-2 ${lead ? "text-[34px] sm:text-[40px]" : compact ? "text-[18px]" : "text-[21px]"}`}>
        <a href={story.url} target="_blank" rel="noopener noreferrer" onClick={() => tracker.track("open", story.id)} className="hover:underline decoration-1 underline-offset-4">
          {story.headline}
        </a>
      </h3>
      {!lead && !compact && story.image && <img src={story.image} alt="" className="mt-3 aspect-[16/10] w-full rounded-[3px] object-cover" />}
      {!compact && <p className={`deck mt-2 ${lead ? "dropcap text-[18px]" : "text-[15.5px]"}`}>{story.summary}</p>}
      {open && story.points.length > 0 && (
        <ul className="mt-3 space-y-1 border-l-2 border-sun pl-3 font-serif text-[15px] text-ink-80">
          {story.points.map((p) => <li key={p}>{p}</li>)}
        </ul>
      )}
      {story.why && <p className="mt-3 text-[13px] italic text-ink-60"><span className="not-italic font-semibold text-sun-deep">Why you&apos;re seeing this:</span> {story.why}</p>}
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
        <VerifiedBadge story={story} />
        {story.also_reported_by.length > 0 && <span className="text-[12px] text-ink-48">Also in {story.also_reported_by.slice(0, 3).join(", ")}</span>}
      </div>
      <div className="mt-3 flex items-center gap-1 text-[13px] text-ink-60">
        <span className="mr-auto">{story.source} · {timeAgo(story.published_at)}</span>
        {!lead && !compact && story.points.length > 0 && <button className="px-2 py-1 hover:text-ink" onClick={() => setOpen(!open)}>{open ? "Less" : "Key facts"}</button>}
        <button data-react="like" aria-label="More like this" title="More like this" onClick={() => react("like")} className={`rounded-full px-2 py-1 hover:bg-black/5 ${reaction === "like" ? "text-success" : ""}`}>▲</button>
        <button data-react="dislike" aria-label="Less like this" title="Less like this" onClick={() => react("dislike")} className={`rounded-full px-2 py-1 hover:bg-black/5 ${reaction === "dislike" ? "text-danger" : ""}`}>▼</button>
        <button aria-label="Save" title="Save" onClick={() => { setSaved(true); tracker.track("save", story.id); }} className={`rounded-full px-2 py-1 hover:bg-black/5 ${saved ? "text-sun-deep" : ""}`}>{saved ? "★" : "☆"}</button>
        <button aria-label="Skip" title="Skip — not interested" onClick={skip} className="rounded-full px-2 py-1 hover:bg-black/5">✕</button>
      </div>
    </article>
  );
}
