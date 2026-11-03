import test from "node:test";
import assert from "node:assert/strict";
import {
  displayValue,
  workflowMessage,
  graduationRequest,
} from "../src/lib/graduation.js";

test("unknown is distinct from a confirmed zero", () => {
  assert.equal(displayValue(null), "待確認");
  assert.equal(displayValue(0), "0");
});
test("failure and revision cap never appear as verified", () => {
  assert.match(
    workflowMessage({ status: "fallback", stop_reason: "REVISION_LIMIT" }),
    /仍未通過/,
  );
  assert.match(
    workflowMessage({
      status: "fallback",
      stop_reason: "PROVIDER_NOT_CONFIGURED",
    }),
    /尚未設定/,
  );
  assert.match(workflowMessage({ status: "verified" }), /已通過/);
});
test("HTTP failure rejects instead of returning old demo data", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    json: async () => ({ error: { message: "規則損壞" } }),
  });
  try {
    await assert.rejects(graduationRequest("graduation-progress"), /規則損壞/);
  } finally {
    globalThis.fetch = original;
  }
});
