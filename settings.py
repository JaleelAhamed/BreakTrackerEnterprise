"""
Break Tracker Enterprise
Settings Module

Version: 1.0.0
Sprint: 9

Provides a professional Tkinter Settings window that allows the
user to view, edit, validate and persist application settings to
config.json.

This module intentionally works directly against config.json using
the standard library (json + pathlib). No ConfigManager class is
introduced, per project architecture constraints.

Standard library only:
    tkinter, tkinter.ttk, tkinter.filedialog, tkinter.messagebox,
    json, pathlib, typing
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, Optional

from logger import get_logger


# ============================================================
# MODULE CONSTANTS
# ============================================================

logger = get_logger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "idle_threshold": 5,
    "allowed_break_minutes": 60,
    "auto_start": True,
    "minimize_to_tray": True,
    "enable_notifications": True,
    "report_folder": "reports",
    "log_folder": "logs",
}

WINDOW_TITLE = "Break Tracker Enterprise - Settings"
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 560


# ============================================================
# SETTINGS WINDOW
# ============================================================

class SettingsWindow:
    """
    Professional Settings window for Break Tracker Enterprise.

    Responsible for:

    - Loading settings from config.json
    - Presenting settings in a Tkinter/ttk interface
    - Validating user input before saving
    - Detecting unsaved changes and prompting the user
    - Resetting settings to defaults (without auto-saving)
    - Saving settings back to config.json while preserving the
      rest of the JSON structure
    """

    def __init__(self, master: Optional[tk.Misc] = None) -> None:
        """
        Initialize the Settings window.

        Parameters
        ----------
        master:
            Optional parent Tk widget. If None, the window is
            created as its own root.
        """

        self._owns_root = master is None
        self.root: tk.Misc = tk.Tk() if master is None else tk.Toplevel(master)

        self.config_data: Dict[str, Any] = {}
        self.modified: bool = False

        # Tkinter variables bound to widgets
        self.idle_var = tk.StringVar()
        self.break_var = tk.StringVar()
        self.auto_start_var = tk.BooleanVar()
        self.minimize_tray_var = tk.BooleanVar()
        self.notifications_var = tk.BooleanVar()
        self.report_folder_var = tk.StringVar()
        self.log_folder_var = tk.StringVar()

        logger.info("Settings window opened.")

        self._load_config()
        self._build_ui()
        self._populate_fields()
        self._bind_change_tracking()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._center_window()

    # ============================================================
    # CONFIG I/O
    # ============================================================

    def _load_config(self) -> None:
        """
        Load config.json from disk.

        Handles a missing file and invalid JSON gracefully by
        falling back to sensible defaults while preserving any
        other top-level sections that could still be read.
        """

        if not CONFIG_PATH.exists():
            logger.warning(
                "config.json not found at %s. Using default settings.",
                CONFIG_PATH,
            )
            self.config_data = {"settings": dict(DEFAULT_SETTINGS)}
            return

        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
                self.config_data = json.load(config_file)

            if "settings" not in self.config_data:
                self.config_data["settings"] = {}

        except json.JSONDecodeError as error:
            logger.error("Failed to parse config.json: %s", error)
            messagebox.showerror(
                "Invalid Configuration",
                "config.json is corrupted or not valid JSON.\n"
                "Default settings will be used instead.",
                parent=self.root,
            )
            self.config_data = {"settings": dict(DEFAULT_SETTINGS)}

        except OSError as error:
            logger.error("Failed to read config.json: %s", error)
            messagebox.showerror(
                "Read Error",
                f"Could not read config.json:\n{error}",
                parent=self.root,
            )
            self.config_data = {"settings": dict(DEFAULT_SETTINGS)}

    def _get_setting(self, key: str) -> Any:
        """
        Retrieve a setting value, falling back to its default.
        """

        return self.config_data.get("settings", {}).get(
            key, DEFAULT_SETTINGS[key]
        )

    def _save_config(self) -> bool:
        """
        Validate and persist current field values to config.json,
        preserving any other existing top-level sections.

        Returns
        -------
        bool
            True if the save succeeded, False otherwise.
        """

        if not self._validate():
            return False

        settings_section = self.config_data.get("settings", {})
        settings_section["idle_threshold"] = int(self.idle_var.get())
        settings_section["allowed_break_minutes"] = int(self.break_var.get())
        settings_section["auto_start"] = self.auto_start_var.get()
        settings_section["minimize_to_tray"] = self.minimize_tray_var.get()
        settings_section["enable_notifications"] = self.notifications_var.get()
        settings_section["report_folder"] = self.report_folder_var.get().strip()
        settings_section["log_folder"] = self.log_folder_var.get().strip()

        self.config_data["settings"] = settings_section

        try:
            with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
                json.dump(self.config_data, config_file, indent=4)

        except OSError as error:
            logger.error("Failed to write config.json: %s", error)
            messagebox.showerror(
                "Save Error",
                f"Could not save settings:\n{error}",
                parent=self.root,
            )
            return False

        logger.info("Settings saved successfully.")
        self.modified = False
        return True

    # ============================================================
    # UI CONSTRUCTION
    # ============================================================

    def _build_ui(self) -> None:
        """
        Build the full Settings window layout.
        """

        self.root.title(WINDOW_TITLE)
        self.root.resizable(False, False)

        style = ttk.Style(self.root)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        style.configure("Header.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"))

        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        self._build_idle_frame(container)
        self._build_break_frame(container)
        self._build_application_frame(container)
        self._build_storage_frame(container)
        self._build_buttons_frame(container)

    def _build_idle_frame(self, parent: ttk.Frame) -> None:
        """Build the Idle Detection settings group."""

        frame = ttk.Labelframe(parent, text="Idle Detection", padding=12)
        frame.pack(fill="x", pady=(0, 10))

        ttk.Label(frame, text="Idle Timeout (minutes):").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=4
        )
        entry = ttk.Entry(frame, textvariable=self.idle_var, width=10)
        entry.grid(row=0, column=1, sticky="w", pady=4)

    def _build_break_frame(self, parent: ttk.Frame) -> None:
        """Build the Break Policy settings group."""

        frame = ttk.Labelframe(parent, text="Break Policy", padding=12)
        frame.pack(fill="x", pady=(0, 10))

        ttk.Label(frame, text="Allowed Break Minutes:").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=4
        )
        entry = ttk.Entry(frame, textvariable=self.break_var, width=10)
        entry.grid(row=0, column=1, sticky="w", pady=4)

    def _build_application_frame(self, parent: ttk.Frame) -> None:
        """Build the Application settings group (checkbuttons)."""

        frame = ttk.Labelframe(parent, text="Application", padding=12)
        frame.pack(fill="x", pady=(0, 10))

        ttk.Checkbutton(
            frame, text="Auto Start Monitoring", variable=self.auto_start_var
        ).pack(anchor="w", pady=2)

        ttk.Checkbutton(
            frame, text="Minimize to System Tray", variable=self.minimize_tray_var
        ).pack(anchor="w", pady=2)

        ttk.Checkbutton(
            frame, text="Enable Notifications", variable=self.notifications_var
        ).pack(anchor="w", pady=2)

    def _build_storage_frame(self, parent: ttk.Frame) -> None:
        """Build the Storage settings group (folder pickers)."""

        frame = ttk.Labelframe(parent, text="Storage", padding=12)
        frame.pack(fill="x", pady=(0, 10))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Report Folder:").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=4
        )
        ttk.Entry(frame, textvariable=self.report_folder_var).grid(
            row=0, column=1, sticky="ew", pady=4
        )
        ttk.Button(
            frame, text="Browse...", command=self._browse_report_folder
        ).grid(row=0, column=2, padx=(8, 0), pady=4)

        ttk.Label(frame, text="Log Folder:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=4
        )
        ttk.Entry(frame, textvariable=self.log_folder_var).grid(
            row=1, column=1, sticky="ew", pady=4
        )
        ttk.Button(
            frame, text="Browse...", command=self._browse_log_folder
        ).grid(row=1, column=2, padx=(8, 0), pady=4)

    def _build_buttons_frame(self, parent: ttk.Frame) -> None:
        """Build the Save / Cancel / Reset Defaults button row."""

        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(10, 0))

        ttk.Button(
            frame, text="Reset Defaults", command=self._on_reset
        ).pack(side="left")

        ttk.Button(
            frame, text="Cancel", command=self._on_cancel
        ).pack(side="right", padx=(6, 0))

        ttk.Button(
            frame, text="Save", command=self._on_save
        ).pack(side="right")

    # ============================================================
    # FIELD POPULATION / CHANGE TRACKING
    # ============================================================

    def _populate_fields(self) -> None:
        """
        Populate all widgets from the currently loaded config data.
        """

        self.idle_var.set(str(self._get_setting("idle_threshold")))
        self.break_var.set(str(self._get_setting("allowed_break_minutes")))
        self.auto_start_var.set(bool(self._get_setting("auto_start")))
        self.minimize_tray_var.set(bool(self._get_setting("minimize_to_tray")))
        self.notifications_var.set(bool(self._get_setting("enable_notifications")))
        self.report_folder_var.set(str(self._get_setting("report_folder")))
        self.log_folder_var.set(str(self._get_setting("log_folder")))

    def _bind_change_tracking(self) -> None:
        """
        Attach trace callbacks so any field change marks the
        window as having unsaved modifications.
        """

        for variable in (
            self.idle_var,
            self.break_var,
            self.auto_start_var,
            self.minimize_tray_var,
            self.notifications_var,
            self.report_folder_var,
            self.log_folder_var,
        ):
            variable.trace_add("write", self._on_setting_changed)

    def _on_setting_changed(self, *_args: Any) -> None:
        """
        Callback fired whenever a bound setting variable changes.
        """

        self._mark_modified()

    def _mark_modified(self) -> None:
        """
        Mark the window as having unsaved changes and reflect
        that in the window title.
        """

        if not self.modified:
            self.modified = True

        if not self.root.title().endswith("*"):
            self.root.title(f"{WINDOW_TITLE} *")

    def _clear_modified(self) -> None:
        """
        Clear the unsaved-changes flag and window title marker.
        """

        self.modified = False
        self.root.title(WINDOW_TITLE)

    # ============================================================
    # BROWSE HANDLERS
    # ============================================================

    def _browse_report_folder(self) -> None:
        """Open a folder picker for the report folder field."""

        folder = filedialog.askdirectory(parent=self.root, mustexist=False)
        if folder:
            self.report_folder_var.set(folder)

    def _browse_log_folder(self) -> None:
        """Open a folder picker for the log folder field."""

        folder = filedialog.askdirectory(parent=self.root, mustexist=False)
        if folder:
            self.log_folder_var.set(folder)

    # ============================================================
    # VALIDATION
    # ============================================================

    def _validate(self) -> bool:
        """
        Validate all fields before saving.

        Returns
        -------
        bool
            True if every field is valid, False otherwise. On
            failure, an error dialog is shown and the failure is
            logged.
        """

        errors = []

        try:
            idle_value = int(self.idle_var.get())
            if idle_value <= 0:
                errors.append("Idle Timeout must be greater than 0.")
        except ValueError:
            errors.append("Idle Timeout must be a whole number.")

        try:
            break_value = int(self.break_var.get())
            if break_value <= 0:
                errors.append("Allowed Break Minutes must be greater than 0.")
        except ValueError:
            errors.append("Allowed Break Minutes must be a whole number.")

        if not self.report_folder_var.get().strip():
            errors.append("Report Folder cannot be empty.")

        if not self.log_folder_var.get().strip():
            errors.append("Log Folder cannot be empty.")

        if errors:
            logger.warning("Settings validation failed: %s", "; ".join(errors))
            messagebox.showerror(
                "Validation Error",
                "\n".join(errors),
                parent=self.root,
            )
            return False

        return True

    # ============================================================
    # BUTTON HANDLERS
    # ============================================================

    def _on_save(self) -> None:
        """
        Handle the Save button: validate, persist, and close.
        """

        if self._save_config():
            self._clear_modified()
            self._close_window()

    def _on_cancel(self) -> None:
        """
        Handle the Cancel button, prompting for unsaved changes.
        """

        if self.modified:
            self._prompt_unsaved_changes()
        else:
            self._close_window()

    def _on_close(self) -> None:
        """
        Handle the window Close (X) button, prompting for unsaved
        changes.
        """

        if self.modified:
            self._prompt_unsaved_changes()
        else:
            self._close_window()

    def _prompt_unsaved_changes(self) -> None:
        """
        Display the unsaved-changes Yes/No/Cancel dialog and act
        on the user's choice.
        """

        response = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved changes.\n"
            "Would you like to save them before closing?",
            parent=self.root,
        )

        if response is True:
            # Yes -> Save settings, then close
            if self._save_config():
                self._clear_modified()
                self._close_window()
        elif response is False:
            # No -> Close without saving
            self._close_window()
        # Cancel (response is None) -> return to settings window, do nothing

    def _on_reset(self) -> None:
        """
        Handle Reset Defaults: confirm, then restore default
        values into the fields without saving to disk.
        """

        confirmed = messagebox.askyesno(
            "Reset Defaults",
            "This will restore all settings to their default values.\n"
            "Continue?",
            parent=self.root,
        )

        if not confirmed:
            return

        self.idle_var.set(str(DEFAULT_SETTINGS["idle_threshold"]))
        self.break_var.set(str(DEFAULT_SETTINGS["allowed_break_minutes"]))
        self.auto_start_var.set(DEFAULT_SETTINGS["auto_start"])
        self.minimize_tray_var.set(DEFAULT_SETTINGS["minimize_to_tray"])
        self.notifications_var.set(DEFAULT_SETTINGS["enable_notifications"])
        self.report_folder_var.set(DEFAULT_SETTINGS["report_folder"])
        self.log_folder_var.set(DEFAULT_SETTINGS["log_folder"])

        logger.info("Settings reset to defaults (not yet saved).")
        self._mark_modified()

    # ============================================================
    # WINDOW HELPERS
    # ============================================================

    def _center_window(self) -> None:
        """
        Center the window on the screen at a fixed size.
        """

        self.root.update_idletasks()

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x_position = (screen_width // 2) - (WINDOW_WIDTH // 2)
        y_position = (screen_height // 2) - (WINDOW_HEIGHT // 2)

        self.root.geometry(
            f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x_position}+{y_position}"
        )

    def _close_window(self) -> None:
        """
        Destroy the settings window (or quit the root loop if this
        window owns its own Tk root).
        """

        self.root.destroy()

    def run(self) -> None:
        """
        Start the Tkinter event loop for this window. Only call
        this if the window owns its own root (i.e. was created
        without a parent).
        """

        if self._owns_root:
            self.root.mainloop()
        else:
            self.root.wait_window()


# ============================================================
# ENTRY POINT (for standalone testing)
# ============================================================

if __name__ == "__main__":
    settings_window = SettingsWindow()
    settings_window.run()