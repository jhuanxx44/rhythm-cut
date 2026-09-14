#!/usr/bin/env python3
"""Run one redacted Gemini 3.8 Flash request."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rhythm_cut.providers.gemini_client import GeminiClient


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", default="Reply with exactly the word OK.")
    parser.add_argument("--image", type=Path, help="Optional image path for vision validation")
    parser.add_argument("--out", type=Path, help="Optional redacted evidence JSON path")
    args = parser.parse_args()

    images = [args.image] if args.image else []
    try:
        client = GeminiClient()
        response = client.generate(
            args.text,
            model="gemini-3.8-flash",
            images=images,
            max_output_tokens=2000,
            thinking_level="low",
        )
    except Exception as exc:  # noqa: BLE001
        print(f"failed model=gemini-3.8-flash error={type(exc).__name__}: {str(exc)[:500]}")
        return 1
    print(
        f"ok model={response.model} protocol={response.protocol} "
        f"http={response.http_status} latency_ms={response.latency_ms} "
        f"chars={len(response.text)}"
    )
    print(f"text={response.text[:200]!r}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(response.evidence(), ensure_ascii=False, indent=2) + "\n"
        )
        print(f"evidence={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
