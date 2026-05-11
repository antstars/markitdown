import asyncio
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from markitdown import DocumentConverterResult

from markitdown_web.app import create_app
from markitdown_web.config import Settings
from markitdown_web.jobs import JobStore


class DummyConverter:
    def convert_local(self, path, stream_info=None):
        if "fail" in Path(path).name:
            raise RuntimeError("forced failure")
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        return DocumentConverterResult(f"# {stream_info.filename}\n\n{text}", title=stream_info.filename)


@pytest.fixture()
def client(tmp_path):
    settings = Settings(
        password="secret",
        secret_key="test-secret",
        max_file_mb=1,
        max_batch=3,
        ttl_minutes=60,
        max_workers=1,
        temp_root=tmp_path,
        enable_plugins=False,
        openai_api_key=None,
        llm_model="gpt-4o",
        docintel_endpoint=None,
        url_timeout_seconds=2,
    )
    store = JobStore(settings, converter_factory=DummyConverter)
    app = create_app(settings, store)
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"password": "secret"})
    assert response.status_code == 200
    return client.cookies["mid_csrf"]


def wait_for_job(client: TestClient, job_id: str) -> dict:
    for _ in range(50):
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] not in {"queued", "running"}:
            return payload
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_auth_required(client):
    response = client.get("/api/config")
    assert response.status_code == 401


def test_health_does_not_require_auth(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_login_rejects_bad_password(client):
    response = client.post("/api/auth/login", json={"password": "bad"})
    assert response.status_code == 401


def test_file_conversion_and_download(client):
    csrf = login(client)
    response = client.post(
        "/api/convert/files",
        files=[("files", ("hello.txt", b"hello world", "text/plain"))],
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 200
    job = wait_for_job(client, response.json()["id"])
    assert job["status"] == "succeeded"
    item = job["items"][0]
    download = client.get(item["markdown_url"])
    assert download.status_code == 200
    assert "# hello.txt" in download.text


def test_batch_allows_partial_failure(client):
    csrf = login(client)
    response = client.post(
        "/api/convert/files",
        files=[
            ("files", ("ok.txt", b"ok", "text/plain")),
            ("files", ("fail.txt", b"fail", "text/plain")),
        ],
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 200
    job = wait_for_job(client, response.json()["id"])
    assert job["status"] == "partial"
    assert [item["status"] for item in job["items"]] == ["succeeded", "failed"]


def test_csrf_required_for_mutations(client):
    login(client)
    response = client.post(
        "/api/convert/files",
        files=[("files", ("hello.txt", b"hello", "text/plain"))],
    )
    assert response.status_code == 403


def test_batch_limit(client):
    csrf = login(client)
    response = client.post(
        "/api/convert/url",
        json={"urls": ["https://example.com/a", "https://example.com/b", "https://example.com/c", "https://example.com/d"]},
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 413


def test_upload_size_limit(client):
    csrf = login(client)
    response = client.post(
        "/api/convert/files",
        files=[("files", ("large.txt", b"x" * (1024 * 1024 + 1), "text/plain"))],
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 413


def test_private_url_rejected(client):
    csrf = login(client)
    response = client.post(
        "/api/convert/url",
        json={"urls": ["http://127.0.0.1/private"]},
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 200
    job = wait_for_job(client, response.json()["id"])
    assert job["status"] == "failed"
    assert "Private or local network" in job["items"][0]["error"]


def test_zip_download(client):
    csrf = login(client)
    response = client.post(
        "/api/convert/files",
        files=[("files", ("hello.txt", b"hello", "text/plain"))],
        headers={"x-csrf-token": csrf},
    )
    job = wait_for_job(client, response.json()["id"])
    download = client.get(f"/api/jobs/{job['id']}/download.zip")
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"


def test_cleanup_expired(tmp_path):
    settings = Settings(
        password="secret",
        secret_key="test-secret",
        max_file_mb=1,
        max_batch=3,
        ttl_minutes=0,
        max_workers=1,
        temp_root=tmp_path,
        enable_plugins=False,
        openai_api_key=None,
        llm_model="gpt-4o",
        docintel_endpoint=None,
        url_timeout_seconds=2,
    )
    store = JobStore(settings, converter_factory=DummyConverter)

    async def scenario():
        job = store._new_job()
        await store._register(job)
        assert job.directory.exists()
        await store.cleanup_expired()
        assert not job.directory.exists()

    asyncio.run(scenario())
