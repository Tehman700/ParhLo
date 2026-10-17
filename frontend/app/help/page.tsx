import type { Metadata } from "next";
import { HelpCenter } from "@/components/HelpCenter";

export const metadata: Metadata = { title: "Help & contact · ParhLo", description: "Answers to common questions, or send the ParhLo team a message." };

export default function HelpPage() {
  return <HelpCenter />;
}
