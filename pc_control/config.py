"""Central configuration and constants."""

import ctypes
import sys
from pathlib import Path

# DPI awareness — must be set before any GUI operations
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor V2
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
RECORDINGS_DIR = PROJECT_ROOT / "recordings"
BROWSER_STATE_DIR = PROJECT_ROOT / ".browser"
BROWSER_STATE_FILE = BROWSER_STATE_DIR / "session.json"
BROWSER_USER_DATA = BROWSER_STATE_DIR / "chrome-profile"
SCRIPTS_DIR = Path(__file__).parent / "scripts"

# Browser
DEFAULT_CDP_PORT = 9222

# Screenshots
SCREENSHOT_FORMAT = "png"
SCREENSHOT_QUALITY = 85  # for jpeg

CHAT_STATE_DIR = PROJECT_ROOT / ".chat"
API_CONFIG_DIR = PROJECT_ROOT / ".api"
VISION_DIR = PROJECT_ROOT / "vision_output"

# Ensure directories exist
SCREENSHOTS_DIR.mkdir(exist_ok=True)
RECORDINGS_DIR.mkdir(exist_ok=True)
BROWSER_STATE_DIR.mkdir(exist_ok=True)
CHAT_STATE_DIR.mkdir(exist_ok=True)
API_CONFIG_DIR.mkdir(exist_ok=True)
VISION_DIR.mkdir(exist_ok=True)
