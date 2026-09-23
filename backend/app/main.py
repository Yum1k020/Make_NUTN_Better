"""本機單人使用的待辦 API；資料以 SQLite 持久保存。"""

from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TaskCreate(TaskFields):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    due_at: datetime | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    completed: bool = False


class TaskUpdate(TaskFields):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    due_at: datetime | None = None
    priority: Literal["low", "medium", "high"] | None = None
    completed: bool | None = None

    @model_validator(mode="after")
    def validate_patch(self):
        if not self.model_fields_set:
            raise ValueError("至少提供一個要修改的欄位")
        for name in self.model_fields_set - {"due_at"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} 不可為 null")
        return self


class Task(TaskCreate):
    id: str
    created_at: datetime
    updated_at: datetime


def create_app(db_path: str | Path | None = None) -> FastAPI:
    path = Path(db_path or os.environ.get(
        "PLANNER_DB_PATH", str(Path(__file__).resolve().parents[1] / "data/planner.sqlite3")
    ))

    @contextmanager
    def connection():
        db = sqlite3.connect(path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @asynccontextmanager
    async def lifespan(app):
        path.parent.mkdir(parents=True, exist_ok=True)
        with connection() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    due_at TEXT,
                    priority TEXT NOT NULL CHECK(priority IN ('low', 'medium', 'high')),
                    completed INTEGER NOT NULL CHECK(completed IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
        yield

    app = FastAPI(title="學生個人安排 API", version="0.1.0", lifespan=lifespan)

    def get_task(db, task_id):
        row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "找不到此待辦事項")
        return dict(row)

    @app.get("/api/v1/health")
    def health():
        with connection() as db:
            db.execute("SELECT count(*) FROM tasks").fetchone()
        return {"status": "ok"}

    @app.post("/api/v1/tasks", response_model=Task, status_code=201)
    def add_task(payload: TaskCreate):
        now = datetime.now(timezone.utc).isoformat()
        task = {"id": str(uuid4()), **payload.model_dump(mode="json"),
                "created_at": now, "updated_at": now}
        with connection() as db:
            db.execute("""INSERT INTO tasks
                (id, title, description, due_at, priority, completed, created_at, updated_at)
                VALUES (:id, :title, :description, :due_at, :priority, :completed,
                        :created_at, :updated_at)""", task)
            return get_task(db, task["id"])

    @app.get("/api/v1/tasks", response_model=list[Task])
    def list_tasks(completed: bool | None = None,
                   limit: int = Query(default=50, ge=1, le=200),
                   offset: int = Query(default=0, ge=0)):
        sql = "SELECT * FROM tasks"
        params = []
        if completed is not None:
            sql += " WHERE completed = ?"
            params.append(completed)
        sql += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        with connection() as db:
            return [dict(row) for row in db.execute(sql, [*params, limit, offset])]

    @app.get("/api/v1/tasks/{task_id}", response_model=Task)
    def read_task(task_id: str):
        with connection() as db:
            return get_task(db, task_id)

    @app.patch("/api/v1/tasks/{task_id}", response_model=Task)
    def update_task(task_id: str, payload: TaskUpdate):
        changes = payload.model_dump(mode="json", exclude_unset=True)
        changes["updated_at"] = datetime.now(timezone.utc).isoformat()
        # 欄位名稱僅來自已驗證的 model，資料值全部透過 SQL 參數傳入。
        assignments = ", ".join(f"{name} = ?" for name in changes)
        with connection() as db:
            get_task(db, task_id)
            db.execute(f"UPDATE tasks SET {assignments} WHERE id = ?",
                       [*changes.values(), task_id])
            return get_task(db, task_id)

    @app.delete("/api/v1/tasks/{task_id}", status_code=204)
    def delete_task(task_id: str):
        with connection() as db:
            cursor = db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if cursor.rowcount == 0:
                raise HTTPException(404, "找不到此待辦事項")
        return Response(status_code=204)

    return app


app = create_app()
