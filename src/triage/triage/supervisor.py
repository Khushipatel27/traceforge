"""v2 — incident triage.

metrics + trace + log agents -> ranked candidates -> the top-ranked candidate is
the diagnosis -> the LLM explains it -> verification checks the explanation
against the evidence that was collected.

The LLM does not decide the root cause. On the pilot runs a 3B model, given the
same evidence, overruled a correct ranking in favour of the service with the
loudest symptom. Its own choice is still recorded as an ablation.
"""

import json
import os
import re
import time
import urllib.request
from collections import defaultdict

from .agents import FAULT_TYPE, log_agent, metrics_agent, trace_agent

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
FAULT_TYPES = ["errors", "latency", "cpu", "memory", "queue", "traffic"]

CHOOSE_PROMPT = """You are an SRE triaging a live incident in a microservice system.
Specialist agents measured the telemetry below. Each candidate service lists its
findings; every finding has an evidence id (E1, E2, ...).

Decide which ONE service is the root cause and what kind of fault it is.
Errors and latency propagate upstream to callers: prefer the service where
errors ORIGINATE (trace_error_origin) or where time is SPENT (trace_self_time)
over services that merely see failures from their dependencies. Resource
signals (cpu, memory, queue) point at the service that owns the resource.

Fault type must be one of: {types}.

Candidates:
{candidates}

Reply with JSON only:
{{"service": "<name>", "fault_type": "<type>"}}"""

EXPLAIN_PROMPT = """You are an SRE writing the incident summary for a microservice system.
The root cause has already been determined from the telemetry below:

    root cause service: {service}
    fault type: {fault_type}

Telemetry findings (every finding has an evidence id):
{candidates}

Write 2 sentences for the on-call engineer explaining what is wrong with
{service} and how it affects other services. Use only numbers that appear in
the findings above, copied exactly. Cite the evidence ids that support it.

Reply with JSON only:
{{"summary": "<2 sentences>", "evidence": ["E<n>", ...]}}"""


def _ollama(prompt):
    body = {"model": OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False, "keep_alive": "60m",
            "options": {"temperature": 0}}
    req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(json.loads(r.read())["response"])


PROPAGATED = {"errors", "log_errors"}


def rank(findings):
    """Group findings by service; strongest service first.

    Errors propagate to every caller, so callers pile up symptoms (high error
    ratio, error logs) that can outscore the one service actually failing. When
    traces show where errors originate, other services' error symptoms are
    treated as propagation and dropped.
    """
    origins = {f["service"] for f in findings if f["signal"] == "trace_error_origin" and f["score"] >= 3}
    if origins:
        findings = [f for f in findings if f["signal"] not in PROPAGATED or f["service"] in origins]
    by_svc = defaultdict(list)
    for f in findings:
        by_svc[f["service"]].append(f)
    ranked = []
    for svc, fs in by_svc.items():
        best_per_signal = {}
        for f in fs:
            if f["score"] > best_per_signal.get(f["signal"], {"score": -1})["score"]:
                best_per_signal[f["signal"]] = f
        top = max(best_per_signal.values(), key=lambda f: f["score"])
        ranked.append({"service": svc, "score": sum(f["score"] for f in best_per_signal.values()),
                       "fault_type": FAULT_TYPE[top["signal"]],
                       "findings": sorted(best_per_signal.values(), key=lambda f: -f["score"])})
    return sorted(ranked, key=lambda c: -c["score"])


def diagnose(base_start, base_end, fault_start, now, use_llm=True):
    t0 = time.time()
    findings = metrics_agent(base_start, base_end, fault_start, now)
    focus = [c["service"] for c in rank(findings)]
    trace_findings, trace_stats = trace_agent(base_start, base_end, fault_start, now, focus)
    findings += trace_findings + log_agent(base_start, base_end, fault_start, now)
    ranked = rank(findings)[:5]

    if not ranked:
        return {"service": None, "fault_type": None, "summary": "no anomaly detected",
                "evidence": [], "verified": False, "deterministic": None, "candidates": [],
                "trace_stats": trace_stats, "compute_s": round(time.time() - t0, 2)}

    # Number every piece of evidence so the LLM can cite it and we can check it.
    evidence, lines = {}, []
    for c in ranked:
        lines.append(f"- {c['service']}")
        for f in c["findings"]:
            eid = f"E{len(evidence) + 1}"
            evidence[eid] = {"service": c["service"], "signal": f["signal"], "items": f["evidence"]}
            lines.append(f"    [{eid}] {f['signal']}: {f['detail']}")

    decision = {"service": ranked[0]["service"], "fault_type": ranked[0]["fault_type"]}
    candidates_text = "\n".join(lines)
    explanation, llm_choice, llm_error = {}, None, None
    if use_llm:
        try:
            explanation = _ollama(EXPLAIN_PROMPT.format(candidates=candidates_text, **decision))
            # Ablation only: what would the LLM blame if it were allowed to decide?
            llm_choice = _ollama(CHOOSE_PROMPT.format(types=", ".join(FAULT_TYPES), candidates=candidates_text))
        except Exception as e:  # noqa: BLE001 — the decision never depends on the LLM
            llm_error = repr(e)

    summary = str(explanation.get("summary", "")) if isinstance(explanation, dict) else ""
    cited_ids = explanation.get("evidence", []) if isinstance(explanation, dict) else []
    cited_ids = [str(e) for e in cited_ids] if isinstance(cited_ids, list) else []
    verified, problems = verify(decision["service"], summary, cited_ids, evidence, candidates_text)
    return {
        **decision,
        "summary": summary,
        "evidence": [item for eid in cited_ids if eid in evidence for item in evidence[eid]["items"]],
        "verified": verified,
        "verification_problems": problems,
        "llm_choice": {k: llm_choice.get(k) for k in ("service", "fault_type")} if isinstance(llm_choice, dict) else None,
        "llm_error": llm_error,
        "candidates": [{"service": c["service"], "score": round(c["score"], 2),
                        "findings": [f"{f['signal']}: {f['detail']}" for f in c["findings"]]} for c in ranked],
        "trace_stats": trace_stats,
        "compute_s": round(time.time() - t0, 2),
    }


NUMBER = re.compile(r"\d+(?:\.\d+)?")  # integers and decimals, e.g. 44 or 44.0
EVIDENCE_ID = re.compile(r"\bE\d+\b")  # citation ids like E3 are not claims


def verify(service, summary, cited_ids, evidence, candidates_text):
    """The explanation is verified only if it names the blamed service, cites at
    least one real piece of evidence about that service, and every number it
    states appears in the evidence the agents collected."""
    problems = []
    if not summary:
        problems.append("no explanation")
    elif service not in summary:
        problems.append(f"explanation does not name {service}")
    if not cited_ids:
        problems.append("no evidence cited")
    for eid in cited_ids:
        if eid not in evidence:
            problems.append(f"cited {eid} does not exist")
        elif evidence[eid]["service"] != service:
            problems.append(f"cited {eid} is about {evidence[eid]['service']}, not {service}")
    def numbers(text):
        return NUMBER.findall(EVIDENCE_ID.sub("", text))

    known = {float(n) for n in numbers(candidates_text)}
    for n in numbers(summary):
        if float(n) not in known:
            problems.append(f"number {n} not found in evidence")
    return not problems, problems
