# MarkItDown Web

`markitdown-web` is a FastAPI + React web application for converting uploaded files and remote HTTP(S) URLs to Markdown with MarkItDown.

## Run locally

```bash
pip install -e ../markitdown[all]
pip install -e .[test]
set MARKITDOWN_WEB_PASSWORD=change-me
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
| `MARKITDOWN_ENABLE_PLUGINS` | `false` | Enable installed MarkItDown plugins. |
| `OPENAI_API_KEY` | unset | Enables optional LLM features when the `openai` package is installed. |
| `MARKITDOWN_LLM_MODEL` | `gpt-4o` | LLM model used for image descriptions/OCR plugins. |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | unset | Enables Azure Document Intelligence conversion. |

## Frontend development

```bash
cd frontend
npm install
npm run dev
```

For production:

```bash
cd frontend
npm run build
```

The build writes static assets into `src/markitdown_web/static`.
