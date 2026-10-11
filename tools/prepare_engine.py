# Copyright 2026 The Ren'Py fork contributors
# SPDX-License-Identifier: MIT

"""Prepare the companion SDL2 engine without resetting unrelated or local work."""

import argparse
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from renpybuild.engine import validate_engine

DEFAULT_REPOSITORY = "https://github.com/potato-flower-alt/renpy.git"


def git(engine, *args):
    return subprocess.check_output(["git", "-C", str(engine), *args], text=True).strip()


def repository_key(repository):
    repository = repository.rstrip("/").removesuffix(".git")
    for prefix in ("https://github.com/", "git@github.com:"):
        if repository.startswith(prefix):
            return "github.com/" + repository.removeprefix(prefix).lower()
    return repository


def prepare_engine(engine, repository=DEFAULT_REPOSITORY, branch="main"):
    engine = Path(engine).resolve()
    if engine.exists():
        if not (engine / ".git").exists():
            raise ValueError(f"Existing engine directory {engine} is not a Git checkout; select a matching engine explicitly.")
        origin = git(engine, "remote", "get-url", "origin")
        if repository_key(origin) != repository_key(repository):
            raise ValueError(
                f"Engine checkout {engine} has a different origin. "
                "Use the companion SDL2 fork or explicitly set RENPY_ENGINE_REPOSITORY; the checkout was not changed."
            )
        if git(engine, "status", "--porcelain"):
            raise ValueError(f"Engine checkout {engine} has local changes; commit them before updating. No reset was performed.")
        subprocess.run(["git", "-C", str(engine), "fetch", "origin", branch], check=True)
        subprocess.run(["git", "-C", str(engine), "checkout", branch], check=True)
        subprocess.run(["git", "-C", str(engine), "merge", "--ff-only", "FETCH_HEAD"], check=True)
    else:
        subprocess.run(["git", "clone", "--branch", branch, "--", repository, str(engine)], check=True)
    validate_engine(engine, ("windows", "linux", "mac"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", type=Path)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--branch", default="main")
    args = parser.parse_args()
    try:
        prepare_engine(args.engine, args.repository, args.branch)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
