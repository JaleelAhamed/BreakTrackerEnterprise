"""
tray_manager.py
===============

Break Tracker Enterprise - System Tray Module

Responsibilities of this module (and only these):
    * Create and run a system tray icon (via pystray) on a background
      thread, without blocking Tkinter's main loop.
    * Hide and restore the Tkinter application window.
    * Build and manage the tray's right-click menu (Open / Logout / Exit).
    * Display tray (Windows balloon-style) notifications.
    * Invoke caller-supplied logout/exit callbacks and shut the tray
      down cleanly.

This module is fully self-contained: pystray and PIL are only ever
imported here. Other modules should only construct a `TrayManager` and
call its public methods (start, stop, hide_window, show_window,
toggle_window, show_notification, update_tooltip) - no tray-specific
logic belongs anywhere else in the project.

Author: Break Tracker Enterprise Team
Python: 3.13
"""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from typing import Callable, Optional

import pystray
from PIL import Image, ImageDraw
from pystray import Menu, MenuItem

from logger import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

DEFAULT_ICON_FILENAME: str = "icon.ico"
DEFAULT_ICON_SIZE: tuple[int, int] = (64, 64)
DEFAULT_ICON_BG_COLOR: tuple[int, int, int] = (31, 78, 120)  # Enterprise dark blue.
DEFAULT_ICON_FG_COLOR: tuple[int, int, int] = (255, 255, 255)
DEFAULT_ICON_LETTER: str = "B"


