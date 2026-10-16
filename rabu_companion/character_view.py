import base64
import logging
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QObject, QPoint, Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineView,
)
from PyQt5.QtWidgets import QWidget

from .storage import get_data_dir


CHARACTER_PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    :root, html, body, main, model-viewer {
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
      background: transparent !important;
    }
    model-viewer {
      display: block;
      --poster-color: transparent;
      --progress-bar-color: transparent;
    }
  </style>
  <script type="module"
    src="https://unpkg.com/@google/model-viewer@1.12.0/dist/model-viewer.min.js"></script>
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
</head>
<body>
  <main>
    <model-viewer
      src="data:model/gltf-binary;base64,__RABU_MODEL_BASE64__"
      alt="Rabu, your desktop companion"
      autoplay
      animation-name="Idle"
      camera-controls
      interaction-prompt="none"
      shadow-intensity="0"
      exposure="1.1">
    </model-viewer>
  </main>
  <script>
    const character = document.querySelector("model-viewer");
    let companion;
    let greetingTimer;
    let pointerOrigin;
    let dragged = false;

    new QWebChannel(qt.webChannelTransport, (channel) => {
      companion = channel.objects.companion;
    });

    character.addEventListener("pointerdown", (event) => {
      pointerOrigin = {x: event.clientX, y: event.clientY};
      dragged = false;
    });
    character.addEventListener("pointermove", (event) => {
      if (pointerOrigin) {
        dragged = dragged || Math.hypot(
          event.clientX - pointerOrigin.x,
          event.clientY - pointerOrigin.y,
        ) > 6;
      }
    });
    character.addEventListener("pointerup", () => {
      pointerOrigin = undefined;
    });

    function playAnimation(name) {
      customElements.whenDefined("model-viewer").then(() => {
        window.clearTimeout(greetingTimer);
        character.animationName = name;
        character.currentTime = 0;
        character.play();
        if (name === "Wave") {
          greetingTimer = window.setTimeout(() => playAnimation("Idle"), 1500);
        }
      });
    }

    character.addEventListener("click", () => {
      if (companion && !dragged) {
        companion.greet();
      }
      dragged = false;
    });

    character.addEventListener("error", () => {
      if (companion) {
        companion.reportError("The Rabu GLB model could not be loaded.");
      }
    });
  </script>
</body>
</html>
"""


logger = logging.getLogger(__name__)


class _CompanionBridge(QObject):
    greeting_requested = pyqtSignal()

    @pyqtSlot(str)
    def reportError(self, message: str) -> None:
        logger.error("Character viewer: %s", message)

    @pyqtSlot()
    def greet(self) -> None:
        self.greeting_requested.emit()


class _CharacterPage(QWebEnginePage):
    def __init__(self, profile: QWebEngineProfile, parent: QWidget):
        super().__init__(profile, parent)

    def javaScriptConsoleMessage(
        self,
        level: QWebEnginePage.JavaScriptConsoleMessageLevel,
        message: str,
        line_number: int,
        source_id: str,
    ) -> None:
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            logger.error(
                "Character viewer JavaScript error in %s at line %s: %s",
                source_id,
                line_number,
                message,
            )


class CharacterView(QWebEngineView):
    context_menu_requested = pyqtSignal(QPoint)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent; border: none;")
        webengine_dir = get_data_dir() / "webengine"
        cache_dir = webengine_dir / "cache"
        storage_dir = webengine_dir / "storage"
        cache_dir.mkdir(parents=True, exist_ok=True)
        storage_dir.mkdir(parents=True, exist_ok=True)
        self.profile = QWebEngineProfile("Rabu", self)
        self.profile.setCachePath(str(cache_dir))
        self.profile.setPersistentStoragePath(str(storage_dir))
        self.setPage(_CharacterPage(self.profile, self))
        self.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self.bridge = _CompanionBridge(self)
        self.channel = QWebChannel(self.page())
        self.channel.registerObject("companion", self.bridge)
        self.page().setWebChannel(self.channel)
        self._drag_offset: QPoint | None = None
        self._page_loaded = False
        self._pending_animation = "Idle"
        self.loadFinished.connect(self._report_load_result)

    def load_character(self) -> None:
        model_path = Path(__file__).resolve().parent / "assets" / "rabu.glb"
        try:
            model_data = base64.b64encode(model_path.read_bytes()).decode("ascii")
        except OSError:
            logger.exception("Could not read the Rabu character model at %s", model_path)
            return
        self.setHtml(
            CHARACTER_PAGE.replace("__RABU_MODEL_BASE64__", model_data),
            self._project_base_url(),
        )

    def _report_load_result(self, success: bool) -> None:
        if not success:
            logger.error("The embedded character page failed to load.")
            return
        self._page_loaded = True
        self._run_animation(self._pending_animation)

    @staticmethod
    def _project_base_url():
        return QUrl("https://rabu.local/")

    def set_animation(self, name: str) -> None:
        if name not in {"Idle", "Wave", "Explain", "Point", "Think"}:
            raise ValueError(f"Unsupported character animation: {name}")
        self._pending_animation = name
        if self._page_loaded:
            self._run_animation(name)

    def _run_animation(self, name: str) -> None:
        self.page().runJavaScript(f"playAnimation({name!r})")

    def contextMenuEvent(self, event: Any) -> None:
        self.context_menu_requested.emit(event.globalPos())
        event.accept()

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier:
            self._drag_offset = event.globalPos() - self.window().frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPos() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        if event.button() == Qt.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            event.accept()
            return
        super().mouseReleaseEvent(event)
