from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .storage import get_data_dir


@dataclass
class Reminder:
    message: str
    time: datetime
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    id: Optional[int] = field(default=None, repr=False)


class ReminderManager:
    """Store reminders in SQLite and expose queries for the companion UI."""

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = (
            Path(database_path).expanduser().resolve() if database_path is not None
            else get_data_dir() / "rabu.sqlite3"
        )
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()
        self._reminders = self._load_reminders()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT NOT NULL CHECK (length(trim(message)) > 0),
                    reminder_time TEXT NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminders_time_completed "
                "ON reminders (completed, reminder_time)"
            )

    def _load_reminders(self) -> List[Reminder]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, message, reminder_time, completed, created_at, completed_at
                FROM reminders
                ORDER BY id
                """
            ).fetchall()
        return [
            Reminder(
                message=row[1],
                time=datetime.fromisoformat(row[2]),
                completed=bool(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                completed_at=(
                    datetime.fromisoformat(row[5]) if row[5] is not None else None
                ),
                id=row[0],
            )
            for row in rows
        ]

    # ---------- CRUD ----------

    def add_reminder(self, reminder: Reminder) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO reminders
                    (message, reminder_time, completed, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    reminder.message,
                    reminder.time.isoformat(),
                    int(reminder.completed),
                    reminder.created_at.isoformat(),
                    reminder.completed_at.isoformat()
                    if reminder.completed_at is not None else None,
                ),
            )
            reminder.id = cursor.lastrowid
        self._reminders.append(reminder)

    def mark_completed(self, reminder: Reminder) -> None:
        if reminder.id is None:
            raise ValueError("Cannot complete a reminder that has not been saved")
        completed_at = datetime.now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE reminders SET completed = 1, completed_at = ?
                WHERE id = ?
                """,
                (completed_at.isoformat(), reminder.id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Reminder {reminder.id} no longer exists")
        reminder.completed = True
        reminder.completed_at = completed_at

    # ---------- Queries ----------

    def get_due_reminders(self, now: datetime) -> List[Reminder]:
        """
        Return reminders that are due now or overdue and not yet completed.
        """
        return [
            r
            for r in self._reminders
            if not r.completed and r.time <= now
        ]

    def next_upcoming(self, now: datetime) -> Optional[Reminder]:
        """
        Get the next upcoming, not yet completed reminder after now.
        """
        upcoming = [r for r in self._reminders if not r.completed and r.time > now]
        if not upcoming:
            return None
        return min(upcoming, key=lambda r: r.time)

    def had_recent_completion(self, now: datetime, window_minutes: int = 10) -> bool:
        """
        Have we completed any reminders in the last N minutes?
        """
        window = timedelta(minutes=window_minutes)
        for r in self._reminders:
            if r.completed and r.completed_at is not None:
                if now - r.completed_at <= window:
                    return True
        return False
