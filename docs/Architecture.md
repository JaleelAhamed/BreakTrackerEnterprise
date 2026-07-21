# System Architecture

# Break Tracker Enterprise

**Version:** 1.0.0-alpha

---

# Overview

Break Tracker Enterprise follows a modular desktop application architecture. Each module has a single responsibility, making the application easy to maintain, test, and extend.

---

# Architecture Diagram

Employee
    │
    ▼
Login Window
    │
    ▼
Main Dashboard
    │
    ▼
Idle Detection Engine
    │
    ▼
Break Manager
    │
    ▼
Report Generator
    │
 ┌──┴───────────────┐
 ▼                  ▼
Local Reports    SharePoint (Future)

---

# Components

## Employee Module

Responsible for:

- Employee Registration
- Employee Login
- Employee Profile

---

## Session Manager

Responsible for:

- Login Time
- Logout Time
- Session Duration

---

## Idle Detection Engine

Responsible for:

- Keyboard Detection
- Mouse Detection
- Idle Time Calculation

---

## Break Manager

Responsible for:

- Break Start
- Break End
- Break Reason
- Break Calculation

---

## Report Generator

Responsible for:

- Excel Report
- CSV Report (Future)
- PDF Report (Future)

---

## Storage

Version 1

- Local JSON
- Local Excel Reports

Future

- SharePoint
- NAS
- Database

---

# Design Principles

- Modular Architecture
- Separation of Concerns
- Single Responsibility Principle
- Easy Maintainability
- Enterprise Scalability

---

# Future Architecture

Desktop Application

↓

REST API

↓

Database

↓

Web Dashboard

↓

Analytics