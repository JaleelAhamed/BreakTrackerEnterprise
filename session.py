"""
session.py
==========

Break Tracker Enterprise - Session Module

Responsibilities of this module (and only these):
    * Record login time
    * Record logout time
    * Display a live working timer that updates every second
    * Calculate total session duration on logout

This module intentionally does NOT implement idle detection, report
generation, dashboards, or any persistence beyond an in-memory
WorkSession. Those concerns belong to other modules.

No threads are used. The live timer relies exclusively on Tkinter's
`after()` scheduling mechanism, which is safe to use on the main
GUI thread.

Author: Break Tracker Enterprise Team
Python: 3.13
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

APP_TITLE: str = "Break Tracker Enterprise"
TIMER_UPDATE_INTERVAL_MS: int = 1000  # 1 second


# --------------------------------------------------------------------------- #
# Data Model
# --------------------------------------------------------------------------- #

@dataclass
class WorkSession:
    """
    Represents a single continuous working session for an employee.

    This dataclass is intentionally minimal and independent of the
    Employee model in employee.py - it stores only a display name so
    that session.py has no hard dependency on other modules.
    """

    employee_display_name: str = ""
    login_time: Optional[datetime] = None
    logout_time: Optional[datetime] = None

    def is_active(self) -> bool:
        """Return True while the session has started but not yet ended."""
        return self.login_time is not None and self.logout_time is None

    def duration(self, as_of: Optional[datetime] = None) -> timedelta:
        """
        Return the session duration.

        If the session has ended, the duration is fixed (logout - login).
        If the session is still active, duration is measured up to
        `as_of` (defaulting to the current time) - useful for live
        timer display.
        """
        if self.login_time is None:
            return timedelta(0)

        end_point = self.logout_time or as_of or datetime.now()
        return end_point - self.login_time


# --------------------------------------------------------------------------- #
# Session Logic (UI-independent)
# --------------------------------------------------------------------------- #

class SessionManager:
    """
    Owns the lifecycle and business logic of a WorkSession.

    Kept separate from any UI code so that session start/stop/duration
    calculations can be tested or reused without Tkinter.
    """

    def __init__(self, employee_display_name: str = "") -> None:
        self._session: WorkSession = WorkSession(
            employee_display_name=employee_display_name
        )

    @property
    def session(self) -> WorkSession:
        """Expose the current (or most recently completed) session."""
        return self._session

    def start_session(self) -> WorkSession:
        """
        Begin a new work session, recording the current time as login.

        Raises:
            RuntimeError: if a session is already active.
        """
        if self._session.is_active():
            raise RuntimeError("A session is already active; cannot start another.")

        self._session = WorkSession(
            employee_display_name=self._session.employee_display_name,
            login_time=datetime.now(),
            logout_time=None,
        )
        return self._session

    def end_session(self) -> WorkSession:
        """
        End the active work session, recording the current time as logout.

        Raises:
            RuntimeError: if no session is currently active.

        Returns:
            The completed WorkSession, with duration now fixed.
        """
        if not self._session.is_active():
            raise RuntimeError("No active session to end.")

        self._session.logout_time = datetime.now()
        return self._session

    def get_elapsed(self) -> timedelta:
        """Return elapsed time for the current session, live if active."""
        return self._session.duration()

    @staticmethod
    def format_duration(duration: timedelta) -> str:
        """Format a timedelta as HH:MM:SS for display purposes."""
        total_seconds = int(duration.total_seconds())
        # Guard against any negative drift (e.g. system clock changes).
        total_seconds = max(total_seconds, 0)

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


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
# Session Timer Window (UI)
# --------------------------------------------------------------------------- #

class SessionTimerWindow:
    """
    Displays a live working timer and a Logout button.

    The window starts a new session on construction and schedules a
    self-repeating `after()` callback to refresh the elapsed-time
    label every second. On Logout, the session is ended, the timer
    is cancelled, and an optional callback is invoked with the
    completed WorkSession.
    """

    WINDOW_WIDTH: int = 360
    WINDOW_HEIGHT: int = 260

    def __init__(
        self,
        employee_display_name: str = "",
        on_logout: Optional[Callable[[WorkSession], None]] = None,
        session_manager: Optional[SessionManager] = None,
    ) -> None:
        self._manager = session_manager or SessionManager(employee_display_name)
        self._on_logout = on_logout

        # Holds the identifier returned by `after()` so it can be
        # cancelled cleanly on logout or window close.
        self._after_id: Optional[str] = None

        self._root = tk.Tk()
        _configure_fixed_window(
            self._root, self.WINDOW_WIDTH, self.WINDOW_HEIGHT, APP_TITLE
        )
        self._root.protocol("WM_DELETE_WINDOW", self._handle_window_close)

        self._timer_var = tk.StringVar(value="00:00:00")
        self._status_var = tk.StringVar(value="")

        self._build_ui()
        self._start_session_and_timer()

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

        status_label = tk.Label(
            container, textvariable=self._status_var, font=("Segoe UI", 11)
        )
        status_label.pack(pady=(0, 20))

        timer_label = tk.Label(
            container,
            textvariable=self._timer_var,
            font=("Consolas", 28, "bold"),
        )
        timer_label.pack(pady=(0, 25))

        logout_button = tk.Button(
            container,
            text="Logout",
            width=20,
            command=self._handle_logout,
        )
        logout_button.pack()

    # -- Session/timer control --------------------------------------------- #

    def _start_session_and_timer(self) -> None:
        """Record login time and kick off the recurring timer update."""
        self._manager.start_session()

        display_name = self._manager.session.employee_display_name
        self._status_var.set(
            f"Working - {display_name}" if display_name else "Working"
        )

        self._schedule_next_tick()

    def _schedule_next_tick(self) -> None:
        """Schedule the next timer refresh using Tkinter's after()."""
        self._update_timer_display()
        self._after_id = self._root.after(
            TIMER_UPDATE_INTERVAL_MS, self._schedule_next_tick
        )

    def _update_timer_display(self) -> None:
        """Refresh the on-screen elapsed-time label."""
        elapsed = self._manager.get_elapsed()
        self._timer_var.set(SessionManager.format_duration(elapsed))

    def _cancel_timer(self) -> None:
        """Cancel any pending after() callback, if one is scheduled."""
        if self._after_id is not None:
            self._root.after_cancel(self._after_id)
            self._after_id = None

    # -- Event handlers ---------------------------------------------------- #

    def _handle_logout(self) -> None:
        """End the session, freeze the timer, and notify the caller."""
        self._cancel_timer()

        completed_session = self._manager.end_session()
        self._update_timer_display()  # Show final frozen duration.

        if self._on_logout:
            self._on_logout(completed_session)

        self._root.destroy()

    def _handle_window_close(self) -> None:
        """
        Treat closing the window (e.g. the OS close button) the same
        as an explicit logout, so a session is never left dangling.
        """
        if self._manager.session.is_active():
            self._handle_logout()
        else:
            self._cancel_timer()
            self._root.destroy()


# --------------------------------------------------------------------------- #
# Public Entry Point
# --------------------------------------------------------------------------- #

def launch_session_window(
    employee_display_name: str = "",
    on_logout: Optional[Callable[[WorkSession], None]] = None,
) -> None:
    """
    Launch the live session timer window for the given employee.

    This is the single public entry point other modules should call
    to start tracking a work session and display the live timer.
    """
    SessionTimerWindow(
        employee_display_name=employee_display_name, on_logout=on_logout
    ).run()


if __name__ == "__main__":
    def _print_summary(session: WorkSession) -> None:
        duration = SessionManager.format_duration(session.duration())
        print(f"Session ended for '{session.employee_display_name}'.")
        print(f"Login:  {session.login_time}")
        print(f"Logout: {session.logout_time}")
        print(f"Total duration: {duration}")

    launch_session_window(employee_display_name="Jaleel Ahamed", on_logout=_print_summary)