"""
admin_settings.py
==================

Break Tracker Enterprise
Administrator Settings Launcher

Version: 1.0.0
Sprint: 9

Standalone entry point that lets an administrator open the
Settings window independently of the employee application.

Run directly:

    python admin_settings.py

Responsibilities
----------------
- Create a hidden Tkinter root window.
- Launch the SettingsWindow as a child of that hidden root.
- Start the Tkinter main loop.
- Exit cleanly once the Settings window is closed.

Isolation from the employee workflow
-------------------------------------
This module is completely separate from the employee application
flow started in main.py. It is not imported by main.py, does not
share a root with the employee windows, and does not run alongside
them - it is only ever launched on its own, directly by an
administrator.

Authentication
---------------
No administrator authentication is implemented yet. Anyone able to
run this script can currently open the Settings window. Access
control is planned for a future sprint and must be added before
this launcher is exposed outside of trusted administrator use.
"""

from __future__ import annotations

import tkinter as tk

from settings import SettingsWindow

from logger import get_logger

logger = get_logger(__name__)


def launch_admin_settings() -> None:
    """
    Launch the Settings window in standalone administrator mode.

    Creates a hidden Tk root so no empty base window is shown to
    the administrator, opens the SettingsWindow as a Toplevel on
    that root, and then runs the Tkinter main loop until the
    Settings window is closed - at which point the hidden root is
    destroyed as well and the process exits.
    """

    logger.info("Administrator settings launcher started.")

    root = tk.Tk()
    root.withdraw()

    def _on_settings_closed() -> None:
        """Tear down the hidden root once Settings is closed."""

        try:
            root.destroy()
        except tk.TclError:
            # Root may already be gone; nothing further to do.
            pass

    settings_window = SettingsWindow(master=root)

    # SettingsWindow already handles its own close/cancel/save
    # confirmation flow internally. We just need the hidden root to
    # go away once that Toplevel is gone, so the process can exit
    # instead of hanging on an invisible window.
    settings_window.root.bind(
        "<Destroy>",
        lambda event: _on_settings_closed()
        if event.widget is settings_window.root
        else None,
    )

    root.mainloop()

    logger.info("Administrator settings launcher closed.")


def main() -> None:
    """Administrator settings entry point."""

    launch_admin_settings()


if __name__ == "__main__":
    main()