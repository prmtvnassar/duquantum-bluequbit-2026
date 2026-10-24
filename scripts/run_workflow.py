"""CLI for sample calibration and the graded-circuit preparation workflow."""

import argparse
import json
from otoc.calibration import import_references, load_settings, run_local, write_report
from otoc.experiment_store import ExperimentStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",default="configs/workflow_v0.json")
    parser.add_argument("--output",default="results/workflow")
    sub = parser.add_subparsers(dest="command",required=True)
    sub.add_parser("import-references")
    sub.add_parser("report")
    sub.add_parser("tune")
    run = sub.add_parser("run-local")
    run.add_argument("--samples",nargs="+",choices=["S1","S2","S3"],default=["S1","S2","S3"])
    run.add_argument("--max-jobs",type=int,default=100)
    run.add_argument("--seconds",type=float,default=900)
    args = parser.parse_args()
    settings, store = load_settings(args.config), ExperimentStore(args.output)
    if args.command == "import-references":
        print(f"Imported {import_references(store)} exact references")
    elif args.command == "run-local":
        run_local(store,settings,args.samples,args.max_jobs,args.seconds)
    elif args.command == "tune":
        from otoc.tuning import tune
        evidence=tune(store,settings)
        print(json.dumps(evidence,indent=2))
    report = write_report(store,settings)
    print(json.dumps({k:report[k] for k in ("record_count","reference_count","sample_cost_usd")}))
    for row in report["benchmarks"]:
        if row["complete"]:
            print(f"{row['problem']} {row['method']} {row['parameters']}: score={row['local_score']}; {row['csv_path']}")


if __name__ == "__main__":
    main()
