"""v1 vs v2 benchmark: inject each fault via flagd, diagnose with both, score.

Runs inside a container on the compose network (see README). For each scenario:

    all flags off -> settle -> inject one flag -> diagnose at each checkpoint
    -> flag off -> next scenario

Results are written after every scenario, so a partial run is still usable.

    python run_eval.py                      # full benchmark
    python run_eval.py --only paymentFailure --checkpoints 60 120
    python run_eval.py --report results/run-XXXX.json   # re-print the table
"""

import argparse
import json
import os
import shutil
import statistics
import sys
import time
import traceback

from triage import baseline, supervisor

FLAG_FILE = os.environ.get("FLAG_FILE", "/repo/src/flagd/demo.flagd.json")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

# flag, variant to inject, services accepted as root cause, fault types accepted.
# Ordered so faults whose effects outlast the flag (memory leaks) run last.
SCENARIOS = [
    ("paymentFailure", "50%", ["payment"], ["errors"]),
    ("paymentUnreachable", "on", ["payment"], ["errors"]),
    ("cartFailure", "50%", ["cart"], ["errors"]),
    ("adFailure", "on", ["ad"], ["errors"]),
    ("productCatalogFailure", "on", ["product-catalog"], ["errors"]),
    ("productCatalogLockContention", "on", ["product-catalog", "astronomy-db"], ["latency"]),
    ("intlShippingSlowdown", "5sec", ["shipping"], ["latency"]),
    ("adHighCpu", "on", ["ad"], ["cpu"]),
    ("adManualGc", "on", ["ad"], ["latency", "cpu"]),
    ("kafkaQueueProblems", "on", ["kafka", "accounting", "fraud-detection"], ["queue"]),
    ("loadGeneratorFloodHomepage", "on", ["frontend", "frontend-proxy"], ["traffic"]),
    ("recommendationCacheFailure", "on", ["recommendation"], ["memory", "latency"]),
    ("emailMemoryLeak", "100x", ["email"], ["memory"]),
]
# Not benchmarked: imageSlowLoad (only visible to real browsers; the load
# generator's browser traffic is off), failedReadinessProbe (Kubernetes only),
# aiSlowResponse / aiRunawayAgent (agent service not in the default stack),
# emitRawPii (not a fault).


def set_flag(original, flag=None, variant=None):
    """No flag: restore the original file (all flags off). Otherwise inject one."""
    if not flag:
        with open(FLAG_FILE, "wb") as f:
            f.write(original)
        return
    data = json.loads(original)
    data["flags"][flag]["defaultVariant"] = variant
    with open(FLAG_FILE, "w") as f:
        f.write(json.dumps(data, indent=2) + "\n")


def correct(ans, services, types):
    svc_ok = ans.get("service") in services
    return svc_ok, svc_ok and ans.get("fault_type") in types


def run(args):
    with open(FLAG_FILE, "rb") as f:
        original = f.read()  # bytes: restored exactly, line endings included
    backup = FLAG_FILE + ".bak"
    shutil.copyfile(FLAG_FILE, backup)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, time.strftime("run-%Y%m%d-%H%M%S.json"))
    results = {"started": time.time(), "model": supervisor.OLLAMA_MODEL,
               "checkpoints": args.checkpoints, "settle_s": args.settle, "scenarios": []}
    scenarios = [s for s in SCENARIOS if not args.only or s[0] in args.only]
    try:
        set_flag(original)
        log(f"warming up {supervisor.OLLAMA_MODEL}")
        supervisor._ollama('Reply with JSON {"ok": true}')
        for i, (flag, variant, services, types) in enumerate(scenarios, 1):
            log(f"[{i}/{len(scenarios)}] {flag}={variant}: settling {args.settle}s")
            time.sleep(args.settle)
            inject = time.time()
            set_flag(original, flag, variant)
            log(f"    injected at {time.strftime('%H:%M:%S')}")
            base_start, base_end = inject - args.baseline, inject - 5
            sc = {"flag": flag, "variant": variant, "accept_services": services,
                  "accept_types": types, "injected": inject, "checkpoints": []}
            for cp in args.checkpoints:
                wait = inject + cp - time.time()
                if wait > 0:
                    time.sleep(wait)
                row = {"t": cp}
                for name, fn in (("v1", baseline.diagnose), ("v2", supervisor.diagnose)):
                    asked = time.time()
                    try:
                        ans = fn(base_start, base_end, inject, asked)
                    except Exception:  # noqa: BLE001 — record and keep the run going
                        ans = {"service": None, "fault_type": None, "error": traceback.format_exc()}
                    ans["answered_after_s"] = round(time.time() - inject, 1)
                    ans["service_ok"], ans["type_ok"] = correct(ans, services, types)
                    row[name] = ans
                    log(f"    t={cp:>3}s {name}: {ans.get('service')} / {ans.get('fault_type')}"
                        f"  {'OK' if ans['service_ok'] else 'wrong'}"
                        f"{'  verified' if ans.get('verified') else ''}")
                choice = row["v2"].get("llm_choice") or {}
                row["v2_llm_choice"] = {**choice, "answered_after_s": row["v2"]["answered_after_s"]}
                row["v2_llm_choice"]["service_ok"], row["v2_llm_choice"]["type_ok"] = correct(choice, services, types)
                sc["checkpoints"].append(row)
            set_flag(original)
            results["scenarios"].append(sc)
            with open(out_path, "w") as f:
                json.dump(results, f, indent=1)
    finally:
        with open(FLAG_FILE, "wb") as f:
            f.write(original)
        os.remove(backup)
        log("flags restored")
    results["finished"] = time.time()
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1)
    log(f"results: {out_path}")
    print(report(results))


