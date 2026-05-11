# MarkItDown

[![PyPI](https://img.shields.io/pypi/v/markitdown.svg)](https://pypi.org/project/markitdown/)
![PyPI - Downloads](https://img.shields.io/pypi/dd/markitdown)
[![Built by AutoGen Team](https://img.shields.io/badge/Built%20by-AutoGen%20Team-blue)](https://github.com/microsoft/autogen)

[English](https://github.com/antstars/markitdown/blob/main/README.md) | [中文](https://github.com/antstars/markitdown/blob/main/README.zh-CN.md)

> [!IMPORTANT]
> MarkItDown 会以当前进程的权限执行 I/O 操作。它像 `open()` 或 `requests.get()` 一样，可以访问当前进程有权限访问的本地资源或网络资源。在不可信环境中使用时，请清理输入，并优先调用范围最窄的转换函数，例如 `convert_stream()` 或 `convert_local()`。更多信息请阅读本文档的“安全注意事项”。

MarkItDown 是一个轻量级 Python 工具，可以把多种文件格式转换为 Markdown，便于 LLM、文本分析和知识处理流程使用。它会尽量保留标题、列表、表格、链接等重要文档结构。输出通常足够易读，但主要目标是给文本分析工具消费，而不是做高保真排版还原。

MarkItDown 当前支持从以下内容转换：

- PDF
- PowerPoint
- Word
- Excel
- 图片，包含 EXIF 元数据和可选 OCR
- 音频，包含 EXIF 元数据和语音转写
- HTML
- 文本类格式，例如 CSV、JSON、XML
- ZIP 文件，会遍历压缩包内容
- YouTube URL
- EPub
- 以及更多格式

## 为什么选择 Markdown？

Markdown 非常接近纯文本，但仍能表达常见文档结构。主流 LLM 对 Markdown 的理解很好，也经常自然生成 Markdown。另一个实际好处是，Markdown 通常比较节省 token。

## 环境要求

MarkItDown 需要 Python 3.10 或更高版本。建议使用虚拟环境，避免依赖冲突。

标准 Python 虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

使用 `uv`：

```bash
uv venv --python=3.12 .venv
source .venv/bin/activate
# 注意：在这个虚拟环境里推荐使用 uv pip install，而不是直接 pip install
```

使用 Anaconda：

```bash
conda create -n markitdown python=3.12
conda activate markitdown
```

## 安装

从 PyPI 安装：

```bash
pip install 'markitdown[all]'
```

从源码安装：

```bash
git clone https://github.com/antstars/markitdown.git
cd markitdown
pip install -e 'packages/markitdown[all]'
```

## 使用方法

### 命令行

```bash
markitdown path-to-file.pdf > document.md
```

指定输出文件：

```bash
markitdown path-to-file.pdf -o document.md
```

也可以通过管道输入：

```bash
cat path-to-file.pdf | markitdown
```

### 可选依赖

MarkItDown 使用可选依赖来启用不同格式。安装 `[all]` 会安装所有可选依赖，也可以按需安装：

```bash
pip install 'markitdown[pdf, docx, pptx]'
```

当前可选依赖包括：

- `[all]`：安装所有可选依赖
- `[pptx]`：PowerPoint 支持
- `[docx]`：Word 支持
- `[xlsx]`：新版 Excel 支持
- `[xls]`：旧版 Excel 支持
- `[pdf]`：PDF 支持
- `[outlook]`：Outlook `.msg` 邮件支持
- `[az-doc-intel]`：Azure Document Intelligence 支持
- `[audio-transcription]`：`wav` 和 `mp3` 音频转写支持
- `[youtube-transcription]`：YouTube 字幕获取支持

### 插件

MarkItDown 支持第三方插件。插件默认关闭。

列出已安装插件：

```bash
markitdown --list-plugins
```

启用插件转换：

```bash
markitdown --use-plugins path-to-file.pdf
```

可以在 GitHub 上搜索 `#markitdown-plugin` 查找插件。插件开发示例见 [markitdown-sample-plugin](https://github.com/antstars/markitdown/tree/main/packages/markitdown-sample-plugin)。

#### markitdown-ocr 插件

`markitdown-ocr` 插件为 PDF、DOCX、PPTX 和 XLSX 转换器增加 OCR 能力，可以用 LLM Vision 从嵌入图片中提取文字。它复用 MarkItDown 已有的 `llm_client` / `llm_model` 模式，不引入新的本地机器学习模型或二进制依赖。

安装：

```bash
pip install markitdown-ocr
pip install openai
```

使用：

```python
from markitdown import MarkItDown
from openai import OpenAI

md = MarkItDown(
    enable_plugins=True,
    llm_client=OpenAI(),
    llm_model="gpt-4o",
)
result = md.convert("document_with_images.pdf")
print(result.text_content)
```

如果没有提供 `llm_client`，插件仍会加载，但会跳过 OCR，回退到内置转换器。详细说明见 [markitdown-ocr README](https://github.com/antstars/markitdown/blob/main/packages/markitdown-ocr/README.md)。

### Azure Document Intelligence

使用 Microsoft Document Intelligence 转换：

```bash
markitdown path-to-file.pdf -o document.md -d -e "<document_intelligence_endpoint>"
```

Azure Document Intelligence 资源创建说明见 [Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/how-to-guides/create-document-intelligence-resource?view=doc-intel-4.0.0)。

### Python API

基础用法：

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=False)
result = md.convert("test.xlsx")
print(result.text_content)
```

使用 Document Intelligence：

```python
from markitdown import MarkItDown

md = MarkItDown(docintel_endpoint="<document_intelligence_endpoint>")
result = md.convert("test.pdf")
print(result.text_content)
```

使用大语言模型生成图片说明，目前主要用于 PPTX 和图片文件：

```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI()
md = MarkItDown(llm_client=client, llm_model="gpt-4o", llm_prompt="optional custom prompt")
result = md.convert("example.jpg")
print(result.text_content)
```

## Web 应用

本仓库包含 [markitdown-web](https://github.com/antstars/markitdown/tree/main/packages/markitdown-web)，这是一个 FastAPI + React Web 应用，可以在浏览器中上传文件或提交 HTTP(S) URL，并批量转换为 Markdown。

功能包括：

- 拖拽上传文件
- 批量 URL 转换
- 每个条目的转换状态和错误提示
- Markdown 预览、复制、单文件下载和批量 ZIP 下载
- 密码登录、签名 Cookie 和 CSRF 保护
- 临时任务存储和自动清理
- 文件大小、批量数量、URL 超时和 SSRF 防护
- 通过环境变量启用插件、LLM、OCR 和 Azure Document Intelligence

从源码运行：

```bash
pip install -e 'packages/markitdown[all]'
pip install -e 'packages/markitdown-web'

export MARKITDOWN_WEB_PASSWORD='change-me'
markitdown-web --host 127.0.0.1 --port 3000
```

Windows PowerShell：

```powershell
pip install -e 'packages/markitdown[all]'
pip install -e 'packages/markitdown-web'

$env:MARKITDOWN_WEB_PASSWORD = 'change-me'
markitdown-web --host 127.0.0.1 --port 3000
```

然后打开 `http://127.0.0.1:3000`。

前端开发：

```bash
cd packages/markitdown-web/frontend
npm install
npm run dev
```

生产前端资源构建：

```bash
cd packages/markitdown-web/frontend
npm ci
npm run build
```

构建结果会写入 `packages/markitdown-web/src/markitdown_web/static`。

## 编译桌面可执行文件

`markitdown-web` 可以用 PyInstaller 打包成自包含可执行文件。PyInstaller 构建是平台相关的：Windows `.exe` 需要在 Windows 上构建，Linux 二进制需要在 Linux 上构建，macOS 二进制需要在 macOS 上构建。为了获得完整可选依赖支持，建议使用 Python 3.10-3.13。

先安装 Python 和 Node 依赖：

```bash
pip install -U pyinstaller
pip install -e 'packages/markitdown[all]'
pip install -e 'packages/markitdown-web'

cd packages/markitdown-web/frontend
npm ci
npm run build
cd ../../..
```

### Windows

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

输出文件：

```text
dist/MarkItDownWeb.exe
```

运行：

```powershell
.\dist\MarkItDownWeb.exe --port 3000 --password change-me
```

### Linux

需要音频或 EXIF 元数据支持时，先安装系统工具：

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg exiftool
```

构建：

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

输出文件：

```text
dist/MarkItDownWeb
```

运行：

```bash
./dist/MarkItDownWeb --port 3000 --password change-me
```

### macOS

需要音频或 EXIF 元数据支持时，先安装系统工具：

```bash
brew install ffmpeg exiftool
```

构建：

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

输出文件：

```text
dist/MarkItDownWeb
```

运行：

```bash
./dist/MarkItDownWeb --port 3000 --password change-me
```

启动器默认会自动打开浏览器。使用 `--no-browser` 可以关闭自动打开浏览器。部分转换功能依赖外部工具，例如 `ffmpeg` 或 `exiftool`；需要音频元数据、音频转写或 EXIF 元数据时，请在目标机器安装这些工具并加入 `PATH`。

## Docker

命令行转换镜像：

```bash
docker build -t markitdown:latest .
docker run --rm -i markitdown:latest < ~/your-file.pdf > output.md
```

Web 应用镜像：

```bash
docker build -f packages/markitdown-web/Dockerfile -t markitdown-web:latest .
docker run --rm -p 3000:3000 \
  -e MARKITDOWN_WEB_PASSWORD=change-me \
  -e MARKITDOWN_WEB_SECRET_KEY=replace-with-a-long-random-secret \
  markitdown-web:latest
```

打开 `http://127.0.0.1:3000`。

Docker Compose：

```bash
cp deploy/linux/markitdown-web.env.example .env
# 编辑 .env，设置 MARKITDOWN_WEB_PASSWORD 和 MARKITDOWN_WEB_SECRET_KEY。
docker compose up --build
```

生产服务模板见 `deploy/linux/markitdown-web.service`（systemd）和 `deploy/macos/com.markitdown.web.plist`（macOS launchd）。公开部署时建议放在 TLS 反向代理后面，并必须设置强 `MARKITDOWN_WEB_PASSWORD` 和稳定的 `MARKITDOWN_WEB_SECRET_KEY`。

## 贡献

欢迎提交问题、建议和代码贡献。项目贡献说明、行为准则和测试流程可参考英文版 [README](https://github.com/antstars/markitdown/blob/main/README.md)。

运行核心包测试：

```bash
cd packages/markitdown
pip install hatch
hatch shell
hatch test
```

运行 Web 包测试：

```bash
python -m pip install -e packages/markitdown -e packages/markitdown-web[test]
python -m pytest packages/markitdown-web/tests
```

运行前端构建：

```bash
cd packages/markitdown-web/frontend
npm ci
npm run build
```

## 安全注意事项

MarkItDown 会以当前进程权限进行 I/O。处理不可信输入时，请优先使用最小权限、容器或沙箱环境。公开部署 `markitdown-web` 时，请设置强密码，配置稳定的 `MARKITDOWN_WEB_SECRET_KEY`，限制文件大小和批量数量，并谨慎开放网络访问范围。
