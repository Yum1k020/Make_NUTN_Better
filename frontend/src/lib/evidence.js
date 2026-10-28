import {
  evidenceDocuments,
  fixedQueries,
  generatorComparisons,
  sourceCards,
  topKTraces,
} from "../data/evidence.js";

export function getDocument(documentId) {
  return evidenceDocuments.find((document) => document.id === documentId);
}

export function getSource(sourceId) {
  return sourceCards.find((source) => source.id === sourceId);
}

function coverageValue(label) {
  const [covered, total] = label.split("/").map(Number);
  return { covered, total };
}

export function getSelectedEvidence(queryId) {
  return (topKTraces[queryId] || [])
    .filter((trace) => trace.selected)
    .map((trace) => getDocument(trace.documentId))
    .filter(Boolean);
}

export function getCitationAudit(queryId) {
  const result = generatorComparisons[queryId]?.evidenceLocked;
  if (!result) return { citations: [], missing: [], unused: [] };
  const selectedIds = new Set(
    getSelectedEvidence(queryId).map((document) => document.id),
  );
  const citationIds = new Set(result.citations);
  return {
    citations: result.citations,
    missing: [...citationIds].filter((id) => !selectedIds.has(id)),
    unused: [...selectedIds].filter((id) => !citationIds.has(id)),
  };
}

export function getEvidenceGateMetrics() {
  const selectedResults = fixedQueries.map(
    (query) => generatorComparisons[query.id].evidenceLocked,
  );
  const coveredQueries = selectedResults
    .map((result) => coverageValue(result.factCoverage))
    .filter((current) => current.covered === current.total).length;
  const unsupportedClaims = selectedResults.reduce(
    (sum, result) => sum + result.unsupportedClaims,
    0,
  );
  const citationIssues = fixedQueries.flatMap((query) => {
    const audit = getCitationAudit(query.id);
    return [...audit.missing, ...audit.unused];
  });

  return {
    fixedQueryCount: fixedQueries.length,
    noAnswerCount: fixedQueries.filter(
      (query) => query.category === "no-answer",
    ).length,
    coverage: {
      covered: coveredQueries,
      total: fixedQueries.length,
    },
    unsupportedClaims,
    citationConsistent: citationIssues.length === 0,
  };
}

export function buildComparisonJson(queryId) {
  const query = fixedQueries.find((item) => item.id === queryId);
  const selectedEvidence = getSelectedEvidence(queryId);
  const comparison = generatorComparisons[queryId];
  return {
    query_id: query.id,
    question: query.question,
    selected_evidence: selectedEvidence.map((document) => ({
      document_id: document.id,
      source_id: document.sourceId,
      quote: document.quote,
    })),
    generator_comparison: comparison,
    citation_audit: getCitationAudit(queryId),
  };
}
