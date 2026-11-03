import test from "node:test";
import assert from "node:assert/strict";
import {
  GraduationMemory,
  validityReason,
} from "../src/lib/graduationMemory.js";

const context = (time = 1000, source = "v1", scope = "s1") => ({
  scope_id: scope,
  source_sha256: source,
  server_now_ms: time,
});
const data = () => ({
  progress: { earned_credits: 3 },
  workflow: {
    status: "verified",
    run_id: "synthetic-run",
    explanation: [{ text: "3 credits" }],
    validity: { ...context(), issued_at_ms: 1000, expires_at_ms: 301000 },
  },
});
function setup(request) {
  let now = 1000;
  const updates = [];
  const store = new GraduationMemory({
    request,
    update: (s) => updates.push(s),
    now: () => now,
  });
  return {
    store,
    updates,
    advance: (value) => {
      now = value;
    },
  };
}

test("normal first read, TTL boundary removes clauses, later reads do not extend TTL", async () => {
  const { store, updates, advance } = setup(async (path) =>
    path === "graduation-explanation" ? data() : context(),
  );
  await store.generate();
  assert.equal(updates.at(-1).workflow.run_id, "synthetic-run");
  advance(2000);
  await store.verify();
  advance(301000);
  store.tick();
  assert.equal(updates.at(-1).workflow, null);
  assert.equal(updates.at(-1).reason, "EXPIRED");
});

test("source update on recheck removes explanation", async () => {
  let source = "v1";
  const { store, updates } = setup(async (path) =>
    path === "graduation-explanation" ? data() : context(1000, source),
  );
  await store.generate();
  source = "v2";
  await store.verify();
  assert.equal(updates.at(-1).reason, "SOURCE_CHANGED");
  assert.equal(store.workflow, null);
});

test("session change removes explanation; no model call on verify", async () => {
  let scope = "s1",
    calls = 0;
  const { store, updates } = setup(async (path) => {
    if (path === "graduation-explanation") {
      calls++;
      return data();
    }
    return context(1000, "v1", scope);
  });
  await store.generate();
  scope = "s2";
  await store.verify();
  assert.equal(updates.at(-1).reason, "SESSION_CHANGED");
  assert.equal(calls, 1);
});

test("failed source check fails closed with no stale clauses", async () => {
  let failed = false;
  const { store, updates } = setup(async (path) => {
    if (failed) throw Error("injected timeout");
    return path === "graduation-explanation" ? data() : context();
  });
  await store.generate();
  failed = true;
  await store.verify();
  assert.equal(updates.at(-1).reason, "UNAVAILABLE");
  assert.equal(store.workflow, null);
});

test("old model response after clear cannot overwrite a new session", async () => {
  let resolve;
  const held = new Promise((r) => {
    resolve = r;
  });
  const { store, updates } = setup(async (path) =>
    path === "graduation-explanation" ? held : context(),
  );
  const pending = store.generate();
  await Promise.resolve();
  await Promise.resolve();
  store.clear("SESSION_CHANGED");
  resolve(data());
  await pending;
  assert.equal(updates.at(-1).workflow, null);
  assert.equal(updates.at(-1).reason, "SESSION_CHANGED");
});

test("old revalidation cannot restore cleared state", async () => {
  let hold = false,
    resolve;
  const held = new Promise((r) => {
    resolve = r;
  });
  const { store, updates } = setup(async (path) =>
    path === "graduation-explanation" ? data() : hold ? held : context(),
  );
  await store.generate();
  hold = true;
  const pending = store.verify();
  store.clear("SESSION_CHANGED");
  resolve(context());
  await pending;
  assert.equal(updates.at(-1).reason, "SESSION_CHANGED");
});

test("source changed during model request is rejected before first display", async () => {
  const d = data();
  d.workflow.status = "stale";
  d.workflow.explanation = [];
  d.workflow.stop_reason = "SOURCE_CHANGED";
  const { store, updates } = setup(async (path) =>
    path === "graduation-explanation" ? d : context(),
  );
  await store.generate();
  assert.equal(updates.at(-1).reason, "SOURCE_CHANGED");
  assert.ok(updates.every((s) => s.workflow === null));
});

test("dispose prevents late response after navigation/unmount", async () => {
  let resolve;
  const held = new Promise((r) => {
    resolve = r;
  });
  const { store, updates } = setup(async () => held);
  const pending = store.generate();
  store.dispose();
  const count = updates.length;
  resolve(context());
  await pending;
  assert.equal(updates.length, count);
});

test("explicit new session calls reset API and removes all clauses", async () => {
  const routes = [];
  const { store, updates } = setup(async (path) => {
    routes.push(path);
    return path === "graduation-explanation" ? data() : context();
  });
  await store.generate();
  await store.reset();
  assert.equal(routes.at(-1), "graduation-session/reset");
  assert.equal(updates.at(-1).workflow, null);
});

test("expiry checked using server time, never client-provided identity", () => {
  assert.equal(
    validityReason(data().workflow.validity, context(301000)),
    "EXPIRED",
  );
  assert.equal(validityReason(null, context()), "UNAVAILABLE");
});

test("server-expired in-flight result reports expiry instead of source update", async () => {
  const d = data();
  d.workflow.status = "stale";
  d.workflow.stop_reason = "EXPIRED";
  d.workflow.explanation = [];
  const { store, updates } = setup(async (path) =>
    path === "graduation-explanation" ? d : context(),
  );
  await store.generate();
  assert.equal(updates.at(-1).reason, "EXPIRED");
});
