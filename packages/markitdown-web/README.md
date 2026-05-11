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
docker run --rm -p 3000:3000 -e MARKITDOWN_WEB_PASSWORD=change-me markitdown-web:latest
```

Open `http://127.0.0.1:3000`.
