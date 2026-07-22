"""
idle.py
=======

Break Tracker Enterprise - Idle Detection Module (Sprint 3)

Responsibilities of this module (and only these):
    * Detect keyboard/mouse inactivity (idle threshold: 3 minutes).
    * Once activity resumes after an idle period that met/exceeded the
      threshold, prompt the employee for a break reason.
    * Represent each qualifying idle period as a `BreakEvent`.
    * Maintain a running `BreakLog` for the current work session.

This module does NOT implement report generation, session login/logout,
or employee registration - it only extends those existing modules by
consuming a display name / session context passed in by the caller.

Global mouse/keyboard activity cannot be observed from Tkinter alone,
so a background thread (via `pynput`) is used strictly for OS-level
input hooks. All UI updates and state transitions are still driven from
the main thread using Tkinter's `after()`, per project convention.

Author: Break Tracker Enterprise Team
Python: 3.13
"""

from __future__ import annotations

import threading
import tkinter as tk
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from tkinter import ttk
from typing import Callable, Optional

try:
    from pynput import keyboard, mouse
except ImportError as exc:  # pragma: no cover - environment guard
    raise ImportError(
        "The 'pynput' package is required for idle detection. "
        "Install it with: pip install pynput"
    ) from exc

from logger import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

APP_TITLE: str = "Break Tracker Enterprise"
IDLE_THRESHOLD: timedelta = timedelta(minutes=3)
POLL_INTERVAL_MS: int = 1000  # Check activity state once per second.

BREAK_REASONS: tuple[str, ...] = (
    "Tea Break",
    "Lunch",
    "Restroom",
    "Meeting",
    "Phone Call",
    "Technical Issue",
    "Personal Work",
    "Other",
)


# --------------------------------------------------------------------------- #
# Data Model
# --------------------------------------------------------------------------- #

@dataclass
class BreakEvent:
    """Represents a single qualifying idle/break period."""

    start_time: datetime
    end_time: datetime
    duration: timedelta
    reason: str = ""

    def formatted_duration(self) -> str:
        """Return the break duration formatted as HH:MM:SS."""
        total_seconds = max(int(self.duration.total_seconds()), 0)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class BreakLog:
    """
    Holds the collection of BreakEvents recorded during a work session.

    Kept separate from UI/detection code so it can be handed directly
    to the report-generation module (Sprint 4) without modification.
    """

    def __init__(self) -> None:
        self._breaks: list[BreakEvent] = []

    def add(self, break_event: BreakEvent) -> None:
        """Append a completed break event to the log."""
        self._breaks.append(break_event)

    @property
    def breaks(self) -> list[BreakEvent]:
        """Return a copy of the recorded break events, in order."""
        return list(self._breaks)

    def total_duration(self) -> timedelta:
        """Return the sum of all recorded break durations."""
        total = timedelta(0)
        for break_event in self._breaks:
            total += break_event.duration
        return total

    def count(self) -> int:
        """Return the number of recorded breaks."""
        return len(self._breaks)


# --------------------------------------------------------------------------- #
# Activity Tracking (background OS-level hooks)
# --------------------------------------------------------------------------- #

