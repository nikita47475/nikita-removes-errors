from __future__ import annotations
import ast
import json
import os
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path

from .config import JOB_TIMEOUT_SECONDS, MAX_UPLOAD_MB

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".html", ".htm", ".css", ".sh", ".bash", ".ps1", ".bat", ".cmd", ".json", ".yaml", ".yml"
}

@dataclass
class Issue:
    severity: str
    file: str
    line: int | None
    message: str
    suggestion: str


def safe_zip_members(zf: zipfile.ZipFile) -> None:
    total_unpacked = 0
    max_total = MAX_UPLOAD_MB * 4 * 1024 * 1024
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or name == ".." or name.startswith("../") or "/../" in name:
            raise ValueError(f"Unsafe ZIP path: {info.filename}")
        # Reject Unix symlinks in ZIP archives; they can escape the intended extraction tree.
        if ((info.external_attr >> 16) & 0o170000) == 0o120000:
            raise ValueError(f"Symlink is not allowed in ZIP: {info.filename}")
        if info.file_size > MAX_UPLOAD_MB * 1024 * 1024:
            raise ValueError(f"ZIP member too large: {info.filename}")
        total_unpacked += info.file_size
        if total_unpacked > max_total:
            raise ValueError("ZIP unpacked size is too large")


def extract_upload(src: Path, job_dir: Path) -> Path:
    work = job_dir / "project"
    work.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as zf:
            safe_zip_members(zf)
            zf.extractall(work)
    else:
        target = work / src.name
        shutil.copy2(src, target)
    return work


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None


def static_check(path: Path) -> list[Issue]:
    issues: list[Issue] = []
    files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
    for f in files:
        if f.stat().st_size > 2 * 1024 * 1024:
            continue
        text = _read_text(f)
        if text is None:
            continue
        rel = str(f.relative_to(path if path.is_dir() else f.parent)).replace("\\", "/")
        suffix = f.suffix.lower()
        lines = text.splitlines()
        if suffix == ".py":
            try:
                ast.parse(text, filename=str(f))
            except SyntaxError as e:
                issues.append(Issue("error", rel, e.lineno, e.msg, "Исправьте синтаксис Python в указанной строке."))
        if suffix in {".json"}:
            try:
                json.loads(text)
            except json.JSONDecodeError as e:
                issues.append(Issue("error", rel, e.lineno, f"JSON: {e.msg}", "Проверьте запятые, кавычки и структуру JSON."))
        if suffix in {".html", ".htm"} and "<html" not in text.lower():
            issues.append(Issue("warning", rel, 1, "HTML-документ не содержит <html>.", "Проверьте структуру HTML."))
        if "TODO_ERROR" in text:
            issues.append(Issue("warning", rel, next((i for i,l in enumerate(lines,1) if "TODO_ERROR" in l),1), "Найден маркер TODO_ERROR.", "Замените временный маркер реальной логикой."))
        if re.search(r"\b(eval|exec)\s*\(", text) and suffix == ".py":
            issues.append(Issue("warning", rel, 1, "Используется eval/exec.", "Уберите динамическое выполнение кода, если оно не требуется."))
    return issues


def conservative_fix(path: Path) -> int:
    changed = 0
    files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
    for f in files:
        if f.suffix.lower() not in CODE_EXTENSIONS or f.stat().st_size > 2 * 1024 * 1024:
            continue
        text = _read_text(f)
        if text is None:
            continue
        fixed = text.replace("\r\n", "\n").replace("\r", "\n")
        fixed = "\n".join(line.rstrip() for line in fixed.split("\n"))
        if fixed and not fixed.endswith("\n"):
            fixed += "\n"
        if fixed != text:
            f.write_text(fixed, encoding="utf-8")
            changed += 1
    return changed


def run_safe_python_checks(project: Path) -> list[Issue]:
    issues: list[Issue] = []
    py_files = list(project.rglob("*.py")) if project.is_dir() else ([project] if project.suffix == ".py" else [])
    for f in py_files:
        try:
            completed = subprocess.run(
                [os.environ.get("PYTHON", "python"), "-m", "py_compile", str(f)],
                cwd=str(project if project.is_dir() else f.parent),
                capture_output=True,
                text=True,
                timeout=JOB_TIMEOUT_SECONDS,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        except subprocess.TimeoutExpired:
            issues.append(Issue("error", f.name, None, "Проверка Python превысила лимит времени.", "Проверьте бесконечные циклы и тяжёлые операции."))
            continue
        if completed.returncode != 0:
            issues.append(Issue("error", f.name, None, completed.stderr[-1000:] or "Python check failed.", "Исправьте ошибку компиляции Python."))
    return issues


def package_fixed(project: Path, out_zip: Path) -> None:
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        base = project.parent
        for p in project.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(base))


def run_job(src: Path, job_dir: Path) -> dict:
    project = extract_upload(src, job_dir)
    initial = static_check(project)
    runtime = run_safe_python_checks(project)
    changed = conservative_fix(project)
    after = static_check(project) + run_safe_python_checks(project)
    output_zip = job_dir / "fixed_project.zip"
    package_fixed(project, output_zip)
    return {
        "initial_issues": [asdict(x) for x in initial + runtime],
        "remaining_issues": [asdict(x) for x in after],
        "changed_files": changed,
        "fixed_archive": output_zip.name,
    }
