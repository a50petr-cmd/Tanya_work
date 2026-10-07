from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.parser import METRIC_FIELDS, ParsedReport, normalize_name

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    employee TEXT NOT NULL,
    employee_key TEXT NOT NULL,
    report_date TEXT NOT NULL,
    meetings_ab INTEGER NOT NULL,
    stars INTEGER NOT NULL,
    passives INTEGER NOT NULL,
    pl_credit INTEGER NOT NULL,
    issues INTEGER NOT NULL,
    leasing INTEGER NOT NULL,
    salary INTEGER NOT NULL,
    te INTEGER NOT NULL,
    knk INTEGER NOT NULL,
    chkd_blago INTEGER NOT NULL,
    chkd_sberhealth INTEGER NOT NULL,
    chkd_accreds INTEGER NOT NULL,
    submitted_at TEXT NOT NULL,
    form_answer_id TEXT,
    UNIQUE(employee_key, report_date)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_setting(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row["value"])

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            conn.commit()

    def upsert_report(self, report: ParsedReport, submitted_at: datetime) -> None:
        columns = ", ".join(METRIC_FIELDS)
        placeholders = ", ".join("?" for _ in METRIC_FIELDS)
        updates = ", ".join(f"{field} = excluded.{field}" for field in METRIC_FIELDS)
        values = [report.metrics[field] for field in METRIC_FIELDS]
        sql = f"""
            INSERT INTO reports (
                employee, employee_key, report_date, {columns}, submitted_at, form_answer_id
            ) VALUES (?, ?, ?, {placeholders}, ?, ?)
            ON CONFLICT(employee_key, report_date) DO UPDATE SET
                employee = excluded.employee,
                {updates},
                submitted_at = excluded.submitted_at,
                form_answer_id = excluded.form_answer_id
        """
        with self._connect() as conn:
            conn.execute(
                sql,
                [
                    report.employee,
                    report.employee_key,
                    report.report_date.isoformat(),
                    *values,
                    submitted_at.isoformat(),
                    report.form_answer_id,
                ],
            )
            conn.commit()

    def reports_for(self, report_date: date) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reports WHERE report_date = ? ORDER BY employee COLLATE NOCASE",
                (report_date.isoformat(),),
            ).fetchall()
        return [dict(row) for row in rows]

    def missing_for(self, report_date: date, employees: tuple[str, ...]) -> list[str]:
        submitted = {row["employee_key"] for row in self.reports_for(report_date)}
        missing = []
        for name in employees:
            if normalize_name(name) not in submitted:
                missing.append(name)
        return missing
