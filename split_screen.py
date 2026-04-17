import sys
import json
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineSettings,
    QWebEngineScript,
    QWebEngineProfile,
    QWebEnginePage,
)
from PyQt6.QtCore import QUrl, Qt, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence

CONFIG_FILE = Path(__file__).parent / "config.json"

# Default config with new settings
DEFAULT_CONFIG = {
    "left_url": "https://example.com",
    "right_url": "https://example.com",
    "auto_reload_interval": 60,  # seconds between health checks
    "max_reload_attempts": 3,    # max consecutive reloads before giving up temporarily
}


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        print(f"Created default config at {CONFIG_FILE} — edit it to set your URLs and reload settings.")
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    # Merge defaults for any missing keys
    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
    return config


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
    
    # Store the intended URL for reloads
    view.setProperty("intended_url", url)
    view.setProperty("reload_count", 0)
    
    view.load(QUrl(url))
    return view


class SplitScreenWindow(QMainWindow):
    def __init__(self, left_url: str, right_url: str, auto_reload_interval: int = 60, max_reloads: int = 3):
        super().__init__()
        self.auto_reload_interval = auto_reload_interval
        self.max_reloads = max_reloads
        self.left_url = left_url
        self.right_url = right_url

        central = QWidget()
        self.setCentralWidget(central)

        screen = QApplication.primaryScreen().geometry()
        portrait = screen.height() > screen.width()
        layout = QVBoxLayout(central) if portrait else QHBoxLayout(central)
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

        self.left_view = make_view(left_url, left_profile)
        self.right_view = make_view(right_url, right_profile)

        layout.addWidget(self.left_view, stretch=1)
        layout.addWidget(self.right_view, stretch=1)

        self._setup_reload_handlers()
        self._setup_health_check()

        # Manual reload shortcut
        QShortcut(QKeySequence("Ctrl+R"), self, self._reload_all)
        QShortcut(QKeySequence("Escape"), self, self.close)

        self.showFullScreen()

    def _setup_reload_handlers(self):
        """Connect loadFinished signals to auto-reload on failure."""
        for view in [self.left_view, self.right_view]:
            view.page().loadFinished.connect(
                lambda ok, v=view: self._on_load_finished(v, ok)
            )

    def _on_load_finished(self, view: QWebEngineView, success: bool):
        """Handle page load completion - reload on failure."""
        if success:
            # Reset reload counter on successful load
            view.setProperty("reload_count", 0)
            return

        # Load failed - increment counter and reload if under limit
        reload_count = view.property("reload_count") or 0
        
        if reload_count < self.max_reloads:
            view.setProperty("reload_count", reload_count + 1)
            url = view.property("intended_url")
            print(f"Reload attempt {reload_count + 1}/{self.max_reloads} for {url}")
            view.load(QUrl(url))
        else:
            print(f"Max reload attempts reached for {view.property('intended_url')}, will retry on next health check")

    def _setup_health_check(self):
        """Set up periodic health check timer."""
        self.health_timer = QTimer(self)
        self.health_timer.timeout.connect(self._check_health)
        self.health_timer.start(self.auto_reload_interval * 1000)  # Convert to ms

    def _check_health(self):
        """Periodically check if pages need reloading."""
        for view in [self.left_view, self.right_view]:
            self._check_view_health(view)

    def _check_view_health(self, view: QWebEngineView):
        """Check a single view's health and reload if needed."""
        # Run JavaScript to detect blank/error pages
        view.page().runJavaScript(r"""
            (function() {
                var body = document.body;
                if (!body) return { blank: true, title: '' };
                
                var bgColor = window.getComputedStyle(body).backgroundColor;
                var isWhiteBg = /rgba?\(255,\s*255,\s*255/.test(bgColor) || 
                               /transparent/.test(bgColor);
                
                var hasContent = body.textContent.trim().length > 0 ||
                                body.querySelectorAll('iframe, img, video, svg').length > 0;
                
                var title = document.title || '';
                
                var textContent = body.textContent.toLowerCase();
                
                // Check for common error page indicators
                var isErrorPage = title.toLowerCase().includes('error') ||
                                  title.toLowerCase().includes('problem') ||
                                  title.toLowerCase().includes('404') ||
                                  title.toLowerCase().includes('500') ||
                                  textContent.includes('cannot connect') ||
                                  textContent.includes('connection refused') ||
                                  textContent.includes('connection reset');
                
                return {
                    blank: isWhiteBg && !hasContent,
                    title: title,
                    isError: isErrorPage,
                    url: window.location.href
                };
            })();
        """, self._handle_health_result(view))

    def _handle_health_result(self, view: QWebEngineView):
        """Handle the result of the health check JavaScript."""
        def callback(result):
            if isinstance(result, dict):
                if result.get("blank") or result.get("isError"):
                    reload_count = view.property("reload_count") or 0
                    if reload_count < self.max_reloads:
                        view.setProperty("reload_count", reload_count + 1)
                        url = view.property("intended_url")
                        print(f"Health check: Reloading blank/error page. URL: {url}, Current: {result.get('url')}, Title: {result.get('title')}")
                        view.load(QUrl(url))
                    else:
                        print(f"Health check: Skipping reload (max attempts). Title: {result.get('title')}")
            elif not result:  # JavaScript might fail on blank pages
                # If we can't even run JS, it's definitely a blank/error page
                reload_count = view.property("reload_count") or 0
                if reload_count < self.max_reloads:
                    view.setProperty("reload_count", reload_count + 1)
                    url = view.property("intended_url")
                    print(f"Health check: Reloading unresponsive page at {url}")
                    view.load(QUrl(url))
        
        return callback

    def _reload_all(self):
        """Manually reload both views."""
        print("Manual reload triggered")
        for view in [self.left_view, self.right_view]:
            view.setProperty("reload_count", 0)
            url = view.property("intended_url")
            view.load(QUrl(url))


def main():
    config = load_config()
    app = QApplication(sys.argv)
    app.setApplicationName("SplitScreen")
    window = SplitScreenWindow(
        config["left_url"],
        config["right_url"],
        auto_reload_interval=config["auto_reload_interval"],
        max_reloads=config["max_reload_attempts"],
    )
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
