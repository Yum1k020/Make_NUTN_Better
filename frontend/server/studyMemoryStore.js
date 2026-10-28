import { randomUUID } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

export const STUDY_SESSION_MINUTES_KEY = "study_session_minutes";

const operationIdSchema = z
  .string()
  .trim()
  .min(8)
  .max(120)
  .regex(/^[A-Za-z0-9_-]+$/, "operationId 格式不正確。");

export const saveStudyPreferenceSchema = z
  .object({
    operationId: operationIdSchema,
    expectedVersion: z.number().int().min(0),
    value: z.number().int().min(15).max(240),
    expiresInDays: z.number().int().min(1).max(365),
    confirmed: z.literal(true),
  })
  .strict();

export const withdrawStudyPreferenceSchema = z
  .object({
    operationId: operationIdSchema,
    expectedVersion: z.number().int().min(1),
    confirmed: z.literal(true),
  })
  .strict();

const memoryRecordSchema = z
  .object({
    id: z.string().min(1),
    userId: z.string().min(1),
    key: z.literal(STUDY_SESSION_MINUTES_KEY),
    value: z.number().int().min(15).max(240).nullable(),
    owner: z.string().min(1),
    source: z
      .object({
        type: z.literal("user-confirmed"),
        surface: z.literal("study-planner"),
      })
      .strict(),
    version: z.number().int().positive(),
    status: z.enum(["active", "withdrawn"]),
    expiresAt: z.string().datetime().nullable(),
    updatedAt: z.string().datetime(),
  })
  .strict();

const memoryOperationSchema = z
  .object({
    operationId: operationIdSchema,
    userId: z.string().min(1),
    action: z.enum(["save", "withdraw"]),
    fingerprint: z.string().min(1),
    result: z
      .object({
        record: memoryRecordSchema.nullable(),
        latestVersion: z.number().int().min(0),
      })
      .strict(),
    createdAt: z.string().datetime(),
  })
  .strict();

const memoryDocumentSchema = z
  .object({
    schemaVersion: z.literal(1),
    records: z.array(memoryRecordSchema),
    operations: z.array(memoryOperationSchema),
  })
  .strict();

const DEFAULT_MEMORY_FILE = fileURLToPath(
  new URL("../data/study-memory.json", import.meta.url),
);

export class StudyMemoryError extends Error {
  constructor({ code, message, statusCode = 400, cause }) {
    super(message, cause ? { cause } : undefined);
    this.name = "StudyMemoryError";
    this.code = code;
    this.statusCode = statusCode;
  }
}

function emptyDocument() {
  return { schemaVersion: 1, records: [], operations: [] };
}

function normalizeUserId(userId) {
  if (
    typeof userId !== "string" ||
    !/^[A-Za-z0-9_-]{3,80}$/.test(userId.trim())
  ) {
    throw new StudyMemoryError({
      code: "MEMORY_IDENTITY_REQUIRED",
      message: "需要有效的使用者身分才能存取記憶。",
      statusCode: 401,
    });
  }
  return userId.trim();
}

function fingerprint(action, userId, input) {
  return JSON.stringify({ action, userId, ...input });
}

function isActive(record, now) {
  return (
    record?.status === "active" &&
    Number.isInteger(record.value) &&
    typeof record.expiresAt === "string" &&
    Date.parse(record.expiresAt) > now.getTime()
  );
}

function publicState(record, now) {
  return {
    record: isActive(record, now) ? structuredClone(record) : null,
    latestVersion: record?.version || 0,
  };
}

export class StudyMemoryStore {
  constructor({
    filePath = DEFAULT_MEMORY_FILE,
    clock = () => new Date(),
    idFactory = randomUUID,
  } = {}) {
    this.filePath = filePath;
    this.clock = clock;
    this.idFactory = idFactory;
    this.writeQueue = Promise.resolve();
  }

  async readDocument() {
    let raw;
    try {
      raw = await readFile(this.filePath, "utf8");
    } catch (error) {
      if (error?.code === "ENOENT") return emptyDocument();
      throw error;
    }

    try {
      return memoryDocumentSchema.parse(JSON.parse(raw));
    } catch (error) {
      throw new StudyMemoryError({
        code: "MEMORY_STORE_INVALID",
        message: "記憶檔案格式無效，已停止讀取以避免覆蓋資料。",
        statusCode: 500,
        cause: error,
      });
    }
  }

  async writeDocument(document) {
    const parsed = memoryDocumentSchema.parse(document);
    const temporaryPath = `${this.filePath}.${process.pid}.tmp`;
    await mkdir(dirname(this.filePath), { recursive: true });
    await writeFile(
      temporaryPath,
      `${JSON.stringify(parsed, null, 2)}\n`,
      "utf8",
    );
    await rename(temporaryPath, this.filePath);
  }

  queueMutation(mutation) {
    const pending = this.writeQueue.then(mutation, mutation);
    this.writeQueue = pending.catch(() => undefined);
    return pending;
  }

