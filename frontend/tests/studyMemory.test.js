import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { ZodError } from "zod";
import {
  StudyMemoryError,
  StudyMemoryStore,
} from "../server/studyMemoryStore.js";

async function createTestContext() {
  const directory = await mkdtemp(join(tmpdir(), "nutn-study-memory-"));
  const filePath = join(directory, "study-memory.json");
  let currentTime = new Date("2026-10-28T00:00:00.000Z");
  let nextId = 0;
  return {
    directory,
    filePath,
    clock: () => new Date(currentTime),
    advanceDays(days) {
      currentTime = new Date(
        currentTime.getTime() + days * 24 * 60 * 60 * 1000,
      );
    },
    createStore() {
      return new StudyMemoryStore({
        filePath,
        clock: () => new Date(currentTime),
        idFactory: () => `test-${++nextId}`,
      });
    },
  };
}

async function cleanup(context) {
  await rm(context.directory, { recursive: true, force: true });
}

function saveInput(overrides = {}) {
  return {
    operationId: "operation-save-001",
    expectedVersion: 0,
    value: "afternoon",
    expiresInDays: 30,
    confirmed: true,
    ...overrides,
  };
}

test("week07 A1: confirmed preference persists across a new store session", async () => {
  const context = await createTestContext();
  try {
    const firstSession = context.createStore();
    const saved = await firstSession.savePreference(
      "student-u001",
      saveInput(),
    );

    assert.equal(saved.record.value, "afternoon");
    assert.equal(saved.record.owner, "student-u001");
    assert.equal(saved.record.source.type, "user-confirmed");
    assert.equal(saved.record.version, 1);
    assert.equal(saved.replayed, false);

    const newSession = context.createStore();
    const recalled = await newSession.getPreference("student-u001");
    assert.equal(recalled.record.id, saved.record.id);
    assert.equal(recalled.record.value, "afternoon");
    assert.equal(recalled.latestVersion, 1);
  } finally {
    await cleanup(context);
  }
});

test("week07 A2: correction creates a newer version and rejects a stale write", async () => {
  const context = await createTestContext();
  try {
    const store = context.createStore();
    await store.savePreference("student-u001", saveInput());
    const corrected = await store.savePreference(
      "student-u001",
      saveInput({
        operationId: "operation-save-002",
        expectedVersion: 1,
        value: "evening",
      }),
    );

    assert.equal(corrected.record.value, "evening");
    assert.equal(corrected.record.version, 2);
    await assert.rejects(
      store.savePreference(
        "student-u001",
        saveInput({
          operationId: "operation-save-stale",
          expectedVersion: 1,
          value: "morning",
        }),
      ),
      (error) =>
        error instanceof StudyMemoryError &&
        error.code === "MEMORY_VERSION_CONFLICT",
    );
  } finally {
    await cleanup(context);
  }
});

test("week07 A3: withdrawal hides the value from new reads", async () => {
  const context = await createTestContext();
  try {
    const store = context.createStore();
    await store.savePreference("student-u001", saveInput());
    const withdrawn = await store.withdrawPreference("student-u001", {
      operationId: "operation-withdraw-001",
      expectedVersion: 1,
      confirmed: true,
    });

    assert.equal(withdrawn.record, null);
    assert.equal(withdrawn.latestVersion, 2);
    const recalled = await context.createStore().getPreference("student-u001");
    assert.equal(recalled.record, null);
    assert.equal(recalled.latestVersion, 2);
  } finally {
    await cleanup(context);
  }
});

test("week07 C02: one user cannot read another user's preference", async () => {
  const context = await createTestContext();
  try {
    const store = context.createStore();
    await store.savePreference("student-u001", saveInput());

    const otherUser = await store.getPreference("student-u002");
    assert.equal(otherUser.record, null);
    assert.equal(otherUser.latestVersion, 0);
  } finally {
    await cleanup(context);
  }
});

test("week07 boundary: expired preference is excluded from retrieval", async () => {
  const context = await createTestContext();
  try {
    const store = context.createStore();
    await store.savePreference("student-u001", saveInput({ expiresInDays: 1 }));
    context.advanceDays(2);

    const recalled = await store.getPreference("student-u001");
    assert.equal(recalled.record, null);
    assert.equal(recalled.latestVersion, 1);
  } finally {
    await cleanup(context);
  }
});

test("week07 W01: missing identity is rejected without a write", async () => {
  const context = await createTestContext();
  try {
    const store = context.createStore();
    await assert.rejects(
      store.savePreference(undefined, saveInput()),
      (error) =>
        error instanceof StudyMemoryError &&
        error.code === "MEMORY_IDENTITY_REQUIRED",
    );
    const recalled = await store.getPreference("student-u001");
    assert.equal(recalled.record, null);
    await assert.rejects(readFile(context.filePath, "utf8"), {
      code: "ENOENT",
    });
  } finally {
    await cleanup(context);
  }
});

test("week07 boundary: unconfirmed input is rejected without a write", async () => {
  const context = await createTestContext();
  try {
    const store = context.createStore();
    await assert.rejects(
      store.savePreference("student-u001", saveInput({ confirmed: false })),
      ZodError,
    );
    const recalled = await store.getPreference("student-u001");
    assert.equal(recalled.record, null);
    await assert.rejects(readFile(context.filePath, "utf8"), {
      code: "ENOENT",
    });
  } finally {
    await cleanup(context);
  }
});

test("week07 W02: replaying the same operation ID has one side effect", async () => {
  const context = await createTestContext();
  try {
    const store = context.createStore();
    const first = await store.savePreference("student-u001", saveInput());
    const replay = await store.savePreference("student-u001", saveInput());
    const document = JSON.parse(await readFile(context.filePath, "utf8"));

    assert.equal(first.record.version, 1);
    assert.equal(replay.record.version, 1);
    assert.equal(replay.replayed, true);
    assert.equal(document.records.length, 1);
    assert.equal(document.operations.length, 1);
  } finally {
    await cleanup(context);
  }
});
