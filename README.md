# kiosk-browser-window

A Python kiosk application that displays two browser windows side-by-side in fullscreen. Built as a collaboration between Daniel Backman and Claude (Anthropic).

## Features

- Two web views displayed side-by-side, each taking half the screen
- Launches in fullscreen automatically
- Press **Escape** to quit
- Scrollbars hidden in both views
- Both panes use separate persistent browser profiles (cookies and local storage survive restarts)
- No context menu

## Requirements

```
pip install -r requirements.txt
```

Requires Python 3 and:
- `PyQt6`
- `PyQt6-WebEngine`

## Configuration

On first run, a `config.json` is auto-created with placeholder URLs. Edit it to set your own:

```json
{
  "left_url": "https://example.com",
  "right_url": "https://example.com"
}
```

## Usage

```
python split_screen.py
```
