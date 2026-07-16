"""Repository-level portability and tracked-file hygiene checks."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_tracked_paths_do_not_collide_on_case_insensitive_filesystems() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repository_root,
        check=True,
        capture_output=True,
    )
    tracked_paths = [
        item.decode("utf-8", errors="strict")
        for item in result.stdout.split(b"\0")
        if item
    ]
    paths_by_casefold: dict[str, list[str]] = {}
    for path in tracked_paths:
        paths_by_casefold.setdefault(path.casefold(), []).append(path)

    collisions = [
        sorted(paths)
        for paths in paths_by_casefold.values()
        if len(set(paths)) > 1
    ]

    assert collisions == [], f"Tracked paths collide by case: {collisions}"
