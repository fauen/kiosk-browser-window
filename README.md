# kiosk-browser-window

A Python kiosk application that displays two browser windows side-by-side in fullscreen. Built as a collaboration between Daniel Backman and Mistral Vibe.

## Features

- Two web views displayed side-by-side, each taking half the screen
- Launches in fullscreen automatically
- Press **Escape** to quit, **Ctrl+R** to reload both panes
- Scrollbars hidden in both views
- Both panes use separate persistent browser profiles (cookies and local storage survive restarts)
- No context menu
- **Auto-reload on connection failure** - automatically retries failed page loads
- **Periodic health checks** - detects blank or error pages and reloads them

## Requirements

```
pip install -r requirements.txt
```

Requires Python 3 and:
- `PyQt6`
- `PyQt6-WebEngine`

## Configuration

On first run, a `config.json` is auto-created with default settings. Edit it to configure your URLs and reload behavior:

```json
{
  "left_url": "https://example.com",
  "right_url": "https://example.com",
  "auto_reload_interval": 60,
  "max_reload_attempts": 3
}
```

| Option | Description | Default |
|--------|-------------|---------|
| `left_url` | URL for the left pane | `https://example.com` |
| `right_url` | URL for the right pane | `https://example.com` |
| `auto_reload_interval` | Seconds between health checks | `60` |
| `max_reload_attempts` | Maximum consecutive reload attempts per check cycle | `3` |

## Usage

```
python split_screen.py
```

## How Auto-Reload Works

1. **Immediate retry**: If a page fails to load (connection error, timeout), it automatically retries up to `max_reload_attempts` times
2. **Periodic health check**: Every `auto_reload_interval` seconds, each pane is checked for:
   - Blank/white pages
   - Error pages (404, 500, "connection refused", etc.)
3. **Manual reload**: Press **Ctrl+R** to force reload both panes at any time
