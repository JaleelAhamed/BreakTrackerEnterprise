"""
admin_auth.py
=============

Break Tracker Enterprise - Administrator Authentication Module

Responsibilities of this module (and only these):
    * Displaying the administrator password dialog
    * Verifying the administrator password (SHA-256, from config.json)
    * Handling failed attempts and temporary lockout
    * Logging authentication events
    * Opening SettingsWindow() after a successful authentication, and
      preventing duplicate Settings windows

This module intentionally does NOT implement employee login,
registration, session tracking, or settings field validation. Those
concerns belong to employee.py and settings.py respectively.

Standard library only:
    tkinter, tkinter.ttk, tkinter.messagebox, hashlib, hmac, json,
    pathlib, typing

Author: Break Tracker Enterprise Team
Python: 3.13
"""

from __future__ import annotations

import hashlib
import hmac
import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, Optional

from logger import get_logger
from settings import SettingsWindow

logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

CONFIG_PATH: Path = Path(__file__).resolve().parent / "config.json"

DIALOG_TITLE: str = "Administrator Authentication"
DIALOG_WIDTH: int = 360
DIALOG_HEIGHT: int = 190

# Defaults used only if config.json does not yet define an "admin"
# section. The default password is "admin123" - intended purely as a
# first-run placeholder and should be changed via config.json.
DEFAULT_ADMIN_CONFIG: Dict[str, Any] = {
    "admin_password_hash": hashlib.sha256(b"admin123").hexdigest(),
    "max_admin_attempts": 3,
    "admin_lockout_seconds": 30,
}


# --------------------------------------------------------------------------- #
# Admin Configuration
# --------------------------------------------------------------------------- #

class AdminConfigError(Exception):
    """Raised when the administrator configuration cannot be read or written."""


class AdminConfig:
    """
    Loads and, if necessary, provisions the "admin" section of
    config.json.

    This class intentionally reads/writes config.json directly
    (matching settings.py's approach) rather than routing through
    employee.ConfigManager, so that admin_auth.py has no dependency
    on employee.py.
    """

    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        self._config_path = config_path

    def load(self) -> Dict[str, Any]:
        """
        Return the "admin" section of config.json.

        If config.json is missing the "admin" section (or the whole
        file does not yet exist), it is created with
        DEFAULT_ADMIN_CONFIG and persisted so future reads are stable.
        """
        try:
            data = self._read_full_config()
        except AdminConfigError:
            raise

        admin_section = data.get("admin")
        if not isinstance(admin_section, dict):
            admin_section = {}

        merged = dict(DEFAULT_ADMIN_CONFIG)
        merged.update(admin_section)

        if admin_section != merged:
            data["admin"] = merged
            self._write_full_config(data)
            logger.info("Administrator configuration provisioned with defaults.")

        return merged

    # -- internal helpers ---------------------------------------------- #

    def _read_full_config(self) -> Dict[str, Any]:
        if not self._config_path.exists():
            return {}
        try:
            with self._config_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise AdminConfigError(
                f"Unable to load administrator configuration: {exc}"
            ) from exc

    def _write_full_config(self, data: Dict[str, Any]) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with self._config_path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=4)
        except OSError as exc:
            raise AdminConfigError(
                f"Unable to save administrator configuration: {exc}"
            ) from exc


# --------------------------------------------------------------------------- #
# Password Verification
# --------------------------------------------------------------------------- #

