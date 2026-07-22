"""
main.py
=======

Break Tracker Enterprise

Application Entry Point

Responsibilities
----------------
- Start the application
- Load/Register employee
- Launch the work session
- Handle unexpected startup errors

Business logic belongs in the individual modules.
This file only coordinates the application flow.

Single-root architecture
-------------------------
The application uses exactly ONE Tk() root for its entire lifetime,
created here and passed down to both launch_employee_flow() and
launch_session_window(). Those functions build their windows onto
this shared root instead of creating their own, and mainloop() is
called exactly once, right here, after the first window is shown.

This matters: previously each stage created its own Tk() and called
its own mainloop(), so logging in triggered a *nested* mainloop while
the Employee window's mainloop() was still on the call stack. That
left the old window stuck alive (visible in the taskbar) until logout,
caused the live session timer to bind unreliably across two competing
Tk interpreters, and left a dangling window that raised
`tkinter.TclError: application has been destroyed` if closed by hand.
With a single root and a single mainloop(), none of that can happen.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from employee import (
    Employee,
    ConfigManager,
    launch_employee_flow,
)

from session import launch_session_window

from logger import get_logger

logger = get_logger(__name__)


class BreakTrackerApplication:
    """Coordinates the overall application startup."""

    def __init__(self) -> None:
        self.config_manager = ConfigManager()
        # Created once run() starts; shared by every window shown for
        # the lifetime of the application.
        self.root: tk.Tk | None = None

    def run(self) -> None:
        """
        Start Break Tracker Enterprise.
        """

        logger.info("Application started")

        try:
            self.config_manager.ensure_config_exists()

            self.root = tk.Tk()

            launch_employee_flow(
                config_manager=self.config_manager,
                on_registered=self.start_session,
                on_login=self.start_session,
                root=self.root,
            )

            # The one and only mainloop() call for the entire
            # application. It starts here (showing the Registration or
            # Login window) and keeps running - uninterrupted - through
            # the transition into the Session window, returning only
            # once the Session window destroys the root at logout.
            self.root.mainloop()

            # mainloop() only returns once the shared root has been
            # destroyed (i.e. at logout), so reaching this line means
            # the application is shutting down normally.
            logger.info("Application closed")

        except Exception as exc:
            logger.exception("Unhandled exception during application startup")
            self._show_error(
                "Startup Error",
                f"Unable to start Break Tracker Enterprise.\n\n{exc}",
            )

    def start_session(self, employee: Employee) -> None:
        """
        Launch the employee work session.

        Called as the on_registered/on_login callback from the
        Employee window, which has already torn down its own widgets
        on the shared root before invoking this. This method builds
        the Session UI onto that same root - it does not open a new
        window or call mainloop() again; the loop started in run() is
        still running and simply continues driving the new UI.
        """

        try:
            launch_session_window(
                employee_display_name=employee.name,
                employee=employee,
                config_manager=self.config_manager,
                root=self.root,
            )

        except Exception as exc:
            logger.exception("Unhandled exception while starting the employee session")
            self._show_error(
                "Session Error",
                f"Unable to start the employee session.\n\n{exc}",
            )

    @staticmethod
    def _show_error(title: str, message: str) -> None:
        """Display a fatal application error."""

        root = tk.Tk()
        root.withdraw()

        messagebox.showerror(title, message)

        root.destroy()


def main() -> None:
    """Application entry point."""

    app = BreakTrackerApplication()
    app.run()


if __name__ == "__main__":
    main()