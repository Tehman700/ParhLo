import type { Metadata } from "next";
import Link from "next/link";
import { CONTACT_EMAIL, DocPage } from "@/components/DocPage";

export const metadata: Metadata = { title: "Privacy Policy · ParhLo" };

export default function Privacy() {
  return (
    <DocPage title="Privacy Policy" updated="17 October 2026"
      lead="ParhLo builds a newspaper around what you read. This page explains exactly what we keep to do that, and how to remove it.">
      <h2>What we collect</h2>
      <h3>Your account</h3>
      <ul>
        <li><strong>Email address</strong>, used to sign you in. If you continue with Google, we also receive your name and Google account ID. We never see your Google password.</li>
        <li><strong>Sign-in codes</strong>, stored only as a one-way hash, which expires after 10 minutes.</li>
      </ul>
      <h3>What you tell us</h3>
      <ul>
        <li>Your name, city, reading time, and how much Pakistan and world news you want.</li>
        <li>The topics you choose, the people, teams and companies you follow, and anything you write in &ldquo;About you&rdquo;.</li>
      </ul>
      <h3>How you read</h3>
      <ul>
        <li>Which stories you open, how long you spend on them, and which ones you like, skip or ask for less of.</li>
        <li>Whether you download the PDF or listen to a story.</li>
      </ul>
      <h3>Friends</h3>
      <ul>
        <li>Who you invited and who accepted, so we can show your friends list and notify you.</li>
        <li>If you turn on <strong>Learn from friends</strong>, stories you liked or saved in the last few days can appear in your friends&apos; papers with your name (&ldquo;Ali liked this&rdquo;), but only for friends who also turned it on. Nothing else about your reading is shown to them. It is off by default.</li>
      </ul>
      <p>We don&apos;t use advertising trackers and we don&apos;t record your location. Your city is only used for the weather and air quality in the morning box.</p>

      <h2>How we use it</h2>
      <ul>
        <li>To choose and order the stories in your paper, and to explain why each one is there.</li>
        <li>To learn your interests over time. Each night your reading is turned into updated topic weights, which you can see and change on your <Link href="/dashboard">dashboard</Link>.</li>
        <li>To send your sign-in codes and, if you ask for it, your morning paper by email.</li>
      </ul>
      <p>We don&apos;t sell your data, share it with advertisers, or use it to build profiles for anyone else.</p>

      <h2>Services we use</h2>
      <p>ParhLo runs on a small number of providers, who process data only to provide their service to us:</p>
      <ul>
        <li><strong>Vercel</strong>, which hosts the website and app.</li>
        <li><strong>Neon</strong>, which hosts our database.</li>
        <li><strong>Amazon Web Services</strong>, for email delivery, audio and file storage.</li>
        <li><strong>Google</strong>, for &ldquo;Continue with Google&rdquo; and for sending email.</li>
        <li><strong>OpenAI</strong> and <strong>TypeSafe</strong>, which classify and summarize news articles. What we send them is article text and, when building your paper, a short description of your interests. Your email address is never sent.</li>
        <li><strong>Open-Meteo</strong>, for weather. Only your city is sent.</li>
      </ul>

      <h2>Cookies</h2>
      <p>We use one cookie, <code>parhlo_session</code>, to keep you signed in for up to 30 days. It can&apos;t be read by scripts on the page. If you try the demo, a demo reader ID is kept in your browser&apos;s local storage until you exit the demo.</p>

      <h2>How long we keep it</h2>
      <p>We keep your account and reading history for as long as you have an account. Past papers stay in your archive so you can go back to them. When you delete your account, everything is deleted straight away: your profile, interests, reading history and papers.</p>

      <h2>Your choices</h2>
      <ul>
        <li><strong>See and edit</strong> your interests, topics and everything ParhLo remembers on your <Link href="/dashboard">dashboard</Link>.</li>
        <li><strong>Remove</strong> any single thing ParhLo remembers about you, any saved story, or any friend.</li>
        <li><strong>Turn off Learn from friends</strong> to stop sharing your likes with friends and stop their likes shaping your paper.</li>
        <li><strong>Delete your account</strong> at any time from the dashboard. This can&apos;t be undone.</li>
        <li><strong>Ask us</strong> for a copy of your data, or anything else, at <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.</li>
      </ul>

      <h2>Security</h2>
      <p>All traffic is encrypted with HTTPS. Sign-in codes are hashed, limited to 5 attempts and expire quickly. Session cookies are signed, secure and HTTP-only.</p>

      <h2>Children</h2>
      <p>ParhLo is not intended for children under 13, and we don&apos;t knowingly collect their data.</p>

      <h2>Changes</h2>
      <p>If we change this policy in a way that matters, we&apos;ll update the date at the top and tell you in the app before it takes effect.</p>
    </DocPage>
  );
}
