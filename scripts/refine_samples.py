"""Finish useful sample refinement vectors; every attempt enters runs/jobs.csv."""
from bluequbit_samples.models import RunConfig
from bluequbit_samples.runtime import execute
from otoc.calibration import load_settings, sample_inputs, write_report, recover_local_receipts
from otoc.experiment_store import ExperimentStore
from otoc.ledger import event


def main():
    settings, store = load_settings(), ExperimentStore()
    config = RunConfig(cpu_threads=2, memory_limit_mb=700, walltime_seconds=90, max_paulis=100000)
    samples = sample_inputs()
    campaign = [("S1","mps",[16]), ("S3","pps_threshold",[.001,.0001]),
                ("S2","mps",[32,64,128,256])]
    with store.lock():
        recover_local_receipts(store)
        for problem, method, levels in campaign:
            failures = 0
            for level in levels:
                params = {"chi":level} if method == "mps" else {"epsilon":level,"level":1}
                for sample in (s for s in samples if s.sample == problem):
                    if (store.root / "STOP").exists() or (store.root / "STOP_LOCAL").exists():
                        return
                    existing = [i["record"] for i in store.records() if i["record"]["circuit_id"]==sample.circuit_id
                                and i["record"]["method"]==method
                                and all(i["record"]["parameters"].get(k)==v for k,v in params.items())]
                    if any(r["status"]=="SUCCEEDED" for r in existing):
                        continue
                    event("calibration_decision", {"circuit_id":sample.circuit_id,"method":method,"parameters":params,
                           "reason":"Complete the next precision vector to test pointwise error and method allocation"})
                    record = execute(sample,method,params,config,store.root / "local").to_dict()
                    record["cost_usd"] = 0.0
                    store.save({"circuit_id":sample.circuit_id,"method":method,"parameters":params,
                                "input_sha256":sample.qasm_sha256,"engine_source":record["diagnostics"]["source_sha256"],
                                "origin":"local"},record)
                    failures += record["status"] != "SUCCEEDED"
                    print(f"{sample.circuit_id} {method} {params}: {record['status']}, {record['wall_seconds']:.2f}s",flush=True)
                    if failures >= 2:
                        break
                report = write_report(store,settings)
                selected = [b for b in report["benchmarks"] if b["problem"]==problem and b["method"]==method
                            and all(b["parameters"].get(k)==v for k,v in params.items()) and b["complete"]]
                if failures >= 2 or any(b["max_absolute_error"] is not None and b["max_absolute_error"] <= .01
                                         and b["local_score"] >= 99 for b in selected):
                    break


if __name__ == "__main__":
    main()
