"""A process entry point, never a scheduler or remote-submission client."""

import json
from pathlib import Path
import sys

from .models import RunConfig, SampleCircuit
from .provenance import atomic_json


def main():
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    sample = SampleCircuit(**request["sample"])
    config = RunConfig(**request["config"])
    from .engines import run_exact, run_mps, run_pps
    method, parameters = request["method"], request["parameters"]
    if method == "exact":
        result = run_exact(sample, config)
    elif method == "mps":
        result = run_mps(sample, parameters.get("chi", 32), config)
    else:
        result = run_pps(sample, parameters.get("eta", 1e-3), config)
    import psutil
    memory = psutil.Process().memory_info()
    peak = getattr(memory, "peak_wset", memory.rss)
    try:
        import resource
        peak = max(peak, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024))
    except ImportError:
        pass
    result.diagnostics["worker_peak_rss"] = int(peak)
    atomic_json(sys.argv[2], result.to_dict())


if __name__ == "__main__":
    main()
