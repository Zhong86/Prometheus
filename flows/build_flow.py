"""Regenerate flows/Prometheus.json from flows/prompts/*.md and the custom components.

The prompt files are the source of truth for every LLM node (prompt template,
format instructions, output schema); this script turns them into the Langflow
DAG so the flow never drifts from them.

    python flows/build_flow.py            # write flows/Prometheus.json
    python flows/build_flow.py --push     # ...and update the "Prometheus" flow in Langflow

Needs the Langflow container running (http://localhost:7860, auto-login on):
custom-component nodes are taken from its live /api/v1/all catalog so they
match the code in flows/components/. Built-in nodes (Chat I/O, Astra DB,
Prompt Template, Structured Output) are copied from the original UI export in
flows/Prometheus.agents-backup.json, which keeps the exact shape the UI writes.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import json
import re
import urllib.request
from pathlib import Path

FLOWS = Path(__file__).resolve().parent
PROMPTS = FLOWS / "prompts"
BASE_EXPORT = FLOWS / "Prometheus.agents-backup.json"
OUT = FLOWS / "Prometheus.json"
LANGFLOW = "http://localhost:7860"
FLOW_NAME = "Prometheus"

MODEL = [{
    "icon": "GoogleGenerativeAI",
    "metadata": {
        "icon": "GoogleGenerativeAI", "tool_calling": True, "reasoning": True, "search": False,
        "preview": False, "not_supported": False, "deprecated": False, "default": False,
        "model_type": "llm", "vision": True, "context_window": 1048576,
    },
    "name": "gemini-3.5-flash-lite",
    "provider": "Google Generative AI",
}]

# Astra DB token: referenced by global-variable name, never embedded in the flow file.
# Langflow creates this variable at startup from the container env (see docker-compose.yml).
ASTRA_TOKEN_VAR = "ASTRA_DB_APPLICATION_TOKEN"

# Built-in nodes reused as-is from the original export, and the ones used as templates.
CHAT_IN = "ChatInput-dcugP"
ASTRA = "ext:datastax:AstraDBVectorStoreComponent@official-wCOtf"
ASTRA_PARSER = "ParserComponent-9IetQ"
ASTRA_SAVE = "ext:datastax:AstraDBVectorStoreComponent@official-Save1"
CHAT_OUT = "ChatOutput-3Q8kg"
PROMPT_PROTO = "Prompt Template-T4UQX"
STRUCTURED_PROTO = "StructuredOutput-ZqXqB"

ACAD = "ext:prometheus:AcademicProblemsComponent@extra"
FRIC = "ext:prometheus:PublicFrictionComponent@extra"
COMP = "ext:prometheus:CompetitionAnalystComponent@extra"
FMT = "ext:prometheus:FormatIdeasComponent@extra"
REPORT = "ext:prometheus:IdeaReportComponent@extra"


# ── Langflow API ─────────────────────────────────────────────────────────────
def api(path: str, token: str | None = None, method: str = "GET", body: dict | None = None):
    req = urllib.request.Request(f"{LANGFLOW}{path}", method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, data=data) as resp:
        raw = resp.read()
    if raw[:2] == b"\x1f\x8b":  # Langflow gzips large responses even without Accept-Encoding
        raw = gzip.decompress(raw)
    return json.loads(raw)


# ── prompt .md parsing ───────────────────────────────────────────────────────
def section(md: str, heading: str) -> str:
    start = md.index(heading)
    end = md.find("\n## ", start + 1)
    return md[start : end if end != -1 else None]


def code_blocks(text: str) -> list[str]:
    return re.findall(r"```\n(.*?)\n```", text, re.S)


def schema_rows(md: str) -> list[dict]:
    rows = []
    for line in section(md, "## Output Schema").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        name, typ, as_list, desc = cells
        rows.append({"name": name.strip("`"), "type": typ, "multiple": as_list, "description": desc.replace("`", "")})
    return rows


def load_prompt(fname: str) -> dict:
    md = (PROMPTS / fname).read_text()
    prompt = {
        "template": code_blocks(section(md, "## Prompt Template"))[0],
        "system": code_blocks(section(md, "## Format Instructions"))[0],
        "schema": schema_rows(md),
        "schema_name": re.search(r"\*\*Schema Name\*\* — `(\w+)`", md).group(1),
    }
    if "## Format Ideas template" in md:
        header, template = code_blocks(section(md, "## Format Ideas template"))[:2]
        prompt["format_ideas"] = {"header": header, "template": template}
    return prompt


# ── flow assembly ────────────────────────────────────────────────────────────
class FlowBuilder:
    def __init__(self, base: dict, catalog: dict):
        self.base = {n["id"]: n for n in base["data"]["nodes"]}
        self.base_edges = base["data"]["edges"]
        self.catalog = catalog
        self.nodes: list[dict] = []
        self.edges: list[dict] = []

    def _place(self, node_id, data_type, node, x, y):
        self.nodes.append({
            "data": {"id": node_id, "node": node, "showNode": True, "type": data_type},
            "dragging": False,
            "id": node_id,
            "position": {"x": x, "y": y},
            "selected": False,
            "type": "genericNode",
        })

    def keep(self, node_id, x, y, new_id=None, display_name=None, **values):
        n = copy.deepcopy(self.base[node_id])
        n.pop("measured", None)
        n["position"] = {"x": x, "y": y}
        if new_id:
            n["id"] = n["data"]["id"] = new_id
        if display_name:
            n["data"]["node"]["display_name"] = display_name
        for k, v in values.items():
            n["data"]["node"]["template"][k]["value"] = v
        if "token" in n["data"]["node"]["template"]:  # Astra DB nodes
            n["data"]["node"]["template"]["token"].update(value=ASTRA_TOKEN_VAR, load_from_db=True)
        self.nodes.append(n)

    def prompt_template(self, node_id, template, x, y, display_name):
        node = copy.deepcopy(self.base[PROMPT_PROTO]["data"]["node"])
        var_proto = node["template"]["topic"]
        for v in node["custom_fields"]["template"]:
            node["template"].pop(v, None)
        variables = list(dict.fromkeys(re.findall(r"\{(\w+)\}", template)))
        for v in variables:
            f = copy.deepcopy(var_proto)
            f["name"] = f["display_name"] = v
            f["value"] = ""
            node["template"][v] = f
        node["custom_fields"] = {"template": variables}
        node["template"]["template"]["value"] = template
        node["display_name"] = display_name
        self._place(node_id, "Prompt Template", node, x, y)

    def structured_output(self, node_id, p, x, y, display_name):
        node = copy.deepcopy(self.base[STRUCTURED_PROTO]["data"]["node"])
        t = node["template"]
        t["model"]["value"] = copy.deepcopy(MODEL)
        t["api_key"]["value"] = ""
        t["system_prompt"]["value"] = p["system"]
        t["output_schema"]["value"] = p["schema"]
        t["schema_name"]["value"] = p["schema_name"]
        t["input_value"]["value"] = ""
        node["display_name"] = display_name
        self._place(node_id, "StructuredOutput", node, x, y)

    def custom(self, node_id, key, x, y, **values):
        node = copy.deepcopy(self.catalog["prometheus"][key])
        for k, v in values.items():
            node["template"][k]["value"] = v
        self._place(node_id, key, node, x, y)

    def base_output_name(self, source_id):
        return next(e["data"]["sourceHandle"]["name"] for e in self.base_edges if e["source"] == source_id)

    def connect(self, src_id, out_name, tgt_id, field):
        enc = lambda d: json.dumps(d, separators=(",", ":")).replace('"', "œ")  # noqa: E731
        src = next(n for n in self.nodes if n["id"] == src_id)
        tgt = next(n for n in self.nodes if n["id"] == tgt_id)
        out = next(o for o in src["data"]["node"]["outputs"] if o["name"] == out_name)
        fld = tgt["data"]["node"]["template"][field]
        sh = {"dataType": src["data"]["type"], "id": src_id, "name": out_name, "output_types": out["types"]}
        th = {"fieldName": field, "id": tgt_id, "inputTypes": fld.get("input_types") or [], "type": fld.get("type", "str")}
        self.edges.append({
            "animated": False,
            "className": "",
            "data": {"sourceHandle": sh, "targetHandle": th},
            "id": f"xy-edge__{src_id}{enc(sh)}-{tgt_id}{enc(th)}",
            "selected": False,
            "source": src_id,
            "sourceHandle": enc(sh),
            "target": tgt_id,
            "targetHandle": enc(th),
        })


def build(base: dict, catalog: dict) -> dict:
    planner = load_prompt("query_planner.md")
    synth = load_prompt("synthesize.md")
    comp = load_prompt("competition_analysis.md")
    feas = load_prompt("feasibility.md")

    b = FlowBuilder(base, catalog)
    col = lambda i: -1200 + 500 * i  # noqa: E731

    b.keep(CHAT_IN, col(0), 0)
    b.keep(ASTRA, col(0), 500, number_of_results=12)  # past ideas fed back as "ideas to avoid"
    b.keep(ASTRA_PARSER, col(1), 600, pattern="- {text}")

    b.prompt_template("Prompt Template-QPlan", planner["template"], col(2), 0, "Query Planner Prompt")
    b.structured_output("StructuredOutput-QPlan", planner, col(3), 0, "Query Planner")
    b.custom(f"{ACAD}-Acad1", ACAD, col(4), -450)
    b.custom(f"{FRIC}-Fric1", FRIC, col(4), 250)

    b.prompt_template("Prompt Template-Synth", synth["template"], col(5), 0, "Synthesize Prompt")
    b.structured_output("StructuredOutput-Synth", synth, col(6), 0, "Synthesize")
    b.custom(f"{FMT}-Idea", FMT, col(7), 500, **synth["format_ideas"])
    b.custom(f"{COMP}-Comp1", COMP, col(7), -350)

    b.prompt_template("Prompt Template-Comp", comp["template"], col(8), -300, "Competition Analysis Prompt")
    b.structured_output("StructuredOutput-Comp", comp, col(9), -300, "Competition Analysis")
    b.custom(f"{FMT}-Comp", FMT, col(10), 300, **comp["format_ideas"])

    b.prompt_template("Prompt Template-Feas", feas["template"], col(11), 300, "Feasibility Prompt")
    b.structured_output("StructuredOutput-Feas", feas, col(12), 300, "Feasibility")
    b.custom(f"{REPORT}-Report", REPORT, col(13), 0)
    b.keep(CHAT_OUT, col(14), 0)
    b.keep(ASTRA, col(14), 500, new_id=ASTRA_SAVE, display_name="Save Ideas (Astra DB)")  # same DB/collection/embeddings as the search node

    chat = b.base_output_name(CHAT_IN)
    b.connect(CHAT_IN, chat, ASTRA, "search_query")
    b.connect(ASTRA, b.base_output_name(ASTRA), ASTRA_PARSER, "input_data")

    b.connect(CHAT_IN, chat, "Prompt Template-QPlan", "topic")
    b.connect(ASTRA_PARSER, "parsed_text", "Prompt Template-QPlan", "negative_context")
    b.connect("Prompt Template-QPlan", "prompt", "StructuredOutput-QPlan", "input_value")
    b.connect("StructuredOutput-QPlan", "structured_output", f"{ACAD}-Acad1", "queries")
    b.connect("StructuredOutput-QPlan", "structured_output", f"{FRIC}-Fric1", "queries")

    b.connect(CHAT_IN, chat, "Prompt Template-Synth", "topic")
    b.connect(ASTRA_PARSER, "parsed_text", "Prompt Template-Synth", "negative_context")
    b.connect(f"{ACAD}-Acad1", "papers", "Prompt Template-Synth", "academic_findings")
    b.connect(f"{FRIC}-Fric1", "complaints", "Prompt Template-Synth", "friction_findings")
    b.connect("Prompt Template-Synth", "prompt", "StructuredOutput-Synth", "input_value")

    b.connect("StructuredOutput-Synth", "structured_output", f"{COMP}-Comp1", "queries")
    b.connect("StructuredOutput-Synth", "structured_output", f"{FMT}-Idea", "data")
    b.connect("StructuredOutput-Synth", "structured_output", f"{REPORT}-Report", "synthesis")

    b.connect(f"{FMT}-Idea", "formatted", "Prompt Template-Comp", "idea")
    b.connect(f"{COMP}-Comp1", "results", "Prompt Template-Comp", "competitor_results")
    b.connect("Prompt Template-Comp", "prompt", "StructuredOutput-Comp", "input_value")
    b.connect("StructuredOutput-Comp", "structured_output", f"{FMT}-Comp", "data")
    b.connect("StructuredOutput-Comp", "structured_output", f"{REPORT}-Report", "competition")

    b.connect(f"{FMT}-Idea", "formatted", "Prompt Template-Feas", "idea")
    b.connect(f"{FMT}-Comp", "formatted", "Prompt Template-Feas", "competition")
    b.connect("Prompt Template-Feas", "prompt", "StructuredOutput-Feas", "input_value")
    b.connect("StructuredOutput-Feas", "structured_output", f"{REPORT}-Report", "feasibility")

    b.connect(CHAT_IN, chat, f"{REPORT}-Report", "topic")
    b.connect(f"{REPORT}-Report", "report", CHAT_OUT, "input_value")
    b.connect(f"{REPORT}-Report", "documents", ASTRA_SAVE, "ingest_data")

    flow = copy.deepcopy(base)
    flow["name"] = FLOW_NAME
    flow["data"]["nodes"] = b.nodes
    flow["data"]["edges"] = b.edges
    flow["data"]["viewport"] = {"x": 700, "y": 400, "zoom": 0.3}
    return flow


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--push", action="store_true", help=f'also update the "{FLOW_NAME}" flow in Langflow')
    args = parser.parse_args()

    token = api("/api/v1/auto_login")["access_token"]
    catalog = api("/api/v1/all", token)
    flow = build(json.loads(BASE_EXPORT.read_text()), catalog)
    OUT.write_text(json.dumps(flow, indent=2, ensure_ascii=False))
    print(f"{len(flow['data']['nodes'])} nodes, {len(flow['data']['edges'])} edges -> {OUT}")

    if args.push:
        flows = api("/api/v1/flows/?get_all=true&remove_example_flows=true", token)
        existing = next((f for f in flows if f["name"] == FLOW_NAME), None)
        body = {"name": FLOW_NAME, "data": flow["data"]}
        if existing:
            api(f"/api/v1/flows/{existing['id']}", token, "PATCH", body)
            print(f'updated Langflow flow "{FLOW_NAME}" ({existing["id"]})')
        else:
            created = api("/api/v1/flows/", token, "POST", body)
            print(f'created Langflow flow "{FLOW_NAME}" ({created["id"]})')


if __name__ == "__main__":
    main()
