#!/usr/bin/env python3
"""Create a fictional Git history for trying Repo Ofrenda."""

import os
import subprocess
import sys
from pathlib import Path


def run(repo: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, env=env, capture_output=True, text=True)


def commit(repo: Path, day: str, author: str, message: str) -> None:
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": author,
        "GIT_AUTHOR_EMAIL": "demo@example.invalid",
        "GIT_COMMITTER_NAME": author,
        "GIT_COMMITTER_EMAIL": "demo@example.invalid",
        "GIT_AUTHOR_DATE": f"{day}T12:00:00+05:30",
        "GIT_COMMITTER_DATE": f"{day}T12:00:00+05:30",
    })
    run(repo, "add", "-A", env=env)
    run(repo, "commit", "-m", message, env=env)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 make_demo.py /path/to/new-demo-repository")
    repo = Path(sys.argv[1]).expanduser().resolve()
    if repo.exists() and any(repo.iterdir()):
        raise SystemExit(f"Refusing to overwrite a non-empty directory: {repo}")
    repo.mkdir(parents=True, exist_ok=True)
    run(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("# Lantern\n\nA fictional neighbourhood library project.\n")
    commit(repo, "2026-03-02", "Mira", "Begin the Lantern catalogue")
    (repo / "catalogue.csv").write_text("title,year\nThe Paper Garden,1987\n")
    commit(repo, "2026-03-18", "Mira", "Add the first borrowed stories")
    (repo / "README.md").write_text("# Lantern\n\nA tiny catalogue for the neighbourhood library.\n")
    (repo / "checkouts.py").write_text('def checkout(title, reader):\n    return {"title": title, "reader": reader}\n')
    commit(repo, "2026-04-04", "Ishan", "Remember who took each book home")
    (repo / "tests.md").write_text("Manual check: a returned book should be available again.\n")
    commit(repo, "2026-04-20", "Mira", "Write down the return-desk ritual")
    (repo / "catalogue.csv").write_text("title,year\nThe Paper Garden,1987\nA Map of Small Things,2001\n")
    commit(repo, "2026-05-11", "Ishan", "Make room for the spring collection")
    (repo / "README.md").write_text("# Lantern\n\nThe first shelf is ready. More stories soon.\n")
    commit(repo, "2026-05-28", "Mira", "Open the first shelf to neighbours")
    print(f"Created fictional demo history at {repo}")


if __name__ == "__main__":
    main()
