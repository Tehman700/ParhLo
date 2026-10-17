"use client";

import { useEffect, useState } from "react";
import type { SavedStory } from "@/lib/api";
import { useApi } from "@/lib/auth";
import { timeAgo, topicLabel } from "@/lib/topics";
import { Section } from "./Section";

/** Stories the reader saved from any paper. Removing one also takes it out of what ParhLo remembers. */
export function SavedStories() {
  const api = useApi();
  const [items, setItems] = useState<SavedStory[] | null>(null);

  useEffect(() => {
    api.get<SavedStory[]>("/api/me/saved").then(setItems).catch(() => setItems([]));
  }, [api]);

  async function remove(id: number) {
    setItems((xs) => xs?.filter((x) => x.id !== id) ?? null);
    await api.post("/api/events", [{ type: "unsave", article_id: id }]).catch(() => {});
  }

  return (
    <Section id="saved" title="Saved stories" note="Press the bookmark on any story to keep it here.">
      {items === null ? <p className="t-caption text-ink-48">Loading…</p> : items.length === 0 ? (
        <p className="t-body text-ink-60">Nothing saved yet.</p>
      ) : (
        <ul className="divide-y divide-divider">
          {items.map((s) => (
            <li key={s.id} className="saved-item flex items-start gap-4 py-4 first:pt-0">
              <div className="min-w-0 flex-1">
                <p className="kicker">{topicLabel(s.topics[0])}</p>
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="headline mt-1 block text-[17px] hover:text-primary">{s.title}</a>
                {s.summary && <p className="mt-1 line-clamp-2 t-caption text-ink-60">{s.summary}</p>}
                <p className="mt-1 t-fine text-ink-48">{s.source} · saved {timeAgo(s.saved_at)}</p>
              </div>
              <button className="flex-none t-caption text-ink-48 hover:text-danger" aria-label={`Remove ${s.title} from saved`} onClick={() => remove(s.id)}>Remove</button>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
