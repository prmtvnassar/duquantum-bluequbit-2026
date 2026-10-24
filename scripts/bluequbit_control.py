"""Inspect usage and quote/run individual by-ID jobs through the budget gate."""

import argparse
import json
import logging
import os
from otoc.bluequbit_adapter import BlueQubitAdapter
from otoc.calibration import load_settings
from otoc.experiment_store import ExperimentStore


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=["usage","quote","run"])
    parser.add_argument("--id")
    parser.add_argument("--device",default="cpu")
    parser.add_argument("--options",default="{}")
    parser.add_argument("--justification",default="")
    parser.add_argument("--config",default="configs/workflow_v0.json")
    parser.add_argument("--timeout",type=float)
    args=parser.parse_args()
    logging.disable(logging.CRITICAL)
    try:
        adapter=BlueQubitAdapter()
        if args.command=="usage":
            result=adapter.usage()
        elif args.command=="quote":
            result=adapter.quote(args.id,args.device,json.loads(args.options))
        else:
            settings=load_settings(args.config)
            if args.timeout is not None:
                settings["per_job_seconds"]=args.timeout
            with ExperimentStore().lock("remote_runner"):
                result=adapter.run(args.id,args.device,json.loads(args.options),settings,args.justification)
        print(json.dumps(result,indent=2))
    except Exception as exc:
        token=os.environ.get("BLUEQUBIT_API_TOKEN") or "unconfigured"
        print(json.dumps({"error":type(exc).__name__,"message":str(exc).replace(token,"[REDACTED]")}))
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
