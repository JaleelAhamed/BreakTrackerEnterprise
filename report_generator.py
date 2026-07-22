"""
report_generator.py
====================

Break Tracker Enterprise - Report Generation Module (Sprint 4)

Responsibilities of this module (and only these):
    * Generate an Excel (.xlsx) report summarizing a completed work
      session and its recorded breaks.
    * Save the report under `reports/EmployeeID_YYYY-MM-DD.xlsx`,
      creating the folder automatically if needed.

This module does NOT implement idle detection, session tracking, or
employee management - it consumes an `Employee`, a session-like object,
and a `BreakLog` produced by those existing modules.

IMPORTANT: this module must never import session.py. session.py is the
coordinator and imports report_generator.py to trigger report creation
on logout; importing session.py back from here would create a circular
import. Instead of importing the concrete `WorkSession` class, this
module depends only on the minimal structural shape it actually needs
(`SessionLike`, defined below).

Author: Break Tracker Enterprise Team
Python: 3.13
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from employee import Employee
from idle_detector import BreakEvent, BreakLog

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

REPORTS_DIR_NAME: str = "reports"
DEFAULT_ALLOWED_BREAK_MINUTES: int = 60

SESSION_SUMMARY_SHEET_NAME: str = "Session Summary"
BREAK_DETAILS_SHEET_NAME: str = "Break Details"

HEADER_FONT: Font = Font(bold=True)


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #

class ReportGenerationError(Exception):
    """Raised when the Excel report cannot be built or saved."""


# --------------------------------------------------------------------------- #
# Structural session type (avoids importing session.py)
# --------------------------------------------------------------------------- #

@runtime_checkable
class SessionLike(Protocol):
    """
    Describes the minimal interface this module needs from a session
    object: login/logout timestamps and a duration() method. Any
    object satisfying this shape - including session.py's WorkSession -
    can be passed in without report_generator.py importing session.py.
    """

    login_time: Optional[datetime]
    logout_time: Optional[datetime]

    def duration(self, as_of: Optional[datetime] = None) -> timedelta: ...


# --------------------------------------------------------------------------- #
# Data Model
# --------------------------------------------------------------------------- #

@dataclass
class SessionReportData:
    """
    Aggregated, report-ready figures derived from a session-like object
    and BreakLog. Kept separate from the workbook-building code so the
    calculations can be verified/tested independently of openpyxl.
    """

    employee: Employee
    session: SessionLike
    breaks: list[BreakEvent]
    allowed_break_minutes: int
    total_session_duration: timedelta
    total_break_duration: timedelta
    productive_duration: timedelta
    break_exceeded: bool
    exceeded_minutes: int


# --------------------------------------------------------------------------- #
# Business Logic (UI/workbook independent)
# --------------------------------------------------------------------------- #

def build_report_data(
    employee: Employee,
    session: SessionLike,
    break_log: BreakLog,
    allowed_break_minutes: int = DEFAULT_ALLOWED_BREAK_MINUTES,
) -> SessionReportData:
    """
    Compute all summary figures needed for the report from raw
    session/break objects.

    Raises:
        ReportGenerationError: if the session has no login/logout time.
    """
    if session.login_time is None or session.logout_time is None:
        raise ReportGenerationError(
            "Cannot generate a report for a session without both a "
            "login time and a logout time."
        )

    total_session_duration = session.duration()
    total_break_duration = break_log.total_duration()
    productive_duration = total_session_duration - total_break_duration

    total_break_minutes = total_break_duration.total_seconds() / 60
    break_exceeded = total_break_minutes > allowed_break_minutes
    exceeded_minutes = (
        int(round(total_break_minutes - allowed_break_minutes)) if break_exceeded else 0
    )

    return SessionReportData(
        employee=employee,
        session=session,
        breaks=break_log.breaks,
        allowed_break_minutes=allowed_break_minutes,
        total_session_duration=total_session_duration,
        total_break_duration=total_break_duration,
        productive_duration=productive_duration,
        break_exceeded=break_exceeded,
        exceeded_minutes=exceeded_minutes,
    )


def build_report_file_path(employee: Employee, session: SessionLike, base_dir: Path) -> Path:
    """
    Build the output path for the report file:
        reports/EmployeeID_YYYY-MM-DD.xlsx
    """
    report_date = (session.login_time or datetime.now()).strftime("%Y-%m-%d")
    file_name = f"{employee.employee_id}_{report_date}.xlsx"
    return base_dir / REPORTS_DIR_NAME / file_name


def format_duration(duration: timedelta) -> str:
    """Format a timedelta as HH:MM:SS for display in the workbook."""
    total_seconds = max(int(duration.total_seconds()), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_time(moment: Optional[datetime]) -> str:
    """Format a datetime as HH:MM:SS, or an empty string if missing."""
    return moment.strftime("%H:%M:%S") if moment else ""


# --------------------------------------------------------------------------- #
# Workbook Construction
# --------------------------------------------------------------------------- #

class ReportGenerator:
    """
    Builds and saves the Excel report for a completed work session.

    Separated into small, focused methods so each sheet's construction
    can be reasoned about (and tested) independently.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        # base_dir defaults to this module's directory, matching the
        # convention used by config.json in employee.py.
        self._base_dir: Path = base_dir or Path(__file__).resolve().parent

    def generate(
        self,
        employee: Employee,
        session: SessionLike,
        break_log: BreakLog,
        allowed_break_minutes: int = DEFAULT_ALLOWED_BREAK_MINUTES,
    ) -> Path:
        """
        Generate the full workbook and save it to disk.

        Returns:
            The Path to the saved .xlsx report.

        Raises:
            ReportGenerationError: if the report cannot be built or saved.
        """
        report_data = build_report_data(employee, session, break_log, allowed_break_minutes)
        output_path = build_report_file_path(employee, session, self._base_dir)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ReportGenerationError(
                f"Unable to create reports directory: {exc}"
            ) from exc

        workbook = Workbook()

        # openpyxl creates one default sheet; repurpose it as Sheet 1.
        summary_sheet = workbook.active
        summary_sheet.title = SESSION_SUMMARY_SHEET_NAME
        self._write_summary_sheet(summary_sheet, report_data)

        break_sheet = workbook.create_sheet(BREAK_DETAILS_SHEET_NAME)
        self._write_break_details_sheet(break_sheet, report_data.breaks)

        try:
            workbook.save(output_path)
        except OSError as exc:
            raise ReportGenerationError(
                f"Unable to save report to '{output_path}': {exc}"
            ) from exc

        return output_path

    # -- Sheet 1: Session Summary ---------------------------------------- #

    @staticmethod
    def _write_summary_sheet(sheet: Worksheet, data: SessionReportData) -> None:
        rows: list[tuple[str, object]] = [
            ("Employee Name", data.employee.name),
            ("Employee ID", data.employee.employee_id),
            ("Department", data.employee.department),
            ("Designation", data.employee.designation),
            ("Date", (data.session.login_time or datetime.now()).strftime("%Y-%m-%d")),
            ("Login Time", format_time(data.session.login_time)),
            ("Logout Time", format_time(data.session.logout_time)),
            ("Total Session Duration", format_duration(data.total_session_duration)),
            ("Total Break Duration", format_duration(data.total_break_duration)),
            ("Productive Time", format_duration(data.productive_duration)),
            ("Allowed Break (minutes)", data.allowed_break_minutes),
            ("Break Exceeded", "Yes" if data.break_exceeded else "No"),
            ("Exceeded Minutes", data.exceeded_minutes),
        ]

        sheet.append(["Field", "Value"])
        for label, value in rows:
            sheet.append([label, value])

        ReportGenerator._apply_header_formatting(sheet, header_row=1, num_columns=2)
        ReportGenerator._auto_size_columns(sheet)
        sheet.freeze_panes = "A2"

    # -- Sheet 2: Break Details ------------------------------------------- #

    @staticmethod
    def _write_break_details_sheet(sheet: Worksheet, breaks: list[BreakEvent]) -> None:
        headers = ["Break Number", "Start Time", "End Time", "Duration", "Reason"]
        sheet.append(headers)

        for index, break_event in enumerate(breaks, start=1):
            sheet.append([
                index,
                format_time(break_event.start_time),
                format_time(break_event.end_time),
                break_event.formatted_duration(),
                break_event.reason,
            ])

        ReportGenerator._apply_header_formatting(sheet, header_row=1, num_columns=len(headers))
        ReportGenerator._auto_size_columns(sheet)
        sheet.freeze_panes = "A2"

    # -- Shared formatting helpers ----------------------------------------- #

    @staticmethod
    def _apply_header_formatting(sheet: Worksheet, header_row: int, num_columns: int) -> None:
        """Bold the header row across the given number of columns."""
        for column_index in range(1, num_columns + 1):
            cell = sheet.cell(row=header_row, column=column_index)
            cell.font = HEADER_FONT

    @staticmethod
    def _auto_size_columns(sheet: Worksheet, padding: int = 2) -> None:
        """
        Approximate auto-sizing of column widths based on the longest
        rendered value in each column (openpyxl has no native
        auto-fit, so width is estimated from cell content length).
        """
        for column_cells in sheet.columns:
            longest_value_length = 0
            column_letter = get_column_letter(column_cells[0].column)

            for cell in column_cells:
                if cell.value is not None:
                    longest_value_length = max(longest_value_length, len(str(cell.value)))

            sheet.column_dimensions[column_letter].width = longest_value_length + padding


# --------------------------------------------------------------------------- #
# Public Entry Point (integration point)
# --------------------------------------------------------------------------- #

def generate_session_report(
    employee: Employee,
    session: SessionLike,
    break_log: BreakLog,
    allowed_break_minutes: int = DEFAULT_ALLOWED_BREAK_MINUTES,
    base_dir: Optional[Path] = None,
) -> Path:
    """
    Convenience function other modules should call on logout to
    generate and save the Excel report in one step.

    `session` only needs to satisfy `SessionLike` (login_time,
    logout_time, duration()) - session.py's WorkSession qualifies
    automatically without this module importing session.py.

    Example integration (in session.py's logout handler):

        from report_generator import generate_session_report

        def _on_logout(session: WorkSession) -> None:
            report_path = generate_session_report(
                employee=current_employee,
                session=session,
                break_log=idle_controller.break_log,
            )
            print(f"Report saved to: {report_path}")
    """
    generator = ReportGenerator(base_dir=base_dir)
    return generator.generate(employee, session, break_log, allowed_break_minutes)