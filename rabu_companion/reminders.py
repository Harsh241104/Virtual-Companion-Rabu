from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional


@dataclass
class Reminder:
    """
    Simple in-memory reminder.
    In future versions this can be extended to support persistence,
    calendar sync, etc.
    """

    message: str
    time: datetime
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class ReminderManager:
    """
    Manages reminders and exposes small helper methods so other modules
    (e.g. emotion logic) can query state without knowing implementation details.
    """

    def __init__(self):
        self._reminders: List[Reminder] = []

    # ---------- CRUD ----------

    def add_reminder(self, reminder: Reminder) -> None:
        self._reminders.append(reminder)

    def mark_completed(self, reminder: Reminder) -> None:
        reminder.completed = True
        reminder.completed_at = datetime.now()

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

