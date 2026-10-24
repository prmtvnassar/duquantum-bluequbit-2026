"""Turn one circuit entry from scripts/runner.toml into one job per target qubit.

THIS IS THE FILE TO ADAPT AT KICKOFF. Everything else in the runner treats a job as
"run this circuit, measure this Pauli sum, record the number under this qubit ID".

To support a new way of getting circuits, write a function and decorate it:

    @provider("my_kit_way")
    def _(key, cfg, ctx) -> list[Target]: ...

then set `provider = "my_kit_way"` for that circuit in scripts/runner.toml.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from typing import Callable

from .config import ROOT


@dataclass(frozen=True)
class Target:
    qubit: str        # qubit ID exactly as the workbook / submission template writes it
    circuit: object   # a Qiskit QuantumCircuit, or a stored circuit ID string (hidden circuits)
    pauli_sum: tuple  # ((label, coefficient), ...) in SDK format

    def fingerprint(self) -> str:
        """Stable identity of the circuit, for caching."""
        if isinstance(self.circuit, str):
            return f"id:{self.circuit}"
        try:
            from qiskit import qasm2

            text = qasm2.dumps(self.circuit)
        except Exception:
            text = repr([(i.operation.name, [p for p in i.operation.params], [self.circuit.find_bit(q).index for q in i.qubits])
                         for i in self.circuit.data])
        return "qc:" + hashlib.sha256(text.encode()).hexdigest()[:16]


class Context:
    """Lazy access to things a provider may need (the BlueQubit client, workbook qubit IDs)."""

    def __init__(self, cfg: dict, client_factory: Callable, workbook_qubits: Callable[[str], list[str]]):
        self.cfg = cfg
        self._client_factory = client_factory
        self._client = None
        self.workbook_qubits = workbook_qubits

    @property
    def client(self):
        if self._client is None:
            self._client = self._client_factory()
        return self._client


PROVIDERS: dict[str, Callable] = {}


def provider(name: str):
    def register(fn):
        PROVIDERS[name] = fn
        return fn
    return register


def build_targets(key: str, circuit_cfg: dict, ctx: Context) -> list[Target]:
    name = circuit_cfg.get("provider")
    if name not in PROVIDERS:
        raise ValueError(f"{key}: unknown provider {name!r}. Known: {', '.join(PROVIDERS)}")
    targets = PROVIDERS[name](key, circuit_cfg, ctx)
    ids = [t.qubit for t in targets]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{key}: duplicate qubit IDs from provider {name!r}")
    return targets


# ---------------------------------------------------------------- shared helpers

def qubit_ids(key: str, circuit_cfg: dict, n: int | None, ctx: Context) -> list[str]:
    spec = circuit_cfg.get("qubits", "all")
    if spec == "all":
        if not n:
            raise ValueError(f"{key}: qubits = \"all\" needs a known qubit count")
        return [str(q) for q in range(n)]
    if spec == "workbook":
        ids = ctx.workbook_qubits(key)
        if not ids:
            raise ValueError(f"{key}: qubits = \"workbook\" but Qubits!A6:A165 is empty. Fill it or run --setup.")
        return ids
    if isinstance(spec, list):
        return [str(q) for q in spec]
    raise ValueError(f"{key}: qubits must be \"all\", \"workbook\" or a list")


def qubit_index(qubit_id: str) -> int:
    """Map a qubit ID to its circuit index. Change this if the kit labels qubits differently."""
    return int(qubit_id)


def observable(q: int, n: int, ctx: Context) -> tuple:
    obs = ctx.cfg["observable"]
    if not 0 <= q < n:
        raise ValueError(f"qubit index {q} is outside a {n}-qubit circuit")
    chars = ["I"] * n
    chars[n - 1 - q if obs.get("order", "little") == "little" else q] = obs.get("pauli", "Z")
    return (("".join(chars), 1.0),)


def otoc2_echo(U, b: int, q: int):
    """U, X_b, U^dag, Z_q, U, X_b, U^dag: the OTOC(2) echo (measure Z_q afterwards)."""
    from qiskit import QuantumCircuit

    Ud = U.inverse()
    qc = QuantumCircuit(U.num_qubits, name="OTOC2")
    qc.compose(U, inplace=True); qc.x(b); qc.compose(Ud, inplace=True)
    qc.z(q)
    qc.compose(U, inplace=True); qc.x(b); qc.compose(Ud, inplace=True)
    return qc


def kit_echo(U, b: int, q: int):
    """The kit's own echo builder. VERIFY THE CALL against the kit README at kickoff."""
    sys.path.insert(0, str(ROOT / "kit"))
    import challenge_tools

    return challenge_tools.otoc2_circuit(U, b, q)


def echo(circuit_cfg: dict):
    return kit_echo if circuit_cfg.get("echo", "builtin") == "kit" else otoc2_echo


# ---------------------------------------------------------------- providers

@provider("demo")
def _demo(key, cfg, ctx):
    """Random brickwork U (u3 + cz) with the OTOC(2) echo built locally. For testing only."""
    import numpy as np
    from qiskit import QuantumCircuit

    n, depth, b = int(cfg["n_qubits"]), int(cfg["depth"]), int(cfg.get("butterfly", 0))
    rng = np.random.default_rng(int(cfg.get("seed", 0)))
    U = QuantumCircuit(n, name="U")
    for layer in range(depth):
        for q in range(n):
            U.u(*rng.uniform(0, 2 * np.pi, 3), q)
        for q in range(layer % 2, n - 1, 2):
            U.cz(q, q + 1)
    build = echo(cfg)
    return [Target(qid, build(U, b, qubit_index(qid)), observable(qubit_index(qid), n, ctx))
            for qid in qubit_ids(key, cfg, n, ctx)]


@provider("qasm")
def _qasm(key, cfg, ctx):
    """U loaded from an OpenQASM file (e.g. a kit sample), echo built locally or by the kit."""
    from qiskit import qasm2, qasm3

    path = ROOT / cfg["path"]
    text = path.read_text()
    U = qasm3.loads(text) if "OPENQASM 3" in text else qasm2.loads(
        text, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    U.remove_final_measurements(inplace=True)
    n, b = U.num_qubits, int(cfg["butterfly"])
    build = echo(cfg)
    return [Target(qid, build(U, b, qubit_index(qid)), observable(qubit_index(qid), n, ctx))
            for qid in qubit_ids(key, cfg, n, ctx)]


@provider("stored")
def _stored(key, cfg, ctx):
    """Hidden circuits: run by stored circuit ID; gates are never revealed."""
    pattern = cfg["circuit_id"]
    if "TODO" in pattern or "TODO" in str(cfg.get("official_id", "")):
        raise ValueError(f"{key}: fill in circuit_id / official_id in scripts/runner.toml from the kit")
    n = int(cfg.get("n_qubits") or 0)
    if not n:
        first = pattern.format(qubit=0, official_id=cfg.get("official_id", key))
        n = ctx.client.get_circuit_info(first).num_qubits
    return [Target(qid, pattern.format(qubit=qid, official_id=cfg.get("official_id", key)),
                   observable(qubit_index(qid), n, ctx))
            for qid in qubit_ids(key, cfg, n, ctx)]


@provider("kit")
def _kit(key, cfg, ctx):
    """Placeholder for whatever the kit actually provides (e.g. a function returning
    circuits and observables per qubit). Implement at kickoff."""
    raise NotImplementedError(
        f"{key}: the 'kit' provider is not written yet. Implement _kit() in scripts/runner/targets.py "
        "once the kit README shows how circuits and observables are obtained.")
