import { useEffect, useRef, useState } from 'react';
import { parse, HtmlGenerator } from 'latex.js';

interface PreviewPaneProps {
  latex: string;
  width?: number;
}

export default function PreviewPane({ latex, width }: PreviewPaneProps) {
  const [compiling, setCompiling] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setCompiling(true);
    setError(null);

    const t = setTimeout(() => {
      if (!contentRef.current) return;

      try {
        const generator = new HtmlGenerator({ hyphenate: false });
        const doc = parse(latex, { generator });

        // Clear old content
        const container = contentRef.current;
        container.innerHTML = '';

        // Get the rendered DOM fragment
        const fragment = doc.domFragment();
        container.appendChild(fragment);

        // Inject the LaTeX.js stylesheet if not already present
        const existingStyle = document.getElementById('latex-js-style');
        if (!existingStyle) {
          const styleLink = doc.stylesAndScripts('https://cdn.jsdelivr.net/npm/latex.js@0.12.6/dist/');
          // styleLink is a DocumentFragment with <link> / <style> elements
          if (styleLink) {
            const wrapper = document.createElement('div');
            wrapper.id = 'latex-js-style';
            wrapper.appendChild(styleLink);
            document.head.appendChild(wrapper);
          }
        }

        container.scrollTo(0, 0);
      } catch (err) {
        // Fallback: show the error and raw LaTeX
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);

        if (contentRef.current) {
          contentRef.current.innerHTML = '';
        }
      } finally {
        setCompiling(false);
      }
    }, 500);

    return () => clearTimeout(t);
  }, [latex]);

  return (
    <div className="preview-pane" style={width ? { width, minWidth: width } : undefined}>
      <div className="preview-header">
        <span className={compiling ? 'compiling' : ''}>
          {compiling ? 'Compiling...' : error ? 'Error' : 'Preview'}
        </span>
        <div className="preview-header-actions">
          <button type="button">Zoom to fit</button>
          <button type="button" title="Download">↓</button>
          <button type="button" title="Print">⎙</button>
          <button type="button">⋯</button>
        </div>
      </div>
      <div className="preview-content" ref={contentRef}>
        {compiling && <p className="compiling">Compiling...</p>}
      </div>
      {error && (
        <div className="preview-error">
          <strong>LaTeX parse error:</strong> {error}
        </div>
      )}
    </div>
  );
}
