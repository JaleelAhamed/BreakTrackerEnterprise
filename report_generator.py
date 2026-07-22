"""
Break Tracker Enterprise
Report Generator Module

Version: 2.0.0

Generates professional Excel productivity reports using OpenPyXL.

Public API
----------
generate_session_report(employee, session, break_log, allowed_break_minutes) -> Path
    This is the stable entry point consumed by ``session.py``. Its
    signature and return type must not change.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from logger import get_logger

logger = get_logger(__name__)


# ======================================================================
# Design tokens
# ======================================================================
#
# All colors, spacing, and geometry used by the report live here so that
# the visual design can be tuned in one place without touching the
# report-building logic below.


@dataclass(frozen=True)
class _Palette:
    """Enterprise color palette used throughout the workbook."""

    dark_blue: str = "1F4E78"
    light_blue: str = "4F81BD"
    light_gray: str = "D9E2F3"
    white: str = "FFFFFF"
    black: str = "000000"


@dataclass(frozen=True)
class _Layout:
    """Shared geometry: column spans, row heights, and spacing."""

    section_span: int = 6       # columns spanned by titles & section headers
    table_span: int = 5         # columns spanned by the break-details table
    title_row_height: int = 28
    section_row_height: int = 22
    column_padding: int = 4     # extra width added by auto-fit


PALETTE = _Palette()
LAYOUT = _Layout()


class _StyleKit:
    """
    Builds and caches every Font / Fill / Border / Alignment the report
    needs, once, so call sites reference a shared style object by name
    instead of constructing (and duplicating) style objects inline.
    """

    def __init__(self, palette: _Palette) -> None:
        self.thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        self.title_fill = self._solid_fill(palette.dark_blue)
        self.section_fill = self._solid_fill(palette.light_blue)
        self.table_header_fill = self._solid_fill(palette.dark_blue)
        self.alternate_row_fill = self._solid_fill(palette.light_gray)

        self.title_font = Font(color=palette.white, bold=True, size=18)
        self.section_font = Font(color=palette.white, bold=True, size=12)
        self.table_header_font = Font(color=palette.white, bold=True)
        self.label_font = Font(color=palette.black, bold=True, size=11)
        self.value_font = Font(color=palette.black, size=11)

        self.center = Alignment(horizontal="center", vertical="center")
        self.left = Alignment(horizontal="left", vertical="center")

    @staticmethod
    def _solid_fill(color: str) -> PatternFill:
        return PatternFill(fill_type="solid", start_color=color, end_color=color)


# ======================================================================
# Report generator
# ======================================================================


class ExcelReportGenerator:
    """
    Builds a single-sheet, professionally formatted Break Tracker
    Enterprise productivity report.

    Usage is sequential: each ``add_*`` method appends one section to the
    worksheet and advances an internal row cursor, so sections always
    appear in the order they are called.
    """

    def __init__(self) -> None:
        self.workbook = Workbook()
        self.sheet: Worksheet = self.workbook.active
        self.sheet.title = "Employee Report"

        self.styles = _StyleKit(PALETTE)
        self.current_row = 1

    # ------------------------------------------------------------
    # Low-level cursor / cell helpers
    # ------------------------------------------------------------

    def _advance(self, rows: int = 1) -> None:
        """Move the row cursor forward."""
        self.current_row += rows

    def _write_banner(
        self,
        text: str,
        *,
        font: Font,
        fill: PatternFill,
        alignment: Alignment,
        row_height: int,
    ) -> None:
        """
        Writes a single full-width, merged, filled banner row (used for
        both the report title and section headers) and advances the
        cursor past it.
        """
        start_row = self.current_row

        self.sheet.merge_cells(
            start_row=start_row,
            start_column=1,
            end_row=start_row,
            end_column=LAYOUT.section_span,
        )

        cell = self.sheet.cell(row=start_row, column=1)
        cell.value = text
        cell.font = font
        cell.fill = fill
        cell.alignment = alignment

        self.sheet.row_dimensions[start_row].height = row_height

        self._advance()

    def _write_label_value(self, label: str, value: Any) -> None:
        """Writes one bordered ``label | value`` row."""
        label_cell = self.sheet.cell(row=self.current_row, column=1)
        value_cell = self.sheet.cell(row=self.current_row, column=2)

        label_cell.value = label
        value_cell.value = value

        for cell in (label_cell, value_cell):
            cell.border = self.styles.thin_border
            cell.alignment = self.styles.left

        label_cell.font = self.styles.label_font
        value_cell.font = self.styles.value_font

        self._advance()

    def _write_merged_note(self, text: str, span: int) -> None:
        """Writes a single centered, bordered note spanning ``span`` columns."""
        self.sheet.merge_cells(
            start_row=self.current_row,
            start_column=1,
            end_row=self.current_row,
            end_column=span,
        )

        cell = self.sheet.cell(row=self.current_row, column=1)
        cell.value = text
        cell.alignment = self.styles.center
        cell.border = self.styles.thin_border

        self._advance(2)

    # ------------------------------------------------------------
    # Section header helpers
    # ------------------------------------------------------------

    def _create_title_row(self, text: str) -> None:
        self._write_banner(
            text,
            font=self.styles.title_font,
            fill=self.styles.title_fill,
            alignment=self.styles.center,
            row_height=LAYOUT.title_row_height,
        )

    def _create_section_header(self, title: str) -> None:
        self._write_banner(
            title,
            font=self.styles.section_font,
            fill=self.styles.section_fill,
            alignment=self.styles.left,
            row_height=LAYOUT.section_row_height,
        )

    # ------------------------------------------------------------
    # Table helpers
    # ------------------------------------------------------------

    def _write_table_header(self, headers: Sequence[str]) -> None:
        """Writes a bold, filled header row and enables auto-filter on it."""
        header_row = self.current_row

        for column, header in enumerate(headers, start=1):
            cell = self.sheet.cell(row=header_row, column=column)
            cell.value = header
            cell.font = self.styles.table_header_font
            cell.fill = self.styles.table_header_fill
            cell.border = self.styles.thin_border
            cell.alignment = self.styles.center

        last_column = get_column_letter(len(headers))
        self.sheet.auto_filter.ref = f"A{header_row}:{last_column}{header_row}"

        self._advance()

    def _write_table_row(self, values: Sequence[Any], *, zebra: bool) -> None:
        """Writes one bordered, centered data row, optionally shaded."""
        for column, value in enumerate(values, start=1):
            cell = self.sheet.cell(row=self.current_row, column=column)
            cell.value = value
            cell.border = self.styles.thin_border
            cell.alignment = self.styles.center

            if zebra:
                cell.fill = self.styles.alternate_row_fill

        self._advance()

    # ------------------------------------------------------------
    # Formatting utilities
    # ------------------------------------------------------------

    @staticmethod
    def format_timedelta(duration: timedelta) -> str:
        """Converts a ``timedelta`` into an ``HH:MM:SS`` string."""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def auto_fit_columns(self) -> None:
        """Resizes every column to fit its widest cell's content."""
        for column_cells in self.sheet.columns:
            column_letter = get_column_letter(column_cells[0].column)

            longest = 0
            for cell in column_cells:
                if cell.value is None:
                    continue
                longest = max(longest, len(str(cell.value)))

            self.sheet.column_dimensions[column_letter].width = (
                longest + LAYOUT.column_padding
            )

    # ------------------------------------------------------------
    # Report sections
    # ------------------------------------------------------------

    def create_report_title(self) -> None:
        """Writes the two-line enterprise report title."""
        self._create_title_row("BREAK TRACKER ENTERPRISE")
        self._create_title_row("Employee Productivity Report")

    def add_employee_information(self, employee: Any, report_date: datetime) -> None:
        """Writes the Employee Information section."""
        self._create_section_header("Employee Information")

        self._write_label_value("Employee Name", getattr(employee, "name", ""))
        self._write_label_value("Employee ID", getattr(employee, "employee_id", ""))
        self._write_label_value("Department", getattr(employee, "department", ""))
        self._write_label_value("Designation", getattr(employee, "designation", ""))
        self._write_label_value("Report Date", report_date.strftime("%d-%b-%Y"))

        self._advance()

    def add_session_summary(
        self,
        login_time: datetime,
        logout_time: datetime,
        session_duration: timedelta,
        productive_time: timedelta,
    ) -> None:
        """Writes the Session Summary section."""
        self._create_section_header("Session Summary")

        self._write_label_value("Login Time", login_time.strftime("%H:%M:%S"))
        self._write_label_value("Logout Time", logout_time.strftime("%H:%M:%S"))
        self._write_label_value(
            "Total Session Duration", self.format_timedelta(session_duration)
        )
        self._write_label_value(
            "Productive Time", self.format_timedelta(productive_time)
        )

        self._advance()

    def add_break_summary(
        self,
        total_break: timedelta,
        allowed_break_minutes: int,
        exceeded_minutes: int,
        exceeded: bool,
    ) -> None:
        """Writes the Break Summary section."""
        self._create_section_header("Break Summary")

        self._write_label_value(
            "Total Break Duration", self.format_timedelta(total_break)
        )
        self._write_label_value("Allowed Break (Minutes)", allowed_break_minutes)
        self._write_label_value("Break Exceeded", "Yes" if exceeded else "No")
        self._write_label_value("Exceeded Minutes", exceeded_minutes)

        self._advance()

    def add_break_details(self, break_events: Sequence[Any]) -> None:
        """Writes the detailed, per-break history table."""
        self._create_section_header("Break Details")

        headers = ["No", "Break Start", "Break End", "Duration", "Reason"]
        self._write_table_header(headers)

        if not break_events:
            self._write_merged_note(
                "No breaks recorded during this session.", LAYOUT.table_span
            )
            return

        for index, event in enumerate(break_events, start=1):
            row_values = [
                index,
                event.start_time.strftime("%H:%M:%S"),
                event.end_time.strftime("%H:%M:%S"),
                self.format_timedelta(event.duration),
                event.reason if event.reason else "Not Specified",
            ]
            self._write_table_row(row_values, zebra=(index % 2 == 0))

        self._advance()

    def add_statistics(
        self,
        session_duration: timedelta,
        productive_time: timedelta,
        total_break: timedelta,
        break_events: Sequence[Any],
    ) -> float:
        """
        Writes the Productivity Statistics section and returns the
        computed productivity percentage for reuse in the Remarks section.
        """
        self._create_section_header("Productivity Statistics")

        break_count = len(break_events)

        if break_count > 0:
            longest_break = max(event.duration for event in break_events)
            average_break = total_break / break_count
        else:
            longest_break = timedelta(0)
            average_break = timedelta(0)

        productivity = 0.0
        if session_duration.total_seconds() > 0:
            productivity = (
                productive_time.total_seconds() / session_duration.total_seconds()
            ) * 100

        self._write_label_value("Break Count", break_count)
        self._write_label_value(
            "Longest Break", self.format_timedelta(longest_break)
        )
        self._write_label_value(
            "Average Break", self.format_timedelta(average_break)
        )
        self._write_label_value("Productivity %", f"{productivity:.2f} %")

        self._advance()

        return productivity

    def add_remarks(self, productivity: float, exceeded: bool) -> None:
        """Writes automatically generated remarks and an overall status."""
        self._create_section_header("Remarks")

        remark = (
            "Employee exceeded the configured break allowance."
            if exceeded
            else "Employee remained within the configured break allowance."
        )
        status = self._productivity_status(productivity)

        self._write_label_value("Remarks", remark)
        self._write_label_value("Overall Status", status)

        self._advance()

    @staticmethod
    def _productivity_status(productivity: float) -> str:
        """Maps a productivity percentage to a qualitative status label."""
        if productivity >= 90:
            return "Excellent"
        if productivity >= 75:
            return "Good"
        if productivity >= 60:
            return "Average"
        return "Needs Improvement"

    def add_footer(self) -> None:
        """Writes the report metadata footer."""
        self._create_section_header("Report Information")

        self._write_label_value("Generated By", "Break Tracker Enterprise")
        self._write_label_value("Version", "2.0.0")
        self._write_label_value(
            "Generated On", datetime.now().strftime("%d-%b-%Y %I:%M:%S %p")
        )

        self._advance()

    # ------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------

    def save(self, output_path: Path) -> Path:
        """Auto-fits columns and writes the workbook to ``output_path``."""
        self.auto_fit_columns()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.workbook.save(output_path)

        return output_path


