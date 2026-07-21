"""
employee.py
===========

Break Tracker Enterprise - Employee Module

Responsibilities of this module (and only these):
    * First-time employee registration (Tkinter UI)
    * Employee login (Tkinter UI)
    * Loading employee details from configuration
    * Saving the employee profile to configuration
    * Reading and writing config.json
    * Employee data validation

This module intentionally does NOT implement idle detection, session
tracking, report generation, dashboard UI, or SharePoint upload. Those
concerns belong to other modules in the application.

Author: Break Tracker Enterprise Team
Python: 3.13
"""

from __future__ import annotations

import json
import tkinter as tk
from dataclasses import dataclass, asdict, field
from pathlib import Path
from tkinter import messagebox
from typing import Any, Callable, Optional

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

APP_TITLE: str = "Break Tracker Enterprise"
CONFIG_FILE_NAME: str = "config.json"
CONFIG_PATH: Path = Path(__file__).resolve().parent / CONFIG_FILE_NAME
APP_VERSION: str = "1.0.0-alpha"

# Default structure written to disk the first time the application runs.
DEFAULT_CONFIG: dict[str, Any] = {
    "employee": {
        "name": "",
        "employee_id": "",
        "department": "",
        "designation": "",
    },
    "settings": {
        "idle_threshold": 3,
        "allowed_break_minutes": 60,
        "auto_start": True,
        "minimize_to_tray": True,
    },
    "application": {
        "registered": False,
        "version": APP_VERSION,
    },
}


# --------------------------------------------------------------------------- #
# Data Model
# --------------------------------------------------------------------------- #

@dataclass
class Employee:
    """Represents a single employee profile."""

    name: str = ""
    employee_id: str = ""
    department: str = ""
    designation: str = ""

    def is_complete(self) -> bool:
        """Return True only if every field has non-whitespace content."""
        return all(
            str(value).strip() for value in (
                self.name, self.employee_id, self.department, self.designation
            )
        )

    def to_dict(self) -> dict[str, str]:
        """Serialize the employee to a plain dict for JSON storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Employee":
        """Build an Employee instance from a dict, tolerating missing keys."""
        return cls(
            name=str(data.get("name", "")),
            employee_id=str(data.get("employee_id", "")),
            department=str(data.get("department", "")),
            designation=str(data.get("designation", "")),
        )


# --------------------------------------------------------------------------- #
# Configuration Manager
# --------------------------------------------------------------------------- #

class ConfigError(Exception):
    """Raised when config.json cannot be read or written."""


class ConfigManager:
    """
    Handles all reading/writing of config.json.

    This class is intentionally the single source of truth for
    configuration I/O so that UI code never touches the filesystem
    directly (separation of UI logic from configuration logic).
    """

    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        self._config_path: Path = config_path

    @property
    def config_path(self) -> Path:
        return self._config_path

    def ensure_config_exists(self) -> None:
        """Create config.json with default values if it is missing."""
        if not self._config_path.exists():
            self._write(DEFAULT_CONFIG)

    def load(self) -> dict[str, Any]:
        """
        Load and return the full configuration dict.

        If the file is missing or corrupted, it is (re)created with
        default values so the application can always continue running.
        """
        try:
            if not self._config_path.exists():
                self._write(DEFAULT_CONFIG)
                return json.loads(json.dumps(DEFAULT_CONFIG))

            with self._config_path.open("r", encoding="utf-8") as handle:
                data: dict[str, Any] = json.load(handle)

            return self._merge_with_defaults(data)

        except (OSError, json.JSONDecodeError) as exc:
            # Corrupted or unreadable file: fall back to defaults rather
            # than crashing the application on launch.
            raise ConfigError(f"Unable to load configuration: {exc}") from exc

    def save(self, data: dict[str, Any]) -> None:
        """Persist the given configuration dict to disk."""
        try:
            self._write(data)
        except OSError as exc:
            raise ConfigError(f"Unable to save configuration: {exc}") from exc

    def is_registered(self) -> bool:
        """Convenience check for whether registration has been completed."""
        try:
            data = self.load()
        except ConfigError:
            return False
        return bool(data.get("application", {}).get("registered", False))

    def load_employee(self) -> Employee:
        """Load and return the stored Employee profile."""
        data = self.load()
        return Employee.from_dict(data.get("employee", {}))

    def save_employee(self, employee: Employee) -> None:
        """
        Save the given Employee profile and mark registration as complete.

        Existing settings are preserved; only the "employee" and
        "application.registered" sections are updated.
        """
        data = self.load()
        data["employee"] = employee.to_dict()
        data.setdefault("application", {})["registered"] = True
        data["application"].setdefault("version", APP_VERSION)
        self.save(data)

    # -- internal helpers ---------------------------------------------- #

    def _write(self, data: dict[str, Any]) -> None:
        """Write the given dict to config.json as pretty-printed JSON."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with self._config_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4)

    @staticmethod
    def _merge_with_defaults(data: dict[str, Any]) -> dict[str, Any]:
        """
        Fill in any missing top-level/nested keys using DEFAULT_CONFIG.

        This keeps the module resilient to older or hand-edited
        config.json files that may be missing newer keys.
        """
        merged: dict[str, Any] = json.loads(json.dumps(DEFAULT_CONFIG))
        for section, section_defaults in merged.items():
            provided_section = data.get(section)
            if isinstance(provided_section, dict) and isinstance(section_defaults, dict):
                section_defaults.update(provided_section)
            elif section in data:
                merged[section] = data[section]
        return merged


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def validate_employee_fields(
    name: str, employee_id: str, department: str, designation: str
) -> Optional[str]:
    """
    Validate raw registration input.

    Returns None if valid, otherwise returns a human-readable error
    message describing the first validation failure encountered.
    """
    fields = {
        "Employee Name": name,
        "Employee ID": employee_id,
        "Department": department,
        "Designation": designation,
    }

    for field_label, value in fields.items():
        if not value or not value.strip():
            return f"{field_label} is mandatory and cannot be empty."

    return None


