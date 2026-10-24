"""Reproduce the three originally submitted sample methods, locally at $0 cloud cost."""
import argparse
import csv
import io
import json
from pathlib import Path
from bluequbit_samples.models import RunConfig
from bluequbit_samples.runtime import execute
from otoc.calibration import sample_inputs
from otoc.duke_submission import build_submission, write_submission
from otoc.experiment_store import ExperimentStore
from otoc.ledger import atomic_bytes, event


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples",nargs="+",choices=["S1","S2","S3"],default=["S1","S2","S3"])
    parser.add_argument("--output",type=Path,default=Path("results/reproduction"))
    args=parser.parse_args()
    inputs=sample_inputs()
    config=RunConfig(cpu_threads=2,memory_limit_mb=700,walltime_seconds=90,max_paulis=100000)
    with ExperimentStore().lock():
        for problem in args.samples:
            method,params=("pps_threshold",{"epsilon":.01,"level":1}) if problem=="S3" else ("exact",{})
            results=[]
            for sample in (s for s in inputs if s.sample==problem):
                result=execute(sample,method,params,config,args.output/"execution")
                if not result.succeeded:
                    raise RuntimeError(f"{sample.circuit_id}: {result.status}; see runs/jobs.csv")
                results.append(result)
                print(f"{sample.circuit_id}: {result.estimate:.12g}",flush=True)
            buffer=io.StringIO(newline="")
            writer=csv.writer(buffer,lineterminator="\n")
            writer.writerow(("circuit_id","value"))
            writer.writerows((r.circuit_id,format(r.estimate,".17g")) for r in results)
            csv_path=args.output/f"{problem}.csv"
            write_submission(buffer.getvalue().encode(),csv_path,immutable=True)
            template=next(Path("problems").glob(f"*_{problem}/local_submission_template.csv"))
            build_submission(template,csv_path)
            original=Path("submissions")/problem/"attempt-01.json"
            receipt=json.loads(original.read_text())
            atomic_bytes(csv_path.with_suffix(".txt"),(receipt["method_note"]+"\n").encode())
            with (Path("submissions")/problem/"attempt-01.csv").open(newline="") as stream:
                previous={r["circuit_id"]:float(r["value"]) for r in csv.DictReader(stream)}
            difference=max(abs(r.estimate-previous[r.circuit_id]) for r in results)
            event("sample_reproduction",{"problem":problem,"method":method,"parameters":params,
                  "csv":str(csv_path),"max_difference_from_original_submission":difference,
                  "run_ids":[r.diagnostics["attempt_directory"] for r in results]})
            print(f"{problem}: {csv_path}; max difference from original={difference:.3g}; cloud cost=$0",flush=True)


if __name__=="__main__":
    main()
