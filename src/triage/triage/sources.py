"""Thin stdlib-only clients for the three telemetry backends."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
JAEGER_URL = os.environ.get("JAEGER_URL", "http://jaeger:16686/jaeger/ui")
OPENSEARCH_URL = os.environ.get("OPENSEARCH_URL", "http://opensearch:9200")

# Application services the triage layer is allowed to blame. Infrastructure that
# only exists to observe the system (collector, Jaeger, Grafana, ...) is excluded.
APP_SERVICES = {
    "accounting", "ad", "cart", "checkout", "currency", "email", "fraud-detection",
    "frontend", "frontend-proxy", "image-provider", "kafka", "payment",
    "product-catalog", "quote", "recommendation", "shipping",
    "astronomy-db", "valkey-cart",
}


def _get_json(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def _post_json(url, body, timeout=60):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def promql(query, at):
    """Instant query evaluated at unix time `at`. Returns {labels-tuple: float}."""
    qs = urllib.parse.urlencode({"query": query, "time": f"{at:.3f}"})
    data = _get_json(f"{PROMETHEUS_URL}/api/v1/query?{qs}")
    out = {}
    for row in data["data"]["result"]:
        try:
            v = float(row["value"][1])
        except (TypeError, ValueError):
            continue
        if v != v:  # NaN
            continue
        out[tuple(sorted(row["metric"].items()))] = v
    return out


def by_label(result, label):
    return {dict(k).get(label): v for k, v in result.items() if dict(k).get(label)}


def jaeger_traces(service, start, end, depth, errors_only=False):
    """Traces touching `service` in [start, end], flattened to span dicts."""
    params = {
        "query.service_name": service,
        "query.start_time_min": iso(start),
        "query.start_time_max": iso(end),
        "query.search_depth": depth,
    }
    if errors_only:
        params["query.attributes"] = json.dumps({"error": "true"})
    qs = urllib.parse.urlencode(params)
    try:
        data = _get_json(f"{JAEGER_URL}/api/v3/traces?{qs}", timeout=90)
    except urllib.error.HTTPError as e:
        if e.code == 404:  # no traces in window
            return {}
        raise
    traces = {}
    for rs in data.get("result", {}).get("resourceSpans", []):
        attrs = {a["key"]: _attr_value(a["value"]) for a in rs["resource"].get("attributes", [])}
        svc = attrs.get("service.name", "?")
        for ss in rs.get("scopeSpans", []):
            for sp in ss.get("spans", []):
                span_attrs = {a["key"]: _attr_value(a["value"]) for a in sp.get("attributes", [])}
                traces.setdefault(sp["traceId"], []).append({
                    "service": svc,
                    "span_id": sp["spanId"],
                    "parent_id": sp.get("parentSpanId", ""),
                    "name": sp.get("name", ""),
                    "kind": sp.get("kind", 0),
                    "error": sp.get("status", {}).get("code") in (2, "STATUS_CODE_ERROR"),
                    "start": int(sp["startTimeUnixNano"]),
                    "end": int(sp["endTimeUnixNano"]),
                    "attrs": span_attrs,
                })
    return traces


def _attr_value(v):
    for key in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if key in v:
            return v[key]
    return None


ERROR_LOG_QUERY = {
    "bool": {
        "should": [
            {"range": {"severity.number": {"gte": 17}}},
            {"terms": {"severity.text.keyword": ["ERROR", "Error", "error", "FATAL", "Fatal", "fatal", "CRITICAL", "Critical", "critical"]}},
        ],
        "minimum_should_match": 1,
    }
}


def error_logs(start, end):
    """Error-level log counts per service in [start, end], with one sample message each."""
    body = {
        "size": 0,
        "query": {"bool": {"filter": [
            {"range": {"@timestamp": {"gte": iso(start), "lte": iso(end)}}},
            ERROR_LOG_QUERY,
        ]}},
        "aggs": {"svc": {
            "terms": {"field": "resource.service.name.keyword", "size": 50},
            "aggs": {"sample": {"top_hits": {"size": 1, "_source": ["body"]}}},
        }},
    }
    data = _post_json(f"{OPENSEARCH_URL}/otel-logs-*/_search", body)
    out = {}
    for b in data.get("aggregations", {}).get("svc", {}).get("buckets", []):
        hits = b["sample"]["hits"]["hits"]
        sample = str(hits[0]["_source"].get("body", ""))[:200] if hits else ""
        out[b["key"]] = {"count": b["doc_count"], "sample": sample}
    return out
