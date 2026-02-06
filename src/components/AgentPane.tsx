import { useState, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_AGENT_API_URL || 'http://localhost:8000';

interface FileSummary {
  filename: string;
  summary: string;
  query?: string;
  snippets?: Array<{ title?: string; description?: string; url?: string; snippets?: string[] }>;
  error?: string | null;
}

interface ProcessResult {
  success: boolean;
  message: string;
  files_processed: number;
  points_stored: number;
  summaries: FileSummary[];
}

export default function AgentPane() {
  const [files, setFiles] = useState<FileList | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const list = e.target.files;
    setFiles(list && list.length > 0 ? list : null);
    setResult(null);
    setError(null);
  }, []);

  const processFiles = useCallback(async () => {
    if (!files || files.length === 0) {
      setError('Please select one or more files (CSV, TXT, MD, JSON, XML).');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
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
        setError(data.detail || res.statusText);
        return;
      }
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed. Is the agent API running on ' + API_BASE + '?');
    } finally {
      setLoading(false);
    }
  }, [files]);

  return (
    <div className="agent-pane">
      <div className="agent-pane-header">
        <h2 className="agent-pane-title">Document Agent</h2>
        <p className="agent-pane-subtitle">
          Upload CSV or text files. The agent will store embeddings in Qdrant and research each file via You.com to provide summaries.
        </p>
      </div>
      <div className="agent-upload-section">
        <label className="agent-file-label">
          <span className="agent-file-button">Choose files or folder</span>
          <input
            type="file"
            multiple
            accept=".csv,.txt,.md,.json,.xml"
            onChange={onFileChange}
            className="agent-file-input"
          />
        </label>
        {files && (
          <span className="agent-file-names">
            {files.length} file(s): {Array.from(files).map((f) => f.name).join(', ')}
          </span>
        )}
        <button
          type="button"
          className="agent-process-btn"
          onClick={processFiles}
          disabled={loading || !files || files.length === 0}
        >
          {loading ? 'Processing…' : 'Process & Research'}
        </button>
      </div>
      {error && <div className="agent-error">{error}</div>}
      {result && (
        <div className="agent-result">
          <div className="agent-result-meta">
            {result.message} — {result.points_stored} chunks stored in Qdrant.
          </div>
          <div className="agent-summaries">
            {result.summaries.map((s) => (
              <div key={s.filename} className="agent-summary-card">
                <h3 className="agent-summary-filename">{s.filename}</h3>
                {s.query && <p className="agent-summary-query">Query: {s.query}</p>}
                <p className="agent-summary-text">{s.summary}</p>
                {s.error && <p className="agent-summary-error">{s.error}</p>}
                {s.snippets && s.snippets.length > 0 && (
                  <div className="agent-snippets">
                    <strong>Research snippets:</strong>
                    <ul>
                      {s.snippets.slice(0, 3).map((sn, i) => (
                        <li key={i}>
                          <a href={sn.url} target="_blank" rel="noopener noreferrer">{sn.title || sn.url}</a>
                          {sn.description && ` — ${sn.description.slice(0, 120)}...`}
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
  );
}
