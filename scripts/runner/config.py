"""Load scripts/runner.toml and the BlueQubit client."""

from __future__ import annotations

import os
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        raise SystemExit("The runner needs Python 3.11+, or `pip install tomli` on Python 3.10.") from None

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "scripts" / "runner.toml"
OFFLINE_DIR = ROOT / "scratch" / "offline"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    for key in ("backend", "limits", "observable", "circuits"):
        if key not in cfg:
            raise ValueError(f"{path}: missing [{key}] section")
    return cfg


def circuit_config(cfg: dict, key: str) -> dict:
    circuits = cfg["circuits"]
    if key not in circuits:
        raise ValueError(f"Unknown circuit {key!r}. Known: {', '.join(circuits)}")
    return circuits[key]


def load_token() -> str:
    """BLUEQUBIT_API_TOKEN from the environment, else from the repo's .env."""
    token = os.environ.get("BLUEQUBIT_API_TOKEN")
    if not token and (ROOT / ".env").is_file():
        for line in (ROOT / ".env").read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "BLUEQUBIT_API_TOKEN":
                token = value.strip().strip("'\"")
    if not token:
        raise RuntimeError("BLUEQUBIT_API_TOKEN is not set: put it in .env or the environment.")
    return token


def get_client():
    import bluequbit

    return bluequbit.init(load_token())
