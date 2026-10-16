from __future__ import annotations

from datetime import datetime
from enum import Enum

from .reminders import ReminderManager


class Emotion(str, Enum):
    HAPPY = "happy"
    CALM = "calm"
    CONCERNED = "concerned"


class EmotionEngine:
    """
    Very simple rule-based emotion logic.

    This is intentionally minimal but structured so you can later:
      - Swap rules for a learned model
      - Add more nuanced emotional states
      - Incorporate user mood / calendar load / recent interactions
    """

    def infer_emotion(self, reminders: ReminderManager) -> Emotion:
        now = datetime.now()

        # 1. If a reminder was recently completed, Rabu is happy.
        if reminders.had_recent_completion(now, window_minutes=10):
            return Emotion.HAPPY

        # 2. If a reminder is approaching soon, Rabu is gently concerned.
        next_upcoming = reminders.next_upcoming(now)
        if next_upcoming is not None:
            seconds_until = (next_upcoming.time - now).total_seconds()

            # Within the next 15 minutes: concerned.
            if 0 <= seconds_until <= 15 * 60:
                return Emotion.CONCERNED

        # 3. Otherwise: calm neutral state.
        return Emotion.CALM
