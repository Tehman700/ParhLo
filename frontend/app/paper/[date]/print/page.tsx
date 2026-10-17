"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ErrorNote, Spinner, TopBar } from "@/components/ui";
import { API_URL, type Edition } from "@/lib/api";
import { useApi, useSession } from "@/lib/auth";
import { buildPrintHtml } from "@/lib/printHtml";

/** Print preview (same template as the PDF) + one-click download of the server-rendered PDF. */
export default function PrintPage() {
  const { date } = useParams<{ date: string }>();
  const api = useApi();
  const { ready, headers } = useSession();
  const [edition, setEdition] = useState<Edition | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    api.get<Edition>(`/api/editions/${date}`).then((e) => !cancelled && setEdition(e)).catch((e) => !cancelled && setError(e.message));
    return () => { cancelled = true; };
  }, [ready, api, date]);

  const html = useMemo(() => (edition ? buildPrintHtml(edition) : ""), [edition]);

  async function download() {
    setBusy(true);
    setError(null);
    try {
      const h = await headers();
      const res = await fetch(`/pdf/${date}`, { headers: h, credentials: "include" });
      if (!res.ok) throw new Error(`PDF failed (${res.status})`);
      const url = URL.createObjectURL(await res.blob());
      const a = Object.assign(document.createElement("a"), { href: url, download: `ParhLo-${date}.pdf` });
      a.click();
      URL.revokeObjectURL(url);
      void fetch(`${API_URL}/api/events`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", ...h },
        body: JSON.stringify([{ type: "pdf", edition_id: edition?.id }]) });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen">
      <TopBar right={
        <button className="btn btn-primary !px-4 !py-2 !text-[14px]" onClick={download} disabled={!edition || busy}>
          {busy ? <Spinner dark label="Printing PDF…" /> : "⬇ Download PDF"}
        </button>
      } />
      <main className="mx-auto max-w-[900px] px-4 py-8">
        <ErrorNote error={error} />
        {!edition && !error && <Spinner label="Loading your edition…" />}
        {edition && (
          <iframe title="Print preview" srcDoc={html}
            className="mt-4 h-[1200px] w-full rounded-[6px] border border-rule bg-newsprint shadow-[0_20px_60px_-25px_rgba(0,0,0,.4)]" />
        )}
      </main>
    </div>
  );
}