class ActivityTracker:
    """
    Tracks the timestamp of the most recent keyboard or mouse activity.

    Uses `pynput` background listener threads solely to receive OS-level
    input events - this is the one place in the application where a
    thread is unavoidable, since Tkinter cannot observe global input.
    The tracked timestamp is read by the main-thread poller via a lock,
    so no other application logic runs on the listener threads.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_activity: datetime = datetime.now()
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None

    def start(self) -> None:
        """Start background listeners for mouse and keyboard activity."""
        self._mouse_listener = mouse.Listener(
            on_move=self._on_activity,
            on_click=self._on_activity,
            on_scroll=self._on_activity,
        )
        self._keyboard_listener = keyboard.Listener(on_press=self._on_activity)

        self._mouse_listener.start()
        self._keyboard_listener.start()

    def stop(self) -> None:
        """Stop background listeners, releasing OS input hooks."""
        if self._mouse_listener is not None:
            self._mouse_listener.stop()
            self._mouse_listener = None
        if self._keyboard_listener is not None:
            self._keyboard_listener.stop()
            self._keyboard_listener = None

    def get_last_activity(self) -> datetime:
        """Return the timestamp of the most recently observed activity."""
        with self._lock:
            return self._last_activity

    def _on_activity(self, *_args: object, **_kwargs: object) -> None:
        """Callback invoked by pynput on any mouse/keyboard event."""
        with self._lock:
            self._last_activity = datetime.now()


# --------------------------------------------------------------------------- #
# Idle Detection Logic (UI-independent)
# --------------------------------------------------------------------------- #

class IdleDetector:
    """
    Pure business logic that turns raw activity timestamps into
    break events, independent of both Tkinter and pynput.

    Call `poll()` on a regular interval (driven by Tkinter's `after()`
    in the caller). It returns a completed `BreakEvent` whenever an
    idle period that met the threshold has just ended, otherwise None.
    """

    def __init__(
        self,
        tracker: ActivityTracker,
        idle_threshold: timedelta = IDLE_THRESHOLD,
    ) -> None:
        self._tracker = tracker
        self._idle_threshold = idle_threshold

        self._is_idle: bool = False
        self._idle_start: Optional[datetime] = None
        self._last_seen_activity: datetime = tracker.get_last_activity()

    def poll(self) -> Optional[BreakEvent]:
        """
        Check current activity state and update internal idle tracking.

        Returns:
            A BreakEvent if a qualifying idle period (>= threshold) has
            just ended (i.e. activity resumed), otherwise None.
        """
        now = datetime.now()
        current_activity = self._tracker.get_last_activity()
        activity_occurred = current_activity != self._last_seen_activity

        if activity_occurred:
            return self._handle_activity_resumed(current_activity)

        self._handle_no_new_activity(now, current_activity)
        return None

    # -- internal helpers ---------------------------------------------- #

    def _handle_activity_resumed(self, current_activity: datetime) -> Optional[BreakEvent]:
        """Process the transition from idle back to active, if any."""
        self._last_seen_activity = current_activity

        if not self._is_idle:
            # Activity within the first 3 minutes - ignored entirely.
            return None

        idle_start = self._idle_start
        idle_end = current_activity
        self._is_idle = False
        self._idle_start = None

        if idle_start is None:
            return None

        idle_duration = idle_end - idle_start
        if idle_duration < self._idle_threshold:
            # Should not normally happen (we only set _is_idle once the
            # threshold is crossed), but guard defensively regardless.
            return None

        logger.info(
            "Break ended at %s; break duration %s", idle_end, idle_duration
        )

        return BreakEvent(start_time=idle_start, end_time=idle_end, duration=idle_duration)

    def _handle_no_new_activity(self, now: datetime, current_activity: datetime) -> None:
        """Update idle state when no new activity has been observed."""
        if self._is_idle:
            return  # Already tracking an idle period; nothing new to do.

        idle_duration = now - current_activity
        if idle_duration >= self._idle_threshold:
            self._is_idle = True
            self._idle_start = current_activity
            logger.info("Idle detected; break started at %s", current_activity)


# --------------------------------------------------------------------------- #
# UI Helpers
# --------------------------------------------------------------------------- #

def _center_window(window: tk.Toplevel, width: int, height: int) -> None:
    """Center a Tkinter window on the user's screen."""
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


# --------------------------------------------------------------------------- #
# Break Reason Popup (UI)
# --------------------------------------------------------------------------- #

