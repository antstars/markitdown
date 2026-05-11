# MarkItDown Web

`markitdown-web` is a FastAPI + React web application for converting uploaded files and remote HTTP(S) URLs to Markdown with MarkItDown.

## Features

- Drag-and-drop upload for files supported by MarkItDown
- Batch HTTP(S) URL conversion
- Per-item conversion status, title, and error reporting
- Markdown preview, copy, individual `.md` download, and batch `.zip` download
- Password-protected access with signed cookies and CSRF protection
- Temporary job storage with automatic expiry
- Upload size, batch size, URL timeout, and public-deployment URL safety controls
- Optional plugin, LLM, OCR, and Azure Document Intelligence support through environment variables

## Run Locally

Linux/macOS:

```bash
pip install -e ../markitdown[all]
pip install -e .

export MARKITDOWN_WEB_PASSWORD=change-me
markitdown-web --host 127.0.0.1 --port 3000
```

Windows PowerShell:

```powershell
pip install -e ../markitdown[all]
pip install -e .

$env:MARKITDOWN_WEB_PASSWORD = 'change-me'
markitdown-web --host 127.0.0.1 --port 3000
```

Open `http://127.0.0.1:3000` and sign in with `MARKITDOWN_WEB_PASSWORD`.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `MARKITDOWN_WEB_PASSWORD` | `markitdown` | Single shared access password. Set this before public deployment. |
| `MARKITDOWN_WEB_SECRET_KEY` | generated at startup | HMAC key for session cookies. Set this for multi-worker or restarted deployments. |
| `MARKITDOWN_WEB_MAX_FILE_MB` | `50` | Maximum size per uploaded file or fetched URL. |
| `MARKITDOWN_WEB_MAX_BATCH` | `20` | Maximum items per batch. |
| `MARKITDOWN_WEB_TTL_MINUTES` | `60` | How long temporary job files/results are retained. |
| `MARKITDOWN_WEB_MAX_WORKERS` | `2` | Concurrent conversion workers. |
| `MARKITDOWN_WEB_TEMP_DIR` | `.markitdown-web` | Temporary job root directory. |
| `MARKITDOWN_WEB_URL_TIMEOUT_SECONDS` | `20` | Timeout for server-side URL downloads. |
| `MARKITDOWN_ENABLE_PLUGINS` | `false` | Enable installed MarkItDown plugins. |
| `OPENAI_API_KEY` | unset | Enables optional LLM features when the `openai` package is installed. |
| `MARKITDOWN_LLM_MODEL` | `gpt-4o` | LLM model used for image descriptions/OCR plugins. |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | unset | Enables Azure Document Intelligence conversion. |

## Frontend Development

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:3000`, so run the FastAPI app separately while developing the frontend.

For production:

```bash
cd frontend
npm ci
npm run build
```

The build writes static assets into `src/markitdown_web/static`.

## Build Executables

PyInstaller builds are platform-specific. Build Windows `.exe` files on Windows, Linux binaries on Linux, and macOS binaries on macOS. Python 3.10-3.13 is recommended for full optional dependency support.

Install build dependencies:

```bash
pip install -U pyinstaller
pip install -e ../markitdown[all]
pip install -e .

cd frontend
npm ci
npm run build
cd ..
```

### Windows

Run from the repository root:

```powershell
python -m PyInstaller --noconfirm --clean --name MarkItDownWeb --onefile --console `
  --paths packages/markitdown-web/src `
  --paths packages/markitdown/src `
  --collect-all markitdown `
  --collect-all magika `
  --collect-all pdfplumber `
  --collect-all pypdfium2 `
  --collect-all openpyxl `
  --collect-all pptx `
  --collect-all mammoth `
  --add-data "packages/markitdown-web/src/markitdown_web/static;markitdown_web/static" `
  packages/markitdown-web/scripts/markitdown_web_launcher.py
```

Output:

```text
dist/MarkItDownWeb.exe
```

### Linux

Install useful system tools first when you need audio or EXIF metadata support:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg exiftool
```

Run from the repository root:

```bash
python -m PyInstaller --noconfirm --clean --name MarkItDownWeb --onefile --console \
  --paths packages/markitdown-web/src \
  --paths packages/markitdown/src \
  --collect-all markitdown \
  --collect-all magika \
  --collect-all pdfplumber \
  --collect-all pypdfium2 \
  --collect-all openpyxl \
  --collect-all pptx \
  --collect-all mammoth \
  --add-data "packages/markitdown-web/src/markitdown_web/static:markitdown_web/static" \
  packages/markitdown-web/scripts/markitdown_web_launcher.py