# --------------------------------------------------------------------------- #
# UI Helpers
# --------------------------------------------------------------------------- #

def _center_window(window: tk.Tk | tk.Toplevel, width: int, height: int) -> None:
    """Center a Tkinter window on the user's screen."""
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def _configure_fixed_window(window: tk.Tk | tk.Toplevel, width: int, height: int, title: str) -> None:
    """Apply consistent fixed-size, non-resizable, centered window settings."""
    window.title(title)
    window.resizable(False, False)
    _center_window(window, width, height)


# --------------------------------------------------------------------------- #
# Registration Window
# --------------------------------------------------------------------------- #

class RegistrationWindow:
    """
    First-time employee registration UI.

    Collects Employee Name, Employee ID, Department, and Designation,
    validates them, and persists them via ConfigManager on success.
    """

    WINDOW_WIDTH: int = 420
    WINDOW_HEIGHT: int = 360

    def __init__(
        self,
        config_manager: ConfigManager,
        on_complete: Optional[Callable[[Employee], None]] = None,
    ) -> None:
        self._config_manager = config_manager
        self._on_complete = on_complete

        self._root = tk.Tk()
        _configure_fixed_window(
            self._root, self.WINDOW_WIDTH, self.WINDOW_HEIGHT, APP_TITLE
        )

        self._name_var = tk.StringVar()
        self._employee_id_var = tk.StringVar()
        self._department_var = tk.StringVar()
        self._designation_var = tk.StringVar()

        self._build_ui()

    def run(self) -> None:
        """Start the Tkinter event loop for this window."""
        self._root.mainloop()

    # -- UI construction -------------------------------------------------- #

    def _build_ui(self) -> None:
        container = tk.Frame(self._root, padx=30, pady=20)
        container.pack(fill="both", expand=True)

        title_label = tk.Label(
            container, text=APP_TITLE, font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=(0, 4))

        subtitle_label = tk.Label(
            container, text="Employee Registration", font=("Segoe UI", 11)
        )
        subtitle_label.pack(pady=(0, 20))

        form_frame = tk.Frame(container)
        form_frame.pack(fill="x")

        self._add_form_row(form_frame, 0, "Employee Name", self._name_var)
        self._add_form_row(form_frame, 1, "Employee ID", self._employee_id_var)
        self._add_form_row(form_frame, 2, "Department", self._department_var)
        self._add_form_row(form_frame, 3, "Designation", self._designation_var)

        form_frame.columnconfigure(1, weight=1)

        save_button = tk.Button(
            container,
            text="Save & Continue",
            width=20,
            command=self._handle_save,
        )
        save_button.pack(pady=(25, 0))

    @staticmethod
    def _add_form_row(
        parent: tk.Frame, row: int, label_text: str, text_var: tk.StringVar
    ) -> None:
        """Add a consistently spaced, aligned label/entry pair."""
        label = tk.Label(parent, text=label_text, anchor="w", width=16)
        label.grid(row=row, column=0, sticky="w", pady=8)

        entry = tk.Entry(parent, textvariable=text_var)
        entry.grid(row=row, column=1, sticky="ew", pady=8)

    # -- Event handlers ---------------------------------------------------- #

    def _handle_save(self) -> None:
        name = self._name_var.get().strip()
        employee_id = self._employee_id_var.get().strip()
        department = self._department_var.get().strip()
        designation = self._designation_var.get().strip()

        error_message = validate_employee_fields(
            name, employee_id, department, designation
        )
        if error_message:
            messagebox.showerror("Validation Error", error_message)
            return

        employee = Employee(
            name=name,
            employee_id=employee_id,
            department=department,
            designation=designation,
        )

        try:
            self._config_manager.save_employee(employee)
        except ConfigError as exc:
            messagebox.showerror("Configuration Error", str(exc))
            return

        if self._on_complete:
            self._on_complete(employee)

        self._root.destroy()


