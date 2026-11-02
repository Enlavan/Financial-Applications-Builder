#!/usr/bin/env python3
"""Offline checks for the public skill package. No API calls or dependencies.

This is a conservative packaging check, not a comprehensive secret scanner,
license audit, Markdown parser or live API compatibility test.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
# What Claude installs or uploads: the skill itself.
SKILL_FILES = {"SKILL.md", "LICENSE"}
SKILL_DIRS = {"assets", "references", "scripts"}
# Repository-only material, never packaged into the skill.
REPO_FILES = {"README.md", ".gitignore"}
REPO_DIRS = {"dev", ".github"}
PUBLIC_FILES = SKILL_FILES | REPO_FILES
PUBLIC_DIRS = SKILL_DIRS | REPO_DIRS
SKILL_MD_MAX_LINES = 500
IGNORED = {".git", "__pycache__", ".pytest_cache", ".venv", "venv"}
LOCAL_ROOT = {"captures", "data", "downloads", "outputs", ".idea", ".vscode", ".DS_Store"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".txt"}
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
ALLOWED_EMAILS = {"support@eodhistoricaldata.com", "sales@eodhistoricaldata.com"}
SECRET_PATTERNS = {
    "private-key block": re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    "credential-like token": re.compile(r"\b(?:ghp_|github_pat_|sk_live_|sk_test_)[A-Za-z0-9_]{12,}"),
    "EODHD-token-shaped value": re.compile(r"\b[0-9a-f]{12,16}\.[0-9]{8}\b"),
}


def public_files(root: Path = ROOT, names: set[str] | None = None) -> list[Path]:
    """Enumerate source files of the repository (or of the given root entries)."""
    result = []
    for name in sorted(names or PUBLIC_FILES | PUBLIC_DIRS):
        base = root / name
        if base.is_symlink():
            raise ValueError(f"Symlink is not a release source: {name}")
        candidates = sorted(base.rglob("*")) if base.is_dir() else [base]
        for path in candidates:
            relative = path.relative_to(root)
            if any(part in IGNORED for part in relative.parts):
                continue
            if path.is_symlink():
                raise ValueError(f"Symlink is not a release source: {relative}")
            if path.is_file() and path.suffix not in {".pyc", ".pyo", ".zip"}:
                result.append(path)
    return result


def skill_files(root: Path = ROOT) -> list[Path]:
    """Enumerate only what an installed or uploaded skill contains."""
    return public_files(root, SKILL_FILES | SKILL_DIRS)


def validate(root: Path = ROOT) -> list[str]:
    errors = []
    required = PUBLIC_FILES | {".github/workflows/validate.yml"}
    for name in sorted(required):
        if not (root / name).is_file():
            errors.append(f"Missing release file: {name}")
    for path in root.iterdir():
        if path.name in IGNORED | LOCAL_ROOT or path.name.startswith(".env") or path.suffix == ".zip":
            continue
        if path.name not in PUBLIC_FILES | PUBLIC_DIRS:
            errors.append(f"Non-public or unrecognized root entry: {path.name}")

    scripts = root / "scripts"
    if scripts.is_dir():
        for path in sorted(scripts.glob("*.py")):
            if path.name.startswith("test_") or path.name in {"validate_release.py", "package_release.py"}:
                errors.append(f"Repository tooling belongs in dev/, not the skill: scripts/{path.name}")

    skill = root / "SKILL.md"
    if skill.is_file():
        if len(skill.read_text().splitlines()) > SKILL_MD_MAX_LINES:
            errors.append(f"SKILL.md exceeds {SKILL_MD_MAX_LINES} lines")
        match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", skill.read_text(), re.S)
        if not match:
            errors.append("SKILL.md needs YAML frontmatter")
        else:
            frontmatter = match.group(1)
            if not re.search(r"(?m)^name: eodhd-financial-applications-skill\s*$", frontmatter):
                errors.append("Unexpected skill name")
            if not re.search(r"(?m)^description:\s*\S", frontmatter):
                errors.append("Missing skill description")
    license_path = root / "LICENSE"
    if license_path.is_file():
        license_text = license_path.read_text()
        for expected in ("MIT License", "Copyright (c) 2026 Alex Chernyshev, EOD Historical Data",
                         "The above copyright notice and this permission notice shall be included"):
            if expected not in license_text:
                errors.append(f"Missing MIT license text: {expected}")

    try:
        files = public_files(root)
        in_skill = set(skill_files(root))
    except ValueError as exc:
        return errors + [str(exc)]
    for path in files:
        relative = path.relative_to(root)
        if path.name.startswith(".env") or path.suffix in {".pem", ".key", ".body"}:
            errors.append(f"Private artifact in release: {relative}")
        if path.suffix not in TEXT_SUFFIXES and path.name not in PUBLIC_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            errors.append(f"Expected UTF-8 text: {relative}")
            continue
        if path.suffix == ".py":
            try:
                ast.parse(text, filename=str(relative))
            except SyntaxError as exc:
                errors.append(f"Invalid Python: {relative}:{exc.lineno}")
        if path.suffix == ".json":
            try:
                json.loads(text)
            except ValueError:
                errors.append(f"Invalid JSON: {relative}")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"Possible {label}: {relative} (value withheld)")
        for email in sorted(set(EMAIL.findall(text))):
            if email not in ALLOWED_EMAILS and not email.endswith("@example.com"):
                errors.append(f"Use a synthetic example.com address in {relative} (address withheld)")
        if path.suffix != ".md":
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for target in re.findall(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", line):
                target = target.strip()
                target = target[1:target.index(">")] if target.startswith("<") and ">" in target else target.split()[0]
                target = unquote(target.split("#", 1)[0])
                if not target or re.match(r"[a-z][a-z0-9+.-]*:", target, re.I):
                    continue
                linked = (path.parent / target).resolve()
                if not linked.is_relative_to(root.resolve()):
                    errors.append(f"Local link escapes package: {relative}:{number}")
                elif not linked.exists():
                    errors.append(f"Broken local file link: {relative}:{number}: {target}")
                elif path in in_skill and linked.relative_to(root.resolve()).parts[0] in REPO_FILES | REPO_DIRS:
                    errors.append(f"Skill links to repository-only material: {relative}:{number}: {target}")

    auth = root / "references/api/general/authentication.md"
    if auth.is_file():
        text = auth.read_text()
        if re.search(r"(?m)^\s*echo\s+.*\$\{?EODHD_API_TOKEN", text):
            errors.append("Authentication guide must not print the API token")
        if "❌ `Authorization: Bearer TOKEN`" in text:
            errors.append("Authentication guide contradicts observed Bearer transport")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"PASS: {len(public_files())} repository files, {len(skill_files())} in the skill; metadata, "
          "MIT notice, local file links, Python/JSON syntax and credential/privacy checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
