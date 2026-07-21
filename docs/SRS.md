# Software Requirements Specification (SRS)

# Break Tracker Enterprise

**Version:** 1.0.0-alpha

**Document Version:** 1.0

**Prepared By:** Jaleel Ahamed

**Project Type:** Personal Portfolio Project

**Technology:** Python Desktop Application

**Status:** Draft

---

# 1. Introduction

## 1.1 Purpose

The purpose of Break Tracker Enterprise is to develop a desktop application capable of monitoring employee system activity, detecting idle time, tracking breaks, collecting break reasons, generating professional reports, and providing productivity insights.

The application demonstrates enterprise desktop application development using Python and serves as a personal portfolio project showcasing software architecture, desktop automation, reporting, and application design.

---

## 1.2 Project Objectives

The objectives of this project are:

- Develop an enterprise-style desktop application.
- Automatically detect employee inactivity.
- Track total break duration.
- Generate professional Excel reports.
- Store employee information locally.
- Upload reports to centralized storage (future enhancement).
- Provide a manager dashboard for reviewing employee productivity.
- Demonstrate software engineering best practices.

---

## 1.3 Scope

Break Tracker Enterprise monitors employee activity during working hours.

The application records:

- Employee Login
- Employee Logout
- Working Session Duration
- Idle Time
- Break Time
- Break Reasons
- Productivity Statistics

Reports are generated automatically when the employee logs out.

Future versions will support centralized reporting and web dashboards.

---

# 2. Overall Description

## 2.1 Product Perspective

Break Tracker Enterprise is a standalone Windows desktop application.

Version 1 focuses on local execution and report generation.

Future versions will introduce:

- SharePoint Integration
- NAS Storage
- SQLite Database
- Web Dashboard
- Analytics

---

## 2.2 User Types

### Employee

Can:

- Register
- Login
- Logout
- View own reports
- Provide break reasons

---

### Manager

Can:

- Review employee reports
- View dashboard
- Monitor break statistics

---

### HR

Can:

- Review reports
- Analyze employee productivity
- Export reports

---

# 3. Functional Requirements

## FR-01 Employee Registration

The system shall allow first-time employee registration.

Information collected:

- Employee Name
- Employee ID
- Department
- Designation

The information shall be stored locally.

---

## FR-02 Employee Login

The application shall:

- Display saved employee details.
- Allow one-click login.
- Record login timestamp.

---

## FR-03 Session Tracking

The system shall record:

- Login Time
- Logout Time
- Session Duration

---

## FR-04 Idle Detection

The system shall continuously monitor:

- Mouse Activity
- Keyboard Activity

If no activity is detected for more than 3 minutes:

The employee shall be considered idle.

---

## FR-05 Break Calculation

After the first three minutes of inactivity,

every additional minute shall be counted as break time.

---

## FR-06 Break Reason Collection

When activity resumes,

a popup shall display:

- Break Duration
- Start Time
- End Time

The employee shall select a reason.

Available reasons:

- Tea Break
- Lunch
- Restroom
- Meeting
- Phone Call
- Technical Issue
- Personal Work
- Other

---

## FR-07 Report Generation

Upon logout,

the system shall automatically generate an Excel report.

The report shall contain:

Employee Information

Session Summary

Break Summary

Break Details

Exceeded Break Time

Remarks

---

## FR-08 Local Report Storage

Reports shall be stored locally.

Example:

reports/

EmployeeName_2026-07-21.xlsx

---

## FR-09 Central Report Upload (Future)

The application shall support:

- SharePoint Upload
- NAS Upload
- Database Storage

---

## FR-10 Dashboard (Future)

Managers shall be able to review:

Employee Name

Employee ID

Department

Total Break

Exceeded Limit

Status

---

# 4. Non-Functional Requirements

## Performance

Application startup:

Less than 3 seconds.

Idle detection response:

Less than 1 second.

---

## Resource Usage

Memory Usage:

Less than 100 MB.

CPU Usage:

Less than 2%.

---

## Reliability

The application shall:

Automatically save employee data.

Automatically recover from unexpected shutdown whenever possible.

---

## Security

Employee information shall remain local.

No internet connection is required.

Future versions may support secure cloud synchronization.

---

## Usability

The application shall provide:

Simple interface

Minimal user interaction

Automatic report generation

System tray support

---

# 5. System Workflow

Employee Starts Computer

↓

Launch Break Tracker

↓

Employee Login

↓

Session Starts

↓

Activity Monitoring

↓

Idle Detection

↓

Break Popup

↓

Reason Selection

↓

Continue Working

↓

Logout

↓

Generate Report

↓

Save Report

---

# 6. Technology Stack

Programming Language

Python 3.13

GUI

Tkinter

Report Generation

OpenPyXL

Configuration

JSON

Logging

Python Logging Module

System Tray

Pystray

Images

Pillow

Version Control

Git

Repository

GitHub

---

# 7. Project Deliverables

Desktop Application

Excel Reports

Documentation

Source Code

GitHub Repository

README

Architecture Document

User Guide

Release Notes

---

# 8. Assumptions

Employees login before beginning work.

Employees logout before leaving.

Windows operating system is available.

Python runtime is installed.

---

# 9. Constraints

Version 1 is desktop-only.

No database.

No Active Directory integration.

No biometric integration.

No cloud synchronization.

---

# 10. Future Enhancements

SQLite Database

SharePoint Integration

NAS Storage

Web Dashboard

Analytics

Charts

Weekly Reports

Monthly Reports

Dark Mode

Application Settings

Automatic Updates

PDF Export

Installer Package

Windows Service

---

# 11. Conclusion

Break Tracker Enterprise is designed as an enterprise-style productivity monitoring application that demonstrates desktop application development, software architecture, automation, reporting, and enterprise design principles.

The project serves as a portfolio application showcasing practical software engineering skills and will continue to evolve through future releases.