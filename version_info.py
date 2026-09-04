"""Resolve the ASSET application version for packaging."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess


VERSION_PATTERN = re.compile(r"(?<![A-Za-z0-9])v?(\d+\.\d+\.\d+)(?![A-Za-z0-9.])")


class VersionResolutionError(ValueError):
    """Raised when a package version cannot be resolved."""


def _run_git(repo: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    value = (result.stdout or "").strip()
    return value if result.returncode == 0 and value else None


def _normalize_version(value: str, source: str) -> str:
    normalized_value = value.strip().lstrip("\ufeff")
    match = VERSION_PATTERN.fullmatch(normalized_value)
    if not match:
        raise VersionResolutionError(
            f"{source} must contain a semantic version such as v2.6.4."
        )
    return f"v{match.group(1)}"


def resolve_version(repo: Path, explicit_version: str | None = None) -> str:
    """Return a normalized version using argument, exact tag, then commit subject."""
    if explicit_version:
        return _normalize_version(explicit_version, "The supplied version")

    exact_tag = _run_git(repo, "describe", "--tags", "--exact-match", "HEAD")
    if exact_tag:
        return _normalize_version(exact_tag, "The current Git tag")

    commit_subject = _run_git(repo, "log", "-1", "--pretty=%s")
    match = VERSION_PATTERN.search(commit_subject or "")
    if match:
        return f"v{match.group(1)}"

    raise VersionResolutionError(
        "Unable to resolve a version from an argument, the current Git tag, "
        "or the latest commit subject."
    )


def resolve_runtime_version(repo: Path, version_file: Path) -> str:
    """Read the packaged version resource, with a Git fallback for development."""
    if version_file.is_file():
        try:
            return _normalize_version(
                version_file.read_text(encoding="utf-8").strip(),
                "The packaged version",
            )
        except (OSError, VersionResolutionError):
            pass

    try:
        return resolve_version(repo)
    except VersionResolutionError:
        return "Development Build"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="Optional version override")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        print(resolve_version(args.repo.resolve(), args.version))
    except VersionResolutionError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
