"""Acquire exact sample references only while each CPU quote and bill is zero."""

import argparse
import json
import logging
import math

from bluequbit_samples.provenance import atomic_json
from otoc.bluequbit_adapter import BlueQubitAdapter
from otoc.calibration import load_settings, sample_inputs
from otoc.experiment_store import ExperimentStore, utc_now


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--problem",choices=["S1","S2","S3"],default="S3")
    parser.add_argument("--max-ids",type=int,default=30)
    args=parser.parse_args()
    logging.disable(logging.CRITICAL)
    settings=load_settings()
    settings["per_job_seconds"]=300
    store=ExperimentStore()
    adapter=BlueQubitAdapter()
    samples=[s for s in sample_inputs() if s.sample==args.problem][:args.max_ids]
    with store.lock("remote_runner"):
        completed=0
        for index,sample in enumerate(samples,1):
            if (store.root / "STOP").exists():
                break
            atomic_json(store.root / "reference_status.json",{"status":"RUNNING","circuit_id":sample.circuit_id,
                        "completed_ids":index-1,"requested_ids":len(samples),"updated_at":utc_now()})
            result=adapter.run(sample.circuit_id,"cpu",{},settings)
            if result["status"]!="COMPLETED" or result.get("cost_usd")!=0:
                print(json.dumps(result),flush=True)
                atomic_json(store.root / "reference_status.json",{"status":"BLOCKED","result":result,"updated_at":utc_now()})
                return 1
            value=float(result["estimate"])
            if not math.isfinite(value) or abs(value)>1+1e-8:
                raise ValueError("Invalid exact-reference expectation")
            record={"circuit_id":sample.circuit_id,"sample":sample.sample,"qubit":sample.qubit,
                    "num_qubits":sample.num_qubits,"qasm_sha256":sample.qasm_sha256,"dataset_kind":"official",
                    "method":"exact","parameters":{"precision":"cloud_cpu","shots":None},
                    "status":"SUCCEEDED","estimate":value,"backend":"bluequbit.cpu","cost_usd":0.0,
                    "wall_seconds":((result.get("compute_ms") or 0)+(result.get("queue_ms") or 0))/1000,
                    "diagnostics":{"job_id":result["job_id"],"reference_status":"EXACT_CLOUD_CPU_BY_ID",
                                   "source_identity":"Public sample ID; server QASM hash is not exposed"}}
            store.save({"circuit_id":sample.circuit_id,"method":"exact","parameters":record["parameters"],
                        "input_sha256":sample.qasm_sha256,"origin":"bluequbit.cpu","job_id":result["job_id"]},record)
            completed+=1
            print(f"[{index}/{len(samples)}] {sample.circuit_id}: exact={value:.12g}; actual cost=$0",flush=True)
        atomic_json(store.root / "reference_status.json",{"status":"COMPLETE" if completed==len(samples) else "STOPPED",
                    "completed_ids":completed,"requested_ids":len(samples),"updated_at":utc_now()})
    return 0


if __name__=="__main__":
    raise SystemExit(main())
