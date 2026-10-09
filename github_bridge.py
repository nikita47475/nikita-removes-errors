import base64
from typing import Any
import requests
from .config import GITHUB_OWNER, GITHUB_REPO, GITHUB_REF, GITHUB_TOKEN


def configured() -> bool:
    return bool(GITHUB_OWNER and GITHUB_REPO and GITHUB_TOKEN)


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "User-Agent": "NikyPravitelAI/1.0",
    }


def repo_status() -> dict[str, Any]:
    if not configured():
        return {"configured": False, "message": "GitHub bridge is not configured."}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
    r = requests.get(url, headers=_headers(), timeout=10)
    r.raise_for_status()
    data = r.json()
    return {"configured": True, "private": data.get("private"), "full_name": data.get("full_name"), "default_branch": data.get("default_branch")}


def list_private_files(path: str = "") -> list[dict[str, Any]]:
    if not configured():
        return []
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}" if path else f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents"
    r = requests.get(url, params={"ref": GITHUB_REF}, headers=_headers(), timeout=15)
    r.raise_for_status()
    items = r.json()
    if isinstance(items, dict):
        items = [items]
    return [{"name": x.get("name"), "path": x.get("path"), "type": x.get("type"), "size": x.get("size")} for x in items]


def get_private_file(path: str) -> str:
    if not configured():
        raise RuntimeError("GitHub bridge is not configured")
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    r = requests.get(url, params={"ref": GITHUB_REF}, headers=_headers(), timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("encoding") != "base64":
        raise RuntimeError("Unsupported GitHub content encoding")
    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
