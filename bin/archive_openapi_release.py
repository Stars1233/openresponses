#!/usr/bin/env python3
"""Archive the formatted canonical OpenAPI document as an immutable dated release."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


def _release_version(document: dict[str, Any]) -> str:
    info = document.get("info")
    if not isinstance(info, dict):
        raise RuntimeError("OpenAPI document must contain an info object.")
    version = info.get("version")
    if not isinstance(version, str):
        raise RuntimeError("OpenAPI info.version must be a string.")
    try:
        parsed_version = date.fromisoformat(version)
    except ValueError as exc:
        raise RuntimeError("OpenAPI info.version must use YYYY-MM-DD format.") from exc
    if parsed_version.isoformat() != version:
        raise RuntimeError("OpenAPI info.version must use YYYY-MM-DD format.")
    return version


def archive_release(input_path: Path, output_dir: Path) -> tuple[Path, bool]:
    try:
        content = input_path.read_text(encoding="utf-8")
        document = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read canonical OpenAPI document {input_path}.") from exc
    if not isinstance(document, dict):
        raise RuntimeError("Canonical OpenAPI document must be an object.")

    version = _release_version(document)
    output_path = output_dir / version / "openapi.json"
    if output_path.exists():
        try:
            existing_document = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cannot read existing release {output_path}.") from exc
        if existing_document != document:
            raise RuntimeError(
                f"Refusing to overwrite immutable release {output_path}. "
                "Update info.version before releasing a changed specification."
            )
        return output_path, False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path, True


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Canonical OpenAPI JSON file.")
    parser.add_argument("--output-dir", required=True, help="Root directory for dated releases.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    try:
        output_path, created = archive_release(Path(args.input), Path(args.output_dir))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    action = "Created" if created else "Verified"
    print(f"{action} {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
