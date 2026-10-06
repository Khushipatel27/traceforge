# 🔭 TraceForge

**Break a 20-service production system on purpose — then watch traces, metrics and logs tell you exactly where and why.**

![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-000000?logo=opentelemetry&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Jaeger](https://img.shields.io/badge/Jaeger-66CFE3?logo=jaeger&logoColor=black)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-F46800?logo=grafana&logoColor=white)
![OpenSearch](https://img.shields.io/badge/OpenSearch-005EB8?logo=opensearch&logoColor=white)
![Kafka](https://img.shields.io/badge/Kafka-231F20?logo=apachekafka&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?logo=langchain&logoColor=white)
![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)

> **Attribution.** TraceForge is a fork of the
> [OpenTelemetry Demo (Astronomy Shop)](https://github.com/open-telemetry/opentelemetry-demo),
> © The OpenTelemetry Authors, Apache 2.0. The base system — the services,
> instrumentation and observability stack — is upstream work. What this fork
> adds is listed in [🧠 v2 — The Triage Layer](#-v2--the-triage-layer) and
> [🔀 What's Mine vs Upstream](#-whats-mine-vs-upstream). The original README is
> kept in [README.upstream.md](./README.upstream.md).

---

## 📊 v1 vs v2 — To Be Measured

v1 is the upstream system as-is: a human opens Jaeger and Grafana and hunts for
the cause. v2 adds an incident-triage agent that does the first pass
automatically. Both will be run against the same set of injected faults (one
per failure flag below).

| Metric | v1 (human + dashboards) | v2 (triage agent) |
| --- | --- | --- |
| Root-cause service correctly identified | — | — |
| Fault type correctly identified | — | — |
| Time from fault injection to diagnosis | — | — |
| Answers citing a specific trace / metric | — | — |

> **How to read this table honestly:** nothing here has been measured yet. Rows
> will be filled from a reproducible script, not estimated. Until then, treat v2
> as a design, not a result.

---

## 💡 What It Does

A realistic e-commerce system — storefront, cart, checkout, payment, shipping,
recommendations, ads, fraud detection — split across **15+ microservices in 11
languages**, every one instrumented with OpenTelemetry. All telemetry flows
through one OpenTelemetry Collector into Jaeger, Prometheus, OpenSearch and
Grafana.

The interesting part is the failure injection. Flip a feature flag and the system
breaks in a specific, realistic way:

> *"Payment fails 50% of the time."* *"The email service leaks memory."*
> *"Kafka consumers fall behind."* *"The product catalog DB hits lock contention."*

Then you diagnose it the way an SRE would — from the telemetry alone.

---

## 🧠 v2 — The Triage Layer

*Status: planned. This section describes the design being built.*

v1 makes the evidence available; a human still has to find it. When
`paymentFailure` is on, the cause is in Jaeger — but you have to know to filter
for error spans, follow them from `frontend` through `checkout` to `payment`, and
cross-check the error rate in Prometheus. v2 automates that first pass.

```text
                       ┌──────────────────┐
   alert / question ──▶│    Supervisor    │  rule-based routing
                       └────────┬─────────┘
             ┌──────────────────┼──────────────────┐
             ▼                  ▼                  ▼
    ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
    │  Trace Agent   │ │  Metrics Agent │ │   Log Agent    │
    │                │ │                │ │                │
    │ Jaeger API:    │ │ PromQL: error  │ │ OpenSearch:    │
    │ error / slow   │ │ rate, p95      │ │ error logs     │
    │ spans, service │ │ latency, CPU,  │ │ per service    │
    │ call graph     │ │ memory deltas  │ │ + exceptions   │
    └───────┬────────┘ └───────┬────────┘ └───────┬────────┘
            └──────────────────┼──────────────────┘
                               ▼
                     ┌───────────────────┐
                     │    Synthesize     │  LLM writes the diagnosis
                     └─────────┬─────────┘
                               ▼
                     ┌───────────────────┐
                     │   Verification    │  every claim must cite a
                     │                   │  trace ID or metric query
                     └─────────┬─────────┘
                               ▼
               root cause + evidence links
```

### Design principles

**The agents fetch; the LLM only explains.** Error rates, latency percentiles and
span counts come from PromQL and the Jaeger API in plain Python. An LLM that does
its own arithmetic on telemetry produces numbers that look right and aren't.

**Every claim must be traceable.** "Payment is failing" is only accepted if the
answer links to the trace IDs or PromQL query that show it. A diagnosis without
evidence is flagged, not returned as fact.

---

## 🏗️ Architecture

```text
  Browser / Locust load generator
              │
              ▼
     ┌─────────────────┐
     │ Envoy (8080)    │  frontend-proxy: one port for every UI
     └────────┬────────┘
              ▼
     ┌─────────────────┐      ┌──────────────┐
     │ frontend        │─────▶│ product-     │──▶ PostgreSQL
     │ Next.js         │      │ catalog (Go) │
     └────────┬────────┘      └──────────────┘
              ▼
     ┌─────────────────┐  gRPC  ┌──────────────────────────────────────┐
     │ checkout (Go)   │───────▶│ cart (.NET) → Valkey                 │
     └────────┬────────┘        │ payment (Node) · shipping (Rust)     │
              │                 │ currency (C++) · email (Ruby)        │
              │                 │ quote (PHP)                          │
              ▼                 └──────────────────────────────────────┘
          ┌───────┐
          │ Kafka │──▶ accounting (.NET) · fraud-detection (Kotlin)
          └───────┘

  every service ──OTLP──▶ OpenTelemetry Collector
                              ├──▶ Jaeger      (traces)
                              ├──▶ Prometheus  (metrics, incl. span metrics)
                              ├──▶ OpenSearch  (logs)
                              └──▶ Grafana     (dashboards over all three)

  flagd ── feature flags ──▶ fault injection in any service
```

---

## 🛠️ Tech Stack

| Service | Language | Role |
| --- | --- | --- |
| 🛒 frontend | TypeScript (Next.js) | Storefront UI + server-side API |
| 🚪 frontend-proxy | Envoy | Single entry point, routes to all UIs |
| 💳 checkout | Go | Orchestrates the order flow |
| 📦 product-catalog | Go | Product data from PostgreSQL |
| 🛍️ cart | C# (.NET) | Cart state in Valkey |
| 💰 payment | JavaScript (Node.js) | Card charges |
| 🚚 shipping | Rust | Shipping quotes and tracking |
| 💱 currency | C++ | Currency conversion |
| ✉️ email | Ruby | Order confirmation emails |
| 🧾 quote | PHP | Shipping cost calculation |
| ⭐ recommendation | Python | Product recommendations |
| 📢 ad | Java | Contextual ads |
| 📊 accounting | C# (.NET) | Consumes orders from Kafka |
| 🕵️ fraud-detection | Kotlin | Consumes orders from Kafka |
| 🎚️ flagd + flagd-ui | Go / Elixir | Feature flags for fault injection |
| 🤖 agent, chatbot, mcp | Python (LangGraph) | AI shopping assistant + MCP server |
| 🐝 load-generator | Python (Locust) | Simulated user traffic |

| Layer | Technology |
| --- | --- |
| 📡 Telemetry pipeline | OpenTelemetry Collector |
| 🔍 Traces | Jaeger |
| 📈 Metrics | Prometheus |
| 📜 Logs | OpenSearch |
| 🖥️ Dashboards | Grafana — 10 provisioned dashboards (APM, span metrics, exemplars, PostgreSQL, collector self-monitoring, …) |
| 📨 Messaging | Kafka |
| 🗄️ Storage | PostgreSQL, Valkey |
| 🐳 Deployment | Docker Compose (Kubernetes via the upstream Helm chart) |

---

## 💥 Failure Scenarios

Every scenario is a flagd feature flag. Toggle it at
`http://localhost:8080/feature/` and the fault starts immediately.

| Flag | What breaks |
| --- | --- |
| `paymentFailure` | Payment charges fail n% of the time |
| `paymentUnreachable` | Payment service is unavailable |
| `cartFailure` | Cart service fails n% of the time |
| `failedReadinessProbe` | Cart readiness probe fails |
| `productCatalogFailure` | Product catalog fails on a specific product |
| `productCatalogLockContention` | Lock contention on the product catalog database |
| `recommendationCacheFailure` | Recommendation cache fails |
| `adFailure` | Ad service fails |
| `adHighCpu` | High CPU load in the ad service |
| `adManualGc` | Full manual garbage collections in the ad service |
| `emailMemoryLeak` | Memory leak in the email service |
| `kafkaQueueProblems` | Kafka queue overload + consumer delay → lag spike |
| `intlShippingSlowdown` | International shipping responses are delayed |
| `imageSlowLoad` | Frontend images load slowly |
| `loadGeneratorFloodHomepage` | Floods the frontend with requests |
| `aiSlowResponse` | Slow LLM responses in the agent service |
| `aiRunawayAgent` | Agent loops tool calls until its recursion limit |

---

## ⚡ Quick Start

### Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- **6 GB RAM** allocated to Docker minimum

### 1 — Clone

```bash
git clone https://github.com/Khushipatel27/traceforge.git
cd traceforge
```

### 2 — Launch

```bash
make start            # full stack
make start-minimal    # fewer services, lighter on RAM
make start-agentic    # full stack + AI agent, chatbot and MCP server
```

Without `make` (e.g. on Windows):

```bash
docker compose --env-file .env --env-file .env.override -f compose.yaml -f compose.full.yaml -f compose.observability.yaml -f compose.extras.yaml up --force-recreate --remove-orphans --detach
```

### 3 — Open

| UI | URL |
| --- | --- |
| 🛒 Storefront | <http://localhost:8080> |
| 🖥️ Grafana | <http://localhost:8080/grafana/> |
| 🔍 Jaeger | <http://localhost:8080/jaeger/ui/> |
| 🎚️ Feature flags | <http://localhost:8080/feature/> |
| 🐝 Load generator | <http://localhost:8080/loadgen/> |

### 4 — Break something

1. Open the feature flag UI and turn on `paymentFailure`.
2. Wait a minute for the load generator to place orders.
3. In Jaeger, search service `checkout` with tag `error=true` and follow the span into `payment`.
4. In Grafana, open the span metrics dashboard and watch the payment error rate climb.

Stop everything with `make stop`.

---

## 🧪 Testing

Telemetry sanity tests run in a Dockerized pytest container on the same network
as the stack, and query the backends directly to check that every service is
producing telemetry.

| Test file | Checks |
| --- | --- |
| `test_traces.py` | Each service emits traces to Jaeger |
| `test_traces_edges.py` | Expected service-to-service call edges exist |
| `test_metrics.py` | Each service emits metrics to Prometheus |
| `test_logs.py` | Each service emits logs to OpenSearch |
| `test_collector.py` | The collector pipeline itself is healthy |
| `test_agentic.py` | AI agent / MCP telemetry |

```bash
make run-telemetry-tests            # full stack
make run-telemetry-tests-minimal    # minimal stack
make run-frontend-tests             # Cypress end-to-end tests for the storefront
```

---

## 🔀 What's Mine vs Upstream

| Area | Source |
| --- | --- |
| Microservices, instrumentation, collector config, dashboards, failure flags, tests | Upstream (OpenTelemetry Authors) |
| TraceForge branding, this README | This fork |
| Incident-triage agent (v2) | This fork — in progress |
| v1 vs v2 evaluation over injected faults | This fork — planned |

---

## ⚠️ Known Limitations

- **Heavy.** The full stack runs 20+ containers; under 6 GB of Docker RAM,
  services get OOM-killed and the telemetry looks like a failure that isn't one.
- **Simulated traffic.** Load comes from Locust, so traffic patterns are
  regular in a way real users aren't. Anomalies stand out more cleanly than they
  would in production.
- **One fault at a time.** The flags are designed to be tested individually;
  combining them produces overlapping symptoms that are hard to attribute.

---

## 🔮 Future Improvements

- [ ] Incident-triage agent — trace, metrics and log specialists + verification
- [ ] Reproducible fault-injection benchmark (one run per flag) to fill the v1 vs v2 table
- [ ] SLO dashboard with error-budget burn-rate alerts per service
- [ ] Alertmanager → triage agent hook, so diagnosis starts on alert
- [ ] Written inject → detect → diagnose walkthroughs for each failure flag

---

## 📄 License

Apache License 2.0 — see [LICENSE](./LICENSE). Original source files keep their
`Copyright The OpenTelemetry Authors` headers.

*Built to learn observability the way it's practised in production: by breaking things and reading the telemetry.*