def report(results):
    sc = results["scenarios"]
    n = len(sc)

    def final(s, k):
        return s["checkpoints"][-1][k]

    def first_correct(s, k):
        return next((c[k]["answered_after_s"] for c in s["checkpoints"] if c[k]["service_ok"]), None)

    def stats(k):
        svc = sum(final(s, k)["service_ok"] for s in sc)
        typ = sum(final(s, k)["type_ok"] for s in sc)
        times = [t for t in (first_correct(s, k) for s in sc) if t is not None]
        t = f"{statistics.median(times):.0f} s median ({len(times)}/{n} diagnosed)" if times else "never"
        return svc, typ, t

    v1, v2, v2c = stats("v1"), stats("v2"), stats("v2_llm_choice")
    cited = sum(1 for s in sc if final(s, "v2").get("verified")
                and any(e["kind"] == "trace" for e in final(s, "v2").get("evidence", [])))
    verified = sum(1 for s in sc if final(s, "v2").get("verified"))
    lines = [
        "| Metric | v1 (golden-signals baseline) | v2 (triage agent) |",
        "| --- | --- | --- |",
        f"| Root-cause service correctly identified | {v1[0]}/{n} | {v2[0]}/{n} |",
        f"| Fault type correctly identified | {v1[1]}/{n} | {v2[1]}/{n} |",
        f"| Time from fault injection to diagnosis | {v1[2]} | {v2[2]} |",
        f"| Answers citing a specific trace / metric | n/a — v1 cites nothing | {verified}/{n} verified ({cited}/{n} cite a trace ID) |",
        "",
        f"Ablation: if the LLM ({results['model']}) chooses the root cause from the same evidence: "
        f"{v2c[0]}/{n} root cause, {v2c[1]}/{n} fault type.",
        "",
        "| Flag | Expected | v1 | v2 | v2 verified |",
        "| --- | --- | --- | --- | --- |",
    ]
    for s in sc:
        a, b = final(s, "v1"), final(s, "v2")
        mark = lambda x: f"{x.get('service')} / {x.get('fault_type')} {'✅' if x['type_ok'] else ('🟡' if x['service_ok'] else '❌')}"
        lines.append(f"| `{s['flag']}` | {'/'.join(s['accept_services'])} · {'/'.join(s['accept_types'])} "
                     f"| {mark(a)} | {mark(b)} | {'yes' if b.get('verified') else 'no'} |")
    lines += ["", "✅ service and fault type right · 🟡 service right, fault type wrong · ❌ wrong service"]
    return "\n".join(lines)


def log(msg):
    print(msg, flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--only", nargs="*")
    p.add_argument("--checkpoints", nargs="*", type=int, default=[60, 120, 240])
    p.add_argument("--settle", type=int, default=150, help="seconds with all flags off before injecting")
    p.add_argument("--baseline", type=int, default=120, help="baseline window length before injection")
    p.add_argument("--report")
    p.add_argument("--merge", nargs=3, metavar=("MAIN", "RERUN", "OUT"),
                   help="replace MAIN's scenarios with RERUN's (same flag) and write OUT")
    a = p.parse_args()
    if a.merge:
        main_path, rerun_path, out = a.merge
        with open(main_path) as f:
            merged = json.load(f)
        with open(rerun_path) as f:
            rerun = {s["flag"]: s for s in json.load(f)["scenarios"]}
        merged["scenarios"] = [rerun.get(s["flag"], s) for s in merged["scenarios"]]
        merged["rerun"] = {"from": os.path.basename(rerun_path), "flags": sorted(rerun)}
        with open(out, "w") as f:
            json.dump(merged, f, indent=1)
        print(report(merged))
        sys.exit(0)
    if a.report:
        with open(a.report) as f:
            print(report(json.load(f)))
        sys.exit(0)
    run(a)
