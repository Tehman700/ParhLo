// Every backend call goes through here. Change NEXT_PUBLIC_API_URL in frontend/.env.local if needed.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function handle<T>(res: Response): Promise<T> {
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

export async function api<T = unknown>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init ?? {};
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...rest,
      headers: json !== undefined ? { "Content-Type": "application/json", ...rest.headers } : rest.headers,
      body: json !== undefined ? JSON.stringify(json) : rest.body,
    });
  } catch {
    throw new ApiError(`Cannot reach the backend at ${API_URL}. Is it running?`, 0);
  }
  return handle<T>(res);
}

export const get = <T,>(path: string) => api<T>(path);
export const post = <T,>(path: string, json: unknown) => api<T>(path, { method: "POST", json });
export const del = <T,>(path: string) => api<T>(path, { method: "DELETE" });

export async function postForm<T>(path: string, form: FormData): Promise<T> {
  return api<T>(path, { method: "POST", body: form });
}

/** Stream a chat completion (SSE). Calls onDelta for each text chunk. */
export async function streamChat(
  messages: ChatMessage[],
  onDelta: (text: string) => void,
  opts: { system?: string; signal?: AbortSignal } = {},
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages, system: opts.system }),
      signal: opts.signal,
    });
  } catch {
    throw new ApiError(`Cannot reach the backend at ${API_URL}. Is it running?`, 0);
  }
  if (!res.ok || !res.body) await handle(res);

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const evt of events) {
      const line = evt.trim();
      if (!line.startsWith("data:")) continue;
      const payload = JSON.parse(line.slice(5));
      if (payload.error) throw new ApiError(payload.error, 502);
      if (payload.delta) onDelta(payload.delta);
    }
  }
}

// ---------- Types mirrored from backend/app/models + services ----------

export type ChatMessage = { role: "user" | "assistant" | "system"; content: string };

export type AppConfig = {
  app_name: string;
  llm: { configured: boolean; model: string; vision_model: string; base_url: string };
  embeddings: string;
  features: { rag: boolean; ml: boolean; vision: boolean };
  tools: string[];
};

export type AgentStep = {
  iteration: number;
  tool: string;
  arguments: Record<string, unknown>;
  result: unknown;
  error: string | null;
  duration_ms: number;
};

export type AgentResult = {
  answer: string;
  steps: AgentStep[];
  iterations: number;
  duration_ms: number;
  model: string;
  stopped_reason: string;
};

export type ToolInfo = { name: string; description: string; parameters: Record<string, unknown> };

export type FileInfo = {
  name: string;
  original_name?: string | null;
  kind: "csv" | "pdf" | "text" | "json" | "image" | "other";
  size: number;
  origin: "upload" | "sample";
  processing?: Record<string, unknown> | null;
  error?: string | null;
};

export type SearchHit = {
  ref: number;
  doc_id: string;
  source: string;
  page: number;
  chunk_index: number;
  score: number;
  text: string;
};

export type RagAnswer = { answer: string; sources: SearchHit[]; model: string };
export type RagDocument = { doc_id: string; source: string; chunks: number };

export type DatasetProfile = {
  rows: number;
  columns: number;
  dtypes: Record<string, string>;
  missing: Record<string, number>;
  unique: Record<string, number>;
  numeric_summary: Record<string, Record<string, number>>;
  preview: Record<string, unknown>[];
};

export type ModelMeta = {
  name: string;
  target: string;
  task: "classification" | "regression";
  algorithm: string;
  features: string[];
  dropped_columns: string[];
  train_rows: number;
  test_rows: number;
  metrics: Record<string, unknown>;
  feature_importance: { feature: string; importance: number }[];
  classes: string[] | null;
  trained_at: string;
  duration_ms: number;
};

export type Prediction = {
  model: string;
  task: string;
  predictions: unknown[];
  probabilities?: Record<string, number>[];
};

export type VisionResult = {
  image: { width: number; height: number; format: string | null; processed_width: number; processed_height: number };
  model: string;
  prompt: string;
  text: string | null;
  data: Record<string, unknown> | null;
};
