import type { Metadata } from "next";
import Link from "next/link";
import { CONTACT_EMAIL, DocPage } from "@/components/DocPage";

export const metadata: Metadata = { title: "Terms of Use · ParhLo" };

export default function Terms() {
  return (
    <DocPage title="Terms of Use" updated="17 October 2026"
      lead="The short version: ParhLo is free, it summarizes other people's reporting, and it can make mistakes, so always check the original for anything important.">
      <h2>Using ParhLo</h2>
      <p>By creating an account or using the demo, you agree to these terms. You need to be at least 13 years old. Please keep your email account secure, because that is how you sign in.</p>

      <h2>The news in your paper</h2>
      <p>ParhLo collects headlines from public news sources and uses AI to write short summaries of them. Each summary is checked against the article it came from, and every story links to the original.</p>
      <ul>
        <li><strong>Summaries can be wrong.</strong> AI can miss context or get details wrong, even after checking. Don&apos;t rely on ParhLo alone for decisions about health, money, law or safety.</li>
        <li><strong>The reporting belongs to its publishers.</strong> ParhLo shows short summaries and sends you to the source to read the full story. We are not affiliated with the publishers we link to.</li>
        <li><strong>Your paper is personal.</strong> Stories are chosen to match your interests, with a few picked to widen them. The selection is not an endorsement of any view.</li>
      </ul>

      <h2>Acceptable use</h2>
      <p>Please don&apos;t try to break, overload or scrape the service, access other people&apos;s accounts, or use ParhLo to republish summaries at scale.</p>

      <h2>Your content</h2>
      <p>What you write in &ldquo;About you&rdquo; and the things you follow stay yours. You let us use them only to build your paper. See the <Link href="/privacy">Privacy Policy</Link> for details.</p>

      <h2>Availability</h2>
      <p>We try to have your paper ready every morning, but ParhLo is provided as it is, without guarantees. We may change or stop features, and we&apos;ll tell you before anything that affects your account.</p>

      <h2>Ending your account</h2>
      <p>You can delete your account at any time from your <Link href="/dashboard">dashboard</Link>. We may suspend accounts that break these terms.</p>

      <h2>Liability</h2>
      <p>To the extent the law allows, ParhLo isn&apos;t liable for losses that come from relying on a summary, or from the service being unavailable.</p>

      <h2>Contact</h2>
      <p>Questions about these terms: <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.</p>
    </DocPage>
  );
}
