import type { Edition, Story } from "./api";
import { sharpImage } from "./images";
import { topicLabel } from "./topics";

/** One newspaper template for both the print preview and the server-rendered PDF (A4). */
const esc = (s: string | null | undefined) =>
  (s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

const domain = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
};

function badge(s: Story) {
  if (s.verified === true) return `<span class="ok">✓ Checked against source${s.check?.confidence != null ? ` · ${Math.round(s.check.confidence * 100)}%` : ""}</span>`;
  if (s.grounded_in && s.grounded_in !== "full article") return `<span class="muted">Based on headline and excerpt</span>`;
  return `<span class="muted">AI summary</span>`;
}

function story(s: Story, lead = false, section?: string) {
  const topic = topicLabel(s.topics[0]);
  const label = section && section !== topic ? `<span class="sect">${esc(section)}</span> · ${esc(topic)}` : esc(section ?? topic);
  return `<article class="${lead ? "lead" : "story"}">
    <div class="kicker">${label}${s.core ? ' <span class="disc">Top story</span>' : ""}${s.discovery ? ' <span class="disc">New for you</span>' : ""}</div>
    ${lead && s.image ? `<img class="lead-img" src="${esc(sharpImage(s.image))}" alt="" referrerpolicy="no-referrer" onerror="this.remove()">` : ""}
    <h3><a href="${esc(s.url)}">${esc(s.headline)}</a></h3>
    <p class="${lead ? "deck dropcap" : "deck"}">${esc(s.summary)}</p>
    ${s.points.length ? `<ul class="points">${(lead ? s.points : s.points.slice(0, 2)).map((p) => `<li>${esc(p)}</li>`).join("")}</ul>` : ""}
    ${s.why ? `<p class="why"><b>Why this story:</b> ${esc(s.why)}</p>` : ""}
    <p class="meta">${esc(s.source)} · ${badge(s)}${s.also_reported_by.length ? ` · Also: ${esc(s.also_reported_by.slice(0, 3).join(", "))}` : ""}<br>
      <a href="${esc(s.url)}">${esc(domain(s.url))}</a></p>
  </article>`;
}

