import { useEffect, useRef, useState } from 'react';
import { parse, HtmlGenerator } from 'latex.js';
import katex from 'katex';

/* ─── helpers ────────────────────────────────────────────────────────── */

/** Extract the body between \begin{document} and \end{document}. */
function extractBody(raw: string): string {
  const beginIdx = raw.indexOf('\\begin{document}');
  const endIdx = raw.indexOf('\\end{document}');
  if (beginIdx === -1) return raw;
  return raw.slice(beginIdx + '\\begin{document}'.length, endIdx === -1 ? undefined : endIdx);
}

/**
 * Sanitise a LaTeX string so latex.js (browser build) can handle it.
 * Strips the full preamble and unsupported body commands.
 */
function sanitiseForLatexJs(raw: string): string {
  const beginIdx = raw.indexOf('\\begin{document}');
  if (beginIdx === -1) return raw;                // simple snippet

  const body = extractBody(raw);
  const classMatch = raw.match(/\\documentclass(?:\[[^\]]*\])?\{(\w+)\}/);
  const docClass = classMatch?.[1] ?? 'article';

  const cleaned = body
    .replace(/\\(?:label|ref|cref|Cref|autoref|pageref|eqref)\{[^}]*\}/g, '')
    .replace(/\\(?:tableofcontents|listoffigures|listoftables|newpage|clearpage|cleardoublepage|maketitle)\b/g, '')
    .replace(/\\centering\b/g, '')
    .replace(/\\hline\b/g, '')
    .replace(/\\(?:toprule|midrule|bottomrule)(?:\[[^\]]*\])?/g, '')
    .replace(/\\(?:textwidth|linewidth|columnwidth)/g, '5in')
    .replace(/\\begin\{longtable\}/g, '\\begin{tabular}')
    .replace(/\\end\{longtable\}/g, '\\end{tabular}')
    .replace(/\\(?:endhead|endfoot|endlastfoot)[^\n]*/g, '')
    .replace(/\\captionsetup\{[^}]*\}/g, '');

  return `\\documentclass{${docClass}}\n\\begin{document}\n${cleaned}\n\\end{document}`;
}

/* ─── HTML fallback renderer ─────────────────────────────────────────
 *
 * When latex.js can't handle the document we convert the body to HTML
 * with regex transforms.  It won't look identical to a real TeX compile
 * but it surfaces the full document content (headings, lists, bold/italic,
 * math via KaTeX, tables, etc.).
 * ──────────────────────────────────────────────────────────────────── */

function renderMathKatex(tex: string, displayMode: boolean): string {
  try {
    return katex.renderToString(tex, { displayMode, throwOnError: false, strict: false });
  } catch {
    return `<code>${tex}</code>`;
  }
}

