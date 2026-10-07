"""v1 — golden-signals baseline.

What an on-call engineer gets from a standard RED dashboard: per-service error
rate and p95 latency. Blame whichever service moved the most. No traces, no
logs, no resource metrics, no LLM.
"""

import time

from . import signals


def diagnose(base_start, base_end, fault_start, now):
    t0 = time.time()
    sig = signals.collect(base_start, base_end, fault_start, now, ["calls", "errors", "p95_ms"])
    findings = sorted(signals.golden_signal_anomalies(sig), key=lambda f: -f["score"])
    top = findings[0] if findings else None
    return {
        "service": top["service"] if top else None,
        "fault_type": top["signal"] if top else None,
        "summary": f"{top['service']}: {top['detail']}" if top else "no anomaly detected",
        "evidence": [],
        "verified": False,
        "candidates": [{k: f[k] for k in ("service", "signal", "score", "detail")} for f in findings[:5]],
        "compute_s": round(time.time() - t0, 2),
    }