# ======================================================================
# Public API
# ======================================================================


def _resolve_report_filename(employee: Any, timestamp: str) -> str:
    """Builds the report filename, tolerating either employee attribute name."""
    employee_name = getattr(employee, "employee_name", None) or getattr(
        employee, "name", "employee"
    )
    return f"{employee_name}_{timestamp}.xlsx"


def generate_session_report(
    employee: Any,
    session: Any,
    break_log: Any,
    allowed_break_minutes: int,
) -> Path:
    """
    Generates the employee session report.

    This function is the public API used by ``session.py`` and must keep
    this exact signature and return type.
    """
    employee_name = getattr(employee, "name", "<unknown>")
    logger.info("Report generation started for employee: %s", employee_name)

    try:
        session_duration: timedelta = session.duration()
        total_break: timedelta = break_log.total_duration()

        productive_time = session_duration - total_break
        if productive_time.total_seconds() < 0:
            productive_time = timedelta(0)

        exceeded_minutes = max(
            0,
            int(total_break.total_seconds() // 60) - allowed_break_minutes,
        )
        exceeded = exceeded_minutes > 0

        generator = ExcelReportGenerator()

        generator.create_report_title()

        generator.add_employee_information(
            employee=employee,
            report_date=datetime.now(),
        )

        generator.add_session_summary(
            login_time=session.login_time,
            logout_time=session.logout_time,
            session_duration=session_duration,
            productive_time=productive_time,
        )

        generator.add_break_summary(
            total_break=total_break,
            allowed_break_minutes=allowed_break_minutes,
            exceeded_minutes=exceeded_minutes,
            exceeded=exceeded,
        )

        generator.add_break_details(break_log.breaks)

        productivity = generator.add_statistics(
            session_duration=session_duration,
            productive_time=productive_time,
            total_break=total_break,
            break_events=break_log.breaks,
        )

        generator.add_remarks(productivity=productivity, exceeded=exceeded)

        generator.add_footer()

        logger.info("Employee report created for: %s", employee_name)

        reports_folder = Path(__file__).parent / "reports"
        reports_folder.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = _resolve_report_filename(employee, timestamp)
        report_path = reports_folder / filename

        saved_path = generator.save(report_path)
        logger.info("Excel file saved: %s", saved_path)
        logger.info("Report path: %s", saved_path)

        return saved_path

    except Exception:
        logger.exception("Report generation failed for employee: %s", employee_name)
        raise