"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { Edition } from "@/lib/api";
import { useApi, useSession } from "@/lib/auth";
import { ErrorNote, TopBar } from "../ui";
import { PaperView } from "./PaperView";
import { PrintingPress } from "./PrintingPress";

/** Loads (or prints) an edition and shows it. date = undefined → today's paper. */
export function EditionScreen({ date }: { date?: string }) {
  const router = useRouter();
  const api = useApi();
  const { ready, signedIn } = useSession();
  const [edition, setEdition] = useState<Edition | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!ready) return;
    if (!signedIn) return void router.replace("/");
    let cancelled = false;
    const fetchEdition = date ? api.get<Edition>(`/api/editions/${date}`) : api.post<Edition>("/api/editions/generate", {});
    fetchEdition
      .then((e) => !cancelled && setEdition(e))
      .catch((e: Error & { status?: number }) => {
        if (cancelled) return;
        if (e.status === 409) router.replace("/onboarding");
        else setError(e.message);
      });
    return () => { cancelled = true; };
  }, [ready, signedIn, api, date, router, attempt]);

  if (error) return (<><TopBar /><main className="mx-auto max-w-xl p-10"><ErrorNote error={error} onRetry={() => { setError(null); setAttempt((a) => a + 1); }} /></main></>);
  if (!edition) return <PrintingPress />;

  return (
    <>
      <TopBar right={<Link href={`/paper/${edition.edition_date}/print`} className="btn btn-primary btn-sm !py-1 !text-[12px]">Download PDF</Link>} />
      {edition.read_only && (
        <div className="border-b border-[#d6e6f8] bg-[#e8f1fb]">
          <div className="mx-auto flex max-w-[1024px] flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2.5 t-caption">
            <span className="text-ink">You&apos;re reading {edition.reader.name}&apos;s sample paper. Likes and saves aren&apos;t kept.</span>
            <Link href="/demo" className="link">Read another sample</Link>
            <Link href="/sign-in" className="link font-semibold">Make your own paper ›</Link>
          </div>
        </div>
      )}
      <PaperView edition={edition} actions={
        <>
          <Link href={`/paper/${edition.edition_date}/print`} className="btn btn-primary">Download PDF</Link>
          <Link href="/archive" className="btn btn-secondary">Past papers</Link>
        </>
      } />
    </>
  );
}
