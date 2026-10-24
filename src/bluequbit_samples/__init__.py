"""Public interfaces; heavy simulation libraries are imported only when needed."""

from .models import RunConfig, RunRecord, SampleCircuit

__version__ = "0.1.0"
__all__ = ["RunConfig", "RunRecord", "SampleCircuit", "run_exact", "run_mps", "run_pps"]


def run_exact(sample, config=None):
    from .engines import run_exact as implementation
    return implementation(sample, config or RunConfig())


def run_mps(sample, chi=32, config=None):
    from .engines import run_mps as implementation
    return implementation(sample, chi, config or RunConfig())


def run_pps(sample, eta=1e-3, config=None):
    from .engines import run_pps as implementation
    return implementation(sample, eta, config or RunConfig())

