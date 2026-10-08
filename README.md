
# 🔭 TraceForge

### AI-Powered Observability, Root Cause Analysis & Automated Incident Triage

**17 Services | 11 Languages | 17 Failure Flags | Distributed Tracing | Metrics | Logs | AI-Powered Incident Diagnosis**

![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Observability-blue)
![Docker](https://img.shields.io/badge/Docker-Containerization-blue)
![Jaeger](https://img.shields.io/badge/Jaeger-Tracing-orange)
![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-orange)
![Grafana](https://img.shields.io/badge/Grafana-Dashboards-orange)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-AI%20Agents-purple)
![License](https://img.shields.io/badge/License-Apache%202.0-green)

TraceForge is an end-to-end observability and AI-powered incident-triage platform built on the OpenTelemetry Astronomy Shop microservices ecosystem.

The project combines distributed tracing, real-time metrics, centralized logging, fault injection, and a multi-agent diagnosis pipeline to identify service failures and explain their root causes.

**The goal:** Transform raw observability data into actionable incident diagnoses while reducing the manual investigation required to identify failures across interconnected microservices.

The implementation extends the open-source OpenTelemetry Demo with an incident-triage agent, a golden-signals baseline, deterministic evidence ranking, explanation verification, and a reproducible evaluation benchmark.

---

## 📊 v1 vs v2 — Performance Comparison

I implemented and evaluated two incident-diagnosis approaches to understand how multi-signal telemetry analysis compares with conventional metrics-based monitoring.

### 🔹 v1 — Golden-Signals Baseline

The first version uses traditional observability metrics to identify potentially failing services.

It collects:

- Per-service error rates
- 95th-percentile response latency (p95)
- Prometheus metrics
- Service-level performance changes

The baseline identifies the service showing the largest relevant deviation in error rate or latency.

This represents the first-pass investigation an on-call engineer might perform using a conventional RED metrics dashboard.

### 🔹 v2 — AI-Powered Incident-Triage Agent

The second version introduces an automated incident-triage pipeline that correlates multiple telemetry sources.

It includes:

- Metrics analysis specialist
- Distributed tracing specialist
- Centralized logging specialist
- Deterministic evidence ranking
- LLM-generated incident explanation
- Evidence verification

Rather than relying only on which service shows the largest error or latency increase, v2 investigates where failures originate and how they propagate across service dependencies.

### 🧪 Evaluation Methodology

Both versions were evaluated against the same fault-injection scenarios.

Each experiment followed a controlled process:

1. Disable existing failure flags.
2. Allow the system to return to normal conditions.
3. Enable one fault-injection flag.
4. Generate application traffic through Locust.
5. Collect traces, metrics, and logs.
6. Execute v1 and v2 diagnostic pipelines.
7. Evaluate diagnoses at 60, 120, and 240 seconds.
8. Compare predictions with the expected failure.
9. Record accuracy, diagnosis time, and supporting evidence.
10. Disable the fault and recover the environment.

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

- Root-cause identification improved from **5/12 to 8/12**.
- Fault-type identification improved from **4/12 to 7/12**.
- Median reported diagnosis time decreased from **120 seconds to 80 seconds**.
- Distributed tracing helped distinguish actual failures from downstream symptoms.
- Traffic-rate analysis detected an incident missed by the baseline.
- AI-generated explanations converted technical telemetry into readable incident summaries.

These results represent a small 12-scenario benchmark, not production-scale performance.

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

I evaluated whether allowing the language model to independently select the root cause improved performance.

The experiment compared:

1. Deterministic evidence-based ranking.
2. LLM-based root-cause selection using the same evidence.

The `llama3.2` model achieved the same root-cause accuracy of **8/12**.

This showed that allowing the model to override evidence ranking did not improve accuracy in the evaluated scenarios.

The final architecture separates responsibilities:

- **Deterministic analysis identifies the root cause.**
- **The LLM generates a readable explanation.**
- **Verification checks the explanation against observed evidence.**

### 📋 Evaluation Considerations

- Only 12 valid fault scenarios were evaluated.
- Two payment scenarios were also used during development and debugging.
- Diagnostics were checked at discrete 60-, 120-, and 240-second intervals.
- v2 included approximately 7–37 seconds of LLM computation on CPU.
- The verifier used stricter citation requirements than the explanation prompt.
- `emailMemoryLeak` was repeated after the original run was interrupted.
- `productCatalogFailure` was excluded because targeting rules prevented the intended fault from activating.

**Raw benchmark results:** [src/triage/results/final.json](src/triage/results/final.json)

**Evaluation implementation:** [src/triage/run_eval.py](src/triage/run_eval.py)

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
- Advertisements
- Fraud detection
- Accounting
- Order confirmation emails
- AI shopping assistance

The environment consists of multiple services implemented in different programming languages and connected through APIs, data stores, and asynchronous messaging.

The services produce observability data through OpenTelemetry.

### 📡 Telemetry Collection

The telemetry pipeline collects three primary types of operational data.

**1. Distributed Traces**

Traces capture requests traveling across services and help identify:

- Service dependencies
- Error propagation
- Slow operations
- Latency bottlenecks
- Failure origins
- Request execution paths

**2. Metrics**

Metrics provide measurements including:

- Request rates
- Error ratios
- Response latency
- CPU consumption
- Memory utilization
- Kafka consumer lag
- Service performance trends

**3. Logs**

Centralized logs provide additional diagnostic information:

- Error messages
- Service exceptions
- Application events
- Failure patterns
- Operational context

The OpenTelemetry Collector processes and exports this telemetry to configured observability backends.

### 💥 Fault Injection

The environment includes feature flags that simulate operational failures.

Examples include:

- Payment transaction failures
- Unreachable payment services
- Database lock contention
- Memory leaks
- Increased CPU usage
- Slow shipping responses
- Kafka consumer delays
- Unexpected traffic spikes

Each controlled failure can be used to evaluate the incident-diagnosis pipeline.

---

## 🧠 v2 — Multi-Agent Incident-Triage System

The TraceForge-specific extension is the automated incident-triage layer.

It processes telemetry collected from distributed services to generate evidence-backed root-cause diagnoses.

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
    │   Prometheus   │ │    Jaeger    │ │  OpenSearch  │
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
```

### 🤖 Agent Responsibilities

| Agent | Data Source | Responsibility |
|---|---|---|
| Metrics Agent | Prometheus | Detects error-rate, latency, CPU, memory, queue-lag, and traffic anomalies |
| Trace Agent | Jaeger | Identifies failure origins, dependencies, and execution bottlenecks |
| Log Agent | OpenSearch | Detects error-log frequency changes and extracts sample messages |
| Evidence Ranking | Combined telemetry | Ranks likely root-cause services |
| LLM Explanation | Ranked evidence | Generates readable incident summaries |
| Verification | Collected evidence | Validates attribution, numerical values, and citations |

### 📈 Metrics Specialist

The metrics specialist retrieves and analyzes performance information from Prometheus using PromQL.

It examines:

- Error-rate changes
- p95 latency changes
- CPU utilization
- Memory consumption
- Request-rate anomalies
- Kafka consumer lag
- Baseline-versus-incident differences

### 🔍 Distributed Tracing Specialist

The tracing specialist queries Jaeger to understand request propagation.

It examines:

- Error-producing spans
- Parent-child span relationships
- Service dependency paths
- Downstream error propagation
- Operation durations
- Service self-time

For example, a payment failure may also generate checkout errors.

A metrics-only approach may incorrectly blame checkout.

Trace analysis can follow the request to the payment operation and identify the actual failure origin.

### 📜 Logging Specialist

The logging specialist analyzes centralized logs stored in OpenSearch.

It evaluates:

- Error-log volume changes
- Service-specific error spikes
- Representative error messages
- Changes between baseline and incident periods

### 🧮 Deterministic Evidence Ranking

TraceForge combines specialist findings into an evidence-based ranking.

The ranking attempts to distinguish direct causes from propagated symptoms.

Rather than asking an LLM to infer root causes directly from raw telemetry, Python computes measurements and applies the root-cause ranking logic.

### 📝 LLM Incident Explanation

The language model generates an explanation describing:

- Suspected failing service
- Observed fault type
- Relevant telemetry evidence
- Impact on connected services
- Reason for selecting the likely root cause

The implementation uses `llama3.2` through Ollama.

### ✅ Evidence Verification

The verification stage checks that:

- The explanation identifies the ranked service.
- Cited evidence exists in collected telemetry.
- Numerical values match recorded measurements.
- Unsupported metrics are not introduced.

The current verifier restricts citations to the blamed service, which leads to some explanations about downstream impact failing verification.

---

## ⚙️ Technical Design Decisions

### 1. Trace Origins Instead of Error Volume

Failures propagate through dependent services.

A downstream failure may create upstream error spikes.

TraceForge examines distributed traces to identify where failures begin rather than assuming the service with the largest error count is responsible.

### 2. Counter Difference Calculations

OpenTelemetry span metrics may reach Prometheus at relatively long intervals.

In short observation windows, `increase()` can fail to capture newly appearing error-counter series.

The implementation compares current counter values against values at the beginning of the observation window, treating missing initial values as zero.

### 3. Delayed Trace Analysis

Very recent distributed traces may be incomplete because services export spans in batches.

The tracing specialist excludes approximately the newest 20 seconds of trace data to reduce false attribution caused by partially exported traces.

### 4. Separation of Diagnosis and Explanation

The system separates deterministic numerical analysis from natural-language generation.

- Python handles measurements.
- Evidence ranking selects the likely root cause.
- The LLM explains the diagnosis.
- Verification checks the explanation.

### 5. Baseline and Incident Comparison

Telemetry is evaluated relative to normal system behavior.

This helps distinguish meaningful deviations from ordinary variations in performance and traffic.

---

## 🏗️ Architecture

```text
                        ┌─────────────────────┐
                        │   User / Browser    │
                        └──────────┬──────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │   Frontend Proxy    │
                        │       Envoy         │
                        └──────────┬──────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │  Frontend Service   │
                        │      Next.js        │
                        └──────────┬──────────┘
                                   │
                     ┌─────────────┴─────────────┐
                     │                           │
                     ▼                           ▼
          ┌─────────────────────┐     ┌─────────────────────┐
          │ Product / Cart /    │     │ Checkout / Payment  │
          │ Recommendation      │     │ Shipping / Email    │
          └──────────┬──────────┘     └──────────┬──────────┘
                     │                           │
                     └─────────────┬─────────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │ OpenTelemetry SDKs  │
                        │ & Instrumentation   │
                        └──────────┬──────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │ OpenTelemetry       │
                        │ Collector           │
                        └──────────┬──────────┘
                                   │
               ┌───────────────────┼────────────────────┐
               │                   │                    │
               ▼                   ▼                    ▼
       ┌──────────────┐   ┌──────────────┐    ┌──────────────┐
       │    Jaeger    │   │  Prometheus  │    │  OpenSearch  │
       │    Traces    │   │   Metrics    │    │     Logs     │
       └──────┬───────┘   └──────┬───────┘    └──────┬───────┘
              │                  │                   │
              └──────────────────┼───────────────────┘
                                 │
                                 ▼
                      ┌────────────────────┐
                      │ TraceForge Triage  │
                      │ Agent Pipeline     │
                      └──────────┬─────────┘
                                 │
                                 ▼
                      ┌────────────────────┐
                      │ Root-Cause         │
                      │ Diagnosis          │
                      └────────────────────┘
```

### 🔗 Supporting Infrastructure

The environment also includes:

- Kafka for asynchronous messaging
- PostgreSQL for product data
- Valkey for cart state
- flagd for controlled fault injection
- Grafana for observability dashboards
- Locust for simulated traffic
- Docker Compose for service orchestration

---

## 🛠️ Tech Stack

### 🧩 Microservices

| Service | Language / Technology | Responsibility |
|---|---|---|
| 🛒 frontend | TypeScript / Next.js | Storefront UI and API |
| 🚪 frontend-proxy | Envoy | Application routing |
| 💳 checkout | Go | Checkout orchestration |
| 📦 product-catalog | Go | Product information and PostgreSQL integration |
| 🛍️ cart | C# / .NET | Shopping cart management |
| 💰 payment | JavaScript / Node.js | Payment processing |
| 🚚 shipping | Rust | Shipping operations |
| 💱 currency | C++ | Currency conversion |
| ✉️ email | Ruby | Order confirmation emails |
| 🧾 quote | PHP | Shipping quote calculation |
| ⭐ recommendation | Python | Product recommendations |
| 📢 ad | Java | Advertisement service |
| 📊 accounting | C# / .NET | Kafka order processing |
| 🕵️ fraud-detection | Kotlin | Fraud detection |
| 🎚️ flagd / flagd-ui | Go / Elixir | Feature-flag management |
| 🤖 agent / chatbot / mcp | Python / LangGraph | AI shopping assistant and MCP |
| 🐝 load-generator | Python / Locust | Simulated traffic |

These microservices originate from the OpenTelemetry Demo and serve as the underlying distributed application.

### 📡 Observability & Infrastructure

| Layer | Technology | Purpose |
|---|---|---|
| Instrumentation | OpenTelemetry | Distributed telemetry |
| Telemetry Pipeline | OpenTelemetry Collector | Telemetry processing and export |
| Distributed Tracing | Jaeger | Trace investigation |
| Metrics | Prometheus | Time-series metrics and PromQL |
| Logging | OpenSearch | Centralized log analysis |
| Visualization | Grafana | Operational dashboards |
| Messaging | Kafka | Asynchronous communication |
| Database | PostgreSQL | Relational storage |
| Cache | Valkey | Cart state |
| Deployment | Docker Compose | Container orchestration |
| Failure Injection | flagd | Fault simulation |
| Load Testing | Locust | Traffic simulation |

### 🧠 AI & Evaluation

| Component | Technology |
|---|---|
| Incident Triage | Python |
| Specialist Analysis | Metrics, traces, and logs |
| Language Model | llama3.2 |
| Local LLM Runtime | Ollama |
| Demo AI Agent Framework | LangGraph |
| Root-Cause Ranking | Deterministic Python |
| Benchmark Automation | Python |
| Telemetry Testing | pytest |
| Frontend Testing | Cypress |

---

## 💥 Failure Scenarios

The platform supports 17 feature-flag-controlled failure scenarios.

| Feature Flag | Failure Simulation |
|---|---|
| `paymentFailure` | Payment charges fail for a configured percentage of requests |
| `paymentUnreachable` | Payment service becomes unavailable |
| `cartFailure` | Cart operations fail |
| `failedReadinessProbe` | Cart readiness probe fails |
| `productCatalogFailure` | Product catalog fails for a targeted product |
| `productCatalogLockContention` | Database lock contention |
| `recommendationCacheFailure` | Recommendation cache failures |
| `adFailure` | Advertisement service errors |
| `adHighCpu` | High CPU utilization in ad service |
| `adManualGc` | Manual garbage collection in ad service |
| `emailMemoryLeak` | Email service memory growth |
| `kafkaQueueProblems` | Kafka queue overload and consumer lag |
| `intlShippingSlowdown` | Slow international shipping |
| `imageSlowLoad` | Slow frontend image loading |
| `loadGeneratorFloodHomepage` | Unusually high frontend traffic |
| `aiSlowResponse` | Slow AI responses |
| `aiRunawayAgent` | Repeated AI tool calls until recursion limit |

### 🔬 Incident Simulation Workflow

```text
Normal Application Behavior
            │
            ▼
Select Failure Scenario
            │
            ▼
Activate Feature Flag
            │
            ▼
Simulated Traffic Triggers Failure
            │
            ▼
Telemetry Collection
            │
            ▼
Metrics + Traces + Logs
            │
            ▼
Incident-Triage Pipeline
            │
            ▼
Root-Cause Identification
            │
            ▼
AI-Generated Incident Explanation
            │
            ▼
Verification + Evaluation
            │
            ▼
Disable Fault + System Recovery
```

---

## ⚡ Quick Start

### 📋 Prerequisites

Install:

- Docker Desktop or Docker Engine
- Docker Compose v2
- Git
- Make (optional)
- Ollama for LLM-assisted triage evaluation

Allocate at least **6 GB RAM** to Docker.

### 1 — Clone the Repository

```bash
git clone https://github.com/Khushipatel27/traceforge.git
cd traceforge
```

### 2 — Start the Application

Full stack:

```bash
make start
```

Minimal stack:

```bash
make start-minimal
```

Full stack with AI shopping agent, chatbot, and MCP server:

```bash
make start-agentic
```

### 🐳 Alternative — Docker Compose

```bash
docker compose \
  --env-file .env \
  --env-file .env.override \
  -f compose.yaml \
  -f compose.full.yaml \
  -f compose.observability.yaml \
  -f compose.extras.yaml \
  up --force-recreate --remove-orphans --detach
```

### 3 — Access the Services

| Interface | URL |
|---|---|
| 🛒 Astronomy Shop | http://localhost:8080 |
| 🖥️ Grafana | http://localhost:8080/grafana/ |
| 🔍 Jaeger | http://localhost:8080/jaeger/ui/ |
| 🎚️ Feature Flags | http://localhost:8080/feature/ |
| 🐝 Load Generator | http://localhost:8080/loadgen/ |

### 4 — Inject a Failure

1. Open the feature-flag UI.
2. Locate `paymentFailure`.
3. Enable the flag.
4. Allow Locust to generate checkout requests.
5. Observe the changes in Grafana.
6. Inspect corresponding traces in Jaeger.
7. Run the diagnosis pipeline to analyze collected evidence.

### 5 — Investigate the Failure

**Using Jaeger:**

1. Open Jaeger.
2. Select the `checkout` service.
3. Search for traces containing `error=true`.
4. Inspect the span relationships.
5. Follow the request from checkout to payment.
6. Identify where the error originates.

**Using Grafana:**

1. Open Grafana.
2. Navigate to the span-metrics dashboard.
3. Inspect service error rates.
4. Compare p95 latency and request behavior.
5. Observe changes associated with the fault.

### 6 — Stop the Environment

```bash
make stop
```

---

## 🧪 Testing

TraceForge includes telemetry validation and incident-triage evaluation workflows.

### 🔎 Telemetry Validation

The OpenTelemetry Demo includes Dockerized pytest tests that verify whether services produce telemetry.

| Test File | Validation |
|---|---|
| `test_traces.py` | Traces reach Jaeger |
| `test_traces_edges.py` | Expected service dependencies exist |
| `test_metrics.py` | Metrics reach Prometheus |
| `test_logs.py` | Logs reach OpenSearch |
| `test_collector.py` | Collector pipeline is healthy |
| `test_agentic.py` | Agent and MCP telemetry |

Run full-stack tests:

```bash
make run-telemetry-tests
```

Run minimal-stack tests:

```bash
make run-telemetry-tests-minimal
```

Run frontend tests:

```bash
make run-frontend-tests
```

### 🤖 Triage Benchmark — v1 vs v2

**Requirements:**

- Running application stack
- `LOCUST_USERS=20` in `.env.override`
- Ollama running on the host
- `llama3.2` downloaded
- Sufficient CPU and memory
- Uninterrupted execution

Download the model:

```bash
ollama pull llama3.2
```

Run the benchmark:

```bash
docker run --rm \
  --network opentelemetry-demo \
  -v "$PWD:/repo" \
  -w /repo/src/triage \
  python:3.12-slim \
  python run_eval.py
```

The complete benchmark takes approximately 90 minutes in the documented environment.

Results are written to:

```text
src/triage/results/
```

For additional instructions, see [src/triage/README.md](src/triage/README.md).

### 📊 Benchmark Evaluation Criteria

- Correct root-cause service identification
- Correct fault-type classification
- Time to identify a failure
- Evidence citation availability
- Explanation verification
- Performance across injected fault types

---

## 🔀 Project Implementation & Contributions

TraceForge combines an existing distributed application with a custom automated incident-triage and benchmarking layer.

The OpenTelemetry Astronomy Shop provides the microservices, telemetry instrumentation, infrastructure, dashboards, and fault-injection capabilities.

The TraceForge-specific implementation extends that foundation with automated diagnosis and evaluation.

| Component | Implementation |
|---|---|
| Distributed microservices | OpenTelemetry Demo |
| OpenTelemetry instrumentation | OpenTelemetry Demo |
| Jaeger, Prometheus, OpenSearch, Grafana | Existing observability environment |
| Docker deployment | Existing demo configuration |
| Feature-flag fault injection | Existing demo functionality |
| v1 golden-signals baseline | TraceForge |
| v2 metrics specialist | TraceForge |
| v2 trace specialist | TraceForge |
| v2 log specialist | TraceForge |
| Root-cause evidence ranking | TraceForge |
| LLM incident explanation | TraceForge |
| Evidence verification | TraceForge |
| Fault-injection benchmark | TraceForge |
| v1 vs v2 performance analysis | TraceForge |
| 20-user traffic configuration | TraceForge |
| Documentation and diagrams | TraceForge |

### 📂 Important Project Files

| File / Directory | Purpose |
|---|---|
| `src/triage/` | Incident-triage implementation |
| `src/triage/README.md` | Triage documentation |
| `src/triage/run_eval.py` | Benchmark execution |
| `src/triage/results/final.json` | Recorded results |
| `.env.override` | Configuration overrides |
| `compose.yaml` | Base Docker Compose configuration |
| `compose.full.yaml` | Full application services |
| `compose.observability.yaml` | Observability services |
| `compose.extras.yaml` | Additional services |
| `compose.agent.yaml` | Agent services |
| `test/telemetry/` | Telemetry tests |
| `docs/images/` | Diagrams |
| `README.md` | Project documentation |

---

## 📊 Key Technical Findings

### 1. Error Propagation Can Mislead Metrics-Based Diagnosis

When the payment service fails, checkout can report errors because it depends on payment.

The v1 baseline identified checkout as the cause in both payment-failure scenarios.

The v2 tracing specialist followed the request path and identified payment as the failure origin.

### 2. Request-Rate Monitoring Improves Traffic Anomaly Detection

The baseline focuses on errors and latency.

During the homepage traffic-flood scenario, these signals did not identify the expected fault.

v2 included request-rate analysis and correctly identified the frontend traffic anomaly.

### 3. Resource-Based Faults Need Signal Normalization

CPU, memory, latency, and error rates have different units and scales.

Their anomaly scores are not always directly comparable.

The `adHighCpu` scenario demonstrated this limitation when a real CPU increase ranked below unrelated signal changes.

### 4. Slow Memory Leaks Require Trend-Based Detection

The `emailMemoryLeak` scenario produced memory growth from approximately 70 MB to 95 MB over four minutes.

The change remained below the configured 30 MB threshold.

Longer-window trend analysis would be more appropriate for detecting slow leaks.

### 5. Database Contention Can Affect Multiple Services

During `productCatalogLockContention`, several dependent services experienced timeout behavior.

The trace specialist observed database self-time increasing from approximately 1 ms to 4.2 seconds, but the ranking did not select the correct root cause.

### 6. LLMs Are Useful for Explaining Evidence-Based Diagnoses

The ablation study found no root-cause accuracy improvement when the language model selected the service independently.

The final architecture therefore uses deterministic analysis for root-cause selection and the language model for explanations.

---

## ⚠️ Known Limitations

### 1. Resource Requirements

The complete environment runs more than 20 containers.

Insufficient Docker memory can cause unexpected container termination and unrelated telemetry anomalies.

At least 6 GB of Docker RAM is recommended.

### 2. Simulated Traffic

Traffic comes from Locust instead of production users.

Regular simulated patterns may make anomalies easier to identify.

### 3. One Fault at a Time

The current benchmark evaluates individual fault scenarios.

Simultaneous failures may produce overlapping symptoms and complicate attribution.

### 4. Resource Signal Ranking

The current scoring approach does not fully normalize CPU, memory, latency, and error-rate changes.

Some resource faults can therefore be outranked by unrelated metrics.

### 5. Slow Memory Leak Detection

Memory growth below a fixed threshold may remain undetected.

Longer-window growth-rate detection is needed.

### 6. Low-Frequency Failure Detection

Some failures affect infrequently executed operations.

For example, `cartFailure` affects `EmptyCart`, which may not occur frequently enough to exceed the noise threshold.

### 7. Database Contention Attribution

Database contention can create latency increases across multiple services.

The ranking may select a downstream service rather than the underlying database-related cause.

### 8. Kafka Queue Classification

The `kafkaQueueProblems` scenario identified the affected consumer but classified the issue as latency instead of queue lag.

Queue-specific scoring needs improvement.

### 9. Evidence Verification Constraints

The explanation generator may cite downstream services when describing an incident.

The current verifier rejects citations that do not refer to the blamed service.

This contributes to the verified-citation score of 3/12.

### 10. CPU-Based LLM Inference

Local Ollama inference runs on CPU.

Explanation generation adds approximately 7–37 seconds and consumes resources on the same system being evaluated.

### 11. Limited Benchmark Size

The benchmark includes 12 valid scenarios.

Additional repetitions, workload variations, and realistic traffic would be required to measure broader reliability.

---

## 🔮 Future Improvements

### ✅ Implemented

- [x] Used the OpenTelemetry microservices environment
- [x] Integrated the existing observability infrastructure
- [x] Used feature-flag-based failure injection
- [x] Implemented the v1 golden-signals baseline
- [x] Developed the v2 incident-triage pipeline
- [x] Added metrics, tracing, and logging specialists
- [x] Implemented deterministic evidence ranking
- [x] Added LLM-generated incident explanations
- [x] Added evidence verification
- [x] Developed a reproducible fault-injection benchmark
- [x] Compared v1 and v2 diagnostic performance
- [x] Documented benchmark results and limitations

### 🚀 Planned Enhancements

- [ ] Normalize anomaly scores across signal types
- [ ] Implement longer-window memory growth detection
- [ ] Improve database contention attribution
- [ ] Improve queue-lag fault classification
- [ ] Align verification rules with the explanation prompt
- [ ] Allow downstream-service evidence citations
- [ ] Correct `productCatalogFailure` targeting
- [ ] Add excluded fault scenarios to the benchmark
- [ ] Repeat evaluations and report variance
- [ ] Add SLO and error-budget burn-rate monitoring
- [ ] Integrate Alertmanager with the triage pipeline
- [ ] Trigger incident diagnosis from alerts
- [ ] Create detailed fault-injection walkthroughs
- [ ] Evaluate simultaneous failures
- [ ] Improve local LLM resource efficiency
- [ ] Evaluate more realistic traffic patterns

---

## 🎯 Project Outcomes

TraceForge demonstrates how combining traditional observability infrastructure with automated evidence analysis can support incident investigation in distributed applications.

### Technical Outcomes

**1. Unified Observability**

Combined distributed traces, metrics, and centralized logs for incident investigation.

**2. Automated Root-Cause Analysis**

Implemented automated ranking of likely failing services using telemetry evidence.

**3. Multi-Signal Diagnosis**

Extended beyond error rates and latency to CPU, memory, request rates, and Kafka behavior.

**4. AI-Assisted Incident Reporting**

Integrated a local language model for readable incident explanations.

**5. Reproducible Evaluation**

Developed a controlled fault-injection benchmark for comparing diagnosis approaches.

**6. Measurable Improvement**

Improved correct root-cause service identification from 5/12 to 8/12 scenarios in the documented evaluation.

### Skills Demonstrated

- Distributed Systems
- Microservices Architecture
- Site Reliability Engineering
- Observability Engineering
- OpenTelemetry
- Distributed Tracing
- Prometheus and PromQL
- OpenSearch Log Analysis
- Root-Cause Analysis
- AI-Assisted Incident Diagnosis
- Python Automation
- LLM Integration
- Benchmark Design
- Docker Containerization
- Performance Monitoring
- Failure Injection
- Reliability Testing

---

## 📚 References & Acknowledgments

TraceForge builds upon the OpenTelemetry Astronomy Shop Demo.

The upstream demo provides the distributed application, service implementations, telemetry instrumentation, observability infrastructure, dashboards, testing framework, and existing failure-injection flags.

TraceForge extends that foundation with automated incident triage, evidence-based root-cause identification, AI-assisted explanations, and evaluation.

**OpenTelemetry Demo:**  
https://github.com/open-telemetry/opentelemetry-demo

**OpenTelemetry Documentation:**  
https://opentelemetry.io/docs/

**Jaeger Documentation:**  
https://www.jaegertracing.io/docs/

**Prometheus Documentation:**  
https://prometheus.io/docs/

**Grafana Documentation:**  
https://grafana.com/docs/

**LangGraph Documentation:**  
https://docs.langchain.com/oss/python/langgraph/overview

**Ollama:**  
https://ollama.com/

---

## 📄 License

This project is distributed under the **Apache License 2.0**.

See [LICENSE](LICENSE) for licensing details.

The upstream OpenTelemetry Demo components remain subject to their original licensing and attribution requirements.

---

## 👩‍💻 Author

**Khushi Patel**

M.S. Applied Data Science  
University of Southern California

**GitHub:** [Khushipatel27](https://github.com/Khushipatel27)

**Repository:** [TraceForge](https://github.com/Khushipatel27/traceforge)

---

### 🔭 TraceForge — From Telemetry to Root Cause

*An observability and incident-triage platform combining distributed systems, telemetry analysis, deterministic reasoning, and AI-generated explanations to investigate microservice failures.*
