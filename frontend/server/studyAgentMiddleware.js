import { ZodError } from "zod";
import { createStudyAgentService } from "./studyAgent.js";
import { StudyPlanWorkflowError } from "./studyPlanWorkflow.js";

const MAX_BODY_BYTES = 100_000;

function sendJson(response, statusCode, body) {
  response.statusCode = statusCode;
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.end(JSON.stringify(body));
}

async function readJsonBody(request) {
  const chunks = [];
  let size = 0;

  for await (const chunk of request) {
    size += chunk.length;
    if (size > MAX_BODY_BYTES) {
      throw new Error("REQUEST_TOO_LARGE");
    }
    chunks.push(chunk);
  }

  if (!chunks.length) throw new Error("EMPTY_REQUEST");
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

export function createStudyAgentMiddleware({
  apiKey,
  model,
  tracingEnabled = false,
  serviceFactory = createStudyAgentService,
} = {}) {
  let service;

  function getService() {
    if (!service) {
      service = serviceFactory({ apiKey, model, tracingEnabled });
    }
    return service;
  }

  return async function studyAgentMiddleware(request, response, next) {
    const path = (request.url || "/").split("?")[0];

    if (request.method === "GET" && path === "/health") {
      return sendJson(response, 200, {
        ok: true,
        configured: Boolean(apiKey?.trim()),
        framework: "OpenAI Agents SDK",
      });
    }

    if (request.method !== "POST" || path !== "/run") {
      return next();
    }

    try {
      const body = await readJsonBody(request);
      const result = await getService().run(body);
      return sendJson(response, 200, result);
    } catch (error) {
      if (error instanceof SyntaxError) {
        return sendJson(response, 400, { error: "Request body must be JSON." });
      }
      if (error instanceof ZodError) {
        return sendJson(response, 422, {
          error: "學習規劃資料格式不正確。",
          issues: error.issues.map((issue) => ({
            path: issue.path.join("."),
            message: issue.message,
          })),
        });
      }
      if (error instanceof StudyPlanWorkflowError) {
        console.error("[study-agent] workflow stopped:", error.code);
        return sendJson(response, error.statusCode, {
          error: error.message,
          code: error.code,
          workflow: error.workflow,
          ...(error.issues.length ? { issues: error.issues } : {}),
        });
      }
      if (error instanceof Error && error.message === "REQUEST_TOO_LARGE") {
        return sendJson(response, 413, { error: "Request body is too large." });
      }
      if (error instanceof Error && error.message === "EMPTY_REQUEST") {
        return sendJson(response, 400, { error: "Request body is required." });
      }
      if (
        error instanceof Error &&
        error.message === "Missing server-side OPENAI_API_KEY."
      ) {
        return sendJson(response, 503, {
          error: "伺服器尚未設定 OPENAI_API_KEY。",
        });
      }

      console.error(
        "[study-agent] run failed:",
        error instanceof Error ? error.message : "Unknown error",
      );
      return sendJson(response, 502, {
        error: "Agent 執行失敗，請稍後再試；原本的規則排程仍可使用。",
      });
    }
  };
}
