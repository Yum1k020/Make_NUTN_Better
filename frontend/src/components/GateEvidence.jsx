import React, { useMemo, useState } from "react";
import Icon from "./Icon.jsx";
import {
  evidenceDocuments,
  fixedQueries,
  generatorComparisons,
  proposalBrief,
  sourceCards,
  topKTraces,
} from "../data/evidence.js";
import {
  buildComparisonJson,
  getCitationAudit,
  getDocument,
  getEvidenceGateMetrics,
  getSource,
} from "../lib/evidence.js";

function StatusTag({ children, tone = "blue" }) {
  return <span className={`gate-tag tone-${tone}`}>{children}</span>;
}

function SourceCard({ source }) {
  return (
    <article className="source-card">
      <div className="source-card-head">
        <h3>{source.name}</h3>
        <StatusTag tone={source.status === "allowed" ? "mint" : "red"}>
          {source.status === "allowed" ? "可引用" : "不可引用"}
        </StatusTag>
      </div>
      <dl>
        <div>
          <dt>authority</dt>
          <dd>{source.authority}</dd>
        </div>
        <div>
          <dt>permission</dt>
          <dd>{source.permission}</dd>
        </div>
        <div>
          <dt>freshness</dt>
          <dd>{source.freshness}</dd>
        </div>
        <div>
          <dt>PII</dt>
          <dd>{source.pii}</dd>
        </div>
        <div>
          <dt>撤回</dt>
          <dd>{source.revocation}</dd>
        </div>
      </dl>
    </article>
  );
}

function QueryButton({ query, selected, onSelect }) {
  return (
    <button
      type="button"
      className={`query-button ${selected ? "selected" : ""}`}
      onClick={() => onSelect(query.id)}
    >
      <span>{query.label}</span>
      <strong>{query.question}</strong>
      <small>
        {query.category === "no-answer" ? "含拒答條件" : "可由 fixture 回答"}
      </small>
    </button>
  );
}

function EvidenceRow({ trace }) {
  const document = getDocument(trace.documentId);
  const source = document ? getSource(document.sourceId) : null;
  return (
    <article className={`trace-row ${trace.selected ? "selected" : ""}`}>
      <div className="trace-rank">#{trace.rank}</div>
      <div>
        <div className="trace-title">
          <h3>{document?.title || trace.documentId}</h3>
          <StatusTag tone={trace.selected ? "mint" : "amber"}>
            {trace.selected ? "selected" : "rejected"}
          </StatusTag>
        </div>
        <p>{document?.quote || source?.authority}</p>
        <small>{trace.reason}</small>
      </div>
      <strong>{trace.score.toFixed(2)}</strong>
    </article>
  );
}

function GeneratorCard({ result, tone }) {
  return (
    <article className={`generator-card tone-${tone}`}>
      <div className="generator-head">
        <h3>{result.name}</h3>
        <div>
          <StatusTag tone={result.unsupportedClaims === 0 ? "mint" : "red"}>
            unsupported {result.unsupportedClaims}
          </StatusTag>
          <StatusTag tone="blue">coverage {result.factCoverage}</StatusTag>
        </div>
      </div>
      <p>{result.answer}</p>
      <div className="citation-list">
        {result.citations.length ? (
          result.citations.map((citation) => (
            <span key={citation}>{citation}</span>
          ))
        ) : (
          <span>no citation</span>
        )}
      </div>
      <small>{result.observation}</small>
    </article>
  );
}

