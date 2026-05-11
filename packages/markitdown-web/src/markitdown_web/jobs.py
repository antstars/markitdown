import asyncio
import os
import shutil
import tempfile
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Literal
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile, status
from markitdown import MarkItDown, StreamInfo

from .config import Settings
from .security import fetch_public_url

JobStatus = Literal["queued", "running", "succeeded", "failed", "partial"]
ItemStatus = Literal["queued", "running", "succeeded", "failed"]


@dataclass
class JobItem:
    id: str
    name: str
    source_type: Literal["file", "url"]
    status: ItemStatus = "queued"
    title: str | None = None
    error: str | None = None
    markdown_path: Path | None = None


@dataclass
class Job:
    id: str
    status: JobStatus
    created_at: datetime
    expires_at: datetime
    directory: Path
    items: list[JobItem] = field(default_factory=list)


@dataclass
class ConversionInput:
    name: str
    source_type: Literal["file", "url"]
    local_path: Path | None = None
    url: str | None = None
    content_type: str | None = None


class JobStore:
    def __init__(self, settings: Settings, converter_factory: Callable[[], MarkItDown] | None = None) -> None:
        self._settings = settings
        self._settings.temp_root.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=settings.max_workers)
        self._converter_factory = converter_factory or self._build_converter

    async def create_file_job(self, files: list[UploadFile]) -> Job:
        self._validate_batch(len(files))
        job = self._new_job()
        inputs: list[ConversionInput] = []
        upload_dir = job.directory / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        for upload in files:
            filename = Path(upload.filename or "upload").name
            local_path = upload_dir / f"{uuid.uuid4().hex}_{filename}"
            await self._save_upload(upload, local_path)
            item = JobItem(id=uuid.uuid4().hex, name=filename, source_type="file")
            job.items.append(item)
            inputs.append(ConversionInput(name=filename, source_type="file", local_path=local_path, content_type=upload.content_type))
        await self._register(job)
        asyncio.create_task(self._run_job(job.id, inputs))
        return job

    async def create_url_job(self, urls: list[str]) -> Job:
        clean_urls = [url.strip() for url in urls if url.strip()]
        self._validate_batch(len(clean_urls))
        job = self._new_job()
        await self._register(job)
        inputs = [
            ConversionInput(name=url, source_type="url", url=url)
            for url in clean_urls
        ]
        for item_input in inputs:
            job.items.append(JobItem(id=uuid.uuid4().hex, name=item_input.name, source_type="url"))
        asyncio.create_task(self._run_job(job.id, inputs))
        return job

    async def get_job(self, job_id: str) -> Job:
        await self.cleanup_expired()
        async with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
        return job

    async def get_item_markdown_path(self, job_id: str, item_id: str) -> Path:
        job = await self.get_job(job_id)
        for item in job.items:
            if item.id == item_id:
                if item.status != "succeeded" or item.markdown_path is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Markdown result is not available.")
                return item.markdown_path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job item not found.")

    async def create_zip(self, job_id: str) -> Path:
        job = await self.get_job(job_id)
        zip_path = job.directory / "results.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for index, item in enumerate(job.items, start=1):
                if item.status == "succeeded" and item.markdown_path:
                    archive.write(item.markdown_path, arcname=f"{index:02d}-{_safe_stem(item.name)}.md")
        return zip_path

    async def cleanup_expired(self) -> None:
        now = datetime.now(timezone.utc)
        expired: list[Job] = []
        async with self._lock:
            for job_id, job in list(self._jobs.items()):
                if job.expires_at <= now:
                    expired.append(job)
                    del self._jobs[job_id]
        for job in expired:
            shutil.rmtree(job.directory, ignore_errors=True)

    def snapshot(self, job: Job) -> dict:
        return {
            "id": job.id,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "expires_at": job.expires_at.isoformat(),
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "source_type": item.source_type,
                    "status": item.status,
                    "title": item.title,
                    "error": item.error,
                    "markdown_url": f"/api/jobs/{job.id}/items/{item.id}/markdown" if item.status == "succeeded" else None,
                }
                for item in job.items
            ],
        }

    def _new_job(self) -> Job:
        job_id = uuid.uuid4().hex
        directory = Path(tempfile.mkdtemp(prefix=f"{job_id}-", dir=self._settings.temp_root))
        now = datetime.now(timezone.utc)
        return Job(
            id=job_id,
            status="queued",
            created_at=now,
            expires_at=now + timedelta(minutes=self._settings.ttl_minutes),
            directory=directory,
        )

    async def _register(self, job: Job) -> None:
        async with self._lock:
            self._jobs[job.id] = job

    async def _run_job(self, job_id: str, inputs: list[ConversionInput]) -> None:
        job = await self.get_job(job_id)
        job.status = "running"
        loop = asyncio.get_running_loop()
        for item, item_input in zip(job.items, inputs):
            item.status = "running"
            try:
                markdown, title = await loop.run_in_executor(self._executor, self._convert_input, job.directory, item_input)
                result_dir = job.directory / "results"
                result_dir.mkdir(parents=True, exist_ok=True)
                markdown_path = result_dir / f"{item.id}.md"
                markdown_path.write_text(markdown, encoding="utf-8")
                item.markdown_path = markdown_path
                item.title = title
                item.status = "succeeded"
            except Exception as exc:
                item.status = "failed"
                item.error = str(exc)
        successes = sum(1 for item in job.items if item.status == "succeeded")
        if successes == len(job.items):
            job.status = "succeeded"
        elif successes == 0:
            job.status = "failed"
        else:
            job.status = "partial"

    def _convert_input(self, job_dir: Path, item_input: ConversionInput) -> tuple[str, str | None]:
        converter = self._converter_factory()
        if item_input.source_type == "url":
            assert item_input.url is not None
            downloads_dir = job_dir / "downloads"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            parsed = urlparse(item_input.url)
            filename = Path(parsed.path).name or "remote-resource"
            local_path = downloads_dir / f"{uuid.uuid4().hex}_{filename}"
            with local_path.open("wb") as destination:
                content_type, final_url = fetch_public_url(
                    item_input.url,
                    destination,
                    max_bytes=self._settings.max_file_bytes,
                    timeout=self._settings.url_timeout_seconds,
                )
            stream_info = _stream_info(local_path, filename, item_input.url, content_type)
            result = converter.convert_local(local_path, stream_info=stream_info)
        else:
            assert item_input.local_path is not None
            stream_info = _stream_info(item_input.local_path, item_input.name, None, item_input.content_type)
            result = converter.convert_local(item_input.local_path, stream_info=stream_info)
        return result.markdown, result.title

    def _build_converter(self) -> MarkItDown:
        kwargs = {"enable_plugins": self._settings.enable_plugins}
        if self._settings.docintel_endpoint:
            kwargs["docintel_endpoint"] = self._settings.docintel_endpoint
        if self._settings.openai_api_key:
            try:
                from openai import OpenAI

                kwargs["llm_client"] = OpenAI(api_key=self._settings.openai_api_key)
                kwargs["llm_model"] = self._settings.llm_model
            except ModuleNotFoundError:
                pass
        return MarkItDown(**kwargs)

    def _validate_batch(self, count: int) -> None:
        if count < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one item is required.")
        if count > self._settings.max_batch:
            raise HTTPException(status_code=413, detail=f"Batch size exceeds {self._settings.max_batch}.")

    async def _save_upload(self, upload: UploadFile, destination: Path) -> None:
        total = 0
        with destination.open("wb") as output:
            while True:
                chunk = await upload.read(1024 * 256)
                if not chunk:
                    break
                total += len(chunk)
                if total > self._settings.max_file_bytes:
                    raise HTTPException(status_code=413, detail=f"File exceeds {self._settings.max_file_mb} MB.")
                output.write(chunk)
        await upload.close()


def _stream_info(path: Path, filename: str, url: str | None, content_type: str | None) -> StreamInfo:
    mimetype = None
    charset = None
    if content_type:
        parts = [part.strip() for part in content_type.split(";")]
        mimetype = parts[0] if parts and parts[0] else None
        for part in parts[1:]:
            if part.lower().startswith("charset="):
                charset = part.split("=", 1)[1].strip()
    return StreamInfo(
        filename=filename,
        extension=os.path.splitext(filename)[1] or path.suffix,
        local_path=str(path),
        url=url,
        mimetype=mimetype,
        charset=charset,
    )


def _safe_stem(name: str) -> str:
    stem = Path(name).stem or "result"
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in stem)
    return safe[:80] or "result"
