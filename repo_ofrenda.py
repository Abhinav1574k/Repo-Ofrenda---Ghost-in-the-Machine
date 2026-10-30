#!/usr/bin/env python3
"""A local-first memory timeline for Git repositories."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent


def git(*args: str, repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git command failed")
    return result.stdout


def load_history(repo: Path) -> tuple[str, list[dict[str, object]]]:
    repo = repo.expanduser().resolve()
    if not repo.exists() or not git("rev-parse", "--is-inside-work-tree", repo=repo).strip() == "true":
        raise RuntimeError(f"{repo} is not inside a Git repository")

    project = git("rev-parse", "--show-toplevel", repo=repo).strip()
    records = git(
        "log", "--all", "--date=short", "--format=%H%x1f%ad%x1f%an%x1f%s", "--name-only", "-n", "500", repo=repo
    )
    commits: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in records.splitlines():
        if "\x1f" in line:
            if current:
                current["files"] = sorted(set(current["files"]))
                commits.append(current)
            sha, day, author, subject = line.split("\x1f", 3)
            current = {
                "sha": sha[:12],
                "day": day,
                "month": day[:7],
                "author": author,
                "subject": subject or "(no commit message)",
                "files": [],
            }
        elif current and line.strip():
            current["files"].append(line.strip())
    if current:
        current["files"] = sorted(set(current["files"]))
        commits.append(current)
    commits.sort(key=lambda item: (item["day"], item["sha"]))
    return Path(project).name, commits


def local_story(month: str, entries: list[dict[str, object]]) -> str:
    if not entries:
        return "The record is quiet for this chapter. There are no commits in this month."
    authors = sorted({str(entry["author"]) for entry in entries})
    sources = " ".join(f'[{entry["sha"]}]' for entry in entries[-3:])
    opening = f"This chapter contains {len(entries)} recorded changes"
    if len(authors) == 1:
        opening += f", shaped by {authors[0]}."
    else:
        opening += f", with {len(authors)} contributors in the record."
    themes = ", ".join(str(entry["subject"]) for entry in entries[-3:])
    return f"{opening} The latest notes mention {themes}. {sources}"


def tell_with_ollama(month: str, entries: list[dict[str, object]], model: str) -> tuple[str, str | None]:
    context = "\n".join(
        f'- [{item["sha"]}] {item["day"]} — {item["author"]}: {item["subject"]} (files: {", ".join(item["files"][:8])})'
        for item in entries[-60:]
    )
    prompt = (
        "Write a short, thoughtful remembrance of this software project's history for the selected month. "
        "Use only the supplied Git records. Do not infer motives, private feelings, or events beyond the record. "
        "Cite factual sentences with the exact short commit hash in square brackets. If the evidence is sparse, say so. "
        "Keep it to 3–5 sentences, warm but not spooky.\n\n"
        f"Month: {month}\nGit records:\n{context}"
    )
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    request = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps({"model": model, "stream": False, "messages": [{"role": "user", "content": prompt}], "options": {"temperature": 0.35}}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read())
        story = payload.get("message", {}).get("content", "").strip()
        if not story:
            return local_story(month, entries), "The local model returned an empty answer; showing the Git-record summary instead."
        # A citation is useful only if the referenced commit came from this evidence set.
        import re
        allowed = {str(entry["sha"]) for entry in entries[:60]}
        cited = re.findall(r"\[([0-9a-f]{7,12})\]", story)
        if not cited or any(sha not in allowed for sha in cited):
            return local_story(month, entries), "The model cited a commit outside the retrieved records; showing the Git-record summary instead."
        return story, None
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return local_story(month, entries), f"Local model unavailable ({error}). Showing the Git-record summary; start Ollama and pull {model} for AI narration."


class Handler(BaseHTTPRequestHandler):
    repo: Path
    model: str

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            project, commits = load_history(self.repo)
            if parsed.path == "/api/data":
                grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
                for commit in commits:
                    grouped[str(commit["month"])].append(commit)
                payload = {"project": project, "months": [{"month": key, "count": len(value), "commits": value} for key, value in sorted(grouped.items(), reverse=True)]}
                return self._send(200, json.dumps(payload).encode(), "application/json; charset=utf-8")
            if parsed.path == "/api/story":
                month = parse_qs(parsed.query).get("month", [""])[0]
                records = [item for item in commits if item["month"] == month]
                story, note = tell_with_ollama(month, records, self.model)
                return self._send(200, json.dumps({"story": story, "note": note, "sources": records[-12:]}).encode(), "application/json; charset=utf-8")
            if parsed.path == "/" or parsed.path == "/index.html":
                page = (ROOT / "index.html").read_bytes()
                return self._send(200, page, "text/html; charset=utf-8")
            return self._send(404, b"Not found", "text/plain; charset=utf-8")
        except (RuntimeError, OSError) as error:
            return self._send(500, json.dumps({"error": str(error)}).encode(), "application/json; charset=utf-8")

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="A private, local memory timeline for a Git repository.")
    parser.add_argument("repo", nargs="?", default=".", help="Git repository to remember (default: current directory)")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--model", default=os.environ.get("REPO_OFRENDA_MODEL", "qwen2.5:3b"))
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    Handler.repo = repo
    Handler.model = args.model
    project, commits = load_history(repo)
    if not commits:
        raise SystemExit(f"No commits found in {repo}; initialize it with at least one commit first.")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Repo Ofrenda remembers {project}: {len(commits)} commits")
    print(f"Open http://127.0.0.1:{args.port}  (local only; Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nClosing Repo Ofrenda.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
