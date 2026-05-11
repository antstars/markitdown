import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  CheckCircle2,
  Copy,
  Download,
  FileText,
  Link,
  Loader2,
  LogOut,
  UploadCloud,
  XCircle
} from "lucide-react";
import "./styles.css";

const csrf = () => document.cookie.split("; ").find((row) => row.startsWith("mid_csrf="))?.split("=")[1] || "";

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "content-type": "application/json" }),
      ...(options.method && options.method !== "GET" ? { "x-csrf-token": csrf() } : {}),
      ...(options.headers || {})
    }
  });
  if (!response.ok) {
    const text = await response.text();
    let detail = text;
    try {
      detail = JSON.parse(text).detail || text;
    } catch {
      detail = text;
    }
    throw new Error(detail);
  }
  return response.json();
}

function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [password, setPassword] = useState("");
  const [config, setConfig] = useState(null);
  const [files, setFiles] = useState([]);
  const [urls, setUrls] = useState("");
  const [jobs, setJobs] = useState([]);
  const [activeItem, setActiveItem] = useState(null);
  const [preview, setPreview] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/config").then((data) => {
      setConfig(data);
      setAuthenticated(true);
    }).catch(() => setAuthenticated(false));
  }, []);

  useEffect(() => {
    const running = jobs.some((job) => ["queued", "running"].includes(job.status));
    if (!running) return;
    const timer = setInterval(async () => {
      const updated = await Promise.all(jobs.map((job) => api(`/api/jobs/${job.id}`).catch(() => job)));
      setJobs(updated);
    }, 1200);
    return () => clearInterval(timer);
  }, [jobs]);

  const selectedJob = useMemo(() => jobs.find((job) => job.items.some((item) => item.id === activeItem?.id)), [jobs, activeItem]);

  async function login(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/auth/login", { method: "POST", body: JSON.stringify({ password }) });
      const data = await api("/api/config");
      setConfig(data);
      setAuthenticated(true);
    } catch (err) {
      setError(err.message);
    }
  }

  async function logout() {
    await api("/api/auth/logout", { method: "POST", body: JSON.stringify({}) }).catch(() => {});
    setAuthenticated(false);
    setJobs([]);
    setPreview("");
  }

  async function submitFiles() {
    if (files.length === 0) return;
    setError("");
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    try {
      const job = await api("/api/convert/files", { method: "POST", body: form });
      setJobs((current) => [job, ...current]);
      setFiles([]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function submitUrls() {
    const lines = urls.split("\n").map((line) => line.trim()).filter(Boolean);
    if (lines.length === 0) return;
    setError("");
    try {
      const job = await api("/api/convert/url", { method: "POST", body: JSON.stringify({ urls: lines }) });
      setJobs((current) => [job, ...current]);
      setUrls("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function openPreview(job, item) {
    if (item.status !== "succeeded") return;
    const response = await fetch(item.markdown_url, { credentials: "include" });
    const text = await response.text();
    setActiveItem(item);
    setPreview(text);
  }

  if (!authenticated) {
    return (
      <main className="login-shell">
        <form className="login-panel" onSubmit={login}>
          <div className="brand">MarkItDown Web</div>
          <h1>把文件和网页转换成 Markdown</h1>
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="访问密码" autoFocus />
          <button type="submit">登录</button>
          {error && <p className="error-text">{error}</p>}
        </form>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div>
          <div className="brand">MarkItDown Web</div>
          <p className="muted">最大 {config?.max_file_mb} MB / 项，批量最多 {config?.max_batch} 项，结果保留 {config?.ttl_minutes} 分钟。</p>
        </div>
        <div className="feature-list">
          <span>{config?.plugins_enabled ? "插件已启用" : "插件未启用"}</span>
          <span>{config?.llm_available ? "LLM 可用" : "LLM 未配置"}</span>
          <span>{config?.docintel_available ? "Doc Intelligence 可用" : "Doc Intelligence 未配置"}</span>
        </div>
        <button className="ghost" onClick={logout}><LogOut size={16} />退出</button>
      </aside>

      <section className="workspace">
        <header>
          <h1>转换工作台</h1>
          <p>上传 Office、PDF、图片、音频、压缩包，或粘贴 HTTP(S) URL，批量生成 Markdown。</p>
        </header>

        <div className="input-grid">
          <section className="panel dropzone" onDragOver={(event) => event.preventDefault()} onDrop={(event) => {
            event.preventDefault();
            setFiles(Array.from(event.dataTransfer.files));
          }}>
            <UploadCloud size={28} />
            <h2>上传文件</h2>
            <input id="file-input" type="file" multiple onChange={(event) => setFiles(Array.from(event.target.files || []))} />
            <label htmlFor="file-input">选择文件</label>
            <p>{files.length ? `${files.length} 个文件已选择` : "也可以拖拽文件到这里"}</p>
            <button onClick={submitFiles} disabled={!files.length}>开始转换</button>
          </section>

          <section className="panel">
            <Link size={28} />
            <h2>URL 批量转换</h2>
            <textarea value={urls} onChange={(event) => setUrls(event.target.value)} placeholder="每行一个 http(s) URL" />
            <button onClick={submitUrls} disabled={!urls.trim()}>转换 URL</button>
          </section>
        </div>

        {error && <div className="toast">{error}</div>}

        <section className="job-layout">
          <div className="jobs">
            <h2>任务</h2>
            {jobs.length === 0 && <p className="muted">还没有转换任务。</p>}
            {jobs.map((job) => (
              <article className="job" key={job.id}>
                <div className="job-head">
                  <strong>{job.status}</strong>
                  <a href={`/api/jobs/${job.id}/download.zip`}><Download size={16} />ZIP</a>
                </div>
                {job.items.map((item) => (
                  <button className="job-item" key={item.id} onClick={() => openPreview(job, item)}>
                    {item.status === "succeeded" && <CheckCircle2 size={16} />}
                    {item.status === "failed" && <XCircle size={16} />}
                    {["queued", "running"].includes(item.status) && <Loader2 className="spin" size={16} />}
                    <span>{item.name}</span>
                    <small>{item.error || item.title || item.status}</small>
                  </button>
                ))}
              </article>
            ))}
          </div>

          <div className="preview">
            <div className="preview-head">
              <div><FileText size={18} />{activeItem?.name || "Markdown 预览"}</div>
              <button className="ghost" disabled={!preview} onClick={() => navigator.clipboard.writeText(preview)}><Copy size={16} />复制</button>
            </div>
            <pre>{preview || "选择一个成功转换的结果查看 Markdown。"}</pre>
            {selectedJob && activeItem && <a className="download" href={`/api/jobs/${selectedJob.id}/items/${activeItem.id}/markdown`}><Download size={16} />下载 Markdown</a>}
          </div>
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