export function buildPrintHtml(ed: Edition): string {
  const byId = new Map(ed.stories.map((s) => [s.id, s]));
  const lead = byId.get(ed.lead_id) ?? ed.stories[0];
  const date = new Date(`${ed.edition_date}T00:00:00`).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const m = ed.morning;
  // "Your paper today" (replaces "Today in brief", which repeated the 3 things).
  const n = ed.stories.length, top = ed.stories.filter((s) => s.core).length, fresh = ed.stories.filter((s) => s.discovery).length;
  const mostly = ed.sections.filter((s) => s.story_ids.length).slice(0, 3).map((s) => s.name);
  const glance = `${n} ${n === 1 ? "story" : "stories"}${top ? `, including ${top} of today's top ${top === 1 ? "story" : "stories"}` : ""}`
    + `${fresh ? ` and ${fresh} new for you` : ""}.${mostly.length ? ` Mostly ${mostly.join(", ")}, in the order you care about them.` : ""}`;
  const rates = m.rates ? Object.entries(m.rates.pkr).map(([k, v]) => `${k} Rs ${v.toFixed(2)}`).join(" · ") : "—";

  // The rest of the paper flows as one newspaper column set (no half-empty section rows); each story carries its section.
  const seen = new Set<number>(lead ? [lead.id] : []);
  const flow = ed.sections.flatMap((sec) => sec.story_ids.filter((id) => !seen.has(id) && seen.add(id))
    .map((id) => byId.get(id)).filter(Boolean).map((st) => story(st as Story, false, sec.name))).join("");
  const sections = flow ? `<section><h2 class="sec">More in today's paper</h2><div class="cols">${flow}</div></section>` : "";

  return `<!doctype html><html><head><meta charset="utf-8"><title>ParhLo — ${esc(ed.edition_date)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Playfair+Display:ital,wght@0,700;0,900;1,900&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>
  @page { size: A4; margin: 12mm 11mm 14mm; }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: #ffffff; color: #1d1d1f; }
  body { font-family: "Source Serif 4", Georgia, serif; font-size: 9.6pt; line-height: 1.42; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  a { color: inherit; text-decoration: none; }
  .wrap { padding: 0; }
  .metaline { display: flex; justify-content: space-between; font: 600 7.6pt Inter, sans-serif; color: #6e6e73; border-bottom: 0.8pt solid #1d1d1f; padding-bottom: 3pt; }
  .mast { text-align: center; font: 900 58pt/1 "Playfair Display", serif; letter-spacing: -1pt; margin: 6pt 0 2pt; }
  .mast i { color: #0066cc; }
  .tag { text-align: center; font-style: italic; font-size: 9pt; color: #6e6e73; margin-bottom: 4pt; }
  .double { border-top: 3pt double #1d1d1f; }
  .top { display: grid; grid-template-columns: 1.5fr 1fr; gap: 12pt; padding: 8pt 0; border-bottom: 0.6pt solid #e0e0e0; }
  .note { font-style: italic; font-size: 11pt; line-height: 1.45; color: #333; }
  .box { border: 0.6pt solid #e0e0e0; padding: 6pt 8pt; font: 8pt/1.4 Inter, sans-serif; }
  .box b { font: 700 15pt "Playfair Display", serif; }
  .alert { color: #c4291c; font-weight: 700; }
  .kicker { font: 700 6.8pt Inter, sans-serif; letter-spacing: .12em; text-transform: uppercase; color: #0066cc; }
  .disc { background: #1d1d1f; color: #2997ff; padding: 0 4pt; border-radius: 6pt; }
  .front { display: grid; grid-template-columns: 1.7fr 1fr; gap: 14pt; padding: 10pt 0; border-bottom: 3pt solid #1d1d1f; }
  .lead h3 { font: 700 23pt/1.08 "Playfair Display", serif; margin: 4pt 0; }
  .lead-img { width: 100%; height: 150pt; object-fit: cover; margin-top: 4pt; }
  .deck { margin: 3pt 0; text-align: justify; hyphens: auto; }
  .dropcap::first-letter { float: left; font: 900 34pt/0.85 "Playfair Display", serif; padding: 3pt 4pt 0 0; }
  .points { margin: 4pt 0; padding-left: 10pt; border-left: 1.5pt solid #2997ff; list-style: none; }
  .why { font-size: 8.4pt; font-style: italic; color: #6e6e73; margin: 3pt 0; }
  .why b { font-style: normal; color: #0066cc; }
  .meta { font: 7pt/1.4 Inter, sans-serif; color: #7a7a7a; margin: 3pt 0 0; }
  .meta a { color: #0066cc; }
  .ok { color: #1a7f37; font-weight: 700; }
  .muted { color: #7a7a7a; }
  .things { background: #1d1d1f; color: #fff; padding: 8pt 10pt; }
  .things .kicker { color: #2997ff; }
  .things ol { margin: 4pt 0 0; padding-left: 14pt; }
  .things li { margin: 4pt 0; font-size: 9.6pt; }
  .side h4 { font: 700 7pt Inter; letter-spacing: .1em; text-transform: uppercase; color: #7a7a7a; margin: 10pt 0 3pt; }
  section { break-inside: auto; }
  .sec { font: 700 15pt "Playfair Display", serif; border-top: 2.4pt solid #1d1d1f; padding-top: 3pt; margin: 12pt 0 4pt; break-after: avoid; }
  .cols { column-count: 3; column-gap: 14pt; column-rule: 0.6pt solid #e0e0e0; column-fill: balance; }
  .kicker .sect { color: #1d1d1f; }
  .story .points { font-size: 8.6pt; margin: 3pt 0; }
  @media screen { body { padding: 32px 40px 40px; } }
  .story { break-inside: avoid; padding: 0 0 8pt; margin-bottom: 8pt; border-bottom: 0.6pt solid #e0e0e0; }
  .story h3 { font: 700 12.5pt/1.15 "Playfair Display", serif; margin: 2pt 0 3pt; }
  .end { margin-top: 14pt; text-align: center; border-top: 3pt double #1d1d1f; padding-top: 8pt; font: italic 10pt "Source Serif 4", serif; color: #6e6e73; }
</style></head><body><div class="wrap">
  <div class="metaline"><span>No. ${ed.number} · ${esc(ed.reader.city)}</span><span>${esc(date)}</span>
    <span>${m.weather ? `${m.weather.temp}°C ${esc(m.weather.condition)}` : ""}${m.air?.aqi != null ? ` · AQI ${m.air.aqi}` : ""}</span></div>
  <div class="mast">ParhLo</div>
  <div class="tag">For ${esc(ed.reader.name)}</div>
  <div class="double"></div>
  <div class="top">
    <div><div class="kicker" style="color:#7a7a7a">Your paper today</div><p class="note">${esc(glance)}</p></div>
    <div class="box">
      <div>${esc(m.city)}: ${m.weather ? `<b>${m.weather.temp}°</b> ${esc(m.weather.condition)} · H ${m.weather.high}° L ${m.weather.low}°` : "—"}</div>
      <div ${m.smog_alert ? 'class="alert"' : ""}>${m.smog_alert ? "⚠ Smog alert — " : "Air: "}AQI ${m.air?.aqi ?? "—"} ${esc(m.air?.label ?? "")}</div>
      <div>${esc(rates)}</div>
    </div>
  </div>
  <div class="front">
    ${lead ? story(lead, true) : ""}
    <div class="side">
      <div class="things"><div class="kicker">3 things to remember today</div>
        <ol>${ed.three_things.map((t) => `<li>${esc(t.text)}</li>`).join("")}</ol></div>
      <h4>In this edition</h4>
      ${ed.sections.map((s) => `<div>${esc(s.name)}</div>`).join("")}
      ${m.cricket ? `<h4>Cricket</h4><div><a href="${esc(m.cricket.url)}"><b style="font-family:'Playfair Display'">${esc(m.cricket.title)}</b></a></div>` : ""}
    </div>
  </div>
  ${sections}
  <div class="end">That's today's paper. Summaries are written by AI from the linked sources and checked against them.</div>
</div></body></html>`;
}