```

Output:

```text
dist/MarkItDownWeb
```

### macOS

Install useful system tools first when you need audio or EXIF metadata support:

```bash
brew install ffmpeg exiftool
```

Run from the repository root:

```bash
python -m PyInstaller --noconfirm --clean --name MarkItDownWeb --onefile --console \
  --paths packages/markitdown-web/src \
  --paths packages/markitdown/src \
  --collect-all markitdown \
  --collect-all magika \
  --collect-all pdfplumber \
  --collect-all pypdfium2 \
  --collect-all openpyxl \
  --collect-all pptx \
  --collect-all mammoth \
  --add-data "packages/markitdown-web/src/markitdown_web/static:markitdown_web/static" \
  packages/markitdown-web/scripts/markitdown_web_launcher.py
```

Output:

```text
dist/MarkItDownWeb
```

Run the packaged app:

```bash
./dist/MarkItDownWeb --port 3000 --password change-me
```

On Windows:

```powershell
.\dist\MarkItDownWeb.exe --port 3000 --password change-me
```

The launcher opens the browser automatically unless `--no-browser` is supplied.

## Docker

From the repository root:

```bash
docker build -f packages/markitdown-web/Dockerfile -t markitdown-web:latest .
docker run --rm -p 3000:3000 \
  -e MARKITDOWN_WEB_PASSWORD=change-me \
  -e MARKITDOWN_WEB_SECRET_KEY=replace-with-a-long-random-secret \
  markitdown-web:latest
```

Open `http://127.0.0.1:3000`.

For Docker Compose:

```bash
cp deploy/linux/markitdown-web.env.example .env
# Edit .env and set MARKITDOWN_WEB_PASSWORD and MARKITDOWN_WEB_SECRET_KEY.
docker compose up --build
```

The Compose service stores temporary job data in a named volume and checks `GET /api/health`.

## Linux systemd

Copy or clone the repository into `/opt/markitdown`, then create a virtual environment:

```bash
sudo useradd --system --home /opt/markitdown --shell /usr/sbin/nologin markitdown
sudo mkdir -p /opt/markitdown /var/lib/markitdown-web
sudo chown -R markitdown:markitdown /opt/markitdown /var/lib/markitdown-web

cd /opt/markitdown
python3 -m venv .venv
.venv/bin/pip install -e 'packages/markitdown[all]' -e packages/markitdown-web
```

Install the environment and service files:

```bash
sudo cp deploy/linux/markitdown-web.env.example /etc/markitdown-web.env
sudo editor /etc/markitdown-web.env
sudo cp deploy/linux/markitdown-web.service /etc/systemd/system/markitdown-web.service
sudo systemctl daemon-reload
sudo systemctl enable --now markitdown-web
```

Check status and logs:

```bash
systemctl status markitdown-web
journalctl -u markitdown-web -f
```

The service binds to `127.0.0.1:3000` by default. Put it behind a TLS reverse proxy before exposing it publicly.

## macOS launchd

From a user-owned repository checkout, install the app, then edit the plist paths and environment values:

```bash
python3 -m venv .venv
.venv/bin/pip install -e 'packages/markitdown[all]' -e packages/markitdown-web

cp deploy/macos/com.markitdown.web.plist ~/Library/LaunchAgents/com.markitdown.web.plist
open -e ~/Library/LaunchAgents/com.markitdown.web.plist
```

Replace `YOUR_USER`, set `MARKITDOWN_WEB_PASSWORD`, and set a stable `MARKITDOWN_WEB_SECRET_KEY`. Then load it:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.markitdown.web.plist
launchctl enable gui/$(id -u)/com.markitdown.web
launchctl kickstart -k gui/$(id -u)/com.markitdown.web
```

Logs are written to `~/Library/Logs/markitdown-web.log` and `~/Library/Logs/markitdown-web.err.log`.

## Production notes

Always set a strong `MARKITDOWN_WEB_PASSWORD` and a stable `MARKITDOWN_WEB_SECRET_KEY` for production. Keep the app bound to localhost when using systemd or launchd, terminate TLS in a reverse proxy, and tune `MARKITDOWN_WEB_MAX_FILE_MB`, `MARKITDOWN_WEB_MAX_BATCH`, `MARKITDOWN_WEB_MAX_WORKERS`, and `MARKITDOWN_WEB_URL_TIMEOUT_SECONDS` for the machine size and threat model.
