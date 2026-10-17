/** Static product shot of a ParhLo paper (used on the landing page). */
export function PaperMock() {
  return (
    <div className="paper overflow-hidden text-left">
      <div className="flex items-center justify-between border-b border-ink px-6 pb-1.5 pt-4 text-[10px] text-ink-60">
        <span>No. 12 · Lahore</span><span className="font-semibold text-ink">Saturday, 17 October 2026</span><span>28°C · AQI 152</span>
      </div>
      <div className="masthead py-3 text-center text-[44px]">ParhLo</div>
      <div className="double-rule mx-6" />
      <div className="grid grid-cols-[1.6fr_1fr] gap-5 px-6 py-5">
        <div>
          <p className="kicker">Technology</p>
          <img src="/hero-story.webp" alt="" className="mt-2 aspect-[16/8] w-full rounded-[6px] object-cover" />
          <p className="mt-1 text-[9px] text-ink-48">Photo: Dawn</p>
          <p className="headline mt-3 text-[22px]">Pakistan showcases 20 tech firms at TechCrunch Disrupt</p>
          <p className="deck mt-2 text-[13px] leading-relaxed">Twenty Pakistani startups presented their products in San Francisco this week, the country&apos;s largest group at the event so far.</p>
          <p className="mt-2 text-[11px] font-semibold text-success">✓ Checked against source · Also in Business Recorder, TechCrunch</p>
        </div>
        <div className="space-y-4 border-l border-rule pl-5">
          <div className="rounded-[8px] bg-ink p-3.5 text-white">
            <p className="text-[11px] font-semibold text-sun">3 things to remember</p>
            <ol className="mt-2 list-decimal space-y-1.5 pl-4 text-[11.5px] leading-snug text-white/85">
              <li>20 Pakistani startups showcased at TechCrunch Disrupt.</li>
              <li>Smog levels in Lahore are unhealthy today.</li>
              <li>Pakistan won the second T20 by 6 wickets.</li>
            </ol>
          </div>
          <div className="border-t border-rule pt-3">
            <p className="kicker">Cricket</p>
            <p className="headline mt-1 text-[14px]">Pakistan level the series with a six-wicket win</p>
          </div>
          <div className="border-t border-rule pt-3">
            <p className="kicker">Economy</p>
            <p className="headline mt-1 text-[14px]">Rupee holds steady at 277 against the dollar</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Minimal browser window frame around a product shot. */
export function BrowserFrame({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`overflow-hidden rounded-[12px] bg-canvas product-shadow ${className}`}>
      <div className="flex h-8 items-center gap-1.5 border-b border-divider bg-parchment px-3">
        <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" /><span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" /><span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
        <span className="mx-auto rounded-[6px] bg-canvas px-16 py-0.5 text-[10px] text-ink-48">parhlo.app/paper</span>
      </div>
      {children}
    </div>
  );
}
