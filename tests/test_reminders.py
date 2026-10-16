import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from rabu_companion.reminders import Reminder, ReminderManager
from rabu_companion.storage import get_data_dir


class ReminderPersistenceTests(unittest.TestCase):
    def test_reminders_and_completion_survive_reopening_the_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "rabu.sqlite3"
            reminder_time = datetime.now() + timedelta(hours=1)
            reminder = Reminder("Review the notes", reminder_time)

            manager = ReminderManager(database_path)
            manager.add_reminder(reminder)
            saved_id = reminder.id
            manager.mark_completed(reminder)

            reopened_manager = ReminderManager(database_path)
            self.assertEqual(len(reopened_manager._reminders), 1)
            restored = reopened_manager._reminders[0]
            self.assertEqual(restored.id, saved_id)
            self.assertEqual(restored.message, "Review the notes")
            self.assertEqual(restored.time, reminder_time)
            self.assertTrue(restored.completed)
            self.assertEqual(restored.completed_at, reminder.completed_at)

    def test_due_and_upcoming_queries_work_with_persisted_records(self):
        with tempfile.TemporaryDirectory() as directory:
            now = datetime.now()
            manager = ReminderManager(Path(directory) / "rabu.sqlite3")
            manager.add_reminder(Reminder("Due now", now - timedelta(minutes=1)))
            upcoming = Reminder("Coming up", now + timedelta(minutes=5))
            manager.add_reminder(upcoming)

            self.assertEqual(
                [reminder.message for reminder in manager.get_due_reminders(now)],
                ["Due now"],
            )
            self.assertEqual(manager.next_upcoming(now).message, "Coming up")

    def test_data_directory_can_be_configured_for_drive_e(self):
        with tempfile.TemporaryDirectory() as directory:
            data_directory = Path(directory) / "Rabu" / "data"
            with patch.dict(
                os.environ, {"RABU_DATA_DIR": str(data_directory)}
            ):
                self.assertEqual(get_data_dir(), data_directory.resolve())
            self.assertTrue(data_directory.is_dir())


if __name__ == "__main__":
    unittest.main()
