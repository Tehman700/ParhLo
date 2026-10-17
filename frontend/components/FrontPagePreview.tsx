"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRef } from "react";
import { topicLabel } from "@/lib/topics";

export type PreviewItem = { id: number; title: string; source: string; image_url: string | null; topic: string; core?: boolean; followed?: boolean };
export type Preview = { lead: PreviewItem | null; stories: PreviewItem[]; core: PreviewItem[] };

gsap.registerPlugin(useGSAP);

/** Live mini front page shown while the reader picks topics (onboarding step 2). */
export function FrontPagePreview({ preview, name, loading }: { preview: Preview | null; name: string; loading: boolean }) {
  const root = useRef<HTMLDivElement>(null);
  const key = preview ? [preview.lead?.id, ...preview.stories.map((s) => s.id)].join(",") : "empty";

  useGSAP(() => {
    gsap.from(".pv-item", { y: 10, opacity: 0, stagger: 0.05, duration: 0.4, ease: "power2.out" });
  }, { scope: root, dependencies: [key] });

  const hasPersonal = Boolean(preview?.lead || preview?.stories.length);

  return (
    <div ref={root} className="rounded-[18px] bg-parchment p-5">
      <div className="flex items-center justify-between">
        <p className="t-caption font-semibold text-ink-60">Your front page</p>
        <span className="flex items-center gap-1.5 t-fine text-ink-48">
          <span className={`h-1.5 w-1.5 rounded-full ${loading ? "bg-primary" : "bg-success"}`} />{loading ? "Updating" : "Live"}
        </span>
      </div>

      <div className="mt-3 rounded-[12px] bg-canvas p-4">
        <p className="masthead text-center text-[26px]">ParhLo</p>
        <p className="text-center t-fine text-ink-48">For {name || "you"}</p>
        <div className="double-rule mt-2" />

        {!hasPersonal ? (
          <p className="pv-item py-8 text-center t-caption text-ink-48">Pick topics to see your front page fill in.</p>
        ) : (
          <>
            {preview?.lead && (
              <div className="pv-item mt-3">
                <p className="kicker">{topicLabel(preview.lead.topic)}{preview.lead.followed ? " · You follow this" : ""}</p>
                {preview.lead.image_url && <img src={preview.lead.image_url} alt="" referrerPolicy="no-referrer" className="mt-1.5 aspect-[16/9] w-full rounded-[8px] object-cover" />}
                <p className="headline mt-1.5 text-[16px]">{preview.lead.title}</p>
                <p className="t-fine text-ink-48">{preview.lead.source}</p>
              </div>
            )}
            <ul className="mt-2 divide-y divide-hairline">
              {preview?.stories.map((s) => (
                <li key={s.id} className="pv-item py-2">
                  <p className="kicker !text-[11px]">{topicLabel(s.topic)}{s.followed ? " · You follow this" : ""}</p>
                  <p className="text-[13px] font-semibold leading-snug">{s.title}</p>
                </li>
              ))}
            </ul>
          </>
        )}

        {!!preview?.core.length && (
          <div className="mt-3 border-t border-hairline pt-3">
            <p className="t-fine font-semibold text-ink-60">Also today, for everyone</p>
            {preview.core.map((c) => (
              <p key={c.id} className="pv-item mt-1.5 text-[12px] leading-snug text-ink-80">
                <span className="mr-1.5 rounded-full bg-ink px-1.5 py-px text-[10px] font-semibold text-white">Top story</span>{c.title}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
