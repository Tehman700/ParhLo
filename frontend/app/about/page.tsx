import type { Metadata } from "next";
import Link from "next/link";
import { CONTACT_EMAIL, DocPage } from "@/components/DocPage";

export const metadata: Metadata = { title: "About · ParhLo" };

export default function About() {
  return (
    <DocPage title="About ParhLo" lead="One short newspaper every morning, made for one reader.">
      <h2>Why we made it</h2>
      <p>Most news apps never end. There is always another headline, and the stories you actually care about get lost between the ones you don&apos;t. A printed newspaper had a better idea: a fixed number of pages, put together with care, that you could finish.</p>
      <p>ParhLo brings that back, for one reader at a time. Each night it reads the news from trusted sources in Pakistan and around the world, picks what matters to you, and lays it out as a short paper you can read on the web or download as a PDF.</p>

      <h2>What makes it different</h2>
      <ul>
        <li><strong>It ends.</strong> Your paper is sized to the reading time you choose.</li>
        <li><strong>It explains itself.</strong> Every story says why it&apos;s in your paper.</li>
        <li><strong>It checks its summaries.</strong> Each one is compared with the original article, and you can always read the source.</li>
        <li><strong>It doesn&apos;t trap you.</strong> A few stories each day are outside your usual interests, and the two biggest stories of the day are always included.</li>
        <li><strong>It learns quietly, and openly.</strong> What you read changes your paper, and you can see and edit everything it has learned.</li>
      </ul>

      <h2>The name</h2>
      <p>&ldquo;Parh lo&rdquo; means &ldquo;go on, read it&rdquo; in Urdu.</p>

      <h2>Contact</h2>
      <p>We&apos;d love to hear from you: <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. Curious how it works? Read <Link href="/how-it-works">How it works</Link>.</p>
    </DocPage>
  );
}
