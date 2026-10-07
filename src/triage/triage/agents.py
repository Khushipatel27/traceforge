"""v2 specialist agents. Each returns findings in the same shape:

    {"service", "signal", "score", "detail", "evidence": [{"kind", "ref"}]}

All numbers are computed here, in Python. The LLM downstream only chooses
between findings and explains them; it never does arithmetic on telemetry.
"""

import math
from collections import Counter, defaultdict

from . import signals
from .sources import APP_SERVICES, error_logs, jaeger_traces

FAULT_TYPE = {"errors": "errors", "latency": "latency", "cpu": "cpu", "memory": "memory",
              "traffic": "traffic", "queue": "queue",
              "trace_error_origin": "errors", "trace_self_time": "latency", "log_errors": "errors"}


# ---------------------------------------------------------------- metrics agent

def metrics_agent(base_start, base_end, fault_start, now):
    sig = signals.collect(base_start, base_end, fault_start, now, list(signals.QUERIES))
    findings = []
    for f in signals.golden_signal_anomalies(sig):
        q = f.pop("query")
        findings.append({**f, "evidence": [{"kind": "promql", "ref": q}]})

    def ratio_findings(name, signal, min_ratio, min_abs, weight, fmt):
        q, fault = sig[name]["fault"]
        _, base = sig[name]["base"]
        for s, f in fault.items():
            b = base.get(s, 0.0)
            ratio = (f + 1e-9) / max(b, 1e-9)
            if ratio > min_ratio and f - b > min_abs:
                findings.append({"service": s, "signal": signal,
                                 "score": weight * math.log2(min(ratio, 1024)),
                                 "detail": fmt(b, f), "evidence": [{"kind": "promql", "ref": q}]})

    ratio_findings("cpu", "cpu", 1.6, 0.15, 1.0, lambda b, f: f"CPU {b:.2f} -> {f:.2f} cores")
    ratio_findings("mem_bytes", "memory", 1.15, 30e6, 3.0,
                   lambda b, f: f"memory {b / 1e6:.0f}MB -> {f / 1e6:.0f}MB")
    ratio_findings("kafka_lag", "queue", 3.0, 50, 1.0, lambda b, f: f"consumer lag {b:.0f} -> {f:.0f}")

    # request-rate spike (traffic flood)
    q, fault_calls = sig["calls"]["fault"]
    _, base_calls = sig["calls"]["base"]
    fw, bw = max(now - fault_start, 1), max(base_end - base_start, 1)
    for s, c in fault_calls.items():
        f_rate, b_rate = c / fw, base_calls.get(s, 0.0) / bw
        if b_rate > 0 and f_rate / b_rate > 2 and f_rate > 1:
            findings.append({"service": s, "signal": "traffic", "score": math.log2(f_rate / b_rate),
                             "detail": f"request rate {b_rate:.1f}/s -> {f_rate:.1f}/s",
                             "evidence": [{"kind": "promql", "ref": q}]})
    return findings


# ------------------------------------------------------------------ trace agent

RPC_SERVICE = {
    "oteldemo.AdService": "ad", "oteldemo.CartService": "cart",
    "oteldemo.CheckoutService": "checkout", "oteldemo.CurrencyService": "currency",
    "oteldemo.EmailService": "email", "oteldemo.PaymentService": "payment",
    "oteldemo.ProductCatalogService": "product-catalog", "oteldemo.QuoteService": "quote",
    "oteldemo.RecommendationService": "recommendation", "oteldemo.ShippingService": "shipping",
}
CLIENT, SERVER = (3, "SPAN_KIND_CLIENT"), (2, "SPAN_KIND_SERVER")


def _callee(span):
    """Service on the far side of a client span, when it can be determined."""
    a = span["attrs"]
    if a.get("rpc.service") in RPC_SERVICE:
        return RPC_SERVICE[a["rpc.service"]]
    # Newer gRPC semconv drops rpc.service and puts "pkg.Service/Method" in rpc.method.
    for method in (a.get("rpc.method"), span["name"]):
        rpc_service = str(method or "").split("/")[0]
        if rpc_service in RPC_SERVICE:
            return RPC_SERVICE[rpc_service]
    if a.get("db.system") in ("postgresql", "postgres") or a.get("db.system.name") == "postgresql":
        return "astronomy-db"
    if a.get("db.system") in ("redis", "valkey"):
        return "valkey-cart"
    # Envoy names its upstream call "router <cluster> egress".
    parts = span["name"].split()
    if len(parts) == 3 and parts[0] == "router" and parts[2] == "egress" and parts[1] in APP_SERVICES:
        return parts[1]
    for key in ("peer.service", "server.address", "net.peer.name"):
        host = str(a.get(key) or "").split(":")[0]
        if host in APP_SERVICES:
            return host
    return None


def _fetch(services, start, end, depth):
    traces = {}
    for s in services:
        traces.update(jaeger_traces(s, start, end, depth))
    return traces


def _fetch_errors(services, start, end):
    traces = {}
    for s in services:
        traces.update(jaeger_traces(s, start, end, 20, errors_only=True))
    return traces


