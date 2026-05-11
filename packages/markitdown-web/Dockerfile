FROM node:22-bookworm-slim AS frontend

WORKDIR /app/frontend
COPY packages/markitdown-web/frontend/package.json packages/markitdown-web/frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY packages/markitdown-web/frontend/ ./
RUN npm run build

FROM python:3.13-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV EXIFTOOL_PATH=/usr/bin/exiftool
ENV FFMPEG_PATH=/usr/bin/ffmpeg
ENV MARKITDOWN_WEB_TEMP_DIR=/tmp/markitdown-web

RUN apt-get update && apt-get install -y --no-install-recommends \
    exiftool \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
COPY --from=frontend /app/src/markitdown_web/static /app/packages/markitdown-web/src/markitdown_web/static

RUN pip --no-cache-dir install \
    /app/packages/markitdown[all] \
    /app/packages/markitdown-web

USER nobody:nogroup
EXPOSE 3000

ENTRYPOINT ["markitdown-web"]
CMD ["--host", "0.0.0.0", "--port", "3000"]