# --------------------------------------------------------------------------- #
# Login Window
# --------------------------------------------------------------------------- #

class LoginWindow:
    """
    Returning-employee login UI.

    Displays the previously registered employee details (read-only)
    and provides a Login button. No re-entry of details is required.
    """

    WINDOW_WIDTH: int = 380
    WINDOW_HEIGHT: int = 320

    def __init__(
        self,
        config_manager: ConfigManager,
        on_login: Optional[Callable[[Employee], None]] = None,
    ) -> None:
        self._config_manager = config_manager
        self._on_login = on_login
        self._employee: Employee = config_manager.load_employee()

        self._root = tk.Tk()
        _configure_fixed_window(
            self._root, self.WINDOW_WIDTH, self.WINDOW_HEIGHT, APP_TITLE
        )

        self._build_ui()

    def run(self) -> None:
        """Start the Tkinter event loop for this window."""
        self._root.mainloop()

    # -- UI construction -------------------------------------------------- #

    def _build_ui(self) -> None:
        container = tk.Frame(self._root, padx=30, pady=20)
        container.pack(fill="both", expand=True)

        title_label = tk.Label(
            container, text=APP_TITLE, font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=(0, 4))

        welcome_label = tk.Label(
            container, text="Welcome Back", font=("Segoe UI", 11)
        )
        welcome_label.pack(pady=(0, 4))

        name_label = tk.Label(
            container, text=self._employee.name, font=("Segoe UI", 13, "bold")
        )
        name_label.pack(pady=(0, 20))

        details_frame = tk.Frame(container)
        details_frame.pack(fill="x")

        self._add_readonly_row(details_frame, 0, "Employee ID", self._employee.employee_id)
        self._add_readonly_row(details_frame, 1, "Department", self._employee.department)
        self._add_readonly_row(details_frame, 2, "Designation", self._employee.designation)

        details_frame.columnconfigure(1, weight=1)

        login_button = tk.Button(
            container,
            text="Login",
            width=20,
            command=self._handle_login,
        )
        login_button.pack(pady=(25, 0))

    @staticmethod
    def _add_readonly_row(parent: tk.Frame, row: int, label_text: str, value: str) -> None:
        """Add a consistently spaced, aligned label/value pair (read-only)."""
        label = tk.Label(parent, text=label_text, anchor="w", width=14)
        label.grid(row=row, column=0, sticky="w", pady=8)

        value_label = tk.Label(parent, text=value, anchor="w")
        value_label.grid(row=row, column=1, sticky="ew", pady=8)

    # -- Event handlers ---------------------------------------------------- #

    def _handle_login(self) -> None:
        if self._on_login:
            self._on_login(self._employee)
        self._root.destroy()


# --------------------------------------------------------------------------- #
# Public Entry Point
# --------------------------------------------------------------------------- #

def launch_employee_flow(
    config_manager: Optional[ConfigManager] = None,
    on_registered: Optional[Callable[[Employee], None]] = None,
    on_login: Optional[Callable[[Employee], None]] = None,
) -> None:
    """
    Launch either the Registration or Login window, whichever is
    appropriate based on config.json's "application.registered" flag.

    This is the single public entry point other modules should call to
    handle the employee identity portion of application startup.
    """
    manager = config_manager or ConfigManager()
    manager.ensure_config_exists()

    if manager.is_registered():
        LoginWindow(manager, on_login=on_login).run()
    else:
        RegistrationWindow(manager, on_complete=on_registered).run()


if __name__ == "__main__":
    launch_employee_flow()