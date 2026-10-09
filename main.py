from __future__ import annotations
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi import BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import APP_NAME, HOST, PORT, JOBS_DIR, MAX_UPLOAD_MB, PUBLIC_API_BASE
from .checker import run_job, static_check, _read_text
from .token_service import generate_token, validate_token
from .github_bridge import repo_status, list_private_files, configured
from .targets import describe_platforms

app = FastAPI(title=APP_NAME, version="1.0.0")
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent.parent / "static"), name="static")


def require_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Введите API токен в формате Bearer <token>.")
    token = authorization[7:].strip()
    if not validate_token(token):
        raise HTTPException(401, "Недействительный или отозванный API токен.")
    return token


@app.get("/", response_class=HTMLResponse)
def home():
    return (Path(__file__).resolve().parent.parent / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health():
    return {"ok": True, "name": APP_NAME, "api_base": PUBLIC_API_BASE}


@app.get("/api/targets")
def targets():
    return describe_platforms()


@app.post("/api/token")
def new_token():
    token = generate_token()
    return {"token": token, "endpoint": f"{PUBLIC_API_BASE}/api/check", "warning": "Показывается один раз. Храните токен как секрет."}


@app.get("/api/github/status")
def github_status(authorization: str | None = Header(default=None)):
    require_token(authorization)
    if not configured():
        return {"configured": False}
    try:
        return repo_status()
    except Exception as e:
        raise HTTPException(502, f"GitHub bridge error: {e}")


@app.get("/api/github/files")
def github_files(path: str = "", authorization: str | None = Header(default=None)):
    require_token(authorization)
    if not configured():
        return {"configured": False, "files": []}
    try:
        return {"configured": True, "files": list_private_files(path)}
    except Exception as e:
        raise HTTPException(502, f"GitHub bridge error: {e}")


@app.post("/api/check")
async def check_code(
    authorization: str | None = Header(default=None),
    platform: str = Form("auto"),
    code: str = Form(""),
    upload: UploadFile | None = File(default=None),
):
    require_token(authorization)
    job_id = str(uuid.uuid4())
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    src = None
    try:
        if upload and upload.filename:
            data = await upload.read()
            if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
                raise HTTPException(413, f"Файл слишком большой. Максимум: {MAX_UPLOAD_MB} MB.")
            safe_name = Path(upload.filename).name
            src = job_dir / safe_name
            src.write_bytes(data)
            result = run_job(src, job_dir)
            result.update({"job_id": job_id, "platform": platform, "mode": "upload"})
            return {"ok": True, "result": result, "download_url": f"/api/download/{job_id}"}
        if code.strip():
            temp = job_dir / "submitted.py" if platform in {"python", "auto"} else job_dir / "submitted.txt"
            temp.write_text(code, encoding="utf-8")
            issues = static_check(temp)
            result = {"job_id": job_id, "platform": platform, "mode": "code", "issues": [i.__dict__ for i in issues], "corrected_code": code}
            return {"ok": True, "result": result}
        raise HTTPException(400, "Загрузите файл или вставьте код.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))
    finally:
        # Keep only the generated archive until download. Original uploads are not retained separately.
        if src and src.exists() and src.suffix.lower() != ".zip":
            src.unlink(missing_ok=True)


@app.get("/api/download/{job_id}")
def download(job_id: str, background_tasks: BackgroundTasks):
    job_dir = JOBS_DIR / job_id
    archive = job_dir / "fixed_project.zip"
    if not archive.exists():
        raise HTTPException(404, "Файл уже удалён или не найден.")
    background_tasks.add_task(shutil.rmtree, job_dir, ignore_errors=True)
    return FileResponse(archive, filename="project-client-fixed.zip", media_type="application/zip", background=background_tasks)


@app.delete("/api/job/{job_id}")
def delete_job(job_id: str):
    job_dir = JOBS_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
