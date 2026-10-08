# 🔭 TraceForge

### AI-Powered Observability, Root Cause Analysis & Automated Incident Triage

**17 Services | 11 Languages | 17 Failure Flags | Distributed Tracing | Metrics | Logs | AI-Powered Incident Diagnosis**

![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Observability-blue)
![Docker](https://img.shields.io/badge/Docker-Containerization-blue)
![Jaeger](https://img.shields.io/badge/Jaeger-Distributed%20Tracing-orange)
![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-orange)
![Grafana](https://img.shields.io/badge/Grafana-Dashboards-orange)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-AI%20Agents-purple)
![License](https://img.shields.io/badge/License-Apache%202.0-green)

TraceForge is an end-to-end observability and AI-powered incident-triage platform built using the OpenTelemetry Astronomy Shop microservices ecosystem.

The project combines distributed tracing, real-time metrics, centralized logging, fault injection, and a multi-agent AI diagnosis pipeline to identify service failures and explain their root causes.

The platform demonstrates how complex distributed systems can be monitored, investigated, and diagnosed using telemetry-driven reasoning.

**The goal:** Transform raw observability data into actionable incident diagnoses while reducing the manual investigation required to identify failures across interconnected microservices.

This implementation builds upon the open-source OpenTelemetry Demo, which provides the microservices, instrumentation, observability infrastructure, and existing fault-injection scenarios. TraceForge extends that foundation with an incident-triage agent, a golden-signals baseline, deterministic evidence ranking, explanation verification, and a reproducible evaluation benchmark.

---

## 📊 v1 vs v2 — Performance Comparison

I implemented and evaluated two incident-diagnosis approaches to understand how AI-assisted telemetry analysis compares with conventional metrics-based monitoring.

### 🔹 v1 — Golden-Signals Baseline

The first version uses traditional observability metrics to identify potentially failing services.

It collects:

- Per-service error rates
- 95th-percentile response latency (p95)
- Prometheus metrics
- Service-level performance changes

The baseline identifies the service showing the largest relevant deviation in error rate or latency.

This represents the type of first-pass investigation an on-call engineer might perform using a conventional RED metrics dashboard.

### 🔹 v2 — AI-Powered Incident-Triage Agent

The second version introduces an automated incident-triage pipeline that correlates multiple sources of telemetry.

The pipeline includes:

- Metrics analysis specialist
- Distributed tracing specialist
- Centralized logging specialist
- Deterministic evidence ranking
- LLM-generated incident explanation
- Evidence verification

Instead of relying only on which service shows the largest error or latency increase, v2 investigates where failures originate and how they propagate across service dependencies.

### 🧪 Evaluation Methodology

Both versions were evaluated against the same fault-injection scenarios.

Each experiment followed a controlled process:

1. Disable all existing failure flags.
2. Allow the system to return to normal operating conditions.
3. Enable one fault-injection feature flag.
4. Generate traffic through the simulated load generator.
5. Collect traces, metrics, and logs.
6. Execute v1 and v2 diagnostic pipelines.
7. Evaluate diagnosis results at 60, 120, and 240 seconds.
8. Compare predictions against the expected failure.
9. Record accuracy, diagnosis time, and supporting evidence.
10. Disable the injected fault and recover the environment.

### 📈 Benchmark Results

| Metric | v1 — Golden-Signals Baseline | v2 — Triage Agent |
|---|---|---|
| Root-cause service correctly identified | 5/12 | 8/12 |
| Fault type correctly identified | 4/12 | 7/12 |
| Median time to diagnosis | 120 seconds | 80 seconds |
| Verified evidence citations | Not supported | 3/12 |
| Distributed tracing analysis | No | Yes |
| Centralized log analysis | No | Yes |
| CPU and memory analysis | No | Yes |
| Traffic anomaly detection | No | Yes |
| AI-generated explanations | No | Yes |
| Evidence verification | No | Yes |

### 🎯 Key Results

The evaluation demonstrated measurable improvements in automated incident diagnosis.

- Root-cause identification improved from **5/12 to 8/12**.
- Fault-type identification improved from **4/12 to 7/12**.
- Median diagnosis time among correctly diagnosed incidents decreased from **120 seconds to 80 seconds**.
- The system successfully identified failures that propagated through multiple microservices.
- Distributed tracing provided additional context for separating root causes from downstream symptoms.
- AI-generated summaries converted technical telemetry into more understandable incident explanations.

These results represent a 12-scenario benchmark rather than a production-scale evaluation.

### 🔍 Fault-by-Fault Results

| Fault Injection | Expected Root Cause | v1 Diagnosis | v2 Diagnosis |
|---|---|---|---|
| `paymentFailure` | payment / errors | checkout / errors ❌ | payment / errors ✅ |
| `paymentUnreachable` | payment / errors | checkout / errors ❌ | payment / errors ✅ |
| `cartFailure` | cart / errors | Not detected ❌ | Not detected ❌ |
| `adFailure` | ad / errors | ad / errors ✅ | ad / errors ✅ |
| `productCatalogLockContention` | product-catalog or DB / latency | recommendation / latency ❌ | recommendation / latency ❌ |
| `intlShippingSlowdown` | shipping / latency | shipping / latency ✅ | shipping / latency ✅ |
| `adHighCpu` | ad / CPU | shipping / latency ❌ | payment / memory ❌ |
| `adManualGc` | ad / latency or CPU | ad / latency ✅ | ad / latency ✅ |
| `kafkaQueueProblems` | Kafka or consumer / queue | fraud-detection / latency 🟡 | fraud-detection / latency 🟡 |
| `loadGeneratorFloodHomepage` | frontend / traffic | Not detected ❌ | frontend / traffic ✅ |
| `recommendationCacheFailure` | recommendation / memory or latency | recommendation / latency ✅ | recommendation / memory ✅ |
| `emailMemoryLeak` | email / memory | Not detected ❌ | Not detected ❌ |

**Result interpretation:**

- ✅ Correct service and fault classification
- 🟡 Correct service but incorrect fault classification
- ❌ Incorrect or missing root-cause identification

### 🧠 LLM Ablation Study

I also evaluated whether allowing the language model to independently select the root cause improved performance.

The experiment compared:

1. Deterministic evidence-based ranking.
2. LLM-based root-cause selection using the same evidence.

The `llama3.2` model achieved the same root-cause accuracy of **8/12**.

This showed that allowing the model to override the evidence ranking did not improve accuracy in this benchmark.

The final architecture therefore separates the responsibilities:

- **Deterministic analysis identifies the root cause.**
- **The LLM generates a readable explanation.**
- **Verification checks the explanation against observed evidence.**

This approach reduces dependence on unconstrained language-model predictions.

### 📋 Evaluation Considerations

The benchmark includes several important considerations.

- Only 12 valid failure scenarios were evaluated.
- Two payment scenarios were also used during development and debugging.
- Diagnostic results were checked at discrete intervals of 60, 120, and 240 seconds.
- The v2 diagnostic process included approximately 7–37 seconds of LLM computation on CPU.
- The evidence verifier used stricter citation requirements than the explanation-generation prompt.
- The `emailMemoryLeak` scenario was repeated after an interrupted experiment.
- `productCatalogFailure` was excluded because its targeting configuration prevented the intended fault from activating.

**Raw benchmark results:**

[src/triage/results/final.json](src/triage/results/final.json)

**Evaluation implementation:**

[src/triage/run_eval.py](src/triage/run_eval.py)

---

## 💡 The Shop — Distributed Microservices Environment

TraceForge operates on the OpenTelemetry Astronomy Shop, a distributed e-commerce application designed to demonstrate observability in complex microservices environments.

The application includes:

- Storefront and product browsing
- Shopping cart management
- Checkout orchestration
- Payment processing
- Shipping calculations
- Currency conversion
- Product recommendations
- Advertisement services
- Fraud detection
- Accounting
- Order confirmation emails
- AI shopping assistance

The environment consists of services implemented in multiple programming languages and connected through synchronous API communication, data stores, and asynchronous messaging.

Every instrumented service produces observability data through OpenTelemetry.

### 📡 Telemetry Collection

The telemetry pipeline collects three primary types of operational data.

**1. Distributed Traces**

Traces capture requests traveling across multiple services and help identify:

- Service dependencies
- Error propagation
- Slow operations
- Latency bottlenecks
- Failure origins
- Request execution paths

**2. Metrics**

Metrics provide numerical measurements such as:

- Request rates
- Error ratios
- Response latency
- CPU consumption
- Memory utilization
- Kafka consumer lag
- Service performance trends

**3. Logs**

Centralized logs provide additional diagnostic information, including:

- Error messages
- Service exceptions
- Application events
- Failure patterns
- Service-specific operational context

The OpenTelemetry Collector processes and exports this information to the configured observability backends.

### 💥 Fault Injection

The environment includes feature flags that simulate operational failures.

Examples include:

- Payment failures affecting a percentage of transactions
- Unreachable payment services
- Database lock contention
- Memory leaks
- Increased CPU usage
- Slow shipping responses
- Kafka consumer delays
- Unexpected traffic spikes

By activating individual failure flags, I can create controlled incidents and evaluate whether the diagnosis pipeline correctly identifies their causes.

---

## 🧠 v2 — Multi-Agent Incident-Triage System

The main TraceForge extension is the automated incident-triage layer.

It uses telemetry collected from the distributed application to generate an evidence-backed root-cause diagnosis.

The pipeline combines specialist analysis with deterministic ranking and language-model-generated explanations.

### 🔄 Incident-Triage Workflow

```text
                  ┌──────────────────────┐
                  │   Incident Trigger   │
                  │   / Fault Injection  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   Triage Supervisor  │
                  └──────────┬───────────┘
                             │
             ┌───────────────┼───────────────┐
             │               │               │
             ▼               ▼               ▼
    ┌────────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Metrics Agent  │ │ Trace Agent  │ │  Log Agent   │
    │                │ │              │ │              │
    │  Prometheus    │ │    Jaeger    │ │  OpenSearch  │
    └────────┬───────┘ └──────┬───────┘ └──────┬───────┘
             │                │                │
             └────────────────┼────────────────┘
                              │
                              ▼
                   ┌────────────────────┐
                   │  Evidence Ranking  │
                   │  & Root Cause      │
                   │  Identification    │
                   └──────────┬─────────┘
                              │
                              ▼
                   ┌────────────────────┐
                   │ LLM Explanation    │
                   │ Generation         │
                   └──────────┬─────────┘
                              │
                              ▼
                   ┌────────────────────┐
                   │ Evidence           │
                   │ Verification       │
                   └──────────┬─────────┘
                              │
                              ▼
                   ┌────────────────────┐
                   │ Final Incident     │
                   │ Diagnosis          │
                   └────────────────────┘
