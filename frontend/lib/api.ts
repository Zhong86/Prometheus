import type { ResearchResult } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Runs the Prometheus pipeline for a topic. Takes minutes, so callers should show progress. */
export async function runResearch(topic: string, signal?: AbortSignal): Promise<ResearchResult> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/research`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new Error(`Could not reach the Prometheus backend at ${API_URL}.`);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail ?? "");
    throw new Error(detail || `Backend returned ${res.status}.`);
  }
  return res.json();
}
