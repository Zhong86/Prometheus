import Link from "next/link";
import { Brand } from "@/components/Logo";

const STEPS = [
  ["01 · TOPIC", "Type a niche or industry you're curious about."],
  ["02 · RESEARCH", "Papers, Reddit, Hacker News, Capterra, Product Hunt."],
  ["03 · IDEAS", "Three ideas with evidence, rivals and a feasibility score."],
];

export default function Home() {
  return (
    <main className="wrap">
      <section className="hero">
        <Brand big />
        <h1>
          Bring fire to your next <span>side project.</span>
        </h1>
        <p className="lede">
          Prometheus (Προμηθεύς) turns a topic into three buildable software ideas. It reads papers,
          forums and reviews to find real user pain, checks the competition and scores how feasible
          each idea is for a small team.
        </p>
        <Link className="btn" href="/dashboard">
          Start researching →
        </Link>
      </section>
      <section className="trio">
        {STEPS.map(([title, text]) => (
          <div key={title}>
            <b>{title}</b>
            <span>{text}</span>
          </div>
        ))}
      </section>
    </main>
  );
}
