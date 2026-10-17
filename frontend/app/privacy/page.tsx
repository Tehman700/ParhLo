import type { Metadata } from "next";
import Link from "next/link";
import { PolicyPage, PolicyTable, type PolicySection } from "@/components/PolicyPage";
import { CONTACT_EMAIL } from "@/lib/site";

export const metadata: Metadata = { title: "Privacy Policy · ParhLo", description: "What ParhLo keeps to build your paper, who processes it, and how to remove it." };

const GLANCE = [
  { icon: "🗞️", title: "Only what builds your paper", text: "Your interests and what you read, so tomorrow's paper fits you better." },
  { icon: "👀", title: "You can see all of it", text: "Your dashboard shows everything ParhLo remembers, and you can remove any of it." },
  { icon: "🚫", title: "Never sold, no ad trackers", text: "We don't sell your data or share it with advertisers." },
  { icon: "🗑️", title: "Delete in one step", text: "Deleting your account removes your profile, interests, reading history and papers at once." },
];

const SECTIONS: PolicySection[] = [
  {
    id: "collect", title: "What we collect", body: (
      <>
        <h3>Your account</h3>
        <ul>
          <li><strong>Email address</strong>, to sign you in and send your paper. With &ldquo;Continue with Google&rdquo; we also receive your name and Google account ID. We never see your Google password.</li>
          <li><strong>Sign-in codes</strong>, stored only as a one-way hash; they expire after 10 minutes.</li>
        </ul>
        <h3>What you tell us</h3>
        <ul>
          <li>Your name, city, reading time, and your Pakistan/world mix.</li>
          <li>Topics you switch on or off, the people, teams and companies you follow, and what you write in &ldquo;About you&rdquo;.</li>
        </ul>
        <h3>How you read</h3>
        <ul>
          <li>Stories you open, how long you read them, and what you like, dislike, save, skip or ask about.</li>
          <li>Whether you download the PDF.</li>
        </ul>
        <h3>What you search and ask</h3>
        <ul>
          <li><strong>Search:</strong> your search words are used to find stories and are not stored on our servers. Your recent searches are kept only in your browser. Opening a result counts as reading it.</li>
          <li><strong>Ask your paper:</strong> your question is used to answer it from your paper. We keep that you asked about a story, as a reading signal, but not the conversation.</li>
        </ul>
        <h3>Friends</h3>
        <ul><li>Who you invited and who accepted, so we can show your friends list and notify you.</li></ul>
        <h3>Messages you send us</h3>
        <ul><li>Your name, email, the topic and your message from <Link href="/help">Help &amp; contact</Link>, so we can reply.</li></ul>
        <p>We don&apos;t use advertising trackers and we don&apos;t track your location. Your city is only used for the weather and air quality in your paper.</p>
      </>
    ),
  },
  {
    id: "use", title: "How we use it", body: (
      <ul>
        <li><strong>To choose your stories</strong> and explain why each one is in your paper.</li>
        <li><strong>To learn your interests over time.</strong> Every night your reading updates your interests; your dashboard shows each change.</li>
        <li><strong>To update your paper straight away</strong> when you change your interests. Today&apos;s paper is reprinted within seconds, then polished in the background.</li>
        <li><strong>To email you</strong> sign-in codes and, unless you turn it off, your paper every morning.</li>
        <li><strong>To answer</strong> your questions in Ask your paper and your Help &amp; contact messages.</li>
        <li><strong>Friends (only if you turn it on):</strong> with &ldquo;Learn from friends&rdquo; on, stories you liked or saved in the last few days can appear in your friends&apos; papers with your name, for friends who also turned it on. Nothing else about your reading is shown to them. It&apos;s off by default.</li>
      </ul>
    ),
  },
  {
    id: "processors", title: "Services that process data for us", body: (
      <>
        <p>ParhLo runs on a few providers. They process data only to provide their service to us.</p>
        <PolicyTable head={["Service", "What it does", "What it receives"]} rows={[
          ["Vercel", "Hosts the website and app", "Your requests to ParhLo"],
          ["Neon", "Our database", "Your account, interests and reading activity"],
          ["OpenAI", "Writes summaries, lays out papers, answers questions, understands searches", "Article text; your questions and search words; a short description of your interests. Never your email address"],
          ["TypeSafe (Jev)", "Sorts stories, checks summaries, finds the story a question is about", "Article text and your questions"],
          ["n8n", "Schedules your paper update when your interests change", "Only your reader ID and the time of the change, in a signed message"],
          ["Google", "“Continue with Google” and sending email", "Your email address and name at sign-in; the emails we send you"],
          ["Amazon Web Services", "Backup email delivery and file storage", "Your email address and the emails we send you"],
          ["Open-Meteo, open.er-api.com", "Weather, air quality and exchange rates", "Only your city"],
        ]} />
      </>
    ),
  },
  {
    id: "cookies", title: "Cookies and your browser", body: (
      <p>We use <strong>one cookie</strong>, <code>parhlo_session</code>, to keep you signed in for up to 30 days. It can&apos;t be read by scripts on the page. Your browser&apos;s local storage holds a demo reader ID (if you try the demo), an invite you opened before signing in, and your recent searches. These stay on your device.</p>
    ),
  },
  {
    id: "keep", title: "How long we keep it", body: (
      <ul>
        <li>Your account, interests, reading history and past papers: for as long as you have an account.</li>
        <li>Demo readers you create without an account are deleted automatically after 3 days.</li>
        <li>Messages you send us are kept so we can follow up. Ask us and we&apos;ll delete them.</li>
        <li>When you delete your account, everything linked to it is deleted straight away.</li>
      </ul>
    ),
  },
  {
    id: "choices", title: "Your choices", body: (
      <ul>
        <li><strong>See and edit</strong> your interests and everything ParhLo remembers on your <Link href="/dashboard">dashboard</Link>, and remove anything, including any saved story or friend.</li>
        <li><strong>Turn off the morning email</strong> on your dashboard or with the one-click unsubscribe link in any email.</li>
        <li><strong>Turn off Learn from friends</strong> to stop sharing your likes with friends and stop theirs shaping your paper.</li>
        <li><strong>Delete your account</strong> from the dashboard at any time. This can&apos;t be undone.</li>
        <li><strong>Ask for a copy</strong> of your data, or anything else, through <Link href="/help">Help &amp; contact</Link> or at <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.</li>
      </ul>
    ),
  },
  {
    id: "security", title: "Security", body: (
      <p>All traffic is encrypted (HTTPS). Sign-in codes are hashed, limited to 5 attempts and expire quickly. Session cookies are signed, secure and HTTP-only. Links in emails (like unsubscribe) and messages to n8n are signed so they can&apos;t be forged.</p>
    ),
  },
  {
    id: "children", title: "Children", body: <p>ParhLo is not intended for children under 13, and we don&apos;t knowingly collect their data.</p>,
  },
  {
    id: "changes", title: "Changes and contact", body: (
      <p>If we change this policy in a way that matters, we&apos;ll update the date at the top and tell you in the app before it takes effect. Questions? Use <Link href="/help">Help &amp; contact</Link> or email <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.</p>
    ),
  },
];

export default function Privacy() {
  return (
    <PolicyPage title="Privacy Policy" updated="17 October 2026" glance={GLANCE} sections={SECTIONS}
      lead="ParhLo builds a newspaper around what you read. This page explains what we keep to do that, who helps us, and how to remove it." />
  );
}
