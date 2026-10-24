"""The same experiment and validation entry points on Windows and Linux."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .models import RunConfig


def _configuration(args):
    root = Path(__file__).resolve().parents[2]
    path = Path(args.config) if args.config else root / "profiles" / f"{args.profile}.json"
    value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"profile": args.profile}
    value["profile"] = args.profile
    for source, target in [("threads", "cpu_threads"), ("memory_mb", "memory_limit_mb"),
                           ("timeout", "walltime_seconds"), ("max_paulis", "max_paulis"),
                           ("expected_total", "expected_total")]:
        current = getattr(args, source, None)
        if current is not None:
            value[target] = current
    return RunConfig(**value)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="S1-S3 exact/MPS/Pauli-backpropagation experiments")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Inspect local QASM/ZIP inputs; no simulations")
    inspect.add_argument("--data-root", default="data/samples")
    inspect.add_argument("--expected-total", type=int, default=50)
    verify = commands.add_parser("verify", help="Read back and verify exported artifact hashes")
    verify.add_argument("directory")
    for name in ("run", "checks"):
        command = commands.add_parser(name)
        command.add_argument("--profile", choices=["local", "nrp", "expanse"], default="local")
        command.add_argument("--config")
        command.add_argument("--output", default="results/samples" if name == "run" else "results/validation")
        command.add_argument("--threads", type=int)
        command.add_argument("--memory-mb", type=int)
        command.add_argument("--timeout", type=float)
        command.add_argument("--max-paulis", type=int)
        if name == "run":
            command.add_argument("--data-root", default="data/samples")
            command.add_argument("--expected-total", type=int)
            command.add_argument("--samples", nargs="+", choices=["S1", "S2", "S3"], default=["S1", "S2", "S3"])
            command.add_argument("--methods", nargs="+", choices=["exact", "mps", "pps"], default=["exact", "mps", "pps"])
            command.add_argument("--chis", nargs="+", type=int, default=[16, 32, 64, 128, 256])
            command.add_argument("--etas", nargs="+", type=float, default=[1e-2, 1e-3, 1e-4, 1e-5])
            command.add_argument("--allow-partial-inputs", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "verify":
        from .analysis import verify_exports
        print(json.dumps(verify_exports(args.directory), indent=2))
        return 0
    if args.command == "inspect":
        from .inputs import discover_samples
        report = discover_samples(args.data_root, args.expected_total)
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        return 0 if report.ready else 2
    config = _configuration(args)
    if args.command == "checks":
        from .checks import run_checks
        from .plots import plot_checks
        checks = run_checks(args.output, config, progress=True)
        figure = plot_checks(checks, Path(args.output) / "figures")
        if figure is not None:
            import matplotlib.pyplot as plt
            plt.close(figure)
        print(checks[["case", "method", "abs_error", "passed", "status"]].to_string(index=False))
        return 0 if checks.passed.all() else 1
    from .inputs import discover_samples
    from .provenance import atomic_json
    report = discover_samples(args.data_root, config.expected_total)
    atomic_json(Path(args.output) / "input_report.json", report.to_dict())
    if not report.ready and not args.allow_partial_inputs:
        print("Official inputs are missing or invalid. No sample simulations started.")
        print("\n".join(report.issues))
        return 2
    if not report.samples:
        print("No valid QASM inputs. No synthetic data will replace them.")
        return 2
    selected = [s for s in report.samples if s.sample in args.samples]
    if not selected:
        print("No inputs for the selected sample circuits.")
        return 2
    from .experiment import run_suite
    from .analysis import summary_table, export_results, verify_exports
    from .plots import plot_predictions, plot_convergence, plot_cost_error, plot_diagnostics
    records = run_suite(selected, args.output, config, methods=tuple(args.methods),
                        chis=tuple(args.chis), etas=tuple(args.etas))
    summary = summary_table(selected, records)
    figures = [plot_predictions(records, Path(args.output) / "exports" / "figures"),
               plot_convergence(summary, Path(args.output) / "exports" / "figures"),
               plot_cost_error(summary, Path(args.output) / "exports" / "figures"),
               plot_diagnostics(records, Path(args.output) / "exports" / "figures")]
    import matplotlib.pyplot as plt
    for figure in figures:
        if figure is not None:
            plt.close(figure)
    export_results(selected, records, Path(args.output) / "exports")
    print(summary.to_string(index=False))
    print(json.dumps(verify_exports(Path(args.output) / "exports")))
    return 0 if all(r.succeeded for r in records) and report.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
