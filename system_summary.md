# 朝礼スピーチ管理システム — System Summary

This system is a Django-based internal web application designed to automate the monthly assignment and scheduling of morning speech rotations for company employees and integrate them with Google Calendar. The workflow is as follows: authorized users in the president’s office can configure eligible employees via a web UI (checkbox selection), and the system will automatically generate next month’s rotation schedule according to business rules—e.g., the president speaks on the first business day, department heads on days 2–6, regular members on the last five business days, and free-speech days fill remaining slots—with exclusions for specific roles (e.g., no department heads in free-speech days, no admin members in work-report days). The admin can review and adjust the generated schedule through the web UI, including drag-and-drop reordering of assigned speakers, manual reassignment, or cancellation of particular days. Once confirmed, the finalized schedule is automatically synced to employees’ Google Calendars via the Google Calendar API, using a service account that has permission to create and manage only the events this system generates. When a change occurs (e.g., a person becomes unavailable), the system retracts previously registered events before re-registering updated ones. All configuration (database credentials, API keys, etc.) is provided via environment variables in a .env file. The entire system runs in Docker containers orchestrated via Docker Compose, with a single command to launch, and only the frontend/reverse proxy (e.g., Nginx) exposed to the public IP. The backend (Django + Gunicorn) handles the business logic and API operations, and PostgreSQL stores persistent data such as employees, schedule templates, and audit logs. The overall design must support easy deployment, secure credential management, and reliable synchronization with Google Calendar, ensuring it modifies only events created by this system and leaves all other calendar data untouched.

## 1. Software Requirements and Goal

### Goal
Automate the creation, adjustment, and management of monthly 朝礼スピーチ (morning speech) schedules, and synchronize confirmed schedules with a shared Google Calendar.

### Core Functional Requirements
1. Auto Assignment: Assign speakers based on business days and roles (社長, 部長, メンバー, 社長室). Apply exclusion rules and avoid duplicates.
2. Manual Adjustment: Allow reassignment, cancellation, or reordering of speakers.
3. Calendar Sync: Register all events via Google Calendar API using a shared calendar. Allow full retraction and re-registration.
4. Participant Management: Checkboxes to include/exclude employees from rotation.
5. Admin UI: Web interface for 社長室 staff to manage schedules.

### Non-Functional Requirements
- Single admin user group (社長室)
- Internal-use web application (no public users)
- Secure handling of Google API credentials
- Deployable with Docker Compose
- Compatible with PostgreSQL

## 2. Proposed System Design

### Architectural Pattern
Three-layer monolithic web application built on Django:
- Presentation Layer: Django templates + minimal JS(To allow for drad and drop)
- Application Layer: Business logic services (rotation_service, calendar_service, adjustment_service)
- Data Layer: PostgreSQL via Django ORM

### Key Components
| Layer | Components | Description |
|--------|-------------|-------------|
| Frontend (UI) | Django templates + Bootstrap | Admin web interface for generation, edit, sync |
| Business Logic | rotation_service.py, calendar_service.py | Implements assignment and calendar sync |
| Database | PostgreSQL / SQLite | Stores employees, events, configuration |
| Integration | Google Calendar API (service account) | Creates/deletes events on shared calendar |
| Deployment | Docker + Docker Compose | Self-contained environment |

### Data Flow
1. Admin selects month → system generates schedule.
2. Admin edits results → confirms.
3. On “Sync to Calendar”, system creates all events via Google API.
4. On “Retract All”, system deletes only events it created.
5. Database tracks event IDs to ensure safe operations.

### Deployment Architecture
- Single static IP → Nginx reverse proxy (only exposed service)
- Internal Docker network → Django (Gunicorn) + PostgreSQL
- Single command launch → docker-compose up -d

User Browser → Nginx Proxy → Django (Gunicorn) → PostgreSQL → Google Calendar API

## 3. Change Constraints and Compliance Rules

Any modification to the system design must adhere to the following constraints:

### Deployment & Network
1. Only one static IP — only the Nginx (frontend) container may expose ports externally.
2. All services must run inside Docker Compose on an internal bridge network.
3. Single-command launch (docker-compose up -d) must remain possible.
4. No direct DB access from outside the container network (Django ORM only).
5. All configurations via environment variables (.env).

### Application & Architecture
6. The system must remain monolithic (single Django app) unless justified by strong technical need.
7. Google Calendar integration must use a service account and only manage events created by this system.
8. Rotation logic cannot be altered without formal SRS revision.
9. UI technology must remain server-rendered (Django templates); JS limited to minor interactivity.
10. Database schema changes must be managed through Django migrations.

### Operational
11. The Dockerfile provided must remain usable for production deployment without modification.
12. Logging, backups, and credentials must remain compatible with internal hosting policies.
13. The system must not depend on any external service other than Google Calendar.
14. All internal communication must use the Docker network.

Summary: A single, modular Django monolith deployed through Docker Compose behind one Nginx static IP. Any design change must preserve this isolation, one-command deployability, and safe Google Calendar integration.



Decided to use sqlite:
Database location made explicit:
In settings.py, the SQLite database file (db.sqlite3) is placed inside your project’s base directory using os.path.join(BASE_DIR, 'db.sqlite3') — ensuring Django always knows where to find it.

Persistent storage for Docker:
In docker-compose.yml, a local folder (./data) is mounted to /app/data inside the container so that the database file lives outside the container and survives rebuilds or restarts.

Declared persistent volume in Dockerfile:
Added VOLUME /app/data so Docker recognizes that directory as persistent storage — keeping the SQLite file safe between container runs.