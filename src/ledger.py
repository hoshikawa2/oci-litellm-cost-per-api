from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  month TEXT NOT NULL,
  api_id TEXT NOT NULL,
  api_name TEXT,
  virtual_key_hash TEXT,
  model TEXT,
  request_id TEXT,
  prompt_tokens INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  total_tokens INTEGER NOT NULL DEFAULT 0,
  response_cost REAL NOT NULL DEFAULT 0,
  latency_ms INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'success',
  metadata_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_month_api ON llm_usage(month, api_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_llm_usage_request ON llm_usage(request_id) WHERE request_id IS NOT NULL;
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def init(self) -> None:
        with self.connect() as con:
            con.executescript(SCHEMA)

    def insert_usage(self, row: dict[str, Any]) -> None:
        keys = ','.join(row.keys())
        params = ','.join([f':{k}' for k in row.keys()])
        with self.connect() as con:
            con.execute(f'INSERT OR IGNORE INTO llm_usage ({keys}) VALUES ({params})', row)

    def monthly_usage(self, month: str) -> list[dict[str, Any]]:
        sql = """
        SELECT
          month,
          api_id,
          MAX(api_name) AS api_name,
          COUNT(*) AS requests,
          SUM(prompt_tokens) AS input_tokens,
          SUM(completion_tokens) AS output_tokens,
          SUM(total_tokens) AS total_tokens,
          SUM(response_cost) AS litellm_estimated_cost,
          AVG(latency_ms) AS avg_latency_ms
        FROM llm_usage
        WHERE month = ? AND status = 'success'
        GROUP BY month, api_id
        ORDER BY total_tokens DESC
        """
        with self.connect() as con:
            return [dict(r) for r in con.execute(sql, (month,)).fetchall()]
