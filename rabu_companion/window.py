from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QMenu,
    QAction,
    QMessageBox,
    QInputDialog,
    QSizePolicy,
)

from .character_view import CharacterView
from .emotions import Emotion, EmotionEngine
from .reminders import Reminder, ReminderManager
from .speech import SpeechEngine


WINDOW_W = 280
WINDOW_H = 320


class RabuWindow(QWidget):
    """
    Transparent, always-on-top desktop companion with an animated 3D model.
    """

    def __init__(self):
        super().__init__()

        self.speech = SpeechEngine()
        self.reminders = ReminderManager()
        self.emotion_engine = EmotionEngine()
        self._current_emotion = Emotion.CALM

        self._setup_window()
        self._setup_ui()
        self._setup_timers()

    # ---------- Setup ----------

    def _setup_window(self):
        self.setWindowTitle("Rabu")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(WINDOW_W, WINDOW_H)

        screen = self.screen() or (self.windowHandle().screen() if self.windowHandle() else None)
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.right() - self.width() - 28
            y = geometry.bottom() - self.height() - 36
            self.move(x, y)

    def _setup_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.bubble = QLabel("")
        self.bubble.setWordWrap(True)
        self.bubble.setAlignment(Qt.AlignCenter)
        self.bubble.setVisible(False)
        self.bubble.setStyleSheet(
            """
            QLabel {
                background: rgba(255, 255, 255, 230);
                color: #1b2430;
                border-radius: 12px;
                padding: 8px 10px;
                font-size: 12px;
            }
            """
        )

        root.addWidget(self.bubble)
        self.character_view = CharacterView(self)
        self.character_view.setMinimumSize(1, 1)
        self.character_view.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.character_view.bridge.greeting_requested.connect(
            self._handle_left_click_greeting
        )
        self.character_view.context_menu_requested.connect(self._show_context_menu)
        root.addWidget(self.character_view)
        self.setLayout(root)

        self.character_view.load_character()
        self._update_emotion_visual(Emotion.CALM)

    def _setup_timers(self):
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self._check_reminders)
        self.reminder_timer.start(1000)

        self.emotion_timer = QTimer(self)
        self.emotion_timer.timeout.connect(self._update_emotion_from_state)
        self.emotion_timer.start(4000)

        self.bubble_timer = QTimer(self)
        self.bubble_timer.setSingleShot(True)
        self.bubble_timer.timeout.connect(lambda: self.bubble.setVisible(False))

    # ---------- Character / Emotion Handling ----------

    def _update_emotion_visual(self, emotion: Emotion):
        self._current_emotion = emotion
        self.character_view.set_animation(
            {
                Emotion.CALM: "Idle",
                Emotion.HAPPY: "Wave",
                Emotion.CONCERNED: "Think",
            }[emotion]
        )

    def _update_emotion_from_state(self):
        emotion = self.emotion_engine.infer_emotion(self.reminders)
        if emotion != self._current_emotion:
            self._update_emotion_visual(emotion)

    def _show_bubble(self, text: str, ms: int = 3200):
        self.bubble.setText(text)
        self.bubble.setVisible(True)
        self.bubble_timer.start(ms)

    # ---------- Reminders ----------

    def _check_reminders(self):
        now = datetime.now()
        due = self.reminders.get_due_reminders(now)
        if not due:
            return

        for reminder in due:
            self._show_bubble(f"It's time: {reminder.message}", 5000)
            QMessageBox.information(
                self,
                "Rabu Reminder",
                f"Hey, it's time for:\n\n{reminder.message}",
            )
            self.speech.speak(f"Hey, it's time for your reminder: {reminder.message}")
            self.reminders.mark_completed(reminder)

        self._update_emotion_visual(Emotion.HAPPY)

    def add_reminder_via_dialog(self):
        message, ok = QInputDialog.getText(
            self,
            "Add Reminder",
            "What should I remind you about?",
        )
        if not ok or not message.strip():
            return

        time_text, ok = QInputDialog.getText(
            self,
            "Reminder Time",
            "When? (24h format, HH:MM)",
        )
        if not ok or not time_text.strip():
            return

        try:
            hour_str, minute_str = time_text.split(":")
            hour = int(hour_str)
            minute = int(minute_str)
            now = datetime.now()
            reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if reminder_time <= now:
                reminder_time = reminder_time + timedelta(days=1)
        except Exception:
            QMessageBox.warning(
                self,
                "Invalid Time",
                "Please enter time in HH:MM 24-hour format, for example: 14:30",
            )
            return

        reminder = Reminder(message=message.strip(), time=reminder_time)
        self.reminders.add_reminder(reminder)

        confirm = (
            f"Okay! I will remind you about {reminder.message} "
            f"at {reminder_time.strftime('%H:%M')}."
        )
        self.speech.speak(confirm)
        self._show_bubble(confirm, 4000)
        self._update_emotion_from_state()

    def contextMenuEvent(self, event):
        self._show_context_menu(event.globalPos())

    def _show_context_menu(self, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background: #1c2736;
                color: #f4fbff;
                border: 1px solid rgba(255,255,255,40);
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 18px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: #2d425c;
            }
            """
        )

        add_reminder_action = QAction("Add reminder", self)
        add_reminder_action.triggered.connect(self.add_reminder_via_dialog)
        menu.addAction(add_reminder_action)

        exit_action = QAction("Exit Rabu", self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

        menu.exec_(global_pos)

    def _handle_left_click_greeting(self):
        text = "Hi, I'm Rabu. I'm here to keep you company and remind you gently."
        self._show_bubble(text)
        self.speech.speak(text)
        self.character_view.set_animation("Wave")