def _verify_password(entered_password: str, stored_hash: str) -> bool:
    """Hash `entered_password` with SHA-256 and compare to `stored_hash`."""
    entered_hash = hashlib.sha256(entered_password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(entered_hash, stored_hash)


# --------------------------------------------------------------------------- #
# Authentication Dialog
# --------------------------------------------------------------------------- #

class _AdminAuthDialog(tk.Toplevel):
    """
    Modal dialog that collects and verifies the administrator
    password, handling failed-attempt tracking and temporary lockout.

    On success, `on_success` is invoked (with no arguments) after the
    dialog has closed itself.
    """

    def __init__(
        self,
        master: tk.Misc,
        admin_config: Dict[str, Any],
        on_success: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._admin_config = admin_config
        self._on_success = on_success

        self._attempts: int = 0
        self._max_attempts: int = int(admin_config["max_admin_attempts"])
        self._lockout_seconds: int = int(admin_config["admin_lockout_seconds"])
        self._lockout_after_id: Optional[str] = None

        self._password_var = tk.StringVar()
        self._show_password_var = tk.BooleanVar(value=False)
        self._status_var = tk.StringVar(value="")

        self._password_entry: Optional[ttk.Entry] = None
        self._ok_button: Optional[ttk.Button] = None

        logger.info("Administrator authentication dialog opened.")

        self._configure_window()
        self._build_ui()
        self._center_window()

        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        if self._password_entry is not None:
            self._password_entry.focus_set()

    # -- window setup ---------------------------------------------------- #

    def _configure_window(self) -> None:
        self.title(DIALOG_TITLE)
        self.resizable(False, False)
        self.geometry(f"{DIALOG_WIDTH}x{DIALOG_HEIGHT}")

    def _center_window(self) -> None:
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_position = (screen_width // 2) - (DIALOG_WIDTH // 2)
        y_position = (screen_height // 2) - (DIALOG_HEIGHT // 2)
        self.geometry(f"{DIALOG_WIDTH}x{DIALOG_HEIGHT}+{x_position}+{y_position}")

    # -- UI construction --------------------------------------------------- #

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        heading = ttk.Label(
            container,
            text="Enter the administrator password to continue.",
            font=("Segoe UI", 9, "bold"),
            wraplength=DIALOG_WIDTH - 40,
            justify="left",
        )
        heading.pack(anchor="w", pady=(0, 12))

        password_row = ttk.Frame(container)
        password_row.pack(fill="x")

        ttk.Label(password_row, text="Password:", width=10).pack(side="left")

        self._password_entry = ttk.Entry(
            password_row,
            textvariable=self._password_var,
            show="*",
            width=24,
        )
        self._password_entry.pack(side="left", fill="x", expand=True)
        self._password_entry.bind("<Return>", lambda _event: self._on_ok())
        self._password_entry.bind("<Escape>", lambda _event: self._on_cancel())

        show_password_check = ttk.Checkbutton(
            container,
            text="Show Password",
            variable=self._show_password_var,
            command=self._toggle_show_password,
        )
        show_password_check.pack(anchor="w", pady=(8, 0))

        status_label = ttk.Label(
            container,
            textvariable=self._status_var,
            foreground="#b00020",
            wraplength=DIALOG_WIDTH - 40,
            justify="left",
        )
        status_label.pack(anchor="w", pady=(8, 0), fill="x")

        button_row = ttk.Frame(container)
        button_row.pack(fill="x", side="bottom", pady=(16, 0))

        self._ok_button = ttk.Button(button_row, text="OK", command=self._on_ok)
        self._ok_button.pack(side="right")

        cancel_button = ttk.Button(
            button_row, text="Cancel", command=self._on_cancel
        )
        cancel_button.pack(side="right", padx=(0, 8))

        self.bind("<Escape>", lambda _event: self._on_cancel())

    def _toggle_show_password(self) -> None:
        if self._password_entry is None:
            return
        self._password_entry.configure(
            show="" if self._show_password_var.get() else "*"
        )

    # -- authentication flow ------------------------------------------------ #

    def _on_ok(self) -> None:
        entered_password = self._password_var.get()
        stored_hash = str(self._admin_config["admin_password_hash"])

        if _verify_password(entered_password, stored_hash):
            logger.info("Administrator authentication successful.")
            self._close()
            self._on_success()
            return

        self._attempts += 1
        logger.warning(
            "Administrator authentication failed (attempt %d of %d).",
            self._attempts, self._max_attempts,
        )
        self._password_var.set("")

        if self._attempts >= self._max_attempts:
            self._start_lockout()
        else:
            self._status_var.set("Incorrect administrator password.")
            if self._password_entry is not None:
                self._password_entry.focus_set()

    def _on_cancel(self) -> None:
        self._close()

    def _close(self) -> None:
        if self._lockout_after_id is not None:
            try:
                self.after_cancel(self._lockout_after_id)
            except tk.TclError:
                pass
            self._lockout_after_id = None
        self.grab_release()
        self.destroy()

    # -- lockout handling ----------------------------------------------- #

    def _start_lockout(self) -> None:
        logger.warning(
            "Administrator access temporarily locked for %d seconds "
            "after %d failed attempts.",
            self._lockout_seconds, self._attempts,
        )

        if self._password_entry is not None:
            self._password_entry.configure(state="disabled")
        if self._ok_button is not None:
            self._ok_button.configure(state="disabled")

        self._status_var.set(
            "Too many failed attempts.\n"
            "Administrator access has been temporarily locked."
        )

        self._lockout_after_id = self.after(
            self._lockout_seconds * 1000, self._end_lockout
        )

    def _end_lockout(self) -> None:
        logger.info("Administrator temporary lockout ended.")

        self._attempts = 0
        self._lockout_after_id = None
        self._status_var.set("")

        if self._password_entry is not None:
            self._password_entry.configure(state="normal")
        if self._ok_button is not None:
            self._ok_button.configure(state="normal")
        if self._password_entry is not None:
            self._password_entry.focus_set()


# --------------------------------------------------------------------------- #
# Public Orchestrator
# --------------------------------------------------------------------------- #

class AdministratorAuth:
    """
    Public entry point for gating access to SettingsWindow behind
    administrator authentication.

    An instance of this class should be held for the lifetime of the
    caller (e.g. one per LoginWindow) so that it can track a single
    open SettingsWindow and avoid creating duplicates.
    """

    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        self._admin_config = AdminConfig(config_path)
        self._settings_window: Optional[SettingsWindow] = None

    def open_admin_settings(self, master: tk.Misc) -> None:
        """
        Entry point called from the Settings (gear) button.

        If a Settings window is already open, it is restored and
        focused instead of prompting for authentication again. Only
        one administrator authentication dialog may be open at a
        time (Tkinter's grab_set on the dialog itself enforces this
        for the duration of the prompt).
        """
        existing = self._settings_window
        if existing is not None:
            try:
                if existing.root.winfo_exists():
                    self._focus_settings_window(existing.root)
                    return
            except tk.TclError:
                pass
            self._settings_window = None

        try:
            admin_config = self._admin_config.load()
        except AdminConfigError as exc:
            logger.exception("Unable to load administrator configuration.")
            messagebox.showerror(
                "Configuration Error",
                f"Could not load administrator configuration:\n{exc}",
                parent=master,
            )
            return

        _AdminAuthDialog(
            master,
            admin_config,
            on_success=lambda: self._launch_settings_window(master),
        )

    # -- internal helpers ---------------------------------------------- #

    def _launch_settings_window(self, master: tk.Misc) -> None:
        settings_window = SettingsWindow(master=master)
        settings_window.root.bind(
            "<Destroy>", self._handle_settings_window_closed, add="+"
        )
        self._settings_window = settings_window
        logger.info("Settings window opened.")

    def _handle_settings_window_closed(self, event: tk.Event) -> None:
        if (
            self._settings_window is not None
            and event.widget is self._settings_window.root
        ):
            self._settings_window = None

    @staticmethod
    def _focus_settings_window(window: tk.Misc) -> None:
        """Restore (if minimized), raise, and focus an existing window."""
        if window.state() == "iconic":
            window.deiconify()
        window.lift()
        window.focus_force()