class TrayManager:
    """
    Manages the system tray icon and its interaction with a Tkinter
    application window.

    TrayManager owns:
        - The pystray.Icon instance and the background thread it runs on.
        - Hiding / restoring the Tk root window.
        - The tray's right-click menu (Open / Logout / Exit).
        - Tray notifications and tooltip text.

    TrayManager does NOT know anything about session, idle-detection,
    or report-generation logic. It only calls the `on_logout` /
    `on_exit` callbacks supplied to its constructor, and otherwise
    exposes a small set of public methods for the rest of the
    application to call.
    """

    def __init__(
        self,
        root: tk.Tk,
        application_name: str = "Break Tracker Enterprise",
        tooltip: Optional[str] = None,
        on_logout: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        icon_path: Optional[Path] = None,
    ) -> None:
        """
        Args:
            root: The application's single Tk root window.
            application_name: Used as the tray icon's internal name
                and as the default tooltip if none is supplied.
            tooltip: Text shown when hovering over the tray icon.
                Defaults to `application_name`.
            on_logout: Invoked (on the Tk main thread) when the user
                selects "Logout" from the tray menu.
            on_exit: Invoked (on the Tk main thread) when the user
                selects "Exit" from the tray menu. If omitted, the
                tray falls back to destroying `root` directly so the
                application can never be left hidden with no way to
                close it.
            icon_path: Optional path to an .ico file to use as the
                tray icon. Defaults to `icon.ico` next to this module.
                If the file is missing or fails to load, a simple
                default icon is generated instead - this never raises.
        """
        self._root = root
        self._application_name = application_name
        self._tooltip = tooltip or application_name
        self._on_logout = on_logout
        self._on_exit = on_exit
        self._icon_path = (
            Path(icon_path)
            if icon_path is not None
            else Path(__file__).resolve().parent / DEFAULT_ICON_FILENAME
        )

        self._icon: Optional[pystray.Icon] = None
        self._icon_thread: Optional[threading.Thread] = None
        self._is_running: bool = False
        self._is_window_hidden: bool = False

    # ------------------------------------------------------------------ #
    # Public lifecycle methods
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """
        Create and start the tray icon on a dedicated background thread.

        pystray's `Icon.run()` blocks the calling thread to pump its own
        event loop, so it must never be called directly on the Tkinter
        main thread - doing so would freeze the application window.
        Running it on a daemon thread keeps Tkinter fully responsive.

        Safe to call more than once: if the tray is already running,
        this logs and returns without creating a second icon.
        """
        if self._is_running:
            logger.info("Tray start() called but the tray is already running.")
            return

        try:
            image = self._load_icon_image()
            menu = self._build_menu()

            self._icon = pystray.Icon(
                name=self._application_name,
                icon=image,
                title=self._tooltip,
                menu=menu,
            )

            self._icon_thread = threading.Thread(
                target=self._run_icon_loop,
                name="TrayManagerIconThread",
                daemon=True,
            )
            self._icon_thread.start()

            self._is_running = True
            logger.info("Tray Started")
        except Exception:
            logger.exception("Failed to start the system tray icon.")

    def stop(self) -> None:
        """
        Stop the tray icon and let its background thread terminate.

        Safe to call multiple times, or before `start()` has been
        called; never raises.
        """
        if not self._is_running or self._icon is None:
            logger.info("Tray stop() called but the tray is not running.")
            return

        try:
            self._icon.stop()
        except Exception:
            logger.exception("Error stopping the system tray icon.")
        finally:
            self._is_running = False
            self._icon = None
            logger.info("Tray Stopped")

    # ------------------------------------------------------------------ #
    # Window visibility
    # ------------------------------------------------------------------ #

    def hide_window(self) -> None:
        """
        Hide the Tkinter window while keeping the application fully
        alive: any background monitoring already running elsewhere
        (idle detection, the live timer, etc.) is completely unaffected,
        and the tray icon remains available to restore the window.
        """
        try:
            # Marshal the actual widget call onto the Tk main thread -
            # this method may be invoked from the tray's own thread
            # (e.g. a menu click), and Tkinter is not thread-safe.
            self._root.after(0, self._hide_window_on_main_thread)
        except Exception:
            logger.exception("Failed to schedule window hide.")

    def show_window(self) -> None:
        """Restore (deiconify, raise, and focus) the Tkinter window."""
        try:
            self._root.after(0, self._show_window_on_main_thread)
        except Exception:
            logger.exception("Failed to schedule window restore.")

    def toggle_window(self) -> None:
        """Hide the window if it's currently visible, or restore it if hidden."""
        if self._is_window_hidden:
            self.show_window()
        else:
            self.hide_window()

    # -- internals that must run on the Tkinter main thread ------------- #

    def _hide_window_on_main_thread(self) -> None:
        try:
            self._root.withdraw()
            self._is_window_hidden = True
            logger.info("Window Hidden")
        except tk.TclError:
            logger.exception("Failed to hide the application window.")

    def _show_window_on_main_thread(self) -> None:
        try:
            self._root.deiconify()
            self._root.lift()
            self._root.focus_force()
            self._is_window_hidden = False
            logger.info("Window Restored")
        except tk.TclError:
            logger.exception("Failed to restore the application window.")

    # ------------------------------------------------------------------ #
    # Notifications
    # ------------------------------------------------------------------ #

    def show_notification(self, title: str, message: str) -> None:
        """
        Display a tray notification (a Windows balloon/toast where the
        platform's pystray backend supports it).

        Examples:
            show_notification("Break Tracker Enterprise", "Running in background.")
            show_notification("Break Tracker Enterprise", "Employee logged in.")
            show_notification("Break Tracker Enterprise", "Employee logged out.")

        This is a safe no-op (logged, not raised) if called before
        `start()`, or if the underlying notification call fails.
        """
        if self._icon is None:
            logger.info("show_notification() called before start(); ignoring.")
            return

        try:
            self._icon.notify(message, title)
            logger.info("Notification Displayed: %s - %s", title, message)
        except Exception:
            logger.exception("Failed to display tray notification.")

    def update_tooltip(self, text: str) -> None:
        """
        Update the tray icon's hover tooltip text.

        The new text is remembered even if called before `start()`, so
        the next call to `start()` picks it up automatically.
        """
        self._tooltip = text

        if self._icon is None:
            return

        try:
            self._icon.title = text
        except Exception:
            logger.exception("Failed to update tray tooltip.")

    # ------------------------------------------------------------------ #
    # Tray menu construction & callbacks
    # ------------------------------------------------------------------ #

    def _build_menu(self) -> Menu:
        """Build the right-click tray menu: Open / Logout / Exit."""
        return Menu(
            MenuItem("Open", self._handle_open, default=True),
            MenuItem("Logout", self._handle_logout),
            MenuItem("Exit", self._handle_exit),
        )

    def _handle_open(self, icon: pystray.Icon, item: MenuItem) -> None:
        """pystray callback (runs on the tray thread): restore the window."""
        self.show_window()

    def _handle_logout(self, icon: pystray.Icon, item: MenuItem) -> None:
        """pystray callback (runs on the tray thread): trigger logout."""
        logger.info("Logout Selected")
        if self._on_logout is None:
            return

        try:
            self._root.after(0, self._on_logout)
        except Exception:
            logger.exception("Error invoking logout callback.")

    def _handle_exit(self, icon: pystray.Icon, item: MenuItem) -> None:
        """
        pystray callback (runs on the tray thread): trigger application
        exit, then stop the tray icon regardless of whether a callback
        was supplied - this guarantees the tray can always be cleanly
        shut down from its own menu.
        """
        logger.info("Exit Selected")

        try:
            if self._on_exit is not None:
                self._root.after(0, self._on_exit)
            else:
                # No exit handler was supplied - fall back to destroying
                # the root directly so the app can never be left hidden
                # in the tray with no way to actually close it.
                self._root.after(0, self._root.destroy)
        except Exception:
            logger.exception("Error invoking exit callback.")
        finally:
            self.stop()

    # ------------------------------------------------------------------ #
    # Icon loop / image helpers
    # ------------------------------------------------------------------ #

    def _run_icon_loop(self) -> None:
        """Entry point for the background tray-icon thread."""
        try:
            self._icon.run()
        except Exception:
            logger.exception("Tray icon loop terminated unexpectedly.")
        finally:
            self._is_running = False

    def _load_icon_image(self) -> Image.Image:
        """
        Load the tray icon from `icon_path` if it exists and is a valid
        image; otherwise generate a simple default icon. This method
        never raises - a missing or broken icon file must never prevent
        the tray from starting.
        """
        if self._icon_path.exists():
            try:
                image = Image.open(self._icon_path)
                image.load()  # Force decode now, while we can still fall back.
                return image
            except Exception:
                logger.exception(
                    "Failed to load icon file '%s'; using a generated "
                    "default icon instead.",
                    self._icon_path,
                )

        return self._generate_default_icon()

    @staticmethod
    def _generate_default_icon() -> Image.Image:
        """
        Generate a simple, clean default tray icon with Pillow: a
        rounded, solid-colored square with the application's initial
        letter centered on it. Used whenever no usable icon.ico exists.
        """
        image = Image.new("RGBA", DEFAULT_ICON_SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        width, height = DEFAULT_ICON_SIZE
        margin = 4
        draw.rounded_rectangle(
            [margin, margin, width - margin, height - margin],
            radius=12,
            fill=DEFAULT_ICON_BG_COLOR,
        )

        try:
            # textbbox gives accurate metrics for centering; Pillow's
            # built-in bitmap font has no adjustable size, but this
            # still centers whatever it renders correctly.
            bbox = draw.textbbox((0, 0), DEFAULT_ICON_LETTER)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            position = (
                (width - text_width) / 2 - bbox[0],
                (height - text_height) / 2 - bbox[1],
            )
        except Exception:
            # Fall back to a reasonable fixed offset if metrics fail
            # for any reason - the icon must never fail to generate.
            position = (width / 2 - 4, height / 2 - 6)

        draw.text(position, DEFAULT_ICON_LETTER, fill=DEFAULT_ICON_FG_COLOR)
        return image

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def is_running(self) -> bool:
        """Whether the tray icon is currently active."""
        return self._is_running

    @property
    def is_window_hidden(self) -> bool:
        """Whether the Tkinter window is currently hidden."""
        return self._is_window_hidden