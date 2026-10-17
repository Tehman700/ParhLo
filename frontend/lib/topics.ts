export const TOPIC_LABELS: Record<string, string> = {
  pakistan: "Pakistan", politics: "Politics", world: "World", business: "Business", economy: "Economy",
  technology: "Technology", ai: "AI", startups: "Startups", science: "Science", health: "Health",
  climate: "Climate", cricket: "Cricket", football: "Football", motorsport: "Formula 1",
  entertainment: "Entertainment", culture: "Culture", education: "Education",
};

export const topicLabel = (slug?: string) => (slug ? TOPIC_LABELS[slug] ?? slug : "News");

export function timeAgo(iso: string | null) {
  if (!iso) return "";
  const h = Math.round((Date.now() - new Date(iso).getTime()) / 3_600_000);
  if (h < 1) return "just now";
  if (h < 24) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}
