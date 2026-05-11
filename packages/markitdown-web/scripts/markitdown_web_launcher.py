import argparse
import os
import threading
import time
import webbrowser

import uvicorn

from markitdown_web.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MarkItDown Web.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to.")
    parser.add_argument("--port", type=int, default=3000, help="Port to listen on.")
    parser.add_argument(
        "--password",
        default=None,
        help="Access password. Defaults to MARKITDOWN_WEB_PASSWORD or markitdown.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically.",
    )
    args = parser.parse_args()

    if args.password:
        os.environ["MARKITDOWN_WEB_PASSWORD"] = args.password
    else:
        os.environ.setdefault("MARKITDOWN_WEB_PASSWORD", "markitdown")

    url = f"http://{args.host}:{args.port}/"
    if not args.no_browser:
        threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    print(f"MarkItDown Web is running at {url}")
    print(f"Password: {os.environ['MARKITDOWN_WEB_PASSWORD']}")
    print("Press Ctrl+C to stop.")
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="info")


def _open_browser(url: str) -> None:
    time.sleep(1.5)
    webbrowser.open(url)


if __name__ == "__main__":
    main()
