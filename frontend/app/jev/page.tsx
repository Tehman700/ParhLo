import type { Metadata } from "next";
import { JevExplainer } from "@/components/JevExplainer";

export const metadata: Metadata = {
  title: "How ParhLo uses Jev · ParhLo",
  description: "Jev, a decision model from TypeSafe, sorts, filters, ranks and fact-checks every story in your paper.",
};

export default function JevPage() {
  return <JevExplainer />;
}
