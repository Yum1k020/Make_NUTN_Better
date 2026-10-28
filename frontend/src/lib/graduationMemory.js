// C route: derived explanations live only in this mounted page; never localStorage.
export const VALIDITY_MESSAGES = {
  EXPIRED: "說明已到期，請重新產生。",
  SOURCE_CHANGED: "修課資料或規則已更新，舊說明停止使用；請重新整理進度。",
  SESSION_CHANGED: "工作階段已變更，舊說明已清除。",
  UNAVAILABLE: "目前無法確認資料有效性，舊說明已停止使用。",
};

export function validityReason(validity, current) {
  if (!validity || !current) return "UNAVAILABLE";
  if (validity.scope_id !== current.scope_id) return "SESSION_CHANGED";
  if (validity.source_sha256 !== current.source_sha256) return "SOURCE_CHANGED";
  if (current.server_now_ms >= validity.expires_at_ms) return "EXPIRED";
  return "";
}

export class GraduationMemory {
  constructor({ request, update, now = () => performance.now() }) {
    this.request = request;
    this.update = update;
    this.now = now;
    this.sequence = 0;
    this.checkSequence = 0;
    this.workflow = null;
    this.deadline = 0;
    this.active = true;
  }
  clear(reason = "") {
    this.sequence += 1;
    this.checkSequence += 1;
    this.workflow = null;
    this.deadline = 0;
    if (this.active) this.update({ workflow: null, reason, busy: false });
  }
  dispose() {
    this.active = false;
    this.clear();
  }
  async generate() {
    this.clear();
    const sequence = this.sequence;
    this.update({ workflow: null, reason: "", busy: true });
    try {
      // Establish a server-issued browser scope before any model request.
      await this.request("graduation-context");
      if (!this.active || sequence !== this.sequence) return;
      const data = await this.request("graduation-explanation", {
        method: "POST",
      });
      if (!this.active || sequence !== this.sequence) return;
      const started = this.now();
      const current = await this.request("graduation-context");
      if (!this.active || sequence !== this.sequence) return;
      const reason =
        data.workflow.status === "stale"
          ? data.workflow.stop_reason === "EXPIRED"
            ? "EXPIRED"
            : "SOURCE_CHANGED"
          : validityReason(data.workflow.validity, current);
      if (reason) {
        this.clear(reason);
        return;
      }
      this.workflow = data.workflow;
      // Server time defines remaining life; round-trip delay only shortens it.
      this.deadline =
        started + data.workflow.validity.expires_at_ms - current.server_now_ms;
      if (this.now() >= this.deadline) {
        this.clear("EXPIRED");
        return;
      }
      this.update({
        workflow: this.workflow,
        progress: data.progress,
        reason: "",
        busy: false,
      });
    } catch (error) {
      if (this.active && sequence === this.sequence) this.clear("UNAVAILABLE");
    }
  }
  tick() {
    if (this.workflow && this.now() >= this.deadline) this.clear("EXPIRED");
  }
  async verify() {
    this.tick();
    if (!this.workflow) return;
    const sequence = this.sequence;
    const check = ++this.checkSequence;
    // Hide clauses while revalidating on timer/focus. A failed request cannot reuse them.
    this.update({ workflow: null, reason: "", busy: false });
    const started = this.now();
    try {
      const current = await this.request("graduation-context");
      if (
        !this.active ||
        sequence !== this.sequence ||
        check !== this.checkSequence
      )
        return;
      const reason = validityReason(this.workflow.validity, current);
      if (reason) {
        this.clear(reason);
        return;
      }
      this.deadline = Math.min(
        this.deadline,
        started + this.workflow.validity.expires_at_ms - current.server_now_ms,
      );
      this.tick();
      if (this.workflow)
        this.update({ workflow: this.workflow, reason: "", busy: false });
    } catch (error) {
      if (
        this.active &&
        sequence === this.sequence &&
        check === this.checkSequence
      )
        this.clear("UNAVAILABLE");
    }
  }
  async reset() {
    this.clear("SESSION_CHANGED");
    const sequence = this.sequence;
    try {
      await this.request("graduation-session/reset", { method: "POST" });
    } catch (error) {
      if (sequence === this.sequence) this.clear("UNAVAILABLE");
    }
  }
}
