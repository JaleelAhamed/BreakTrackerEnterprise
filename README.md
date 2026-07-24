# Break Tracker Enterprise

**Enterprise Desktop Productivity Monitoring System**

> Break Tracker Enterprise is a Windows desktop application that automates employee break tracking and idle-time monitoring — replacing manual, error-prone break logs with an unattended, always-on tracking system.

Manual break tracking is inconsistent, easy to forge, and time-consuming to audit. Break Tracker Enterprise solves this by silently monitoring employee activity in the background, automatically detecting idle time, prompting for break reasons, and generating a professional Excel report the moment an employee logs out — with zero manual data entry.

Originally developed as a portfolio project, the architecture was deliberately designed with real enterprise deployment in mind: a single standalone executable, persistent per-user configuration, administrator-gated settings, and structured logging suitable for IT support and auditing.

---

## 📌 Table of Contents

- [Overview](#-break-tracker-enterprise)
- [Project Highlights](#-project-highlights)
- [Features](#-features)
- [Screenshots](#-screenshots)
- [Application Workflow](#-application-workflow)
- [Architecture](#️-architecture)
- [Project Structure](#-project-structure)
- [Project Statistics](#-project-statistics)
- [Technology Stack](#️-technology-stack)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Enterprise Readiness](#-enterprise-readiness)
- [Documentation](#-documentation)
- [Roadmap](#️-roadmap)
- [Current Version](#-current-version)
- [License](#-license)
- [Author](#-author)

---

# 🚀 Break Tracker Enterprise

Break Tracker Enterprise is a modular desktop productivity monitoring system built in Python for Windows environments.

It automates employee session tracking, detects idle time, collects break reasons, generates professional Excel productivity reports, and provides secure administrator controls for configuration management — all without requiring a server, database, or network dependency.

The project follows enterprise software engineering practices, including a modular architecture, structured logging, secure administrator authentication, centralized configuration management, and professional automated reporting.

This project was developed through an agile, sprint-based approach and currently represents **Version 1.0.0**, deployed as a pilot in a live production environment.

---

# ⭐ Project Highlights

- 🖥️ **Standalone Windows Executable** — no Python installation required for end users
- 💤 **Automatic Idle Detection** — detects inactivity without manual clock-in/out
- 🔒 **Windows Lock Detection** — accurately distinguishes locked sessions from genuine breaks
- 🔑 **Administrator Authentication** — SHA-256 protected settings, with lockout protection
- 📊 **Automated Excel Report Generation** — enterprise-formatted `.xlsx` reports, no templates needed
- 🧭 **System Tray Integration** — runs quietly in the background without interrupting work
- 💾 **Persistent LOCALAPPDATA Storage** — survives executable relaunches and updates
- 🧩 **Modular Architecture** — each module owns a single, well-defined responsibility

---

# ✨ Features

## 👤 Employee Features

- Employee Registration
- Secure Employee Login
- Live Session Timer
- Automatic Logout Report
- Idle Time Detection
- Break Reason Collection
- Background Monitoring
- Minimize to System Tray

## 🛡️ Administrator Features

- Protected Settings Window
- SHA-256 Password Authentication
- Temporary Lockout Protection
- Configuration Management

## 📈 Reporting

- Employee Information
- Session Summary
- Break Summary
- Productivity Statistics
- Automatic Remarks
- Professional Excel Formatting

## ⚙️ System Features

- Enterprise-Grade Logging
- Error & Exception Tracking
- Authentication Audit Logs
- Persistent Configuration Storage

---

# 📸 Screenshots

### 1. Employee Login

The application begins with a secure employee login screen where users authenticate using their Employee ID before starting a work session.

![alt text](screenshotslogin_window.png.png)

### 2. Administrator Authentication

Administrative settings are protected with an additional authentication layer. Only authorized administrators can modify enterprise configuration settings.

![alt text](screenshotsadmin_authentication.png.png)

### 3. Enterprise Settings

The administrator can configure application settings such as idle threshold, allowed break duration, notifications, and report/log locations.

![alt text](screenshotssettings_window.png.png)

### 4. Active Work Session

After login, the employee dashboard displays the active session timer while monitoring user activity in the background.

![alt text](screenshotssession_window.png.png)

### 5. Background Monitoring

The application minimizes to the Windows System Tray, allowing continuous monitoring without interrupting the user's workflow.

![alt text](screenshotssystem_tray.png.png)

### 6. Automatic Break Detection

When user inactivity exceeds the configured threshold, the application prompts the employee to provide a reason for the detected break.

![alt text](screenshotsbreak_popup.png.png)

### 7. Professional Excel Reports

At the end of each session, the application automatically generates a professionally formatted Excel report containing:

- Employee Information
- Session Summary
- Break Details
- Work Statistics
- Daily Activity Report

![alt text](screenshotsexcel_report.png.png)

### 8. Enterprise Logging

Application and error logs are automatically maintained to simplify troubleshooting and auditing.

![alt text](screenshotsapplication_logs.png.png)

---

# 🔄 Application Workflow

```text
Launch Application
        ↓
Employee Login / Registration
        ↓
Live Session Timer Starts
        ↓
Idle Detection (Background)
        ↓
Break Popup Triggered
        ↓
Reason Selection
        ↓
Session Logout
        ↓
Excel Report Generation
```

---

# 🏗️ Architecture

```text
                     +-------------------+
                     |      main.py      |
                     +---------+---------+
                               |
         +---------------------+---------------------+
         |                     |                     |
         |                     |                     |
+--------v--------+   +--------v--------+   +--------v--------+
|  employee.py    |   |    logger.py    |   |  settings.py    |
+--------+--------+   +-----------------+   +--------+--------+
         |                                         |
         |                                         |
+--------v--------+                     +----------v----------+
|   session.py    |                     |   admin_auth.py     |
+--------+--------+                     +---------------------+
         |
         |
+--------+--------+
| idle_detector.py|
+--------+--------+
         |
         |
+--------v--------+
| report_generator|
+-----------------+
         |
         |
+--------v--------+
| tray_manager.py |
+-----------------+
```

---

# 📁 Project Structure

```text
BreakTrackerEnterprise/

assets/
docs/
logs/
reports/
screenshots/

main.py
employee.py
session.py
idle_detector.py
report_generator.py
logger.py
tray_manager.py
settings.py
admin_auth.py
admin_settings.py
config.json
README.md
CHANGELOG.md
LICENSE
VERSION
```

---

# 📊 Project Statistics

| Category            | Details                              |
|----------------------|---------------------------------------|
| **Language**         | Python 3.13                          |
| **GUI Framework**    | Tkinter                              |
| **Packaging**        | PyInstaller (Standalone `.exe`)      |
| **Configuration**    | JSON (`config.json`, per-user store) |
| **Logging**          | Rotating file logs (Application/Error)|
| **Report Format**    | Excel (`.xlsx` via OpenPyXL)          |
| **Platform**         | Windows Desktop                      |
| **Architecture**     | Modular, single-responsibility modules|

---

# 🛠️ Technology Stack

Ordered by role and importance within the application:

- **Python 3.13** — core application language
- **Tkinter** — desktop GUI framework
- **OpenPyXL** — Excel report generation
- **PyStray** — system tray integration
- **Pillow** — tray icon image handling
- **Logging** — enterprise-grade application/error logging
- **Threading** — background idle monitoring
- **JSON** — configuration persistence
- **Git / GitHub** — version control

---

# ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/JaleelAhamed/BreakTrackerEnterprise.git
```

Navigate into the project:

```bash
cd BreakTrackerEnterprise
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python main.py
```

---

# 🔧 Configuration

Application settings are stored in:

`config.json`

Administrators can configure:

- Idle Time Threshold
- Allowed Break Duration
- Working Hours
- Administrator Authentication
- Application Behavior

---

# 🏢 Enterprise Readiness

The current release already supports the foundations required for enterprise deployment:

- ✅ Standalone executable deployment (no Python runtime required on target machines)
- ✅ Persistent, per-user configuration storage (`LOCALAPPDATA`)
- ✅ Administrator-gated settings with authentication and lockout protection
- ✅ Local, automated Excel report generation
- ✅ Modular, maintainable codebase with clear separation of concerns

Planned enhancements for broader enterprise rollout (see [Roadmap](#️-roadmap)):

- 🔜 SharePoint Integration for centralized report storage
- 🔜 Active Directory / Microsoft Entra ID authentication
- 🔜 Centralized Reporting across employees and teams
- 🔜 Manager Dashboard for team-level visibility
- 🔜 Database Backend for scalable, multi-user deployments

---

# 📚 Documentation

Detailed project documentation is available in the `docs/` folder.

- Software Requirements Specification (SRS)
- Architecture Document
- Project Charter
- Roadmap
- User Guide
- Test Plan
- Release Notes

---

# 🗺️ Roadmap

## Version 1.0.0 (Current)

- Employee Registration
- Secure Login
- Idle Detection
- Excel Reporting
- Enterprise Logging
- System Tray Support
- Administrator Authentication

## Version 2.0 (Planned)

- Database Integration
- Centralized Dashboard
- Team Analytics
- Email Reports
- Active Directory Integration
- RBAC
- Cloud Synchronization

---

# 📦 Current Version

| Field             | Details                        |
|-------------------|---------------------------------|
| **Version**       | 1.0.0                          |
| **Release Date**  | 2026                            |
| **Status**        | Production Ready (Pilot Deployment) |
| **Platform**      | Windows                        |
| **Build Type**    | Standalone Executable (PyInstaller) |

---

# 📄 License

This project is licensed under the MIT License.

---

# 👨‍💻 Author

**Jaleel Ahamed**

IT Support Engineer

LinkedIn: [linkedin.com/in/jaleel-ahamed-tech](https://linkedin.com/in/jaleel-ahamed-tech)

GitHub: [github.com/JaleelAhamed](https://github.com/JaleelAhamed)