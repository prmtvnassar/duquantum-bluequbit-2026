"""Shared config: loads BLUEQUBIT_API_TOKEN from .env and returns an initialized client."""
import os

from dotenv import load_dotenv


def get_client():
    import bluequbit

    load_dotenv()
    token = os.environ.get("BLUEQUBIT_API_TOKEN")
    if not token:
        raise RuntimeError("BLUEQUBIT_API_TOKEN not set — copy .env.example to .env and fill it in.")
    return bluequbit.init(token)
