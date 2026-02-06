import { useState, useCallback, useRef, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import EditorPane, { DEFAULT_LATEX } from './components/EditorPane';
import PreviewPane from './components/PreviewPane';
import AgentPane from './components/AgentPane';
import './index.css';

type View = 'editor' | 'agent';

const MIN_PREVIEW_W = 200;
const MAX_PREVIEW_W = 900;
const DEFAULT_PREVIEW_W = 420;

function App() {
  const [latex, setLatex] = useState(DEFAULT_LATEX);
  const [view, setView] = useState<View>('editor');

  // ── Resizable divider state ───────────────────────────────────────
  const [previewWidth, setPreviewWidth] = useState(DEFAULT_PREVIEW_W);
  const dragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      // previewWidth = distance from mouse to right edge of the container
      const newWidth = containerRect.right - e.clientX;
      setPreviewWidth(Math.min(MAX_PREVIEW_W, Math.max(MIN_PREVIEW_W, newWidth)));
    };

    const onMouseUp = () => {
      if (dragging.current) {
        dragging.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

  /** Called by AgentPane when a CONSORT report is generated. */
  const handleLatexGenerated = useCallback(
    (newLatex: string) => {
      setLatex(newLatex);
      setView('editor');
    },
    [],
  );

  return (
    <div className="app-layout">
      <Sidebar activeView={view} onViewChange={setView} />
      {view === 'editor' && (
        <div className="editor-preview-container" ref={containerRef}>
          <EditorPane value={latex} onChange={setLatex} />
          <div className="resize-handle" onMouseDown={onMouseDown}>
            <div className="resize-handle-bar" />
          </div>
          <PreviewPane latex={latex} width={previewWidth} />
        </div>
      )}
      {view === 'agent' && (
        <AgentPane onLatexGenerated={handleLatexGenerated} />
      )}
    </div>
  );
}

export default App;
