"""Publish measured sample evidence, allocation decisions, and scientific plots."""
from collections import Counter
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from otoc.calibration import load_settings, write_report
from otoc.experiment_store import ExperimentStore
from otoc.tuning import tune
from otoc.ledger import atomic_bytes, csv_bytes, sync_history
from otoc.submission_registry import sync_submissions


def main():
    store, settings=ExperimentStore(),load_settings()
    evidence=tune(store,settings)
    report=write_report(store,settings)
    sync_history()
    sync_submissions()
    final=json.loads(Path("configs/workflow_final.json").read_text())
    receipts=[json.loads(p.read_text()) for p in Path("runs/records").glob("*.json")]
    statuses=Counter(r["status"] for r in receipts)
    fields=("problem","method","parameters_json","completed","required","complete","wall_seconds",
            "cost_usd","local_score","mae","max_absolute_error")
    atomic_bytes("reports/sample_benchmarks.csv",csv_bytes(fields,[{**b,"parameters_json":json.dumps(b["parameters"],sort_keys=True)}
                                                              for b in report["benchmarks"]]))
    lines=["# Sample calibration and final allocation", "", f"Generated: {evidence['generated_at']}","",
           f"Release status: **{final['release_status']}**. Numerical exact references: **{report['reference_count']}/50**.","",
           "Official submitted scores: S1 100/100, S2 100/100, S3 100/100 (displayed values; may round). "
           "The official S1/S2 submissions used exact local values; S3 used PPS epsilon 0.01. No extra score-fitting submissions were made.","",
           "## Selected local settings", "", "| Sample | Method | Parameters | Max absolute error | Offline score / 100 | Vector wall seconds |",
           "| --- | --- | --- | ---: | ---: | ---: |"]
    for p,r in evidence["recommendations"].items():
        if r.get("max_absolute_error") is not None:
            lines.append(f"| {p} | {r['method']} | `{json.dumps(r['parameters'],sort_keys=True)}` | {r['max_absolute_error']:.6g} | {r['local_score']:.8f} | {r['wall_seconds']:.2f} |")
        else:
            lines.append(f"| {p} | Reference/coverage incomplete | | | | |")
    lines += ["", "Acceptance requires maximum absolute error <= 0.01 and offline score >= 99. "
              "Timings are observed single-run totals, not a statistically established optimum. "
              "The settings describe local implementations; native transfer remains unverified.","",
              "## What changed because of the evidence", "",
              "- S2: chi 64 missed the absolute-error target; chi 128 reduced worst error to about 0.0033. However, native G2 chi128 quotes exceed the budget/runtime allocation. The graded baseline uses affordable PPS .001 pilots (S2 max error about 0.111), with chi16 independent checks. This quality compromise is explicit.",
              "- S3: the officially submitted coarse vector displayed 100/100 but had material pointwise error. The complete epsilon sweep is checked against all exact CPU references. Tighter epsilon 0.0001 hit the 100,000-term cap on two IDs; those incomplete runs were never accepted as values.",
              "- G1: reuse a teammate's 30 exact CPU outputs, matched against his submitted CSV and source job ledger. No repeat simulation is scheduled. Larger G2-G4 CPU and exact-GPU requests were rejected for size.",
              "- G4: no sample matches its Haar-grid family. Chi64 native CPU/GPU quotes were too costly/slow. Use PPS .001 pilots plus MPS chi16, requiring a resolved pilot signal and an independent result before bulk coverage. These are engineering priors, not validated G4 settings.",
              "- Fusion and extrapolation are disabled. Within-method signed trends, contraction and oscillation affect refinement priority alongside cross-method differences. Official scores reweight whole-problem effort only. No diagnostic certifies an error bound.",
              "- The original MPS norm guard incorrectly rejected a small finite norm. Explicit rescaling repaired the operational issue; its failed attempt is preserved and excluded from calibration retries.","",
              "## Complete benchmark vectors", "",
              "| Problem | Method / precision | Offline score | Max error | Wall seconds |",
              "| --- | --- | ---: | ---: | ---: |"]
    for b in report["benchmarks"]:
        if b["complete"] and b["max_absolute_error"] is not None:
            lines.append(f"| {b['problem']} | {b['method']} `{json.dumps(b['parameters'],sort_keys=True)}` | {b['local_score']:.8f} | {b['max_absolute_error']:.6g} | {b['wall_seconds']:.2f} |")
    lines += ["", "## Stopping replay", ""]
    for c in evidence["stopping_checks"]:
        lines.append(f"- {c['problem']}: {c['status']}; {len(c.get('prefixes',[]))} complete prefix pairs, "
                     f"{c['stopped_count']} candidate per-ID stops, {c['false_stops']} false stops against the 0.01 error target.")
    lines += ["", "No universal native stopping guarantee follows from these samples. The raw replay includes every complete earlier precision prefix, so an early shared bias cannot be hidden by a good final answer.","",
              "## Audit and costs", "", f"Recorded execution attempts: **{len(receipts)}**; states: `{dict(statuses)}`.","",
              "Every observed sample cloud job cost $0. Independent native MPS/PPS sample quotes of $0.20 were blocked. "
              "Graded quotation is not simulation or spending. The $30 balance is reserved for graded work; automatic planned spend is limited to $25.50, plus protection for remaining baseline coverage.","",
              "See [runs/jobs.csv](../runs/jobs.csv), [runs/decisions.csv](../runs/decisions.csv), "
              "[runs/submissions.csv](../runs/submissions.csv), and [workflow_final.md](../workflow_final.md). "
              "The cleanup inventory records the recovery commit for removed obsolete files.","",
              "![Maximum pointwise error across complete precision vectors](sample_precision_errors.png)",""]
    Path("reports/SAMPLE_CALIBRATION.md").write_text("\n".join(lines),encoding="utf-8")
    fig,axes=plt.subplots(3,2,figsize=(10,9),layout="constrained")
    for row,problem in enumerate(("S1","S2","S3")):
        for col,method in enumerate(("mps","pps_threshold")):
            ax=axes[row,col]
            points=[b for b in report["benchmarks"] if b["problem"]==problem and b["method"]==method
                    and b["complete"] and b["max_absolute_error"] is not None]
            parameter="chi" if method=="mps" else "epsilon"
            points.sort(key=lambda b:b["parameters"][parameter])
            if points:
                ax.plot([b["parameters"][parameter] for b in points],
                        [max(b["max_absolute_error"],1e-15) for b in points],"o-",color="#215b84")
            ax.axhline(.01,color="#ba5436",ls="--",label="0.01 target")
            ax.set_xscale("log")
            ax.set_yscale("log")
            if method=="pps_threshold": ax.invert_xaxis()
            ax.set_title(problem+" / "+("MPS" if method=="mps" else "local PPS"))
            ax.set_xlabel(parameter+" (more precision to the right)")
            ax.set_ylabel("Maximum absolute error")
            ax.grid(alpha=.2)
    axes[0,0].legend(frameon=False)
    fig.suptitle("Sample precision sweeps against numerical exact references\nComplete vectors only; local kernels; no native error guarantee",fontsize=13)
    fig.savefig("reports/sample_precision_errors.png",dpi=160)
    plt.close(fig)
    print(json.dumps({"release_status":final["release_status"],"reference_count":report["reference_count"],
                      "run_count":len(receipts),"recommendations":evidence["recommendations"]},indent=2))


if __name__=="__main__":
    main()
