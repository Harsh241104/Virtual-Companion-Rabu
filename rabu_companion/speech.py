import threading

import pyttsx3


class SpeechEngine:
    """
    Small wrapper around pyttsx3 for text-to-speech.

    For v1 we create a fresh engine per utterance in a background thread.
    This keeps things simple and avoids cross-thread engine issues.
    Later you could:
      - Maintain a single long-lived engine
      - Add voice selection and rate/pitch controls
      - Swap to cloud TTS for higher-quality voices
    """

    def speak(self, text: str) -> None:
        if not text:
            return

        thread = threading.Thread(target=self._speak_background, args=(text,), daemon=True)
        thread.start()

    @staticmethod
    def _speak_background(text: str) -> None:
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception:
            # Fail silently for now; in future versions this can be logged
            # or surfaced in a subtle UI notification.
            pass

