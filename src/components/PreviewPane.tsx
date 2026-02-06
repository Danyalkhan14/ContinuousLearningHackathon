import { useEffect, useState } from 'react';
import katex from 'katex';

interface PreviewPaneProps {
  latex: string;
}

// Simple extraction of sections and text from LaTeX for preview (no full parser)
function extractSections(latex: string): { title?: string; sections: { title: string; content: string }[] } {
  const sections: { title: string; content: string }[] = [];
  let docTitle: string | undefined;

  const titles: string[] = [];
  let m: RegExpExecArray | null;
  const secReg = /\\(?:section|section\*)\s*\{([^}]*)\}/g;
  while ((m = secReg.exec(latex)) !== null) titles.push(m[1]);

  const sectionSplits = latex.replace(/\\(?:section|section\*)\s*\{[^}]*\}/g, '\x00').split('\x00');
  for (let i = 0; i < titles.length; i++) {
    const raw = sectionSplits[i + 1] || '';
    const content = raw
      .replace(/\\\[[\s\S]*?\\\]/g, ' ')
      .replace(/\$[^$]+\$/g, ' ')
      .replace(/\\begin\{[^}]*\}[\s\S]*?\\end\{[^}]*\}/g, ' ')
      .replace(/\\LaTeX\{\}/g, 'LaTeX')
      .replace(/\\[a-zA-Z]+\*?(\{[^}]*\})?/g, ' ')
      .replace(/\{[^}]*\}/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 500);
    sections.push({ title: titles[i], content });
  }

  const titleMatch = latex.match(/\\title\s*\{([^}]*)\}/);
  if (titleMatch) docTitle = titleMatch[1];
  else if (titles.length) docTitle = titles[0];

  return { title: docTitle, sections };
}

// Render text and replace $...$ and \[...\] with KaTeX
function renderWithMath(text: string): string {
  let out = text;
  const inlineRegex = /\$([^$]+)\$/g;
  const blockRegex = /\\\[([\s\S]*?)\\\]/g;

  try {
    out = out.replace(blockRegex, (_, math) => {
      try {
        return katex.renderToString(math.trim(), { displayMode: true, throwOnError: false });
      } catch {
        return math;
      }
    });
    out = out.replace(inlineRegex, (_, math) => {
      try {
        return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false });
      } catch {
        return math;
      }
    });
  } catch {
    // ignore
  }
  return out;
}

export default function PreviewPane({ latex }: PreviewPaneProps) {
  const [compiling, setCompiling] = useState(true);
  const [previewHtml, setPreviewHtml] = useState<{ title?: string; sections: { title: string; content: string }[] }>({
    sections: [],
  });

  useEffect(() => {
    setCompiling(true);
    const t = setTimeout(() => {
      const extracted = extractSections(latex);
      setPreviewHtml(extracted);
      setCompiling(false);
    }, 600);
    return () => clearTimeout(t);
  }, [latex]);

  return (
    <div className="preview-pane">
      <div className="preview-header">
        <span className={compiling ? 'compiling' : ''}>{compiling ? 'Compiling...' : '01 of 01'}</span>
        <div className="preview-header-actions">
          <button type="button">Zoom to fit</button>
          <button type="button" title="Download">↓</button>
          <button type="button" title="Print">⎙</button>
          <button type="button">⋯</button>
        </div>
      </div>
      <div className="preview-content">
        {compiling ? (
          <p className="compiling">Compiling...</p>
        ) : (
          <>
            {previewHtml.title && (
              <h1 className="doc-title" dangerouslySetInnerHTML={{ __html: renderWithMath(previewHtml.title) }} />
            )}
            {previewHtml.sections.map((sec) => (
              <div key={sec.title}>
                <h2 className="doc-section">{sec.title}</h2>
                <p dangerouslySetInnerHTML={{ __html: renderWithMath(sec.content) }} />
              </div>
            ))}
            {previewHtml.sections.length === 0 && <p className="compiling">No sections found. Add \\section*{'{...}'} in your LaTeX.</p>}
          </>
        )}
      </div>
    </div>
  );
}
