"""
session.py
==========

Break Tracker Enterprise - Session Module

Responsibilities of this module (and only these):
    * Record login time
    * Record logout time
    * Display a live working timer that updates every second
    * Calculate total session duration on logout
    * Coordinate with idle_detector.py (start/stop idle monitoring,
      retrieve the recorded BreakLog) and report_generator.py
      (generate the logout report) via their existing public APIs.
    * Coordinate with tray_manager.py so the window can be minimized
      to the system tray (instead of closed) and restored, logged out,
      or exited from the tray menu.

This module intentionally does NOT implement idle detection logic,
report-building logic, dashboards, tray-icon logic, or any persistence
beyond an in-memory WorkSession. Those concerns belong to
idle_detector.py, report_generator.py, tray_manager.py, and other
modules. session.py is the coordinator: it depends on those modules,
but none of them depends back on it.

No manual threads are created in this module. The live timer relies
exclusively on Tkinter's `after()` scheduling mechanism, which is safe
to use on the main GUI thread. Idle monitoring is delegated entirely
to idle_detector.py, which owns whatever background listening it needs.
The system tray icon is delegated entirely to tray_manager.py, which
owns its own background thread.

Author: Break Tracker Enterprise Team
Python: 3.13
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from tkinter import messagebox
from typing import Callable, Optional

from employee import ConfigManager, Employee
from idle_detector import BreakLog, IdleTrackingController
from report_generator import generate_session_report
from tray_manager import TrayManager
from logger import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

APP_TITLE: str = "Break Tracker Enterprise"
TIMER_UPDATE_INTERVAL_MS: int = 1000  # 1 second
DEFAULT_ALLOWED_BREAK_MINUTES: int = 60  # Fallback if config is unavailable.
TRAY_BACKGROUND_NOTICE: str = (
    "Break Tracker Enterprise is still running in the background."
)


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

    The window starts a new session on construction (this is treated
    as "login successful") and schedules a self-repeating `after()`
    callback to refresh the elapsed-time label every second. On
    Logout, the session is ended, the timer is cancelled, idle
    monitoring is stopped, a report is generated, and an optional
    callback is invoked with the completed WorkSession.
    """

    WINDOW_WIDTH: int = 360
    WINDOW_HEIGHT: int = 260

    def __init__(
        self,
        employee_display_name: str = "",
        on_logout: Optional[Callable[[WorkSession], None]] = None,
        session_manager: Optional[SessionManager] = None,
        employee: Optional[Employee] = None,
        config_manager: Optional[ConfigManager] = None,
        root: Optional[tk.Tk] = None,
    ) -> None:
        # `employee` (full profile) and `config_manager` are optional so
        # existing callers that only pass a display name keep working
        # unchanged; they are used for report generation when available.
        self._employee = employee
        self._config_manager = config_manager

        display_name = employee_display_name or (employee.name if employee else "")
        self._manager = session_manager or SessionManager(display_name)
        self._on_logout = on_logout

        # Holds the identifier returned by `after()` so it can be
        # cancelled cleanly on logout or window close.
        self._after_id: Optional[str] = None

        # Explicit running flag so the tick loop can never be started
        # twice (which would leave a stray after() chain updating
        # nothing the user can see) and never keeps rescheduling
        # itself after it should have stopped.
        self._timer_running: bool = False

        # Owns idle/break monitoring for the current session. Created on
        # login, stopped on logout. IdleTrackingController is the real
        # public entry point exposed by idle_detector.py; it internally
        # owns the ActivityTracker/IdleDetector/BreakLog and the
        # break-reason popup.
        self._idle_detector: Optional[IdleTrackingController] = None

        # Owns the system tray icon for this window. Created once,
        # right after the window/session is up, and stopped on logout
        # or exit. TrayManager owns its own background thread; this
        # class only calls its public methods.
        self._tray_manager: Optional[TrayManager] = None

        # This window normally reuses the single root created by
        # main.py and already carrying the Employee login/registration
        # UI - it does NOT open a second Tk() instance. Opening a
        # second root (the previous behaviour) is what caused the
        # live timer's StringVar/after() calls to bind unreliably
        # across two competing Tk interpreters, and left the login
        # window stuck alive until this one closed.
        self._owns_root = root is None
        self._root = root or tk.Tk()

        # Defensive cleanup: if this root previously hosted another
        # window's widgets, clear them before building the session UI,
        # regardless of whether the caller already tore its own down.
        for child in self._root.winfo_children():
            child.destroy()

        _configure_fixed_window(
            self._root, self.WINDOW_WIDTH, self.WINDOW_HEIGHT, APP_TITLE
        )
        # The OS close (X) button no longer ends the session - it
        # minimizes the window to the system tray instead. Logout and
        # Exit are performed explicitly, either from the in-window
        # Logout button or from the tray menu.
        self._root.protocol("WM_DELETE_WINDOW", self._handle_close_button)

        self._timer_var = tk.StringVar(master=self._root, value="00:00:00")
        self._status_var = tk.StringVar(master=self._root, value="")

        self._build_ui()
        self._start_session_and_timer()
        self._start_tray_manager()

    def run(self) -> None:
        """
        Start the Tkinter event loop for this window.

        Only relevant for standalone usage where this window owns its
        root. When integrated into the application flow via a shared
        root, the caller (launch_session_window / main.py) owns the
        single, already-running event loop.
        """
        if self._owns_root:
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
        """Record login time, kick off the timer, and start idle monitoring."""
        self._manager.start_session()

        display_name = self._manager.session.employee_display_name
        self._status_var.set(
            f"Working - {display_name}" if display_name else "Working"
        )
        logger.info(
            "Session started for %s at %s",
            display_name or "<unknown>",
            self._manager.session.login_time,
        )

        self._timer_running = True
        self._schedule_next_tick()
        self._start_idle_detection()

    def _schedule_next_tick(self) -> None:
        """Schedule the next timer refresh using Tkinter's after()."""
        if not self._timer_running:
            return  # Timer was stopped; do not reschedule.

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
        self._timer_running = False
        if self._after_id is not None:
            self._root.after_cancel(self._after_id)
            self._after_id = None

    # -- Idle detection integration ---------------------------------------- #

    def _start_idle_detection(self) -> None:
        """
        Create and start the IdleTrackingController for this session.

        idle_detector.py owns all monitoring internals (including the
        background pynput listeners); this call must not block the UI
        thread - IdleTrackingController.start() only schedules an
        after() poll and returns immediately.
        """
        try:
            idle_minutes = self._get_idle_threshold_minutes()
            self._idle_detector = IdleTrackingController(
                self._root,
                idle_threshold=timedelta(minutes=idle_minutes),
            )
            self._idle_detector.start()
            logger.info(
                "Idle detection started for %s",
                self._manager.session.employee_display_name or "<unknown>",
            )
        except Exception as exc:  # Idle monitoring must never crash login.
            logger.error("Failed to start idle detection: %s", exc)
            messagebox.showerror(
                "Idle Detection Error",
                f"Idle monitoring could not be started:\n{exc}",
            )

    def _stop_idle_detection(self) -> None:
        """Stop the IdleTrackingController cleanly, ensuring no listeners remain."""
        if self._idle_detector is None:
            return

        try:
            self._idle_detector.stop()
            logger.info("Idle detection stopped.")
        except Exception as exc:  # Logout must proceed regardless.
            logger.error("Failed to stop idle detection cleanly: %s", exc)

    def _get_break_log(self) -> BreakLog:
        """
        Retrieve the BreakLog recorded by the IdleTrackingController.

        Returns an empty BreakLog if idle detection never started (or
        failed to start), so report generation can proceed regardless.
        """
        if self._idle_detector is None:
            return BreakLog()

        try:
            return self._idle_detector.break_log
        except Exception as exc:
            logger.error("Failed to retrieve break log: %s", exc)
            return BreakLog()

    def _get_idle_threshold_minutes(self) -> int:
        """Read the idle timeout (minutes) from config.json via ConfigManager."""
        try:
            config_manager = self._config_manager or ConfigManager()
            config = config_manager.load()
            return int(config.get("settings", {}).get("idle_threshold", 3))
        except Exception as exc:
            logger.error("Failed to load idle threshold from config: %s", exc)
            return 3

    def _get_allowed_break_minutes(self) -> int:
        """Read the allowed break limit from config.json via ConfigManager."""
        try:
            config_manager = self._config_manager or ConfigManager()
            config = config_manager.load()
            return int(
                config.get("settings", {}).get(
                    "allowed_break_minutes", DEFAULT_ALLOWED_BREAK_MINUTES
                )
            )
        except Exception as exc:
            logger.error("Failed to load allowed break minutes from config: %s", exc)
            return DEFAULT_ALLOWED_BREAK_MINUTES

    # -- System tray integration --------------------------------------------- #

    def _start_tray_manager(self) -> None:
        """
        Create and start the system tray icon.

        This lets the window be minimized to the tray (via the close
        button) instead of closed, and lets the employee log out or
        exit from the tray menu. Tray failures are logged and must
        never prevent the session itself from running - the app is
        fully usable without a working tray icon.
        """
        try:
            display_name = self._manager.session.employee_display_name
            tooltip = f"{APP_TITLE} - {display_name}" if display_name else APP_TITLE

            self._tray_manager = TrayManager(
                root=self._root,
                application_name=APP_TITLE,
                tooltip=tooltip,
                on_logout=self._handle_tray_logout,
                on_exit=self._handle_tray_exit,
            )
            self._tray_manager.start()
            logger.info("System tray started for %s", display_name or "<unknown>")
        except Exception as exc:  # The tray must never crash the session.
            logger.error("Failed to start the system tray icon: %s", exc)
            self._tray_manager = None

    def _stop_tray_manager(self) -> None:
        """Stop the system tray icon cleanly, if it was started."""
        if self._tray_manager is None:
            return

        try:
            self._tray_manager.stop()
            logger.info("System tray stopped.")
        except Exception as exc:  # Logout/exit must proceed regardless.
            logger.error("Failed to stop the system tray icon cleanly: %s", exc)

    def _handle_tray_logout(self) -> None:
        """
        Invoked by the tray's "Logout" menu item. Performs exactly the
        same logout process as the in-window Logout button - session
        end, idle-detection stop, report generation, and shutdown.
        """
        logger.info("Logout selected from system tray.")
        if self._manager.session.is_active():
            self._handle_logout()

    def _handle_tray_exit(self) -> None:
        """
        Invoked by the tray's "Exit" menu item. Performs a clean
        shutdown: if a session is still active it is ended exactly
        like a normal logout (so the report is still generated);
        either way, the tray icon and application close afterwards.
        """
        logger.info("Exit selected from system tray.")
        if self._manager.session.is_active():
            self._handle_logout()
        else:
            self._stop_tray_manager()
            self._root.destroy()

    # -- Report generation integration -------------------------------------- #

    def _generate_logout_report(self, completed_session: WorkSession) -> None:
        """
        Build the logout report via report_generator.py's existing API
        and inform the employee of the outcome. Failures here must
        never crash the application.
        """
        if self._employee is None:
            # generate_session_report requires an Employee (for name,
            # ID, department, designation, and the report file name).
            logger.error("Cannot generate report: no Employee profile available.")
            messagebox.showerror(
                "Report Generation Failed",
                "The session report could not be generated because no "
                "employee profile was supplied to this session.",
            )
            return

        break_log = self._get_break_log()
        allowed_break_minutes = self._get_allowed_break_minutes()

        logger.info(
            "Report generation started for %s",
            self._employee.name if self._employee else "<unknown>",
        )

        try:
            report_path = generate_session_report(
                employee=self._employee,
                session=completed_session,
                break_log=break_log,
                allowed_break_minutes=allowed_break_minutes,
            )
            logger.info("Report generation completed: %s", report_path)
            messagebox.showinfo(
                "Report Generated", f"Session report saved to:\n{report_path}"
            )
        except Exception as exc:
            logger.exception("Report generation failed")
            messagebox.showerror(
                "Report Generation Failed",
                f"The session report could not be generated:\n{exc}",
            )

    # -- Event handlers ---------------------------------------------------- #

    def _handle_logout(self) -> None:
        """
        End the session, stop idle monitoring, freeze the timer,
        generate the report, and notify the caller.
        """
        logger.info(
            "Logout requested for %s",
            self._manager.session.employee_display_name or "<unknown>",
        )

        self._cancel_timer()
        self._stop_idle_detection()
        self._stop_tray_manager()

        completed_session = self._manager.end_session()
        self._update_timer_display()  # Show final frozen duration.
        logger.info(
            "Session ended for %s",
            completed_session.employee_display_name or "<unknown>",
        )

        self._generate_logout_report(completed_session)

        if self._on_logout:
            self._on_logout(completed_session)

        # Session is always the last screen in the application flow,
        # so it destroys the root outright (whether or not it created
        # it) - this is what lets the single running mainloop() return
        # and the application exit cleanly with no windows left behind.
        self._root.destroy()

    def _handle_window_close(self) -> None:
        """
        Fallback behaviour if the system tray is unavailable: treat
        closing the window the same as an explicit logout, so a
        session is never left dangling and idle monitoring never keeps
        running unattended with no way to reach it.
        """
        if self._manager.session.is_active():
            self._handle_logout()
        else:
            self._cancel_timer()
            self._stop_idle_detection()
            self._stop_tray_manager()
            self._root.destroy()

    def _handle_close_button(self) -> None:
        """
        Handle the window's OS close (X) button.

        Per the tray-integration requirements, this must NOT end the
        application: it hides the window to the system tray instead,
        showing a notification, while the live timer, idle detection,
        and break tracking all continue running exactly as before.
        Logout and Exit remain available from the tray menu (or the
        in-window Logout button, while the window is visible).
        """
        if self._tray_manager is None:
            # No tray available - fall back to the previous behaviour
            # rather than leaving the close button unresponsive.
            logger.error(
                "Close button pressed but no system tray is available; "
                "falling back to logout-on-close."
            )
            self._handle_window_close()
            return

        logger.info("Close button pressed; minimizing to the system tray.")
        self._tray_manager.hide_window()
        self._tray_manager.show_notification(APP_TITLE, TRAY_BACKGROUND_NOTICE)


