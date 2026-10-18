#!/usr/bin/env python3
"""Conservative Git documentation-only change classifier."""

import subprocess
import sys


DOCUMENTATION_FILES = {
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
}


def git(*args):
    return subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def is_documentation(path):
    return (
        path in DOCUMENTATION_FILES
        or (path.startswith("docs/") and len(path) > len("docs/"))
    )


def classify(base, head):
    resolved = []

    for revision in (base, head):
        result = git("rev-parse", "--verify", f"{revision}^{{commit}}")
        if result.returncode != 0:
            return "FULL_CI"
        resolved.append(result.stdout.decode("ascii").strip())

    base, head = resolved

    if base == head:
        return "FULL_CI"

    ancestry = git("merge-base", "--is-ancestor", base, head)
    if ancestry.returncode != 0:
        return "FULL_CI"

    merges = git("rev-list", "--min-parents=2", f"{base}..{head}")
    if merges.returncode != 0 or merges.stdout.strip():
        return "FULL_CI"

    history = git(
        "log", "--format=", "--name-only", "--no-renames",
        "-z", f"{base}..{head}",
    )
    if history.returncode != 0:
        return "FULL_CI"

    changed_paths = [
        path.decode("utf-8", errors="surrogateescape")
        for path in history.stdout.split(b"\0")
        if path
    ]
    if not changed_paths or not all(
        is_documentation(path) for path in changed_paths
    ):
        return "FULL_CI"

    result = git(
        "diff",
        "--name-only",
        "--no-renames",
        "-z",
        base,
        head,
        "--",
    )

    if result.returncode != 0:
        return "FULL_CI"

    paths = [
        path.decode("utf-8", errors="surrogateescape")
        for path in result.stdout.split(b"\0")
        if path
    ]

    if not paths:
        return "FULL_CI"

    if all(is_documentation(path) for path in paths):
        return "DOCS_ONLY"

    return "FULL_CI"


def main():
    if len(sys.argv) != 3:
        print("FULL_CI")
        return 0

    try:
        print(classify(sys.argv[1], sys.argv[2]))
    except (OSError, ValueError):
        print("FULL_CI")

    return 0


if __name__ == "__main__":
    sys.exit(main())
