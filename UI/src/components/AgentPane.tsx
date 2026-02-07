import { useState, useCallback, useRef } from 'react';

// Empty string in production (Docker) → same-origin; dev → local backend
const API_BASE = import.meta.env.VITE_AGENT_API_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');

/* ── Response types (match the FastAPI schemas) ─────────────────────── */

interface FileSummary {
  filename: string;
  summary: string;
  query?: string;
  snippets?: Array<{ title?: string; description?: string; url?: string }>;
  error?: string | null;
}

interface ProcessResult {
  success: boolean;
  message: string;
  files_processed: number;
  points_stored: number;
  summaries: FileSummary[];
}

interface SSEProgress {
  type: 'progress' | 'complete' | 'error';
  message: string;
  progress?: number;
  total?: number;
  latex?: string;
  items_processed?: number;
}

/* ── Props ──────────────────────────────────────────────────────────── */

interface AgentPaneProps {
  onLatexGenerated?: (latex: string) => void;
}

/* ── Component ──────────────────────────────────────────────────────── */

export default function AgentPane({ onLatexGenerated }: AgentPaneProps) {
  // ── Ingest state ───────────────────────────────────────────────────
  const [files, setFiles] = useState<FileList | null>(null);
  const [ingesting, setIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<ProcessResult | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);

  // ── Generate state ─────────────────────────────────────────────────
  const [generating, setGenerating] = useState(false);
  const [genStatus, setGenStatus] = useState<string | null>(null);
  const [genLatex, setGenLatex] = useState<string | null>(null);
  const [genError, setGenError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  /* ─── Ingest: file selection ─────────────────────────────────────── */
  const onFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const list = e.target.files;
    setFiles(list && list.length > 0 ? list : null);
    setIngestResult(null);
    setIngestError(null);
  }, []);

  /* ─── Ingest: upload & process ───────────────────────────────────── */
  const processFiles = useCallback(async () => {
    if (!files || files.length === 0) {
      setIngestError('Please select one or more files.');
      return;
    }
    setIngesting(true);
    setIngestError(null);
    setIngestResult(null);

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    try {
      const res = await fetch(`${API_BASE}/api/process`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        setIngestError(data.detail || res.statusText);
        return;
      }
      setIngestResult(data as ProcessResult);
    } catch (err) {
      setIngestError(
        err instanceof Error
          ? err.message
          : `Request failed. Is the agent API running on ${API_BASE}?`,
      );
    } finally {
      setIngesting(false);
    }
  }, [files]);

  /* ─── Generate: run the CONSORT agent ────────────────────────────── */
  const generateReport = useCallback(async () => {
    setGenerating(true);
    setGenStatus('Connecting to agent...');
    setGenLatex(null);
    setGenError(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`${API_BASE}/api/generate`, {
        method: 'POST',
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setGenError(body?.detail || res.statusText);
        setGenerating(false);
        return;
      }

      // ── Read the SSE stream ──────────────────────────────────────
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      if (!reader) {
        setGenError('No response body received.');
        setGenerating(false);
        return;
      }

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        // Keep the last (potentially incomplete) line in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const event: SSEProgress = JSON.parse(line.slice(6));
            if (event.type === 'progress') {
              setGenStatus(event.message);
            } else if (event.type === 'complete') {
              setGenStatus(event.message);
              if (event.latex) setGenLatex(event.latex);
            } else if (event.type === 'error') {
              setGenError(event.message);
            }
          } catch {
            // ignore malformed lines
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setGenError(
          err instanceof Error
            ? err.message
            : `Request failed. Is the agent API running on ${API_BASE}?`,
        );
      }
    } finally {
      setGenerating(false);
      abortRef.current = null;
    }
  }, []);

  const cancelGenerate = useCallback(() => {
    abortRef.current?.abort();
    setGenerating(false);
    setGenStatus('Generation cancelled.');
  }, []);

  const loadIntoEditor = useCallback(() => {
    if (genLatex && onLatexGenerated) {
      onLatexGenerated(genLatex);
    }
  }, [genLatex, onLatexGenerated]);

  /* ─── Render ─────────────────────────────────────────────────────── */
  return (
    <div className="agent-pane">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="agent-pane-header">
        <h2 className="agent-pane-title">CONSORT Deep Research Agent</h2>
        <p className="agent-pane-subtitle">
          Upload clinical trial documents to ingest them into the vector store,
          then generate a full CONSORT&nbsp;2025-compliant LaTeX report.
        </p>
      </div>

      {/* ── Section 1: Document Ingestion ──────────────────────────── */}
      <div className="agent-section">
        <h3 className="agent-section-title">
          <span className="agent-section-num">1</span>
          Ingest Documents
        </h3>
        <p className="agent-section-desc">
          Upload PDF, DOCX, TXT, CSV, JSON, or XML files. They will be chunked,
          embedded, and stored in Qdrant. You&rsquo;ll get a summary and research
          snippets for each file.
        </p>

        <div className="agent-upload-section">
          <label className="agent-file-label">
            <span className="agent-file-button">Choose files</span>
            <input
              type="file"
              multiple
              accept=".pdf,.docx,.csv,.txt,.md,.json,.xml,.tex"
              onChange={onFileChange}
              className="agent-file-input"
            />
          </label>
          {files && (
            <span className="agent-file-names">
              {files.length} file(s):{' '}
              {Array.from(files)
                .map((f) => f.name)
                .join(', ')}
            </span>
          )}
          <button
            type="button"
            className="agent-process-btn"
            onClick={processFiles}
            disabled={ingesting || !files || files.length === 0}
          >
            {ingesting ? 'Processing\u2026' : 'Process & Ingest'}
          </button>
        </div>

        {ingestError && <div className="agent-error">{ingestError}</div>}

        {ingestResult && (
          <div className="agent-result">
            <div className="agent-result-meta">
              {ingestResult.message} &mdash; {ingestResult.points_stored} chunks
              stored in Qdrant.
            </div>
            <div className="agent-summaries">
              {ingestResult.summaries.map((s) => (
                <div key={s.filename} className="agent-summary-card">
                  <h3 className="agent-summary-filename">{s.filename}</h3>
                  {s.query && (
                    <p className="agent-summary-query">Query: {s.query}</p>
                  )}
                  <p className="agent-summary-text">{s.summary}</p>
                  {s.error && (
                    <p className="agent-summary-error">{s.error}</p>
                  )}
                  {s.snippets && s.snippets.length > 0 && (
                    <div className="agent-snippets">
                      <strong>Research snippets:</strong>
                      <ul>
                        {s.snippets.slice(0, 3).map((sn, i) => (
                          <li key={i}>
                            <a
                              href={sn.url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {sn.title || sn.url}
                            </a>
                            {sn.description &&
                              ` \u2014 ${sn.description.slice(0, 120)}...`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Section 2: Report Generation ───────────────────────────── */}
      <div className="agent-section">
        <h3 className="agent-section-title">
          <span className="agent-section-num">2</span>
          Generate CONSORT Report
        </h3>
        <p className="agent-section-desc">
          Run the deep-research agent across all 42 CONSORT&nbsp;2025 checklist
          items. The agent will retrieve evidence from Qdrant, hydrate terms via
          You.com, and synthesise a complete LaTeX report.
        </p>

        <div className="agent-generate-actions">
          {!generating ? (
            <button
              type="button"
              className="agent-process-btn"
              onClick={generateReport}
            >
              Generate Report
            </button>
          ) : (
            <button
              type="button"
              className="agent-cancel-btn"
              onClick={cancelGenerate}
            >
              Cancel
            </button>
          )}
        </div>

        {/* Progress / status */}
        {generating && (
          <div className="agent-gen-progress">
            <div className="agent-gen-spinner" />
            <span>{genStatus}</span>
          </div>
        )}

        {genError && <div className="agent-error">{genError}</div>}

        {genLatex && !generating && (
          <div className="agent-gen-complete">
            <div className="agent-gen-complete-header">
              <span className="agent-gen-check">&#10003;</span>
              <span>{genStatus}</span>
            </div>
            <div className="agent-gen-complete-actions">
              <button
                type="button"
                className="agent-process-btn"
                onClick={loadIntoEditor}
              >
                Load into Editor
              </button>
              <button
                type="button"
                className="agent-secondary-btn"
                onClick={() => {
                  const blob = new Blob([genLatex], { type: 'application/x-latex' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'consort_report.tex';
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                Download .tex
              </button>
            </div>
            <details className="agent-gen-preview">
              <summary>Preview LaTeX source ({genLatex.length.toLocaleString()} chars)</summary>
              <pre className="agent-gen-code">{genLatex.slice(0, 2000)}{genLatex.length > 2000 ? '\n\n… (truncated)' : ''}</pre>
            </details>
          </div>
        )}
      </div>
    </div>
  );
}