# --------------------------------------------------------------------------- #
# Public Entry Point
# --------------------------------------------------------------------------- #

def launch_session_window(
    employee_display_name: str = "",
    on_logout: Optional[Callable[[WorkSession], None]] = None,
    employee: Optional[Employee] = None,
    config_manager: Optional[ConfigManager] = None,
    root: Optional[tk.Tk] = None,
) -> None:
    """
    Launch the live session timer window for the given employee.

    This is the single public entry point other modules should call
    to start tracking a work session and display the live timer.

    `root` is optional and defaults to None for backward compatibility:
    - If omitted, this function creates its own Tk() root and blocks
      here in mainloop() until logout (unchanged standalone behaviour).
    - If the caller supplies a root (as main.py now does, so the whole
      application stays on a single Tk root across the login -> session
      transition), the session UI is built on that root and this
      function returns immediately; the caller's own mainloop() -
      already running - continues to drive it.
    """
    owns_root = root is None
    active_root = root or tk.Tk()

    window = SessionTimerWindow(
        employee_display_name=employee_display_name,
        on_logout=on_logout,
        employee=employee,
        config_manager=config_manager,
        root=active_root,
    )

    if owns_root:
        window.run()


if __name__ == "__main__":
    def _print_summary(session: WorkSession) -> None:
        duration = SessionManager.format_duration(session.duration())
        print(f"Session ended for '{session.employee_display_name}'.")
        print(f"Login:  {session.login_time}")
        print(f"Logout: {session.logout_time}")
        print(f"Total duration: {duration}")

    launch_session_window(employee_display_name="Jaleel Ahamed", on_logout=_print_summary)