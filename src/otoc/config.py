"""Create a BlueQubit client without exposing credentials in logs."""

from __future__ import annotations

import os
from pathlib import Path


def get_client():
    """Load an optional local .env and initialize the SDK client.

    The caller must run from the repository root if relying on its .env file.
    An existing environment variable takes precedence over the file.
    """
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
    if not os.environ.get("BLUEQUBIT_API_TOKEN"):
        raise RuntimeError("Set BLUEQUBIT_API_TOKEN in the environment or a local .env file")

    import bluequbit

    return bluequbit.init()
