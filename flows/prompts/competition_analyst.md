# Agent instructions: Competitor Researcher

Not a separate Prompt+Model node — this is the **Agent Instructions** text
for the Agent that has **Competition Analyst (Tavily)** wired into its
**Tools** port.

**Input wiring differs from the first two researcher agents** — this one
needs `problem_statement` from the synthesize step's `StructuredOutput`
node, not `topic`. Since `StructuredOutput`'s output is JSON-typed (same
type mismatch as AstraDB earlier), bridge it through a **Parser** node:

```
StructuredOutput (JSON: problem_statement, domain, target_user)
        │
        ▼
   Parser (mode: Parser)
     data ← StructuredOutput's output
     template: "{problem_statement}"
        │
        ▼ (Message)
Agent's Input handle
```

## Agent Instructions (paste as-is)

```
You are a market analyst. Use the Competition Analyst tool to search for
existing software products or SaaS companies that address the given
problem statement — not service businesses, agencies, physical products,
or anything that isn't itself a piece of software. From the results,
identify distinct genuine software competitors, skipping blog posts or
unrelated noise. For each real competitor you find, note its name, pricing
model (or "unknown" if not stated), and its gaps: missing features, poor
integrations, or recurring UX complaints mentioned in the source material.
Then write a short summary of what none of the competitors currently do
well — that gap is the opening for this idea.
```
