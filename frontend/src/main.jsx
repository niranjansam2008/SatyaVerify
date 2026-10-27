import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "https://satyaverify-backend-docker.onrender.com";

function App() {
  const [files, setFiles] = useState([]);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const totalSize = useMemo(() => files.reduce((n, f) => n + f.size, 0), [files]);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    if (!files.length) {
      setError("Choose at least one document first.");
      return;
    }
    const body = new FormData();
    files.forEach((file) => body.append("files", file));
    setBusy(true);
    try {
      const response = await fetch(`${API}/api/verify`, { method: "POST", body });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Verification request failed.");
      setResult(data);
    } catch (err) {
      setError(`${err.message} Make sure the FastAPI backend is running at ${API}.`);
    } finally {
      setBusy(false);
    }
  }

  function onPick(e) {
    setFiles(Array.from(e.target.files || []).slice(0, 5));
    setResult(null);
    setError("");
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand-mark">SV</div>
        <div>
          <div className="brand">SatyaVerify</div>
          <div className="tagline">Trust Before Approval</div>
        </div>
        <span className="prototype">SIH 2026 · MVP</span>
      </header>

      <section className="hero">
        <div className="eyebrow">DOCUMENT INTELLIGENCE PLATFORM</div>
        <h1>Verify with clarity.<br /><span>Decide with confidence.</span></h1>
        <p>Screen application documents, surface missing fields, compare information across files, and get explainable review flags in one place.</p>
        <div className="hero-points">
          <span>✓ Field validation</span><span>✓ Cross-document checks</span><span>✓ Explainable score</span>
        </div>
      </section>

      <section className="workspace">
        <div className="section-heading">
          <div><div className="eyebrow">WORKSPACE</div><h2>Application review</h2></div>
          <span className="status"><i /> API-driven demo</span>
        </div>
        <form onSubmit={submit} className="upload-card">
          <label className="dropzone">
            <div className="upload-icon">↑</div>
            <strong>Upload application documents</strong>
            <span>PDF, PNG, JPG, JPEG or TXT · up to 5 files · 10 MB each</span>
            <input type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.txt" onChange={onPick} />
            <span className="choose">Choose files</span>
          </label>
          {files.length > 0 && (
            <div className="file-list">
              {files.map((f, i) => <div className="file-row" key={`${f.name}-${i}`}><span className="file-icon">▤</span><div className="file-meta"><b>{f.name}</b><small>{(f.size / 1024).toFixed(1)} KB</small></div><span className="file-check">Ready</span></div>)}
              <div className="file-summary">{files.length} file(s) · {(totalSize / (1024 * 1024)).toFixed(2)} MB total</div>
            </div>
          )}
          <button className="primary" disabled={busy}>{busy ? "Screening documents…" : "Run verification"} <span>→</span></button>
          {error && <div className="error">{error}</div>}
        </form>
      </section>

      {result && (
        <section className="results">
          <div className="result-header"><div><div className="eyebrow">SCREENING REPORT</div><h2>Verification summary</h2></div><span className={`decision ${result.overall_decision.toLowerCase()}`}>{result.overall_decision}</span></div>
          <div className="metrics">
            <div className="metric score"><small>Overall trust score</small><div><strong>{result.overall_trust_score}</strong><span>/100</span></div><div className="meter"><i style={{ width: `${result.overall_trust_score}%` }} /></div></div>
            <div className="metric"><small>Documents screened</small><strong>{result.documents.length}</strong><span className="metric-note">Files in this review</span></div>
            <div className="metric"><small>Review flags</small><strong>{result.flags.length}</strong><span className="metric-note">Signals to inspect</span></div>
          </div>

          {result.cross_document_checks?.length > 0 && <div className="panel"><h3>Cross-document consistency</h3>{result.cross_document_checks.map((c, i) => <div className="flag" key={i}><span className="flag-dot high" /><div><b>{c.field.replaceAll("_", " ")}</b><p>{c.message}</p></div><span className="flag-label">MISMATCH</span></div>)}</div>}

          <div className="panel"><h3>Document-level results</h3>
            {result.documents.map((doc, i) => <details className="doc-result" key={`${doc.filename}-${i}`} open={i === 0}>
              <summary><span className="doc-symbol">▤</span><span className="doc-name">{doc.filename}<small>{doc.missing_fields.length ? `${doc.missing_fields.length} missing field(s)` : "Required fields detected"}</small></span><span className="doc-score">{doc.trust_score}/100</span><span className={`decision mini ${doc.decision.toLowerCase()}`}>{doc.decision}</span></summary>
              <div className="doc-body">
                <h4>Extracted fields</h4><div className="fields">{Object.entries(doc.fields).map(([key, value]) => <div className="field" key={key}><small>{key.replaceAll("_", " ")}</small><b className={value ? "" : "empty"}>{value || "Not detected"}</b></div>)}</div>
                <h4>Flags and evidence</h4>
                {doc.flags.length ? doc.flags.map((f, j) => <div className="flag" key={j}><span className={`flag-dot ${f.severity}`} /><div><b>{f.code.replaceAll("_", " ")}</b><p>{f.message}</p></div></div>) : <p className="quiet">No prototype rule flags were triggered.</p>}
                {doc.regulation_matches?.length > 0 && <><h4>Knowledge-base matches (demo rules)</h4>{doc.regulation_matches.map((r, j) => <div className="rule" key={j}><b>{r.title}</b><small>{r.reference} · matched: {r.matched_keywords}</small><p>{r.note}</p></div>)}</>}
                {doc.extracted_text_preview && <details className="text-preview"><summary>View extracted text preview</summary><pre>{doc.extracted_text_preview}</pre></details>}
              </div>
            </details>)}
          </div>
          <div className="disclaimer"><b>Human review required</b><p>{result.disclaimer}</p></div>
        </section>
      )}

      <footer><span>SatyaVerify</span><span>Prototype only · No final legal or authenticity determination</span></footer>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
