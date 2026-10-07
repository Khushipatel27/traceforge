"""PromQL signal extraction shared by the v1 baseline and the v2 metrics agent.

Every signal is computed twice — over a baseline window before the fault and over
the window since injection — and returned with the exact query that produced it,
so any number in an answer can be traced back to a query someone can re-run.
"""

import math

from .sources import APP_SERVICES, by_label, promql

SERVER = 'span_kind=~"SPAN_KIND_SERVER|SPAN_KIND_CONSUMER"'


def _delta(metric, by):
    """Counter growth over the window, as (value now) - (value W seconds ago).

    increase() can't be used here: span metrics reach Prometheus about once a
    minute, and an error series only comes into existence with the first error,
    so increase() over a 1-2 minute window reads ~0 for exactly the series that
    matter. Treating a series missing at the window start as 0 fixes that.
    """
    now = f"sum by ({by}) ({metric})"
    before = f"sum by ({by}) ({metric} offset $Ws)"
    return f"{now} - ({before} or {now} * 0)"


CALLS = f"traces_span_metrics_calls_total{{{SERVER}}}"
ERRORS = f'traces_span_metrics_calls_total{{{SERVER},status_code="STATUS_CODE_ERROR"}}'
BUCKETS = f"traces_span_metrics_duration_milliseconds_bucket{{{SERVER}}}"

QUERIES = {
    "calls": _delta(CALLS, "service_name"),
    "errors": _delta(ERRORS, "service_name"),
    "p95_ms": f"histogram_quantile(0.95, {_delta(BUCKETS, 'service_name, le')})",
    "cpu": "avg by (container_name) (avg_over_time(container_cpu_utilization_ratio[$Ws]))",
    "mem_bytes": "max by (container_name) (max_over_time(container_memory_usage_total_bytes[$Ws]))",
    "kafka_lag": "max by (service_name) (max_over_time(kafka_consumer_records_lag_max[$Ws]))",
}
LABEL = {"calls": "service_name", "errors": "service_name", "p95_ms": "service_name",
         "cpu": "container_name", "mem_bytes": "container_name", "kafka_lag": "service_name"}


def window(name, start, end):
    w = max(int(end - start), 30)
    q = QUERIES[name].replace("$W", str(w))
    vals = {k: v for k, v in by_label(promql(q, end), LABEL[name]).items() if k in APP_SERVICES}
    return q, vals


def collect(base_start, base_end, fault_start, fault_end, names):
    """{signal: {"base": (query, values), "fault": (query, values)}}"""
    return {n: {"base": window(n, base_start, base_end), "fault": window(n, fault_start, fault_end)}
            for n in names}


def error_ratio(sig, which):
    _, calls = sig["calls"][which]
    _, errs = sig["errors"][which]
    return {s: errs.get(s, 0.0) / c for s, c in calls.items() if c >= 5}


def golden_signal_anomalies(sig):
    """Error-rate and latency anomalies per service: the two signals a standard
    RED dashboard shows. Returns a list of finding dicts."""
    out = []
    base_er, fault_er = error_ratio(sig, "base"), error_ratio(sig, "fault")
    _, fault_errs = sig["errors"]["fault"]
    for s, f in fault_er.items():
        delta = f - base_er.get(s, 0.0)
        if delta > 0.02 and fault_errs.get(s, 0) >= 3:
            out.append({"service": s, "signal": "errors", "score": delta * 10,
                        "detail": f"error ratio {base_er.get(s, 0.0):.1%} -> {f:.1%}",
                        "query": sig["errors"]["fault"][0]})
    _, base_p95 = sig["p95_ms"]["base"]
    _, fault_p95 = sig["p95_ms"]["fault"]
    _, base_calls = sig["calls"]["base"]
    _, fault_calls = sig["calls"]["fault"]
    for s, f in fault_p95.items():
        b = base_p95.get(s)
        if b is None or math.isinf(f) or math.isinf(b):
            continue
        # p95 over a handful of requests is noise; low-traffic services swing 2x on their own.
        if min(base_calls.get(s, 0), fault_calls.get(s, 0)) < 20:
            continue
        ratio = f / max(b, 1.0)
        if ratio > 2 and f - b > 50:
            out.append({"service": s, "signal": "latency", "score": math.log2(ratio),
                        "detail": f"p95 {b:.0f}ms -> {f:.0f}ms",
                        "query": sig["p95_ms"]["fault"][0]})
    return out