class BreakReasonDialog:
    """
    Modal popup shown when activity resumes after a qualifying idle
    period. Displays the break start/end time and total duration, and
    asks the employee to select a reason before the dialog can close.

    The dialog also guarantees it is actually seen: since it appears the
    moment the employee returns, it forces itself to the front and takes
    focus rather than relying on the employee to notice it (see
    `_bring_to_front`).
    """

    WINDOW_WIDTH: int = 380
    WINDOW_HEIGHT: int = 320

    def __init__(
        self,
        parent: tk.Misc,
        break_event: BreakEvent,
        on_reason_selected: Callable[[BreakEvent], None],
    ) -> None:
        self._break_event = break_event
        self._on_reason_selected = on_reason_selected

        self._window = tk.Toplevel(parent)
        self._window.title("Break Detected")
        self._window.resizable(False, False)
        _center_window(self._window, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        # Keep the popup modal so a reason must be chosen before
        # tracking can continue.
        self._window.grab_set()
        self._window.protocol("WM_DELETE_WINDOW", self._handle_confirm)

        self._reason_var = tk.StringVar(value=BREAK_REASONS[0])

        self._build_ui()
        self._bring_to_front()

    def _bring_to_front(self) -> None:
        """
        Ensure the popup is immediately visible and focused.

        The employee has typically just returned from being away, so the
        dialog must not be left sitting in the taskbar or behind other
        windows: it is raised, given input focus, and briefly pinned
        above all other windows just long enough to guarantee it is
        actually seen before that pin is released.
        """
        self._window.lift()
        self._window.focus_force()
        self._window.attributes("-topmost", True)
        self._window.after(100, lambda: self._window.attributes("-topmost", False))

    def _build_ui(self) -> None:
        container = tk.Frame(self._window, padx=25, pady=20)
        container.pack(fill="both", expand=True)

        title_label = tk.Label(
            container, text="Welcome Back", font=("Segoe UI", 14, "bold")
        )
        title_label.pack(pady=(0, 12))

        info_frame = tk.Frame(container)
        info_frame.pack(fill="x", pady=(0, 12))

        self._add_info_row(info_frame, 0, "Break Start", self._format_time(self._break_event.start_time))
        self._add_info_row(info_frame, 1, "Break End", self._format_time(self._break_event.end_time))
        self._add_info_row(info_frame, 2, "Total Duration", self._break_event.formatted_duration())

        info_frame.columnconfigure(1, weight=1)

        reason_label = tk.Label(container, text="Reason for Break", anchor="w")
        reason_label.pack(fill="x", pady=(4, 4))

        reason_dropdown = ttk.Combobox(
            container,
            textvariable=self._reason_var,
            values=BREAK_REASONS,
            state="readonly",
        )
        reason_dropdown.pack(fill="x", pady=(0, 20))

        confirm_button = tk.Button(
            container, text="Confirm", width=18, command=self._handle_confirm
        )
        confirm_button.pack()

    @staticmethod
    def _add_info_row(parent: tk.Frame, row: int, label_text: str, value: str) -> None:
        """Add a consistently spaced, aligned label/value pair."""
        label = tk.Label(parent, text=label_text, anchor="w", width=14)
        label.grid(row=row, column=0, sticky="w", pady=4)

        value_label = tk.Label(parent, text=value, anchor="w")
        value_label.grid(row=row, column=1, sticky="ew", pady=4)

    @staticmethod
    def _format_time(moment: datetime) -> str:
        """Format a datetime as a readable HH:MM:SS string."""
        return moment.strftime("%H:%M:%S")

    def _handle_confirm(self) -> None:
        self._break_event.reason = self._reason_var.get()
        logger.info("Break reason submitted: %s", self._break_event.reason)
        self._on_reason_selected(self._break_event)
        self._window.grab_release()
        self._window.destroy()


# --------------------------------------------------------------------------- #
# Idle Tracking Controller (integration point)
# --------------------------------------------------------------------------- #

class IdleTrackingController:
    """
    Wires ActivityTracker + IdleDetector into the Tkinter event loop
    and owns the BreakLog for the current session.

    This is the single integration point another module (e.g. the
    session window) should use: construct it with the active Tk root,
    call `start()` once the session has begun, and call `stop()` on
    logout before generating the report.
    """

    def __init__(
        self,
        root: tk.Misc,
        idle_threshold: timedelta = IDLE_THRESHOLD,
        poll_interval_ms: int = POLL_INTERVAL_MS,
        on_break_logged: Optional[Callable[[BreakEvent], None]] = None,
    ) -> None:
        self._root = root
        self._poll_interval_ms = poll_interval_ms
        self._on_break_logged = on_break_logged

        self._tracker = ActivityTracker()
        self._detector = IdleDetector(self._tracker, idle_threshold)
        self._break_log = BreakLog()

        self._after_id: Optional[str] = None
        self._running: bool = False

    @property
    def break_log(self) -> BreakLog:
        """Expose the running BreakLog (e.g. for report generation)."""
        return self._break_log

    def start(self) -> None:
        """Begin monitoring activity and polling for idle transitions."""
        if self._running:
            return
        self._tracker.start()
        self._running = True
        self._schedule_next_poll()

    def stop(self) -> None:
        """Stop monitoring activity (call this on logout)."""
        if not self._running:
            return
        if self._after_id is not None:
            self._root.after_cancel(self._after_id)
            self._after_id = None
        self._tracker.stop()
        self._running = False

    # -- internal helpers ---------------------------------------------- #

    def _schedule_next_poll(self) -> None:
        self._poll_once()
        self._after_id = self._root.after(self._poll_interval_ms, self._schedule_next_poll)

    def _poll_once(self) -> None:
        break_event = self._detector.poll()
        if break_event is not None:
            self._prompt_for_reason(break_event)

    def _prompt_for_reason(self, break_event: BreakEvent) -> None:
        logger.info(
            "Idle popup displayed for break duration %s",
            break_event.formatted_duration(),
        )
        BreakReasonDialog(
            parent=self._root,
            break_event=break_event,
            on_reason_selected=self._handle_reason_selected,
        )

    def _handle_reason_selected(self, break_event: BreakEvent) -> None:
        self._break_log.add(break_event)
        if self._on_break_logged:
            self._on_break_logged(break_event)