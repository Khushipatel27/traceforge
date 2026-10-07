# Triage

Incident triage for TraceForge: given a time window, find the service that is
actually broken and say what kind of fault it is, citing the telemetry that
shows it.

| Module | Role |
| --- | --- |
| `triage/sources.py` | Clients for Prometheus, Jaeger (api/v3) and OpenSearch. Stdlib only. |
| `triage/signals.py` | PromQL signals shared by v1 and v2, each returned with the query that produced it |
| `triage/baseline.py` | **v1**: golden-signals baseline. Blames the service whose error rate or p95 latency moved most. |
| `triage/agents.py` | **v2** specialists: metrics agent, trace agent (error origin + self-time), log agent |
| `triage/supervisor.py` | **v2**: ranks the evidence, LLM writes the explanation, verification checks it |
| `run_eval.py` | Benchmark: inject each flagd fault, ask v1 and v2 at 60 / 120 / 240 s, score |

## Run the benchmark

The stack must be running with `LOCUST_USERS=20` (set in `.env.override`) and
Ollama must be serving `llama3.2` on the host.

```bash
docker run --rm --network opentelemetry-demo -v "$PWD:/repo" -w /repo/src/triage \
  python:3.12-slim python run_eval.py
```

About 90 minutes. The laptop must not sleep: a suspended machine leaves holes in
the telemetry, and any fault overlapping one has to be re-run. Results are written
to `results/` after every fault.

```bash
python run_eval.py --only paymentFailure adFailure    # a subset
python run_eval.py --report results/final.json        # re-print a results table
```

## Design notes

- **The evidence decides; the LLM explains.** Every number is computed in Python.
  A 3B model allowed to pick the root cause overruled a correct ranking during
  development, so its pick is recorded only as an ablation.
- **Error origin beats error volume.** Callers of a failing service show the same
  or higher error ratios. When traces show where errors start, other services'
  error symptoms are treated as propagation.
- **Counters are diffed, not `increase()`d.** Span metrics reach Prometheus about
  once a minute, and an error series is created by its first error, so
  `increase()` over a short window reads ~0 for exactly the series that matter.
- **The newest 20 s of traces are ignored.** Services export spans in batches, so
  a very recent trace is often missing its downstream half.