def _error_origins(traces):
    """An error span is an origin if none of its children errored. A failing
    client span with no child at all means the callee never answered, so the
    callee is the origin."""
    origins, examples, n_err_traces = Counter(), defaultdict(list), 0
    for tid, spans in traces.items():
        children = defaultdict(list)
        for sp in spans:
            children[sp["parent_id"]].append(sp)
        trace_origins = set()
        for sp in spans:
            if not sp["error"] or any(c["error"] for c in children[sp["span_id"]]):
                continue
            if "upstream_cluster" in sp["attrs"]:
                continue  # proxy gave up waiting (e.g. 504): a symptom, never an origin
            svc = sp["service"]
            if sp["kind"] in CLIENT and not children[sp["span_id"]]:
                svc = _callee(sp)  # unknown callee: can't attribute, skip
            if svc in APP_SERVICES:
                trace_origins.add(svc)
        if trace_origins:
            n_err_traces += 1
            for svc in trace_origins:
                origins[svc] += 1
                if len(examples[svc]) < 3:
                    examples[svc].append(tid)
    return origins, examples, n_err_traces


# Services export spans in batches, so the newest traces are often missing their
# downstream half. Ignoring the last INGEST_LAG_S seconds avoids reading a
# half-arrived trace as "the caller failed on its own".
INGEST_LAG_S = 20


def trace_agent(base_start, base_end, fault_start, now, focus):
    now -= INGEST_LAG_S
    services = ["frontend"] + [s for s in focus if s != "frontend"][:3]
    fault = _fetch(services, fault_start, now, 30)
    base = _fetch(services, base_start, base_end, 30)
    findings = []

    # Failing traces are rare relative to traffic, so search for them directly
    # through every service instead of hoping a sample contains them.
    searchable = sorted(APP_SERVICES - {"astronomy-db", "valkey-cart", "kafka"})
    fault_err = _fetch_errors(searchable, fault_start, now)
    base_err = _fetch_errors(searchable, base_start, base_end)
    origins, examples, n_err_traces = _error_origins(fault_err)
    base_origins, _, _ = _error_origins(base_err)
    fw, bw = max(now - fault_start, 1) / 60, max(base_end - base_start, 1) / 60
    for svc, n in origins.items():
        f_rate, b_rate = n / fw, base_origins.get(svc, 0) / bw
        if n < 3 or f_rate <= 2 * b_rate + 1:  # background errors exist; need a clear rise
            continue
        share = n / n_err_traces
        findings.append({"service": svc, "signal": "trace_error_origin", "score": 6 * share,
                         "detail": f"error originates here in {n}/{n_err_traces} failing traces "
                                   f"({b_rate:.1f}/min before -> {f_rate:.1f}/min)",
                         "evidence": [{"kind": "trace", "ref": t} for t in examples[svc]]})

    # Where is time being spent? Self-time = span duration minus its children.
    def self_times(traces):
        per_svc, worst = defaultdict(list), {}
        for tid, spans in traces.items():
            children = defaultdict(list)
            for sp in spans:
                children[sp["parent_id"]].append(sp)
            for sp in spans:
                dur = sp["end"] - sp["start"]
                kids = sum(c["end"] - c["start"] for c in children[sp["span_id"]])
                self_ms = max(dur - kids, 0) / 1e6
                svc = sp["service"]
                if sp["kind"] in CLIENT and not children[sp["span_id"]]:
                    svc = _callee(sp)
                    if svc is None:
                        continue
                per_svc[svc].append(self_ms)
                if self_ms > worst.get(svc, (0, None))[0]:
                    worst[svc] = (self_ms, tid)
        return per_svc, worst

    f_self, f_worst = self_times(fault)
    b_self, _ = self_times(base)
    for svc, vals in f_self.items():
        if svc not in APP_SERVICES or len(vals) < 3 or len(b_self.get(svc, [])) < 3:
            continue
        f_mean, b_mean = sum(vals) / len(vals), sum(b_self[svc]) / len(b_self[svc])
        ratio = (f_mean + 10) / (b_mean + 10)  # +10ms keeps near-zero baselines from exploding
        if ratio > 2 and f_mean - b_mean > 50:
            findings.append({"service": svc, "signal": "trace_self_time",
                             "score": math.log2(min(ratio, 1024)),
                             "detail": f"mean self-time per span {b_mean:.0f}ms -> {f_mean:.0f}ms",
                             "evidence": [{"kind": "trace", "ref": f_worst[svc][1]}]})
    return findings, {"fault_traces": len(fault), "base_traces": len(base),
                      "error_traces": n_err_traces, "base_error_traces": len(base_err)}


# -------------------------------------------------------------------- log agent

def log_agent(base_start, base_end, fault_start, now):
    base, fault = error_logs(base_start, base_end), error_logs(fault_start, now)
    bw, fw = max(base_end - base_start, 1) / 60, max(now - fault_start, 1) / 60
    findings = []
    for svc, f in fault.items():
        if svc not in APP_SERVICES:
            continue
        f_rate, b_rate = f["count"] / fw, base.get(svc, {}).get("count", 0) / bw
        if f_rate > 2 * b_rate + 1:
            findings.append({"service": svc, "signal": "log_errors",
                             "score": 0.5 * math.log2((f_rate + 1) / (b_rate + 1)),
                             "detail": f"error logs {b_rate:.1f}/min -> {f_rate:.1f}/min; e.g. \"{f['sample'][:120]}\"",
                             "evidence": [{"kind": "logs", "ref": svc}]})
    return findings
