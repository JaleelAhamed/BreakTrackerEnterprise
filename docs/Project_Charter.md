# Project Charter

# Break Tracker Enterprise

**Project Version:** 1.0.0-alpha

**Document Version:** 1.0

**Prepared By:** Jaleel Ahamed

**Project Type:** Personal Portfolio Project

**Status:** Active

---

# 1. Project Overview

Break Tracker Enterprise is a Python-based desktop application designed to simulate an enterprise employee productivity monitoring solution.

The application automatically monitors user activity, detects idle time, records employee breaks, generates daily reports, and provides productivity insights. The project is being developed as a personal portfolio application to demonstrate software engineering, desktop development, automation, reporting, and application architecture skills.

---

# 2. Business Problem

Many organizations manually monitor employee attendance and break durations. This approach is time-consuming, inconsistent, and provides limited visibility into employee productivity.

Managers often lack a simple way to answer questions such as:

- How long was an employee actively working?
- How much break time was taken?
- Was the permitted break duration exceeded?
- What was the reason for extended breaks?

Break Tracker Enterprise aims to automate these processes while producing structured reports for employees, managers, and HR teams.

---

# 3. Vision

To develop a lightweight, enterprise-style desktop application capable of monitoring employee activity, generating productivity reports, and demonstrating professional software engineering practices using Python.

---

# 4. Project Objectives

The primary objectives are:

- Develop a professional desktop application using Python.
- Detect employee inactivity automatically.
- Track break duration accurately.
- Generate Excel-based productivity reports.
- Maintain employee information locally.
- Prepare the application for future centralized reporting.
- Build a portfolio-quality enterprise application.

---

# 5. Project Scope

## In Scope (Version 1)

- Employee registration
- Employee login
- Session tracking
- Idle detection
- Break calculation
- Break reason collection
- Excel report generation
- Local report storage
- System tray support

## Out of Scope (Version 1)

- Database integration
- Active Directory integration
- Biometric authentication
- Cloud synchronization
- Mobile application
- Multi-user administration

These features may be considered in future versions.

---

# 6. Stakeholders

| Stakeholder | Responsibility |
|-------------|----------------|
| Employee | Uses the application and provides break reasons |
| Manager | Reviews productivity reports |
| HR | Reviews daily and monthly reports |
| Developer | Designs, develops, tests, and maintains the application |

---

# 7. Success Criteria

The project will be considered successful if it:

- Detects idle time accurately.
- Tracks employee breaks correctly.
- Generates professional Excel reports.
- Stores employee information reliably.
- Provides a stable desktop application.
- Demonstrates enterprise-level software engineering practices.

---

# 8. Risks

| Risk | Mitigation |
|------|------------|
| Incorrect idle detection | Extensive testing |
| Unexpected application crashes | Logging and exception handling |
| Report generation failures | Input validation and testing |
| Future scalability | Modular architecture |

---

# 9. Assumptions

- Employees log in before starting work.
- Employees log out before leaving.
- Windows operating system is used.
- Python runtime is available during development.

---

# 10. Deliverables

The project will deliver:

- Desktop Application
- Source Code
- Documentation
- Excel Report Generator
- GitHub Repository
- User Guide
- Test Plan
- Release Notes

---

# 11. Milestones

| Milestone | Status |
|-----------|--------|
| Project Initialization | Completed |
| Documentation | In Progress |
| Employee Module | Planned |
| Idle Detection | Planned |
| Break Tracking | Planned |
| Report Generation | Planned |
| Dashboard | Planned |
| Version 1.0 Release | Planned |

---

# 12. Conclusion

Break Tracker Enterprise is intended to demonstrate the design and development of an enterprise-style desktop application using Python. The project emphasizes clean architecture, maintainable code, documentation, reporting, and professional development practices suitable for a software engineering portfolio.