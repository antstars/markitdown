import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests
from fastapi import HTTPException, status


def validate_public_http_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Only http(s) URLs are supported: {url}")
    _reject_private_host(parsed.hostname)
    return parsed.geturl()


def fetch_public_url(url: str, destination, *, max_bytes: int, timeout: int) -> tuple[str | None, str | None]:
    current = validate_public_http_url(url)
    headers = {"User-Agent": "markitdown-web/0.1"}
    with requests.Session() as session:
        for _ in range(6):
            with session.get(current, stream=True, timeout=timeout, allow_redirects=False, headers=headers) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL redirect did not include a Location header.")
                    current = validate_public_http_url(urljoin(current, location))
                    continue
                response.raise_for_status()
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > max_bytes:
                    raise HTTPException(status_code=413, detail="Remote file is too large.")
                total = 0
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        raise HTTPException(status_code=413, detail="Remote file is too large.")
                    destination.write(chunk)
                return response.headers.get("content-type"), current
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many redirects.")


def _reject_private_host(hostname: str) -> None:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to resolve host: {hostname}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Private or local network URLs are not allowed: {hostname}")
