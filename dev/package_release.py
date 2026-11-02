#!/usr/bin/env python3
"""Validate and archive only the skill (SKILL.md, LICENSE, assets, references, scripts) for Claude."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import tempfile
import zipfile

from validate_release import ROOT, skill_files, validate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.suffix.lower() != ".zip":
        parser.error("Use a .zip output path")
    if output.is_relative_to(ROOT):
        parser.error("Write the release outside the source skill directory")
    errors = validate()
    if errors:
        parser.exit(1, "Release validation failed:\n" + "\n".join(errors) + "\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    files = skill_files()
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, Path(ROOT.name) / path.relative_to(ROOT))
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError("ZIP integrity check failed")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Created {output.name}: {len(files)} files, {output.stat().st_size} bytes")
    print(f"SHA-256: {hashlib.sha256(output.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
