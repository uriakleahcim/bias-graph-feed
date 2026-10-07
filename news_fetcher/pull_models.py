"""Ensure Bias Graph Feed's fixed local Ollama profile is available before ingesting.

This module runs only in the short-lived Compose initializer service.  Models
are pulled through Ollama's internal HTTP API into its named Docker volume;
nothing is written to a host model path.
"""

import os
import sys

import requests


OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
MODELS = tuple(
    name.strip()
    for name in os.environ.get(
        "OLLAMA_MODELS",
        "qwen2.5:3b-instruct,qwen2.5:1.5b-instruct,nomic-embed-text:v1.5",
    ).split(",")
    if name.strip()
)


def pull_model(name):
    response = requests.post(
        f"{OLLAMA_HOST}/api/pull",
        json={"model": name, "stream": False},
        timeout=1800,
    )
    response.raise_for_status()


def main():
    for model in MODELS:
        print(f"Ensuring Ollama model is available: {model}", flush=True)
        pull_model(model)
    print("Ollama model profile is ready.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as error:
        print(f"Unable to prepare Ollama model profile: {error}", file=sys.stderr)
        raise SystemExit(1) from error
