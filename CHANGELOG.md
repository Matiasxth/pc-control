# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-04-24

First public release on GitHub.

### Added

- **Core CLI** — `python -m pc_control` / `pc-control` — with 14 top-level modules:
  - `screen` — screenshots (full, region, window) + text-based screen context summary
  - `input` — mouse (click, drag, scroll, smooth, draw) and keyboard (type, key, hotkey)
  - `windows` — list, focus, resize, move, snap, save/restore layouts
  - `browser` — persistent Chromium via Playwright + CDP; navigate, click, fill, eval, screenshot, record & replay
  - `desktop` — UI automation via pywinauto (no screenshots needed)
  - `vision` — image diff, find-text, find-image, element detection
  - `system` — CPU/RAM/disk info, process list, kill
  - `clipboard` — get, set, clear
  - `ocr` — Windows.Media.Ocr file or live screen region
  - `chat whatsapp` — WhatsApp Web via persistent Playwright session
  - `api` — Telegram, email (SMTP/IMAP), inbound webhooks
  - `audio` — volume and mute control
  - `app` — application launcher
  - `workflow` — predefined action sequences
- **Packaging** — PEP 621 `pyproject.toml` with extras: `[browser]`, `[desktop]`, `[vision]`, `[ocr]`, `[all]`, `[dev]`
- **Entry point** — `pc-control` console script → `pc_control.cli:main`
- **CI** — GitHub Actions running ruff (lint + format), compileall, and pytest on Windows matrix (py3.10 / 3.11 / 3.12)
- **Tests** — 43 smoke tests covering CLI parser structure and module imports, with automatic skipping when optional deps are missing
- **Docs** — README with feature table and quickstart, CONTRIBUTING with design contract, examples/ with 5 runnable demo scripts, issue and PR templates
- **License** — MIT

[Unreleased]: https://github.com/Matiasxth/pc-control/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Matiasxth/pc-control/releases/tag/v0.1.0
