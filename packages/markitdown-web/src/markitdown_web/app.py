from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .auth import AuthManager
from .config import Settings, load_settings
from .jobs import JobStore


class LoginRequest(BaseModel):
    password: str


class UrlConvertRequest(BaseModel):
    urls: list[str]


def create_app(settings: Settings | None = None, job_store: JobStore | None = None) -> FastAPI:
    settings = settings or load_settings()
    auth = AuthManager(settings.secret_key, settings.password)
    store = job_store or JobStore(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await store.cleanup_expired()
        yield

    app = FastAPI(title="MarkItDown Web", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.auth = auth
    app.state.jobs = store

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["content-type", "x-csrf-token"],
    )

    def require_auth(request: Request) -> None:
        auth.require_session(request)

    def require_post_auth(request: Request) -> None:
        auth.require_csrf(request)

    @app.get("/api/health")
    async def health() -> dict:
        return {"ok": True}

    @app.get("/api/config")
    async def get_config(_: None = Depends(require_auth)) -> dict:
        return {
            "max_file_mb": settings.max_file_mb,
            "max_batch": settings.max_batch,
            "ttl_minutes": settings.ttl_minutes,
            "plugins_enabled": settings.enable_plugins,
            "llm_available": bool(settings.openai_api_key),
            "docintel_available": bool(settings.docintel_endpoint),
        }

    @app.post("/api/auth/login")
    async def login(payload: LoginRequest, request: Request, response: Response) -> dict:
        if not auth.verify_password(payload.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")
        auth.sign_in(response, secure_cookie=request.url.scheme == "https")
        return {"ok": True}

    @app.post("/api/auth/logout")
    async def logout(request: Request, response: Response) -> dict:
        auth.require_csrf(request)
        auth.sign_out(response)
        return {"ok": True}

    @app.post("/api/convert/files")
    async def convert_files(request: Request, files: list[UploadFile] = File(...)) -> dict:
        auth.require_csrf(request)
        job = await store.create_file_job(files)
        return store.snapshot(job)

    @app.post("/api/convert/url")
    async def convert_urls(request: Request, payload: UrlConvertRequest) -> dict:
        auth.require_csrf(request)
        job = await store.create_url_job(payload.urls)
        return store.snapshot(job)

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str, _: None = Depends(require_auth)) -> dict:
        job = await store.get_job(job_id)
        return store.snapshot(job)

    @app.get("/api/jobs/{job_id}/items/{item_id}/markdown")
    async def download_markdown(job_id: str, item_id: str, _: None = Depends(require_auth)) -> FileResponse:
        markdown_path = await store.get_item_markdown_path(job_id, item_id)
        return FileResponse(markdown_path, media_type="text/markdown; charset=utf-8", filename=f"{item_id}.md")

    @app.get("/api/jobs/{job_id}/download.zip")
    async def download_zip(job_id: str, _: None = Depends(require_auth)) -> FileResponse:
        zip_path = await store.create_zip(job_id)
        return FileResponse(zip_path, media_type="application/zip", filename=f"{job_id}.zip")

    static_dir = Path(__file__).parent / "static"
    if (static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
