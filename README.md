# pc-control

[![CI](https://github.com/Matiasxth/pc-control/actions/workflows/ci.yml/badge.svg)](https://github.com/Matiasxth/pc-control/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](pyproject.toml)
[![Platform](https://img.shields.io/badge/platform-windows-blue)](README.md#requirements)
[![Release](https://img.shields.io/github/v/release/Matiasxth/pc-control?include_prereleases&sort=semver)](https://github.com/Matiasxth/pc-control/releases)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Python CLI toolkit to fully control a Windows PC — screen, input, windows, browser, desktop apps, vision, OCR, messaging, and workflows.

Built for AI agents that need a single, JSON-out-first interface to drive a real machine.

## Features

| Module | What it does |
|---|---|
| `screen` | Screenshots (full / region / window) and text-based screen summaries |
| `input` | Mouse (click, drag, scroll, smooth, draw) and keyboard (type, key, hotkey) |
| `windows` | List, focus, resize, move, snap, save/restore layouts |
| `browser` | Persistent Chromium (Playwright + CDP), navigate, interact, eval JS, record & replay |
| `desktop` | UI automation via pywinauto (no screenshots needed) — inspect, click, type, select |
| `vision` | Image diff, find-text, find-image, element detection (OpenCV + OCR) |
| `system` | CPU/RAM/disk info, process list, kill by pid/name |
| `clipboard` | Get, set, clear |
| `ocr` | Windows.Media.Ocr — file or live screen region |
| `chat whatsapp` | WhatsApp Web via persistent Playwright session + MutationObserver |
| `api telegram` / `email` / `webhook` | Bot API, SMTP/IMAP, inbound HTTP webhooks |
| `workflow` | Chain commands into repeatable flows |

## Requirements

- Windows 10 or 11
- Python 3.10+
- Chromium (auto-installed by Playwright)

## Install

```bash
git clone https://github.com/Matiasxth/pc-control.git
cd pc-control
pip install -e ".[all]"
python -m playwright install chromium
```

Install only the features you need via extras: `[browser]`, `[desktop]`, `[vision]`, `[ocr]`, or `[all]`.

After install, either invocation works:

```bash
pc-control <module> <command> [args]       # via entry point
python -m pc_control <module> <command>    # via module
```

## Quickstart

Every command prints JSON to stdout with a `status` field — easy to pipe into other tools or consume from an agent.

```bash
# Screen
python -m pc_control screen shot --output out.png
python -m pc_control screen context            # text summary, no image

# Input
python -m pc_control input click 500 300
python -m pc_control input type "hello world"
python -m pc_control input hotkey ctrl c

# Windows
python -m pc_control windows list
python -m pc_control windows focus "Visual Studio Code"
python -m pc_control windows snap "Chrome" left

# Browser (persistent — survives across CLI calls)
python -m pc_control browser start
python -m pc_control browser goto https://example.com
python -m pc_control browser text h1
python -m pc_control browser fill "input[name=q]" "search term"

# Desktop app automation (no screenshots)
python -m pc_control desktop scan spotify --type Button
python -m pc_control desktop click spotify --name Play

# System
python -m pc_control system processes --sort memory --limit 10
python -m pc_control clipboard set "copied text"

# OCR
python -m pc_control ocr screen --region 0,0,800,600
```

Full command reference: run `python -m pc_control --help` (or `<module> --help`).

## Design

- **JSON out, always.** Every command prints a single JSON object — no banners, no prompts.
- **Persistent daemons** where it matters. The browser, WhatsApp, and desktop backends run as background processes so subsequent CLI calls are fast and stateful.
- **State is per-user**, not per-repo. Runtime state lives under hidden dirs (`.browser/`, `.chat/`, etc.) and is git-ignored.
- **No surprises.** No telemetry, no network calls beyond what each module explicitly does (e.g. browser navigation, Telegram API).

## License

MIT — see [LICENSE](LICENSE).

## Status

Early-stage but usable. Contributions welcome — start with [CONTRIBUTING.md](CONTRIBUTING.md) and the open issues.
