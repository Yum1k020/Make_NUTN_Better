const DEFAULT_STUDY_AGENT_ENDPOINT = "/api/v1/study-agent/run";

export function getStudyAgentEndpoint(env = import.meta.env || {}) {
  return env.VITE_STUDY_AGENT_ENDPOINT?.trim() || DEFAULT_STUDY_AGENT_ENDPOINT;
}

export function studyPlansMatch(left, right) {
  if (!left || !right) return false;
  const canonicalize = (value) => {
    if (Array.isArray(value)) return value.map(canonicalize);
    if (value && typeof value === "object") {
      return Object.fromEntries(
        Object.keys(value)
          .sort()
          .map((key) => [key, canonicalize(value[key])]),
      );
    }
    return value;
  };
  return (
    JSON.stringify(canonicalize(left)) === JSON.stringify(canonicalize(right))
  );
}

export async function requestStudyAgentPlan({
  payload,
  endpoint = getStudyAgentEndpoint(),
  fetchImpl = globalThis.fetch,
  signal,
} = {}) {
  if (typeof fetchImpl !== "function") {
    throw new Error("No fetch implementation is available.");
  }

  const response = await fetchImpl(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = new Error(
      body.error || `Agent API 回傳 HTTP ${response.status}`,
    );
    error.code = body.code;
    error.workflow = body.workflow;
    throw error;
  }
  if (!body.plan || !body.agent) {
    throw new Error("Agent API 回傳資料不完整。");
  }

  return body;
}

export { DEFAULT_STUDY_AGENT_ENDPOINT };
