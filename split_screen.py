import sys
import json
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineScript, QWebEngineProfile, QWebEnginePage
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QShortcut, QKeySequence

CONFIG_FILE = Path(__file__).parent / "config.json"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        default = {
            "left_url": "https://example.com",
            "right_url": "https://example.com",
        }
        CONFIG_FILE.write_text(json.dumps(default, indent=2))
        print(f"Created default config at {CONFIG_FILE} — edit it to set your URLs.")
        return default
    with open(CONFIG_FILE) as f:
        return json.load(f)


NO_SCROLLBAR_CSS = """
(function() {
    var style = document.createElement('style');
    style.textContent = '::-webkit-scrollbar { display: none; } * { scrollbar-width: none; }';
    document.documentElement.appendChild(style);
})();
"""


def _add_no_scrollbar_script(page: QWebEnginePage) -> None:
    script = QWebEngineScript()
    script.setName("no-scrollbar")
    script.setSourceCode(NO_SCROLLBAR_CSS)
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
    script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    script.setRunsOnSubFrames(True)
    page.scripts().insert(script)


def make_view(url: str, profile: QWebEngineProfile | None = None) -> QWebEngineView:
    view = QWebEngineView()
    if profile is not None:
        page = QWebEnginePage(profile, view)
        view.setPage(page)
    settings = view.settings()
    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
    view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
    _add_no_scrollbar_script(view.page())
    view.load(QUrl(url))
    return view


class SplitScreenWindow(QMainWindow):
    def __init__(self, left_url: str, right_url: str):
        super().__init__()

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        left_profile = QWebEngineProfile("left", self)
        left_profile.setPersistentStoragePath(str(Path(__file__).parent / "profiles" / "left"))
        left_profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        right_profile = QWebEngineProfile("right", self)
        right_profile.setPersistentStoragePath(str(Path(__file__).parent / "profiles" / "right"))
        right_profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        layout.addWidget(make_view(left_url, left_profile), stretch=1)
        layout.addWidget(make_view(right_url, right_profile), stretch=1)

        QShortcut(QKeySequence("Escape"), self, self.close)

        self.showFullScreen()


def main():
    config = load_config()
    app = QApplication(sys.argv)
    app.setApplicationName("SplitScreen")
    _window = SplitScreenWindow(config["left_url"], config["right_url"])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
