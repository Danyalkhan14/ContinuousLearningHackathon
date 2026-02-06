import { useState, useCallback } from 'react';

const ToolsIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M8 2v2M8 12v2M2 8h2M12 8h2M4.93 4.93l1.41 1.41M9.66 9.66l1.41 1.41M4.93 11.07l1.41-1.41M9.66 6.34l1.41-1.41M11.07 4.93l-1.41 1.41M6.34 9.66l-1.41 1.41" />
  </svg>
);

const GridIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="2" y="2" width="5" height="5" rx="0.5" />
    <rect x="9" y="2" width="5" height="5" rx="0.5" />
    <rect x="2" y="9" width="5" height="5" rx="0.5" />
    <rect x="9" y="9" width="5" height="5" rx="0.5" />
  </svg>
);

const GalleryIcon = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="1" y="1" width="16" height="16" rx="2" />
    <circle cx="6" cy="6" r="2" />
    <path d="M1 13l4-4 3 2 5-5 2 2" />
  </svg>
);

const WaveIcon = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M3 9h2v4H3zM7 5h2v8H7zM11 7h2v4h-2zM15 3h2v12h-2z" />
  </svg>
);

const SendIcon = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M2 9l14-7-7 14-2-7-5-0z" />
  </svg>
);

const DEFAULT_LATEX = [
  '\\documentclass{article}',
  '\\usepackage{geometry,amsmath,graphicx}',
  '\\setlength{\\parskip}{0.5em}',
  '\\begin{document}',
  '',
  '\\section*{What is CliniRepGen?}',
  '',
  'CliniRepGen is an AI-powered \\LaTeX{} editor for writing scientific documents. It supports real-time collaboration with coauthors and includes AI-powered intelligence to help you draft and edit text, reason through ideas, and handle formatting.',
  '',
  '\\section*{Features}',
  '',
  'CliniRepGen includes AI directly in the editor: you can ask it to add equations, tables, or proofread. For example: ``Add the equation for the Laplace transform of $t\\cos(at)$ to the introduction.\'\' It will insert the corresponding \\LaTeX{}:',
  '',
  '\\[',
  '  \\mathcal{L}\\{t \\cos(at)\\} = \\frac{s^2 - a^2}{(s^2 + a^2)^2}',
  '\\]',
  '',
  '\\section*{Collaboration}',
  '',
  'Work together with coauthors in real time. Share your project and iterate on scientific content with AI assistance.',
  '',
  '\\end{document}',
].join('\n');

interface EditorPaneProps {
  value: string;
  onChange: (value: string) => void;
}

export default function EditorPane({ value, onChange }: EditorPaneProps) {
  const [aiQuery, setAiQuery] = useState('');

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!aiQuery.trim()) return;
      // Placeholder: in a full app this would call an API
      setAiQuery('');
    },
    [aiQuery]
  );

  return (
    <div className="editor-pane">
      <div className="editor-toolbar">
        <button type="button" title="Tools">
          <ToolsIcon />
        </button>
        <div className="editor-tabs">
          <button type="button" className="editor-tab active">
            main.tex
          </button>
        </div>
        <button type="button" title="Layout" style={{ marginLeft: 'auto' }}>
          <GridIcon />
        </button>
      </div>
      <div className="editor-area">
        <textarea
          className="editor-code"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Write your LaTeX here..."
          spellCheck={false}
        />
        <div className="ai-input-wrap">
          <form onSubmit={handleSubmit} className="ai-input-inner">
            <button type="button" className="ai-icon" title="Attach">
              <GalleryIcon />
            </button>
            <input
              type="text"
              value={aiQuery}
              onChange={(e) => setAiQuery(e.target.value)}
              placeholder="Ask anything"
              aria-label="Ask AI"
            />
            <button type="button" className="ai-icon" title="Voice">
              <WaveIcon />
            </button>
            <button type="submit" title="Send">
              <SendIcon />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export { DEFAULT_LATEX };
