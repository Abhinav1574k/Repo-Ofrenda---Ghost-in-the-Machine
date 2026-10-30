# Repo Ofrenda

**A memory timeline for a project's code.** Repo Ofrenda turns a Git repository's commits into monthly chapters and can ask a locally run open-weight model to write a short, source-grounded remembrance of a chapter.

The project keeps the scope deliberately small: it reads commit metadata and changed file names, not file contents. It binds its web server to `127.0.0.1`, and only sends the selected month's commit metadata to the Ollama instance you configure. No hosted AI service is used.

## Run it

Requirements: Python 3.10+ and Git. For AI narration, install [Ollama](https://ollama.com/) and download a model such as `qwen2.5:3b`:

```bash
ollama pull qwen2.5:3b
python3 repo_ofrenda.py /path/to/your/git/repository
```

Open <http://127.0.0.1:8787> in your browser. Stop the server with `Ctrl+C`.

The history timeline works without Ollama. Without a local model, Repo Ofrenda shows an evidence-only summary and explains that AI narration is unavailable. You can choose a different Ollama model:

```bash
python3 repo_ofrenda.py /path/to/repo --model gemma3:4b --port 8788
```

To use a different local Ollama endpoint, set `OLLAMA_HOST` (default `http://127.0.0.1:11434`).

## Reproducible demo

Create a small, fictional repository with a handful of dated milestones:

```bash
python3 make_demo.py /tmp/ofrenda-demo
python3 repo_ofrenda.py /tmp/ofrenda-demo
```

The fixture is synthetic and does not represent the history of a real project. It gives the timeline a few recognizable chapters so you can try the interface immediately.

## How it works

1. Git supplies up to 500 commits across local branches, with dates, authors, subjects, and changed paths.
2. Repo Ofrenda groups these records by month and renders a chapter timeline.
3. Selecting a chapter submits that month's commit metadata to the configured local Ollama chat endpoint.
4. The model is told to stay within the supplied record and cite commit hashes. If Ollama is unavailable, or a response cites a hash outside the supplied records, the app falls back to a factual summary.
5. The source commits remain visible beside the story so readers can check its grounding.

The citations improve traceability, but they do not prove that every sentence is supported; treat the narration as an interpretation and inspect its source commits.

## Privacy and limits

- The server listens only on localhost.
- The project sends commit metadata (author names, messages, changed paths, and short hashes) to your local Ollama service when you request a story. Those details can themselves be sensitive.
- It does not read or transmit source file contents.
- Ollama may need a network connection to download a model the first time; inference can run locally after that.
- Git history shows recorded changes, not the private thoughts or full intent of contributors. Repo Ofrenda should not invent those.
- Very large histories are capped at the most recent 500 commits.

## Built with

- Python standard library (`http.server`, `urllib`, `subprocess`)
- Git
- Ollama-compatible local model API (optional at runtime)
- HTML, CSS, and browser JavaScript

## License

MIT. See [LICENSE](LICENSE).