export default function GateEvidence() {
  const [selectedQueryId, setSelectedQueryId] = useState(fixedQueries[0].id);
  const [jsonMode, setJsonMode] = useState("pretty");
  const [copyMessage, setCopyMessage] = useState("");
  const metrics = getEvidenceGateMetrics();
  const selectedQuery = fixedQueries.find(
    (query) => query.id === selectedQueryId,
  );
  const comparison = generatorComparisons[selectedQueryId];
  const citationAudit = getCitationAudit(selectedQueryId);
  const comparisonJson = useMemo(
    () => buildComparisonJson(selectedQueryId),
    [selectedQueryId],
  );
  const jsonText = JSON.stringify(
    comparisonJson,
    null,
    jsonMode === "pretty" ? 2 : 0,
  );

  async function copyJson() {
    try {
      await navigator.clipboard.writeText(jsonText);
      setCopyMessage("已複製 JSON");
    } catch {
      setCopyMessage("瀏覽器不允許複製，請直接選取 JSON");
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <div className="title-line">
            <h1>資料證據</h1>
            <span className="demo-badge">Week 03 Gate</span>
          </div>
          <p>
            用學生系統自己的資料檢查 retriever、source card、citation 與
            generator 回答是否一致。
          </p>
        </div>
      </header>

      <section className="gate-hero">
        <div>
          <span className="gate-hero-icon">
            <Icon name="list" size={24} />
          </span>
          <h2>{proposalBrief.title}</h2>
          <p>{proposalBrief.claim}</p>
        </div>
        <div className="gate-score-grid">
          <div>
            <span>fixed queries</span>
            <strong>{metrics.fixedQueryCount}</strong>
          </div>
          <div>
            <span>fact coverage</span>
            <strong>
              {metrics.coverage.covered}/{metrics.coverage.total}
            </strong>
          </div>
          <div>
            <span>unsupported</span>
            <strong>{metrics.unsupportedClaims}</strong>
          </div>
          <div>
            <span>no-answer</span>
            <strong>{metrics.noAnswerCount}</strong>
          </div>
        </div>
      </section>

      <div className="gate-layout">
        <div className="feature-left">
          <section className="panel gate-proposal">
            <div className="panel-heading">
              <h2>一頁 proposal</h2>
              <StatusTag tone={metrics.citationConsistent ? "mint" : "red"}>
                citation {metrics.citationConsistent ? "一致" : "需修正"}
              </StatusTag>
            </div>
            <div className="proposal-grid">
              <div>
                <h3>使用者</h3>
                <ul>
                  {proposalBrief.users.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>資料範圍</h3>
                <ul>
                  {proposalBrief.dataScope.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>拒答條件</h3>
                <ul>
                  {proposalBrief.refusalConditions.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </section>

          <section className="panel query-panel">
            <div className="panel-heading">
              <h2>3 個 fixed queries</h2>
              <span className="subtle">含 no-answer 與 coverage failure</span>
            </div>
            <div className="query-list">
              {fixedQueries.map((query) => (
                <QueryButton
                  key={query.id}
                  query={query}
                  selected={query.id === selectedQueryId}
                  onSelect={setSelectedQueryId}
                />
              ))}
            </div>
          </section>

          <section className="panel trace-panel">
            <div className="panel-heading">
              <h2>Top-k trace</h2>
              <span className="subtle">{selectedQuery?.expectation}</span>
            </div>
            <div className="trace-list">
              {topKTraces[selectedQueryId].map((trace) => (
                <EvidenceRow
                  key={`${selectedQueryId}-${trace.rank}`}
                  trace={trace}
                />
              ))}
            </div>
          </section>
        </div>

        <div className="feature-right">
          <section className="panel source-panel">
            <div className="panel-heading">
              <h2>Source cards</h2>
              <span className="subtle">authority / permission / freshness</span>
            </div>
            <div className="source-card-list">
              {sourceCards.map((source) => (
                <SourceCard key={source.id} source={source} />
              ))}
            </div>
          </section>

          <section className="panel generator-panel">
            <div className="panel-heading">
              <h2>Generator comparison</h2>
              <span className="subtle">
                missing {citationAudit.missing.length}・unused{" "}
                {citationAudit.unused.length}
              </span>
            </div>
            <div className="generator-list">
              <GeneratorCard result={comparison.baseline} tone="baseline" />
              <GeneratorCard result={comparison.evidenceLocked} tone="locked" />
            </div>
          </section>

          <section className="panel json-panel">
            <div className="panel-heading">
              <h2>Comparison JSON</h2>
              <div className="json-actions">
                <div className="segment" role="group" aria-label="JSON 格式">
                  <button
                    type="button"
                    className={jsonMode === "pretty" ? "selected" : ""}
                    onClick={() => setJsonMode("pretty")}
                  >
                    readable
                  </button>
                  <button
                    type="button"
                    className={jsonMode === "compact" ? "selected" : ""}
                    onClick={() => setJsonMode("compact")}
                  >
                    compact
                  </button>
                </div>
                <button
                  type="button"
                  className="secondary-button small"
                  onClick={copyJson}
                >
                  複製
                </button>
              </div>
            </div>
            {copyMessage && (
              <p className="copy-message" role="status">
                {copyMessage}
              </p>
            )}
            <pre className="json-output">{jsonText}</pre>
          </section>
        </div>
      </div>

      <section className="panel evidence-library">
        <div className="panel-heading">
          <h2>Evidence library</h2>
          <span className="subtle">
            {evidenceDocuments.length} 筆可檢查證據
          </span>
        </div>
        <div className="evidence-table">
          {evidenceDocuments.map((document) => (
            <article key={document.id}>
              <strong>{document.title}</strong>
              <span>{document.id}</span>
              <p>{document.quote}</p>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
