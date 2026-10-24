"""Plan one graded action by default; execution requires --execute."""

import argparse
import json
import logging
from pathlib import Path
from otoc.bluequbit_adapter import BlueQubitAdapter
from otoc.calibration import load_settings
from otoc.experiment_store import ExperimentStore
from otoc.graded import plan_next, export_complete


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",default="configs/workflow_final.json")
    parser.add_argument("--problems",nargs="+",choices=["G1","G2","G3","G4"],default=["G1","G2","G3","G4"])
    parser.add_argument("--quote-limit",type=int,default=8)
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--offline-plan",action="store_true",help="Review saved quotes and usage without network or a token")
    parser.add_argument("--max-jobs",type=int,default=1,help="Maximum serial executions; default 1")
    args=parser.parse_args()
    if not 1<=args.max_jobs<=800:
        parser.error("--max-jobs must be between 1 and 800")
    if args.execute and args.offline_plan:
        parser.error("Offline quotes cannot authorize execution")
    logging.disable(logging.CRITICAL)
    settings=load_settings(args.config)
    if args.execute and settings.get("release_status")!="READY":
        parser.error("Complete sample calibration and regenerate the final configuration before executing graded jobs")
    if args.offline_plan:
        class SnapshotAdapter:
            root=Path("results/workflow")
            def usage(self):
                path=self.root/"api_usage.json"
                if not path.exists():
                    path=Path("reports/usage_receipt.json")
                return json.loads(path.read_text())
            def quote(self,cid,device,options):
                quotes=json.loads(Path("reports/native_quotes.json").read_text())["quotes"]
                matches=[q for q in quotes if q["circuit_id"]==cid and q["device"]==device and q["options"]==options]
                return max(matches,key=lambda q:q["quoted_at"]) if matches else {
                    "cost_usd":None,"runtime_seconds":None,"error":"No saved quote; fresh quote required"}
        adapter=SnapshotAdapter()
    else:
        adapter=BlueQubitAdapter()
    with ExperimentStore().lock("remote_runner"):
        for _ in range(args.max_jobs if args.execute else 1):
            settings.pop("protected_baseline_usd",None)
            plan=plan_next(adapter,settings,args.problems,args.quote_limit)
            if args.offline_plan:
                plan["status"]="OFFLINE_SNAPSHOT_REVIEW_ONLY"
                from bluequbit_samples.provenance import atomic_json
                atomic_json("reports/initial_graded_plan.json",plan)
            if not args.execute or not plan["next"]:
                print(json.dumps(plan,indent=2))
                break
            action=plan["next"]
            execution_settings={**settings,"per_job_seconds":action["timeout_seconds"],
                                "protected_baseline_usd":action["protected_baseline_usd"]}
            result=adapter.run(action["circuit_id"],action["device"],action["options"],execution_settings,action["reason"])
            print(json.dumps(result,indent=2),flush=True)
            print(json.dumps({"complete_exports":export_complete(settings)}),flush=True)
            if result["status"]!="COMPLETED":
                break


if __name__=="__main__":
    main()
