# NIKY PRAVITEL AI — Private Repository

Private backend + checker core for the code-checking platform.

## What is included
- FastAPI web app with responsive UI.
- No-registration API-token generation.
- Secure token hashing in SQLite; raw tokens are returned only once.
- Optional GitHub private-repository integration using an environment variable.
- Upload of ZIP files, text/code files and a controlled project archive.
- ZIP extraction with path-traversal protection.
- Static checks for Python, JavaScript, HTML, CSS, Bash and PowerShell.
- Safe Python syntax compilation with timeout/output limits.
- Conservative auto-fixes (whitespace/newline normalization only).
- Downloadable corrected project archive.
- Immediate cleanup of temporary uploads after the job finishes/download begins.
- Target matrix for Windows/Linux/macOS; real OS images are NOT bundled.

## Important architecture rule
Never put a real GitHub token into the public repository or browser JavaScript. GitHub states that personal access tokens are like passwords and should be kept as secrets. Use `GITHUB_TOKEN`/`GITHUB_PAT` as a server-side environment variable or a GitHub Actions secret instead.

The public repository therefore contains no real credential.

## Run locally

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/macOS
python -m app.main
```

Open http://127.0.0.1:8000

## GitHub private repository access
Set:
- `GITHUB_OWNER`
- `GITHUB_REPO`
- `GITHUB_REF` (optional)
- `GITHUB_TOKEN`

For a fine-grained token, grant only the minimum repository access needed, normally `Contents: read` for reading private repository files.

## OS images
Do not commit Windows/macOS installers or disk images into this repository automatically. Put your legally obtained test images into the local `os_images/` directory and configure an external VM/runner. The included target adapters report whether an external runner exists; they do not pretend to have tested an OS when it was not actually available.

See `docs/os-sources.md` for official download/support pages.
