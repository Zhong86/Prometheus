"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { runResearch } from "@/lib/api";
import type { Idea, ResearchResult } from "@/lib/types";
import { Brand } from "./Logo";

const SOURCES: Record<string, string> = {
  paper: "Paper",
  reddit: "Reddit",
  hackernews: "Hacker News",
  capterra: "Capterra",
  producthunt: "Product Hunt",
};
const TYPES: Record<string, string> = {
  software: "Software",
  ai_automation: "AI / Automation",
  iot: "IoT",
  other_tech: "Other tech",
};
const STORAGE_KEY = "prometheus:last-result";

const scoreColor = (n: number) => (n >= 7 ? "var(--good)" : n >= 4 ? "var(--mid)" : "var(--low)");
const capitalize = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);
const hostname = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
};
const formatElapsed = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

function loadSaved(): ResearchResult | null {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
  } catch {
    return null;
  }
}

function save(result: ResearchResult) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(result));
  } catch {}
}

export default function Dashboard() {
  const [topic, setTopic] = useState("");
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [active, setActive] = useState(0);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    const saved = loadSaved();
    if (saved?.ideas?.length) {
      setResult(saved);
      setTopic(saved.topic);
    }
  }, []);

  useEffect(() => {
    if (!running) return;
    const started = Date.now();
    setElapsed(0);
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [running]);

  useEffect(() => () => abort.current?.abort(), []);

  async function run() {
    const t = topic.trim();
    if (t.length < 2 || running) return;
    abort.current = new AbortController();
    setRunning(true);
    setError(null);
    try {
      const data = await runResearch(t, abort.current.signal);
      setResult(data);
      setActive(0);
      save(data);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setRunning(false);
    }
  }

  const idea = result?.ideas[active];

  return (
    <main className="wrap">
      <nav className="dnav">
        <Link href="/" style={{ textDecoration: "none" }}>
          <Brand />
        </Link>
      </nav>

      <div className="bar">
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="What topic should Prometheus research?"
          maxLength={300}
          disabled={running}
          aria-label="Research topic"
        />
        <button className="btn" onClick={run} disabled={running || topic.trim().length < 2}>
          {running ? "Researching…" : "Run research"}
        </button>
      </div>

      {running && (
        <div className="progress" role="status">
          <div className="indeterminate" />
          <p>
            <b>Researching “{topic.trim()}”</b> · {formatElapsed(elapsed)}
          </p>
          <p>
            Reading papers, forums and reviews, then checking competitors and scoring each idea. This usually
            takes a few minutes.
          </p>
        </div>
      )}

      {error && !running && (
        <div className="errbox" role="alert">
          <b>The run failed.</b> {error}
        </div>
      )}

      {!running && !idea && !error && (
        <div className="empty">Enter a topic above. Three ideas will appear here when the run finishes.</div>
      )}

      {!running && result && idea && (
        <>
          <div className="tabs" role="tablist">
            {result.ideas.map((x, i) => (
              <button
                key={x.idea_id}
                role="tab"
                aria-selected={i === active}
                className={`tab${i === active ? " on" : ""}`}
                onClick={() => setActive(i)}
              >
                <small>
                  IDEA {i + 1} · {x.solvability_score}/10
                </small>
                <b>{x.niche}</b>
                <div className="meter">
                  <i style={{ width: `${x.solvability_score * 10}%`, background: scoreColor(x.solvability_score) }} />
                </div>
              </button>
            ))}
          </div>
          <IdeaReader idea={idea} />
        </>
      )}
    </main>
  );
}

function IdeaReader({ idea }: { idea: Idea }) {
  const competitors = idea.competitors ?? [];
  const evidence = idea.evidence ?? [];
  return (
    <div className="reader">
      <article className="doc">
        <h2>{idea.niche}</h2>
        <p className="dom">
          {idea.domain} · for {idea.target_user?.toLowerCase()}
        </p>
        <h4>The problem</h4>
        <p>{idea.problem_statement}</p>
        <h4>The solution</h4>
        <p>{idea.solution_approach}</p>
        <div className="gap">
          <h4>Market gap</h4>
          <p>{idea.market_gap_summary}</p>
        </div>
        <h4>Feasibility reasoning</h4>
        <p>{idea.reasoning}</p>
      </article>

      <aside className="side">
        <div className="box">
          <h5>Feasibility</h5>
          <div className="big" style={{ color: scoreColor(idea.solvability_score) }}>
            {idea.solvability_score}
            <small>/10</small>
          </div>
          <div className="kv first">
            <span>MVP</span>
            <b>{capitalize(idea.mvp_complexity)}</b>
          </div>
          <div className="kv">
            <span>Type</span>
            <b>{TYPES[idea.solution_type] ?? idea.solution_type}</b>
          </div>
          <div className="kv">
            <span>APIs</span>
            <b>{idea.required_apis?.join(", ") || "None"}</b>
          </div>
        </div>

        <div className="box">
          <h5>Competitors</h5>
          {competitors.length === 0 && <p className="muted">None found.</p>}
          {competitors.map((c) => (
            <div className="c" key={c.name}>
              <b>
                {c.url ? (
                  <a href={c.url} target="_blank" rel="noopener noreferrer">
                    {c.name}
                  </a>
                ) : (
                  c.name
                )}
                <em>{c.pricing}</em>
              </b>
              {c.gaps?.[0] && <p>{c.gaps[0]}</p>}
            </div>
          ))}
        </div>

        <div className="box">
          <h5>Evidence</h5>
          {evidence.length === 0 && <p className="muted">None recorded.</p>}
          <ul className="ev">
            {evidence.map((e, i) => (
              <li key={i}>
                <em>{SOURCES[e.source] ?? e.source}</em>
                {e.finding}{" "}
                <a href={e.url} target="_blank" rel="noopener noreferrer">
                  {hostname(e.url)} ↗
                </a>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  );
}
