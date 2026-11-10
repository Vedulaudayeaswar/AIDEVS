import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import "./ProjectsPage.css";
import "./ProjectsTheme.css";

export const LEGAL_DOCS = {
  terms: "Terms of Service",
  privacy: "Privacy Policy",
  "acceptable-use": "Acceptable Use Policy",
  "ai-disclosure": "AI-Generated Content Disclosure",
  "data-retention": "Data Retention & Deletion",
};

// Minimal Markdown renderer (headings, lists, paragraphs, **bold**, `code`, [links](...)).
// Text is rendered as React nodes only - no dangerouslySetInnerHTML.
function inline(text, key) {
  const parts = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let m;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) parts.push(<strong key={`${key}-${m.index}`}>{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith("`")) parts.push(<code key={`${key}-${m.index}`}>{tok.slice(1, -1)}</code>);
    else {
      const [, label, href] = tok.match(/\[([^\]]+)\]\(([^)]+)\)/);
      const safe = /^(https:\/\/|\/|#|mailto:)/.test(href) ? href : "#";
      parts.push(safe.startsWith("/") ? <Link key={`${key}-${m.index}`} to={safe}>{label}</Link>
        : <a key={`${key}-${m.index}`} href={safe} rel="noopener noreferrer">{label}</a>);
    }
    last = m.index + tok.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function render(md) {
  const out = [];
  let list = null;
  md.split(/\r?\n/).forEach((line, i) => {
    const h = line.match(/^(#{1,3})\s+(.*)/);
    const li = line.match(/^\s*[-*]\s+(.*)/);
    if (!li && list) { out.push(<ul key={`ul-${i}`}>{list}</ul>); list = null; }
    if (h) {
      const Tag = `h${h[1].length + 1}`;
      out.push(<Tag key={i}>{inline(h[2], i)}</Tag>);
    } else if (li) {
      (list = list || []).push(<li key={i}>{inline(li[1], i)}</li>);
    } else if (line.startsWith(">")) {
      out.push(<blockquote key={i} className="legal-note">{inline(line.replace(/^>\s?/, ""), i)}</blockquote>);
    } else if (line.trim()) {
      out.push(<p key={i}>{inline(line, i)}</p>);
    }
  });
  if (list) out.push(<ul key="ul-end">{list}</ul>);
  return out;
}

export default function LegalPage() {
  const { doc } = useParams();
  const [text, setText] = useState(null);
  const title = LEGAL_DOCS[doc];
  useEffect(() => {
    if (!title) return;
    setText(null);
    fetch(`${process.env.PUBLIC_URL || ""}/legal/${doc}.md`)
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error("missing"))))
      .then(setText)
      .catch(() => setText("Document unavailable."));
  }, [doc, title]);
  return (
    <div className="pp">
      <div className="pp-top" role="banner">
        <Link to="/" className="pp-logo">AIDevs</Link>
        <nav className="pp-top-right" aria-label="Legal documents">
          {Object.entries(LEGAL_DOCS).map(([k, v]) => <Link key={k} className="aid-btn aid-btn-sm" to={`/legal/${k}`}>{v}</Link>)}
        </nav>
      </div>
      <div className="pp-main legal" role="main">
        {!title ? <p>Unknown document.</p> : text === null ? <div className="aid-spinner" /> : <article>{render(text)}</article>}
      </div>
    </div>
  );
}
