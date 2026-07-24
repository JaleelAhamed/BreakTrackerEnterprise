"""
app_paths.py
============

Break Tracker Enterprise
Centralized Application Data Path Helper

Provides a single source of truth for where Break Tracker Enterprise
stores its persistent runtime data (configuration, employee profile,
logs, and reports).

Why this module exists
-----------------------
When the application is packaged with PyInstaller in --onefile mode,
the running executable's own directory is a temporary extraction
folder (``_MEIxxxxx``) that PyInstaller deletes after the process
exits. Any file previously written next to the executable
(config.json, logs/, reports/) was therefore lost on every relaunch:

    * Employee profile lost every launch
    * Logs not persistent
    * Reports saved inside Temp
    * Config changes not persistent
    * Settings window sometimes unable to locate files

This module fixes that by resolving all persistent storage to a
standard, per-user Windows application-data folder that lives outside
the PyInstaller extraction folder and survives across launches:

    %LOCALAPPDATA%\\BreakTrackerEnterprise

That folder - and its standard children (config.json, employee.json,
logs/, reports/) - is created automatically the first time this
module is used. Every other module that needs one of these paths
imports it from here rather than building its own
``Path(__file__).parent``-based path, which is what tied storage to
the executable/extraction directory in the first place.

Public API
----------
get_app_data_dir() -> Path
    Returns %LOCALAPPDATA%\\BreakTrackerEnterprise, creating it (and
    its standard subfolders/files) if necessary. Safe to call
    repeatedly from multiple modules.

APP_DATA_DIR, CONFIG_PATH, EMPLOYEE_PATH, LOGS_DIR, REPORTS_DIR
    Pre-resolved, ready-to-use Path objects built on top of
    get_app_data_dir(), resolved once at import time.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# ============================================================
# CONFIGURATION
# ============================================================

APP_FOLDER_NAME = "BreakTrackerEnterprise"

CONFIG_FILE_NAME = "config.json"
EMPLOYEE_FILE_NAME = "employee.json"
LOGS_FOLDER_NAME = "logs"
REPORTS_FOLDER_NAME = "reports"

# Placeholder structure written to employee.json the first time the
# application data folder is created. Nothing in the application
# currently reads from this file - the employee profile continues to
# live inside config.json's "employee" section, exactly as before, so
# behaviour is unchanged. This file is scaffolded purely to satisfy
# the enterprise data folder layout (config.json, employee.json,
# logs/, reports/ all present under the app data folder).
_DEFAULT_EMPLOYEE_JSON: dict[str, Any] = {
    "name": "",
    "employee_id": "",
    "department": "",
    "designation": "",
}


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _resolve_local_appdata() -> Path:
    """
    Resolve the user's LOCALAPPDATA directory.

    Uses the LOCALAPPDATA environment variable, which is always set
    on Windows. Falls back to a POSIX-style application-data location
    only so this module doesn't hard-crash on import if it's ever
    loaded outside Windows (e.g. during local testing).
    """
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata)

    # Non-Windows fallback (development/testing only).
    return Path.home() / ".local" / "share"


# ============================================================
# PUBLIC API
# ============================================================

def get_app_data_dir() -> Path:
    """
    Return the Break Tracker Enterprise application data folder,
    creating it - and its config.json, employee.json, logs/, and
    reports/ children - if they do not already exist.

    Idempotent: safe to call repeatedly and from multiple modules.
    It only ever fills in what's missing and never overwrites an
    existing file.
    """
    app_dir = _resolve_local_appdata() / APP_FOLDER_NAME
    app_dir.mkdir(parents=True, exist_ok=True)

    (app_dir / LOGS_FOLDER_NAME).mkdir(parents=True, exist_ok=True)
    (app_dir / REPORTS_FOLDER_NAME).mkdir(parents=True, exist_ok=True)

    employee_path = app_dir / EMPLOYEE_FILE_NAME
    if not employee_path.exists():
        with employee_path.open("w", encoding="utf-8") as handle:
            json.dump(_DEFAULT_EMPLOYEE_JSON, handle, indent=4)

    # config.json is intentionally NOT created here. ConfigManager
    # (employee.py) already owns creating config.json with the full
    # DEFAULT_CONFIG structure the first time the application runs,
    # and remains the single source of truth for that file's
    # contents/schema - this module only decides *where* it lives.

    return app_dir


# ============================================================
# PRE-RESOLVED PATHS
# ============================================================
#
# Resolved once at import time so every module shares the same Path
# objects (and the folder structure is guaranteed to exist) without
# recomputing it on every access.

APP_DATA_DIR: Path = get_app_data_dir()
CONFIG_PATH: Path = APP_DATA_DIR / CONFIG_FILE_NAME
EMPLOYEE_PATH: Path = APP_DATA_DIR / EMPLOYEE_FILE_NAME
LOGS_DIR: Path = APP_DATA_DIR / LOGS_FOLDER_NAME
REPORTS_DIR: Path = APP_DATA_DIR / REPORTS_FOLDER_NAME


if __name__ == "__main__":
    print("Application data folder:", APP_DATA_DIR)
    print("Config path:            ", CONFIG_PATH)
    print("Employee path:          ", EMPLOYEE_PATH)
    print("Logs folder:            ", LOGS_DIR)
    print("Reports folder:         ", REPORTS_DIR)
    