export const DEFAULT_STUDY_MEMORY_ENDPOINT = "/api/study-memory/preference";
export const DEMO_STUDY_USER_ID = "demo-student-001";

export function createMemoryOperationId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `memory-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

async function requestMemory({
  method,
  body,
  endpoint = DEFAULT_STUDY_MEMORY_ENDPOINT,
  userId = DEMO_STUDY_USER_ID,
  fetchImpl = globalThis.fetch,
} = {}) {
  if (typeof fetchImpl !== "function") {
    throw new Error("No fetch implementation is available.");
  }

  const response = await fetchImpl(endpoint, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-Demo-User-Id": userId,
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const responseBody = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      responseBody.error || `記憶 API 回傳 HTTP ${response.status}`,
    );
    error.code = responseBody.code;
    throw error;
  }
  return responseBody;
}

export function loadStudyPreference(options = {}) {
  return requestMemory({ ...options, method: "GET" });
}

export function saveStudyPreference({
  value,
  expectedVersion,
  expiresInDays = 30,
  operationId = createMemoryOperationId(),
  ...options
} = {}) {
  return requestMemory({
    ...options,
    method: "PUT",
    body: {
      operationId,
      expectedVersion,
      value,
      expiresInDays,
      confirmed: true,
    },
  });
}

export function withdrawStudyPreference({
  expectedVersion,
  operationId = createMemoryOperationId(),
  ...options
} = {}) {
  return requestMemory({
    ...options,
    method: "DELETE",
    body: { operationId, expectedVersion, confirmed: true },
  });
}
