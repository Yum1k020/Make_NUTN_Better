import {
  fixedQueries,
  generatorComparisons,
  topKTraces,
} from "../data/evidence.js";
import { getDocument, getSource } from "./evidence.js";

const DEFAULT_MODEL = "gpt-5-mini";
const DEFAULT_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses";

export function getOpenAIConfig(env = import.meta.env || {}) {
  return {
    apiKey: env.VITE_OPENAI_API_KEY || "",
    model: env.VITE_OPENAI_MODEL || DEFAULT_MODEL,
    endpoint: env.VITE_OPENAI_RESPONSES_ENDPOINT || DEFAULT_RESPONSES_ENDPOINT,
  };
}

export function requireOpenAIConfig(config = getOpenAIConfig()) {
  const normalized = {
    apiKey: config.apiKey?.trim() || "",
    model: config.model?.trim() || DEFAULT_MODEL,
    endpoint: config.endpoint?.trim() || DEFAULT_RESPONSES_ENDPOINT,
  };

  if (!normalized.apiKey)
    throw new Error(
      "Missing VITE_OPENAI_API_KEY. Put it in frontend/.env.local.",
    );

  return normalized;
}

export function buildOpenAIRequest({ queryId, model = DEFAULT_MODEL }) {
  const query = fixedQueries.find((item) => item.id === queryId);
  if (!query) throw new Error("Unknown fixed query.");

  const traces = topKTraces[queryId] || [];
  const selectedEvidence = traces
    .filter((trace) => trace.selected)
    .map((trace) => {
      const document = getDocument(trace.documentId);
      const source = document ? getSource(document.sourceId) : null;
      if (!document) return null;
      return {
        document_id: document.id,
        source_id: document.sourceId,
        source_status: source?.status || "unknown",
        quote: document.quote,
        facts: document.facts,
      };
    })
    .filter(Boolean);

  const rejectedEvidence = traces
    .filter((trace) => !trace.selected)
    .map((trace) => ({
      document_id: trace.documentId,
      reason: trace.reason,
    }));

  return {
    model: (model || DEFAULT_MODEL).trim(),
    store: false,
    max_output_tokens: 700,
    input: [
      {
        role: "system",
        content: [
          {
            type: "input_text",
            text: "你是學生個人安排系統的 evidence-locked generator。只能根據 selected_evidence 回答，不能補充未被引用資料。若 selected_evidence 為空，或問題需要尚未授權的 live source，請用繁體中文拒答並指出缺少哪個來源。回答要簡潔、適合課堂展示。",
          },
        ],
      },
      {
        role: "user",
        content: [
          {
            type: "input_text",
            text: JSON.stringify(
              {
                query_id: query.id,
                question: query.question,
                expectation: query.expectation,
                selected_evidence: selectedEvidence,
                rejected_evidence: rejectedEvidence,
                local_generator_reference:
                  generatorComparisons[queryId]?.evidenceLocked || null,
              },
              null,
              2,
            ),
          },
        ],
      },
    ],
  };
}

export function extractOpenAIText(responseBody) {
  if (typeof responseBody?.output_text === "string")
    return responseBody.output_text.trim();

  const parts = (responseBody?.output || [])
    .flatMap((item) => item.content || [])
    .map((content) => {
      if (typeof content.text === "string") return content.text;
      if (typeof content.value === "string") return content.value;
      return "";
    })
    .filter(Boolean);

  return parts.join("\n").trim();
}

export function normalizeOpenAIError(responseBody, fallback) {
  const message =
    responseBody?.error?.message ||
    responseBody?.message ||
    fallback ||
    "OpenAI request failed.";
  return message.replace(/\s+/g, " ").trim();
}

export async function generateEvidenceLockedAnswer({
  queryId,
  config = getOpenAIConfig(),
  fetchImpl = globalThis.fetch,
} = {}) {
  const openAIConfig = requireOpenAIConfig(config);
  if (typeof fetchImpl !== "function")
    throw new Error("No fetch implementation is available.");

  const response = await fetchImpl(openAIConfig.endpoint, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${openAIConfig.apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(
      buildOpenAIRequest({
        queryId,
        model: openAIConfig.model,
      }),
    ),
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(
      normalizeOpenAIError(body, `OpenAI 回傳 HTTP ${response.status}`),
    );

  return extractOpenAIText(body);
}

export { DEFAULT_MODEL, DEFAULT_RESPONSES_ENDPOINT };
