// Backend calls. In production the backend is the same origin (/api/* → FastAPI service);
// locally set NEXT_PUBLIC_API_URL=http://localhost:8000 in frontend/.env.local.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

export type Headers = Record<string, string>;

export async function request<T>(path: string, init: RequestInit & { json?: unknown; headers?: Headers } = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...rest,
      headers: { ...(json !== undefined ? { "Content-Type": "application/json" } : {}), ...headers },
      body: json !== undefined ? JSON.stringify(json) : rest.body,
    });
  } catch {
    throw new ApiError("Can't reach ParhLo's server. Check your connection.", 0);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {}
    throw new ApiError(detail || `Request failed (${res.status})`, res.status);
  }
  return res.json() as Promise<T>;
}

// ---------- types (mirror backend/app/parhlo) ----------

export type Topic = { slug: string; label: string; group: string; desc: string };
export type Headline = { id: number; title: string; source: string; image_url: string | null; topics: string[] };

export type Story = {
  id: number;
  headline: string;
  title: string;
  source: string;
  url: string;
  image: string | null;
  published_at: string | null;
  topics: string[];
  summary: string;
  points: string[];
  verified: boolean | null;
  grounded_in: string | null;
  why: string | null;
  discovery: boolean;
  also_reported_by: string[];
  region: "pakistan" | "global";
};

export type QuizQuestion = { question: string; options: string[]; answer: number; story_id: number };

export type Morning = {
  city: string;
  weather: { temp: number; condition: string; humidity: number; high: number; low: number; rain_chance: number } | null;
  air: { aqi: number | null; pm2_5: number | null; label: string; level: number; advice: string | null } | null;
  rates: { pkr: Record<string, number>; updated: string } | null;
  cricket: { id: number; title: string; source: string; url: string } | null;
  smog_alert: boolean;
};

export type Edition = {
  id: number;
  edition_date: string;
  number: number;
  pdf_key: string | null;
  audio_key: string | null;
  date: string;
  reader: { name: string; city: string };
  editor_note: string;
  morning: Morning;
  lead_id: number;
  sections: { name: string; story_ids: number[] }[];
  three_things: { text: string; story_id: number }[];
  quiz: QuizQuestion[];
  recall_quiz: QuizQuestion[];
  stories: Story[];
  generated_at: string;
};

export type EditionSummary = {
  id: number;
  edition_date: string;
  number: number;
  editor_note: string;
  stories: number;
  lead_headline: string | null;
};

export type Snapshot = {
  taken_at: string;
  topics: Record<string, number>;
  changes: { topic?: string; label?: string; from?: number; to?: number; why: string; topics?: string[] }[];
};

export type Me = {
  user: { id: string; name: string; email: string | null; city: string; reading_minutes: number; region_mix: number; onboarded: boolean; is_demo: boolean };
  profile: { topics: Record<string, number>; entities: string[]; about: string | null; source_affinity: Record<string, number> } | null;
  anchors: { id: number; label: string; kind: string; weight: number; created_at: string }[];
  snapshots: Snapshot[];
};

export type EventType = "open" | "dwell" | "like" | "dislike" | "skip" | "save" | "quiz_correct" | "quiz_wrong" | "pdf" | "listen" | "ask";