function latexToHtml(raw: string): string {
  let body = extractBody(raw);

  // ── character-level substitutions ──
  body = body
    .replace(/\\&/g, '&amp;')        // escaped ampersand
    .replace(/\\%/g, '%')            // escaped percent
    .replace(/\\#/g, '#')
    .replace(/\\\\$/gm, '')          // line-break \\ at end-of-line
    .replace(/\\\\/g, '<br/>')       // remaining line breaks
    .replace(/~/g, '&nbsp;')         // non-breaking space
    .replace(/---/g, '\u2014')       // em-dash
    .replace(/--/g, '\u2013')        // en-dash
    .replace(/``/g, '\u201C')        // left double quote
    .replace(/''/g, '\u201D')        // right double quote
    .replace(/`/g, '\u2018')         // left single quote
    .replace(/'/g, '\u2019');        // right single quote

  // ── display math  \[…\] and $$…$$ ──
  body = body.replace(/\\\[([\s\S]*?)\\\]/g, (_, m) => renderMathKatex(m, true));
  body = body.replace(/\$\$([\s\S]*?)\$\$/g, (_, m) => renderMathKatex(m, true));

  // ── inline math $…$ ──
  body = body.replace(/\$([^$]+?)\$/g, (_, m) => renderMathKatex(m, false));

  // ── strip comments (% to end of line, but not \%) ──
  body = body.replace(/(?<!\\)%[^\n]*/g, '');

  // ── environments ──
  body = body.replace(/\\begin\{itemize\}/g, '<ul>');
  body = body.replace(/\\end\{itemize\}/g, '</ul>');
  body = body.replace(/\\begin\{enumerate\}/g, '<ol>');
  body = body.replace(/\\end\{enumerate\}/g, '</ol>');
  body = body.replace(/\\begin\{description\}/g, '<dl>');
  body = body.replace(/\\end\{description\}/g, '</dl>');
  body = body.replace(/\\begin\{quote\}/g, '<blockquote>');
  body = body.replace(/\\end\{quote\}/g, '</blockquote>');
  body = body.replace(/\\begin\{quotation\}/g, '<blockquote>');
  body = body.replace(/\\end\{quotation\}/g, '</blockquote>');
  body = body.replace(/\\begin\{verbatim\}([\s\S]*?)\\end\{verbatim\}/g, '<pre>$1</pre>');

  // tables: strip begin/end tabular/longtable (just show cell text)
  body = body.replace(/\\begin\{(?:tabular|longtable)\}(?:\[[^\]]*\])?\{[^}]*\}/g, '<table class="preview-table"><tbody>');
  body = body.replace(/\\end\{(?:tabular|longtable)\}/g, '</tbody></table>');
  body = body.replace(/\\(?:toprule|midrule|bottomrule|hline)(?:\[[^\]]*\])?/g, '');
  body = body.replace(/\\(?:endhead|endfoot|endlastfoot)[^\n]*/g, '');
  body = body.replace(/\\caption\{([^}]*)\}/g, '<caption>$1</caption>');
  // split rows on \\ and cells on &
  body = body.replace(/<tbody>([\s\S]*?)<\/tbody>/g, (_match, inner: string) => {
    const rows = inner.split(/\\\\/).filter((r: string) => r.trim());
    const htmlRows = rows.map((row: string) => {
      const cells = row.split('&').map((c: string) => `<td>${c.trim()}</td>`);
      return `<tr>${cells.join('')}</tr>`;
    });
    return `<tbody>${htmlRows.join('\n')}</tbody>`;
  });

  // figure environment – just keep the content
  body = body.replace(/\\begin\{figure\}(?:\[[^\]]*\])?/g, '<figure>');
  body = body.replace(/\\end\{figure\}/g, '</figure>');

  // ── \item ──
  body = body.replace(/\\item\[([^\]]*)\]/g, '<li><strong>$1</strong> ');
  body = body.replace(/\\item\b/g, '<li>');

  // ── sectioning ──
  body = body.replace(/\\section\*?\{([^}]*)\}/g, '<h2>$1</h2>');
  body = body.replace(/\\subsection\*?\{([^}]*)\}/g, '<h3>$1</h3>');
  body = body.replace(/\\subsubsection\*?\{([^}]*)\}/g, '<h4>$1</h4>');
  body = body.replace(/\\paragraph\*?\{([^}]*)\}/g, '<h5>$1</h5>');

  // ── inline formatting (handle nesting by running multiple passes) ──
  for (let i = 0; i < 4; i++) {
    body = body.replace(/\\textbf\{([^{}]*)\}/g, '<strong>$1</strong>');
    body = body.replace(/\\textit\{([^{}]*)\}/g, '<em>$1</em>');
    body = body.replace(/\\emph\{([^{}]*)\}/g, '<em>$1</em>');
    body = body.replace(/\\underline\{([^{}]*)\}/g, '<u>$1</u>');
    body = body.replace(/\\texttt\{([^{}]*)\}/g, '<code>$1</code>');
    body = body.replace(/\\text\{([^{}]*)\}/g, '$1');
  }

  // ── misc commands ──
  body = body.replace(/\\LaTeX\b\{?\}?/g, 'LaTeX');
  body = body.replace(/\\TeX\b\{?\}?/g, 'TeX');
  body = body.replace(/\\(?:tableofcontents|maketitle|newpage|clearpage|cleardoublepage)\b/g, '');
  body = body.replace(/\\(?:label|ref|cref|Cref|autoref|pageref|eqref|captionsetup)\{[^}]*\}/g, '');
  body = body.replace(/\\(?:centering|raggedright|raggedleft|noindent)\b/g, '');
  body = body.replace(/\\(?:vspace|hspace|vskip|hskip)\*?\{[^}]*\}/g, '');
  body = body.replace(/\\(?:small|large|Large|LARGE|huge|Huge|normalsize|footnotesize|scriptsize|tiny)\b/g, '');
  body = body.replace(/\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}/g, '<em>[image]</em>');
  body = body.replace(/\\href\{([^}]*)\}\{([^}]*)\}/g, '<a href="$1">$2</a>');
  body = body.replace(/\\url\{([^}]*)\}/g, '<a href="$1">$1</a>');
  body = body.replace(/\\footnote\{([^}]*)\}/g, '<sup>[$1]</sup>');

  // ── paragraphs: double-newlines → <p> ──
  body = body
    .split(/\n{2,}/)
    .map(p => p.trim())
    .filter(Boolean)
    .map(p => {
      // Don't wrap blocks that are already block-level HTML
      if (/^<(?:h[1-6]|ul|ol|dl|blockquote|pre|table|figure|li|caption|tr|div)/.test(p)) return p;
      return `<p>${p}</p>`;
    })
    .join('\n');

  return body;
}

/* ─── Component ──────────────────────────────────────────────────────── */

interface PreviewPaneProps {
  latex: string;
  width?: number;
}

export default function PreviewPane({ latex, width }: PreviewPaneProps) {
  const [compiling, setCompiling] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [usingFallback, setUsingFallback] = useState(false);
  const latexRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setCompiling(true);
    setError(null);
    setUsingFallback(false);

    const t = setTimeout(() => {
      if (!latexRef.current) return;

      // ── Attempt 1: latex.js ────────────────────────────────────────
      try {
        const sanitised = sanitiseForLatexJs(latex);
        const generator = new HtmlGenerator({ hyphenate: false });
        const doc = parse(sanitised, { generator });

        const container = latexRef.current;
        container.innerHTML = '';
        container.appendChild(doc.domFragment());

        const existingStyle = document.getElementById('latex-js-style');
        if (!existingStyle) {
          const styleLink = doc.stylesAndScripts('https://cdn.jsdelivr.net/npm/latex.js@0.12.6/dist/');
          if (styleLink) {
            const wrapper = document.createElement('div');
            wrapper.id = 'latex-js-style';
            wrapper.appendChild(styleLink);
            document.head.appendChild(wrapper);
          }
        }

        scrollRef.current?.scrollTo(0, 0);
        setError(null);
        setCompiling(false);
        return;
      } catch {
        // latex.js failed – fall through to HTML fallback
      }

      // ── Attempt 2: HTML fallback with KaTeX math ───────────────────
      try {
        const html = latexToHtml(latex);
        const container = latexRef.current;
        container.innerHTML = html;
        scrollRef.current?.scrollTo(0, 0);
        setUsingFallback(true);
        setError(null);
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
        if (latexRef.current) latexRef.current.innerHTML = '';
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
          {compiling ? 'Compiling...' : error ? 'Error' : usingFallback ? 'Preview (simplified)' : 'Preview'}
        </span>
        <div className="preview-header-actions">
          <button type="button">Zoom to fit</button>
          <button type="button" title="Download">↓</button>
          <button type="button" title="Print">⎙</button>
          <button type="button">⋯</button>
        </div>
      </div>
      <div className="preview-content" ref={scrollRef}>
        {compiling && <p className="compiling">Compiling...</p>}
        <div ref={latexRef} />
      </div>
      {error && (
        <div className="preview-error">
          <strong>LaTeX parse error:</strong> {error}
        </div>
      )}
    </div>
  );
}
