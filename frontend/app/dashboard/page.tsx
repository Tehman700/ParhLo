"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { FriendsPanel } from "@/components/dashboard/FriendsPanel";
import { PaperStatus } from "@/components/dashboard/PaperStatus";
import { SavedStories } from "@/components/dashboard/SavedStories";
import { Row, Section } from "@/components/dashboard/Section";
import { ErrorNote, Spinner, TopBar } from "@/components/ui";
import type { Edition, Me } from "@/lib/api";
import { useApi, useSession } from "@/lib/auth";
import { TOPIC_LABELS, topicLabel } from "@/lib/topics";

gsap.registerPlugin(useGSAP);

const KIND_LABEL: Record<string, string> = {
  onboarding: "You chose", entity: "You follow", liked: "You liked", clicked: "You read", disliked: "Show less",
};
const MINUTES = [5, 10, 15, 20];
/** A topic counts as "on" while its weight is at least this. */
const ON = 0.2;

export default function DashboardPage() {
  return <Suspense><Dashboard /></Suspense>;
}

function Dashboard() {
  const router = useRouter();
  const api = useApi();
  const { ready, signedIn, isDemo, signOut, refresh } = useSession();
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", city: "", reading_minutes: 10, region_mix: 0.5 });
  const [about, setAbout] = useState("");
  const [newFollow, setNewFollow] = useState("");
  const [pendingTopic, setPendingTopic] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  // Arriving straight from onboarding: the first paper is still being built (shown in PaperStatus).
  // (read once: the param is removed from the URL after arrival)
  const params = useSearchParams();
  const [welcome] = useState(() => params.has("welcome"));
  const root = useRef<HTMLDivElement>(null);

  const apply = useCallback((m: Me) => {
    setMe(m);
    setForm({ name: m.user.name === "Reader" || m.user.name === "Guest" ? "" : m.user.name, city: m.user.city,
      reading_minutes: m.user.reading_minutes, region_mix: m.user.region_mix });
    setAbout(m.profile?.about ?? "");
  }, []);

  useEffect(() => {
    if (!ready) return;
    if (!signedIn) return void router.replace("/sign-in");
    api.get<Me>("/api/me").then((m) => (m.user.onboarded ? apply(m) : router.replace("/onboarding")))
      .catch((e) => setError(e.message));
  }, [ready, signedIn, api, apply, router]);

  // Arriving from onboarding (?welcome=1) or a notification link (#friends): set up once the page has data.
  useEffect(() => {
    if (!me) return;
    if (welcome) window.history.replaceState(null, "", "/dashboard");
    if (window.location.hash) document.querySelector(window.location.hash)?.scrollIntoView({ behavior: "smooth" });
  }, [Boolean(me)]); // eslint-disable-line react-hooks/exhaustive-deps

  useGSAP(() => {
    if (!me) return;
    gsap.from(".dash-head > *", { y: 20, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out" });
    gsap.from(".panel", { y: 24, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out", delay: 0.1 });
  }, { scope: root, dependencies: [Boolean(me)] });

  function flash(msg: string) {
    setSaved(msg);
    setTimeout(() => setSaved((s) => (s === msg ? null : s)), 2500);
  }

  async function run(label: string, fn: () => Promise<Me>, done?: string) {
    setBusy(label);
    setError(null);
    try {
      apply(await fn());
      if (done) flash(done);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const dirty = me && (form.name !== (me.user.name === "Reader" || me.user.name === "Guest" ? "" : me.user.name)
    || form.city !== me.user.city || form.reading_minutes !== me.user.reading_minutes || form.region_mix !== me.user.region_mix);

  function saveProfile(e: FormEvent) {
    e.preventDefault();
    const body: Record<string, unknown> = { city: form.city.trim(), reading_minutes: form.reading_minutes, region_mix: form.region_mix };
    if (form.name.trim()) body.name = form.name.trim();
    void run("profile", () => api.patch<Me>("/api/me", body), "Profile saved").then(() => refresh());
  }

  async function toggleTopic(slug: string, on: boolean) {
    setPendingTopic(slug);
    // optimistic: flip the switch now, settle with the server's answer
    setMe((m) => (m && m.profile ? { ...m, profile: { ...m.profile, topics: { ...m.profile.topics, [slug]: on ? 0.8 : 0.05 } } } : m));
    try {
      apply(await api.put<Me>(`/api/me/topics/${slug}`, { on }));
    } catch (e) {
      setError((e as Error).message);
      api.get<Me>("/api/me").then(apply).catch(() => {});
    } finally {
      setPendingTopic(null);
    }
  }

  function addFollow(e: FormEvent) {
    e.preventDefault();
    const name = newFollow.trim();
    if (!name) return;
    void run("follow", () => api.post<Me>("/api/me/following", { name }), `Following ${name}`).then(() => setNewFollow(""));
  }

  async function removeAnchor(id: number) {
    await api.del(`/api/me/anchors/${id}`).catch((e) => setError(e.message));
    setMe((m) => (m ? { ...m, anchors: m.anchors.filter((a) => a.id !== id) } : m));
  }

  async function learnAndReprint() {
    setBusy("Updating your interests");
    try {
      await api.post("/api/learn");
      setBusy("Preparing tomorrow's paper");
      const tomorrow = new Date(Date.now() + 5 * 3600_000 + 86400_000).toISOString().slice(0, 10);
      const ed = await api.post<Edition>("/api/editions/generate", { date: tomorrow, force: true });
      router.push(`/paper/${ed.edition_date}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  }

  async function deleteAccount() {
    setBusy("delete");
    try {
      await api.del("/api/me");
      await signOut();
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  }

  if (!me) {
    return (
      <div className="min-h-screen bg-parchment">
        <TopBar />
        <main className="mx-auto max-w-[980px] px-4 py-16">{error ? <ErrorNote error={error} /> : <Spinner label="Loading" />}</main>
      </div>
    );
  }

  const weights = me.profile?.topics ?? {};
  const entities = me.profile?.entities ?? [];
  const latest = me.snapshots.find((s) => s.changes.some((c) => c.topic));
  const displayName = form.name || me.user.email || "Reader";
  const since = new Date(me.user.created_at).toLocaleDateString("en-GB", { month: "long", year: "numeric" });

  return (
    <div ref={root} className="min-h-screen bg-parchment">
      <TopBar />
      <main className="mx-auto max-w-[980px] px-4 py-12 sm:py-16">
        <div className="dash-head flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex items-center gap-4">
            <span className="flex h-16 w-16 items-center justify-center rounded-full bg-ink text-[28px] font-semibold text-white">
              {displayName.charAt(0).toUpperCase()}
            </span>
            <div>
              <h1 className="t-section">{displayName}</h1>
              <p className="t-caption text-ink-60">{me.user.persona ? "Sample reader" : isDemo ? "Demo reader" : `${me.user.email} · Reading since ${since}`}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/paper" className="btn btn-primary">Today&apos;s paper</Link>
            <Link href="/archive" className="btn btn-secondary">Past papers</Link>
          </div>
        </div>

        <div className="sticky top-11 z-30 mt-6 min-h-12 py-2" aria-live="polite">
          {saved && <p className="inline-block rounded-full bg-ink px-4 py-1.5 t-caption text-white">✓ {saved}</p>}
          <ErrorNote error={error} />
        </div>

        <div className="mt-2 grid gap-5">
          {me.user.persona && (
            <div className="flex flex-col gap-3 rounded-[18px] bg-[#e8f1fb] p-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="t-body text-ink">This is {me.user.name}&apos;s sample dashboard. It shows what you can change, but it&apos;s locked so every visitor sees the same sample.</p>
              <Link href="/demo" className="btn btn-primary flex-none">Set up your own paper</Link>
            </div>
          )}

          <PaperStatus welcome={welcome} name={form.name || "there"} />

          {/* Sample readers are shared by every visitor, so their settings are locked. */}
          <fieldset disabled={me.user.persona} className="contents">
          <Section title="Profile" note="Changes apply from your next paper.">
            <form onSubmit={saveProfile}>
              <Row label="Name">
                <input className="input" value={form.name} maxLength={60} placeholder="Your name"
                  onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </Row>
              <Row label="City">
                <input className="input" value={form.city} maxLength={60} required minLength={2}
                  onChange={(e) => setForm({ ...form, city: e.target.value })} />
              </Row>
              <Row label="Reading time">
                <div className="grid grid-cols-4 gap-1 rounded-[12px] bg-parchment p-1" role="radiogroup" aria-label="Reading time">
                  {MINUTES.map((m) => (
                    <button key={m} type="button" role="radio" aria-checked={form.reading_minutes === m}
                      className={`rounded-[9px] py-2 t-caption ${form.reading_minutes === m ? "bg-canvas font-semibold shadow-sm" : "text-ink-60"}`}
                      onClick={() => setForm({ ...form, reading_minutes: m })}>{m} min</button>
                  ))}
                </div>
              </Row>
              <Row label="Pakistan and world news">
                <div>
                  <input type="range" min={0} max={100} step={10} className="w-full accent-[#0066cc]" aria-label="Share of Pakistan news"
                    value={Math.round(form.region_mix * 100)} onChange={(e) => setForm({ ...form, region_mix: Number(e.target.value) / 100 })} />
                  <div className="flex justify-between t-fine text-ink-60">
                    <span>Pakistan {Math.round(form.region_mix * 100)}%</span><span>World {100 - Math.round(form.region_mix * 100)}%</span>
                  </div>
                </div>
              </Row>
              <div className="mt-4 flex justify-end">
                <button className="btn btn-primary" disabled={!dirty || busy === "profile"}>
                  {busy === "profile" ? <Spinner dark label="Saving" /> : "Save changes"}
                </button>
              </div>
            </form>
          </Section>

          <Section title="Topics" note="Turn a topic off and it won't be picked for you. The bar shows how much ParhLo thinks you like it.">
            <ul className="grid gap-x-10 sm:grid-cols-2">
              {Object.keys(TOPIC_LABELS).map((slug) => {
                const w = weights[slug] ?? 0;
                const on = w >= ON;
                return (
                  <li key={slug} className="flex items-center gap-4 border-t border-divider py-3">
                    <div className="min-w-0 flex-1">
                      <p className="t-body">{topicLabel(slug)}</p>
                      <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-parchment">
                        <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${Math.round(w * 100)}%`, opacity: on ? 1 : 0.3 }} />
                      </div>
                    </div>
                    <button type="button" role="switch" aria-checked={on} aria-label={topicLabel(slug)} className="switch"
                      disabled={pendingTopic === slug} onClick={() => toggleTopic(slug, !on)} />
                  </li>
                );
              })}
            </ul>
          </Section>

          <div className="grid gap-5 lg:grid-cols-2">
            <Section title="Following" note="People, teams, companies or places. Stories about them get priority.">
              <div className="flex flex-wrap gap-2">
                {entities.map((e) => (
                  <span key={e} className="inline-flex items-center gap-2 rounded-full bg-parchment px-3.5 py-1.5 t-caption">
                    {e}
                    <button aria-label={`Unfollow ${e}`} className="text-ink-48 hover:text-ink"
                      onClick={() => run("unfollow", () => api.del<Me>(`/api/me/following?name=${encodeURIComponent(e)}`), `Unfollowed ${e}`)}>✕</button>
                  </span>
                ))}
                {!entities.length && <p className="t-body text-ink-60">You aren&apos;t following anything yet.</p>}
              </div>
              <form onSubmit={addFollow} className="mt-5 flex gap-2">
                <input className="input flex-1" value={newFollow} maxLength={60} placeholder="e.g. Babar Azam, Nvidia, Karachi"
                  onChange={(e) => setNewFollow(e.target.value)} />
                <button className="btn btn-primary" disabled={!newFollow.trim() || busy === "follow"}>
                  {busy === "follow" ? <Spinner dark /> : "Follow"}
                </button>
              </form>
            </Section>

            <Section title="About you" note="Describe your interests in your own words. ParhLo reads this to find what you follow.">
              <textarea className="input !h-32 resize-none !py-3 !text-[15px]" value={about} maxLength={500}
                placeholder="I work in fintech in Lahore and follow cricket, startups and anything about AI."
                onChange={(e) => setAbout(e.target.value)} />
              <div className="mt-3 flex items-center justify-between">
                <span className="t-fine text-ink-48">{about.length}/500</span>
                <button className="btn btn-primary" disabled={about === (me.profile?.about ?? "") || busy === "about"}
                  onClick={() => run("about", () => api.patch<Me>("/api/me", { about }), "Saved. Your interests were updated.")}>
                  {busy === "about" ? <Spinner dark label="Reading it" /> : "Save"}
                </button>
              </div>
            </Section>
          </div>

          <FriendsPanel isDemo={isDemo} onChanged={flash} />

          <SavedStories />

          <Section id="memory" title="What ParhLo remembers" note="Each story is matched against these. Remove anything you don't want.">
            <div className="flex flex-wrap gap-2">
              {me.anchors.map((a) => (
                <span key={a.id} className={`inline-flex max-w-[360px] items-center gap-2 rounded-full px-3.5 py-1.5 t-caption ${a.weight < 0 ? "bg-[#fff2f2] text-danger" : "bg-parchment"}`}>
                  <span className="text-ink-48">{KIND_LABEL[a.kind] ?? a.kind}</span>
                  <span className="truncate">{a.label}</span>
                  <button aria-label={`Remove ${a.label}`} className="text-ink-48 hover:text-ink" onClick={() => removeAnchor(a.id)}>✕</button>
                </span>
              ))}
              {!me.anchors.length && <p className="t-body text-ink-60">Nothing yet.</p>}
            </div>

            <h3 className="mt-8 t-body font-semibold">Recent changes</h3>
            {latest ? (
              <ul className="mt-3 space-y-3">
                {latest.changes.filter((c) => c.topic).map((c) => {
                  const up = (c.to ?? 0) > (c.from ?? 0);
                  return (
                    <li key={c.topic} className="flex gap-3">
                      <span className={`mt-0.5 ${up ? "text-primary" : "text-danger"}`}>{up ? "▲" : "▼"}</span>
                      <div>
                        <p className="t-body">{c.label}: {Math.round((c.from ?? 0) * 100)} → {Math.round((c.to ?? 0) * 100)}</p>
                        <p className="t-caption text-ink-60">{c.why}.</p>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : <p className="mt-2 t-body text-ink-60">Read today&apos;s paper, then update below to see what changes.</p>}

            <div className="mt-6 flex flex-wrap items-center gap-4 border-t border-divider pt-6">
              <button className="btn btn-secondary" onClick={learnAndReprint} disabled={!!busy}>
                {busy?.startsWith("Updating") || busy?.startsWith("Preparing") ? <Spinner label={busy} /> : "Update now and see tomorrow's paper"}
              </button>
              <span className="t-caption text-ink-60">This happens automatically every night.</span>
            </div>
          </Section>

          </fieldset>

          <Section title="Account">
            {isDemo ? (
              <div className="flex flex-wrap items-center justify-between gap-4">
                <p className="t-body text-ink-60">You&apos;re using a demo reader. Create an account to keep your own paper.</p>
                <div className="flex gap-3">
                  <Link href="/sign-in" className="btn btn-primary">Create an account</Link>
                  <button className="btn btn-light" onClick={() => signOut()}>Exit demo</button>
                </div>
              </div>
            ) : (
              <>
                <Row label="Email"><p className="t-body text-ink-60 sm:text-right">{me.user.email}</p></Row>
                <Row label="Sign-in method"><p className="t-body text-ink-60 sm:text-right">{me.user.google ? "Google" : "Email code"}</p></Row>
                <Row label="Your data">
                  <p className="t-body sm:text-right"><Link href="/privacy" className="link">How ParhLo uses your data ›</Link></p>
                </Row>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-4 border-t border-divider pt-6">
                  <button className="btn btn-light" onClick={() => signOut()}>Sign out</button>
                  {confirmDelete ? (
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="t-caption text-danger">This deletes your profile, interests and papers. It can&apos;t be undone.</span>
                      <button className="btn btn-light" onClick={() => setConfirmDelete(false)}>Cancel</button>
                      <button className="btn !bg-danger text-white" onClick={deleteAccount} disabled={busy === "delete"}>
                        {busy === "delete" ? <Spinner dark label="Deleting" /> : "Delete my account"}
                      </button>
                    </div>
                  ) : (
                    <button className="t-body text-danger hover:underline" onClick={() => setConfirmDelete(true)}>Delete account…</button>
                  )}
                </div>
              </>
            )}
          </Section>
        </div>
      </main>
    </div>
  );
}