  findRecord(document, userId) {
    return document.records.find(
      (record) =>
        record.userId === userId && record.key === STUDY_SESSION_MINUTES_KEY,
    );
  }

  async getPreference(userId) {
    const normalizedUserId = normalizeUserId(userId);
    await this.writeQueue;
    const document = await this.readDocument();
    return publicState(
      this.findRecord(document, normalizedUserId),
      this.clock(),
    );
  }

  async savePreference(userId, input) {
    const normalizedUserId = normalizeUserId(userId);
    const parsedInput = saveStudyPreferenceSchema.parse(input);
    return this.queueMutation(async () => {
      const document = await this.readDocument();
      const operationFingerprint = fingerprint(
        "save",
        normalizedUserId,
        parsedInput,
      );
      const previousOperation = document.operations.find(
        (operation) => operation.operationId === parsedInput.operationId,
      );
      if (previousOperation) {
        if (previousOperation.fingerprint !== operationFingerprint) {
          throw new StudyMemoryError({
            code: "MEMORY_OPERATION_CONFLICT",
            message: "相同 operationId 不可用於不同的記憶操作。",
            statusCode: 409,
          });
        }
        return { ...structuredClone(previousOperation.result), replayed: true };
      }

      const now = this.clock();
      const existingRecord = this.findRecord(document, normalizedUserId);
      const currentVersion = existingRecord?.version || 0;
      if (parsedInput.expectedVersion !== currentVersion) {
        throw new StudyMemoryError({
          code: "MEMORY_VERSION_CONFLICT",
          message: "記憶版本已變更，請重新讀取後再儲存。",
          statusCode: 409,
        });
      }

      const record = {
        id: existingRecord?.id || `memory-${this.idFactory()}`,
        userId: normalizedUserId,
        key: STUDY_SESSION_MINUTES_KEY,
        value: parsedInput.value,
        owner: normalizedUserId,
        source: { type: "user-confirmed", surface: "study-planner" },
        version: currentVersion + 1,
        status: "active",
        expiresAt: new Date(
          now.getTime() + parsedInput.expiresInDays * 24 * 60 * 60 * 1000,
        ).toISOString(),
        updatedAt: now.toISOString(),
      };

      if (existingRecord) {
        Object.assign(existingRecord, record);
      } else {
        document.records.push(record);
      }

      const result = {
        record: structuredClone(record),
        latestVersion: record.version,
      };
      document.operations.push({
        operationId: parsedInput.operationId,
        userId: normalizedUserId,
        action: "save",
        fingerprint: operationFingerprint,
        result,
        createdAt: now.toISOString(),
      });
      await this.writeDocument(document);
      return { ...structuredClone(result), replayed: false };
    });
  }

  async withdrawPreference(userId, input) {
    const normalizedUserId = normalizeUserId(userId);
    const parsedInput = withdrawStudyPreferenceSchema.parse(input);
    return this.queueMutation(async () => {
      const document = await this.readDocument();
      const operationFingerprint = fingerprint(
        "withdraw",
        normalizedUserId,
        parsedInput,
      );
      const previousOperation = document.operations.find(
        (operation) => operation.operationId === parsedInput.operationId,
      );
      if (previousOperation) {
        if (previousOperation.fingerprint !== operationFingerprint) {
          throw new StudyMemoryError({
            code: "MEMORY_OPERATION_CONFLICT",
            message: "相同 operationId 不可用於不同的記憶操作。",
            statusCode: 409,
          });
        }
        return { ...structuredClone(previousOperation.result), replayed: true };
      }

      const now = this.clock();
      const existingRecord = this.findRecord(document, normalizedUserId);
      if (!existingRecord || !isActive(existingRecord, now)) {
        throw new StudyMemoryError({
          code: "MEMORY_NOT_FOUND",
          message: "目前沒有可撤回的有效學習偏好。",
          statusCode: 404,
        });
      }
      if (parsedInput.expectedVersion !== existingRecord.version) {
        throw new StudyMemoryError({
          code: "MEMORY_VERSION_CONFLICT",
          message: "記憶版本已變更，請重新讀取後再撤回。",
          statusCode: 409,
        });
      }

      existingRecord.value = null;
      existingRecord.version += 1;
      existingRecord.status = "withdrawn";
      existingRecord.expiresAt = null;
      existingRecord.updatedAt = now.toISOString();

      const result = { record: null, latestVersion: existingRecord.version };
      document.operations.push({
        operationId: parsedInput.operationId,
        userId: normalizedUserId,
        action: "withdraw",
        fingerprint: operationFingerprint,
        result,
        createdAt: now.toISOString(),
      });
      await this.writeDocument(document);
      return { ...structuredClone(result), replayed: false };
    });
  }
}

export function createStudyMemoryStore(options) {
  return new StudyMemoryStore(options);
}

export { DEFAULT_MEMORY_FILE };
