import type { Metadata } from "next";
import Link from "next/link";
import { DocPage } from "@/components/DocPage";
import { HowItWorksFlow } from "@/components/HowItWorksFlow";

export const metadata: Metadata = { title: "How it works · ParhLo" };

export default function HowItWorks() {
  return (
    <DocPage title="How it works" lead="What happens between the news being published and your paper arriving." hero={<HowItWorksFlow />}>
      <h2>1. You tell us what you like</h2>
      <p>When you sign up, you pick topics, follow people, teams or companies, and swipe through a few real headlines. You can also describe your interests in your own words. This takes about a minute.</p>

      <h2>2. We read the news every night</h2>
      <p>ParhLo collects new stories from Pakistani and international outlets, including Dawn, Express Tribune, Geo News, Business Recorder, BBC, The Guardian, The New York Times, and specialist sources for technology and sport such as The Verge, TechCrunch and ESPNcricinfo. AI then:</p>
      <ul>
        <li>sorts each story into a topic,</li>
        <li>filters out quizzes, listings and other things that aren&apos;t news,</li>
        <li>rates how important it is,</li>
        <li>and groups stories about the same event, so you see it once.</li>
      </ul>

      <h2>3. We choose your stories</h2>
      <p>Every story is compared with your interests. Your paper is then built from three kinds of story:</p>
      <ul>
        <li><strong>Top stories:</strong> the two most important stories of the day, for everyone.</li>
        <li><strong>Your picks:</strong> stories that match what you follow and read.</li>
        <li><strong>Something new:</strong> a few stories outside your usual interests, so your paper doesn&apos;t get narrower over time.</li>
      </ul>
      <p>The number of stories depends on the reading time you set.</p>

      <h2>4. We write and check the summaries</h2>
      <p>Each story gets a short summary and key points, written from the original article. A second check then compares the summary with the article and flags anything it can&apos;t support. Checked summaries show a ✓. Every story links to the original.</p>

      <h2>5. Your paper is laid out</h2>
      <p>An AI editor orders the stories, writes the headlines and the line that says why each story is there. Your paper is ready on the web each morning, with a PDF version and a morning box with weather, air quality and exchange rates for your city.</p>

      <h2>6. It learns from you</h2>
      <p>Opening, reading, liking or skipping a story is a signal. Each night these signals update your interests. What you chose at sign-up slowly gives way to what you actually read. You can see every change, and remove anything, on your <Link href="/dashboard">dashboard</Link>.</p>

      <h2>7. Friends, if you want</h2>
      <p>Invite friends with your personal link. If you both turn on <strong>Learn from friends</strong>, up to two stories they liked can appear in your paper, labelled with their name, and your interests drift slightly toward theirs. Turn it off at any time. It stops from then on, and what your paper has already learned stays.</p>
      <p>Want to see one first? <Link href="/demo">Try the demo</Link>.</p>
    </DocPage>
  );
}
