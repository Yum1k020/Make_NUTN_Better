import { ZodError } from "zod";
import {
  createStudyMemoryStore,
  StudyMemoryError,
} from "./studyMemoryStore.js";

const MAX_BODY_BYTES = 20_000;

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
    if (size > MAX_BODY_BYTES) throw new Error("REQUEST_TOO_LARGE");
    chunks.push(chunk);
  }
  if (!chunks.length) throw new Error("EMPTY_REQUEST");
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function requestUserId(request) {
  const header = request.headers["x-demo-user-id"];
  return Array.isArray(header) ? header[0] : header;
}

export function createStudyMemoryMiddleware({
  store = createStudyMemoryStore(),
} = {}) {
  return async function studyMemoryMiddleware(request, response, next) {
    const path = (request.url || "/").split("?")[0];

    if (request.method === "GET" && path === "/health") {
      return sendJson(response, 200, {
        ok: true,
        storage: "server-filesystem",
      });
    }

    if (path !== "/preference") return next();

    try {
      const userId = requestUserId(request);
      if (request.method === "GET") {
        return sendJson(response, 200, await store.getPreference(userId));
      }
      if (request.method === "PUT") {
        const body = await readJsonBody(request);
        return sendJson(
          response,
          200,
          await store.savePreference(userId, body),
        );
      }
      if (request.method === "DELETE") {
        const body = await readJsonBody(request);
        return sendJson(
          response,
          200,
          await store.withdrawPreference(userId, body),
        );
      }
      response.setHeader("Allow", "GET, PUT, DELETE");
      return sendJson(response, 405, { error: "Method not allowed." });
    } catch (error) {
      if (error instanceof SyntaxError) {
        return sendJson(response, 400, { error: "Request body must be JSON." });
      }
      if (error instanceof ZodError) {
        return sendJson(response, 422, {
          error: "記憶操作資料格式不正確或尚未確認。",
          code: "MEMORY_INPUT_INVALID",
          issues: error.issues.map((issue) => ({
            path: issue.path.join("."),
            message: issue.message,
          })),
        });
      }
      if (error instanceof StudyMemoryError) {
        return sendJson(response, error.statusCode, {
          error: error.message,
          code: error.code,
        });
      }
      if (error instanceof Error && error.message === "REQUEST_TOO_LARGE") {
        return sendJson(response, 413, { error: "Request body is too large." });
      }
      if (error instanceof Error && error.message === "EMPTY_REQUEST") {
        return sendJson(response, 400, { error: "Request body is required." });
      }

      console.error(
        "[study-memory] request failed:",
        error instanceof Error ? error.message : "Unknown error",
      );
      return sendJson(response, 500, {
        error: "記憶服務暫時無法使用；本次規劃條件仍可手動設定。",
        code: "MEMORY_SERVICE_FAILED",
      });
    }
  };
}
