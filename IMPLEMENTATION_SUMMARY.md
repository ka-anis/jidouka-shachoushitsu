# Django Schedule Management Implementation Summary

## Overview
Successfully implemented four comprehensive Django views, database models, URL patterns, and template for managing schedule generation, preview, Google Calendar integration, and event retraction.

---

## STEP 1: Database Model Updates

### ScheduleEntry Model Enhancements
Added two new fields to track Google Calendar integration:

```python
google_event_id = models.CharField(max_length=200, blank=True, null=True)
is_sent = models.BooleanField(default=False)
```

**Migration Created:** `0005_scheduleentry_google_event_id_scheduleentry_is_sent`

These fields enable:
- Storing the Google Calendar event ID for each schedule entry
- Tracking which entries have been successfully sent to Google Calendar

---

## STEP 2: View Implementation

### 2.1 Generate Schedule View (`/schedule/generate/`)
**HTTP Method:** POST only

**Purpose:** Generate schedule entries for a given month with intelligent assignment rules.

**Input Parameters:**
- `year` (int): The year
- `month` (int): The month (1-12)

**Algorithm:**
1. Compute all business days (Monday-Friday) in the specified month
2. Split business days into three groups:
   - **First 6 business days:** No assignment (speech_type set but no employee assigned)
   - **Middle business days (7 to n-5):** Assigned using `order` field (３分間スピーチ - 3-minute speech)
   - **Last 5 business days:** Assigned using `order_gyomu` field (業務スピーチ - Business speech)
3. Rotate through active employees using their specified order sequences
4. Create/replace `ScheduleEntry` objects for the month
5. Reset Google Calendar fields (`google_event_id=None`, `is_sent=False`)
6. Redirect to Schedule Preview page with success message

**Key Features:**
- Uses `update_or_create()` to safely replace existing entries
- Only includes employees with `is_rotation_active=True`
- Handles edge cases (months with fewer than 11 business days)
- Provides success/error messages via Django messages framework

---

### 2.2 Schedule Preview View (`/schedule/preview/<year>/<month>/`)
**HTTP Method:** GET only

**Purpose:** Display the generated schedule for a selected month.

**Input Parameters:**
- `year` (int): The year
- `month` (int): The month (1-12)

**Features:**
1. Loads all business days for the month
2. Fetches `ScheduleEntry` objects from the database for that month
3. Creates display-friendly data including:
   - Date and day of week (日本語: 月, 火, 水, 木, 金)
   - Speech type (業務 or ３分間)
   - Assigned employee name
   - Send status (Sent or Pending)
4. Groups entries by date in chronological order
5. Passes data to template for HTML rendering

**Template:** `core/schedule_preview.html`
- Clean table layout with color-coded status indicators
- Shows all schedule entries with employee assignments
- Three action buttons:
  - **Back to Dashboard:** Return to employee management
  - **Send to Google Calendar:** Triggers calendar sync
  - **Retract (リトラクト):** Removes previously-sent events

---

### 2.3 Send to Google Calendar View (`/schedule/send/<year>/<month>/`)
**HTTP Method:** POST only

**Purpose:** Send all schedule entries for a month to Google Calendar.

**Input Parameters:**
- `year` (int): The year
- `month` (int): The month (1-12)

**Google Calendar Integration:**
1. Retrieves stored Google credentials from session
2. Builds Google Calendar service client
3. For each schedule entry with an assigned employee:
   - Validates employee email address
   - Creates event with:
     - **Title:** `朝礼スピーチ - {Employee Name} ({Speech Type})`
     - **Description:** Speech type and assigned employee info
     - **Date:** All-day event on the scheduled date
     - **TimeZone:** Asia/Tokyo
     - **Attendee:** Employee email address
   - Retrieves Google event ID from response
   - Saves event ID to `ScheduleEntry.google_event_id`
   - Marks entry as sent (`is_sent=True`)

**Error Handling:**
- Gracefully handles missing/invalid employee emails
- Catches HTTP errors from Google Calendar API
- Continues processing remaining entries on individual failures
- Provides warning messages for each failed entry
- Requires prior authentication (redirects to `/google/auth/` if needed)

**Status Tracking:**
- Success count: Total events sent
- Error count: Failed attempts
- Messages displayed in session after redirect

**Redirect:** Back to Schedule Preview page

---

### 2.4 Retract Schedule View (`/schedule/retract/<year>/<month>/`)
**HTTP Method:** POST only

**Purpose:** Delete previously-sent Google Calendar events and clear local records.

**Input Parameters:**
- `year` (int): The year
- `month` (int): The month (1-12)

**Retraction Process:**
1. Retrieves Google Calendar service from session credentials
2. Filters `ScheduleEntry` objects that:
   - Have `is_sent=True`
   - Have a non-null `google_event_id`
   - Match the specified month/year
3. For each entry:
   - Calls Google Calendar API to delete the event
   - Clears `google_event_id` field
   - Sets `is_sent=False`
   - Saves changes to database

**Error Handling:**
- Handles 404 errors (event already deleted on Google side)
- Treats 404 as successful (clears local record)
- Continues processing remaining entries on failures
- Provides warning messages for API errors

**Status Tracking:**
- Success count: Total events deleted
- Error count: Failed deletions
- Messages displayed in session after redirect

**Redirect:** Back to Schedule Preview page with confirmation

---

## STEP 3: URL Patterns

Added four new routes to `core/urls.py`:

```python
path('schedule/generate/', views.generate_schedule, name='generate_schedule'),
path('schedule/preview/<int:year>/<int:month>/', views.schedule_preview, name='schedule_preview'),
path('schedule/send/<int:year>/<int:month>/', views.send_schedule_to_calendar, name='send_to_calendar_month'),
path('schedule/retract/<int:year>/<int:month>/', views.retract_schedule, name='retract_schedule'),
```

---

## STEP 4: Template Implementation

### schedule_preview.html
Tailwind CSS styled template with:
- Responsive table layout
- Color-coded status badges:
  - Blue: Speech type indicators
  - Green: Sent status
  - Yellow: Pending status
- Comprehensive action buttons with confirmation dialogs
- Django messages integration for user feedback
- Japanese language support

---

## Key Implementation Details

### Helper Functions
```python
def _get_business_days(year, month):
    """Returns all weekday dates (Mon-Fri) in a given month."""
    
def _get_google_service(request):
    """Retrieves Google Calendar service from session credentials."""
```

### Decorators
- `@require_http_methods(["POST"])`: Enforces POST-only access for write operations
- `@require_http_methods(["GET"])`: Enforces GET-only access for preview

### Employee Ordering Logic
- **３分間スピーチ (3-minute speeches):** Uses `Employee.order` field
- **業務スピーチ (Business speeches):** Uses `Employee.order_gyomu` field
- Both respect `is_rotation_active` flag
- Rotation cycles through employees using modulo operator

### Google Calendar Event Creation
- All-day events (date-based, not time-based)
- TimeZone: Asia/Tokyo
- Includes descriptive title and detailed description
- Employee added as attendee (calendar invitation)
- Event ID saved for future reference/deletion

---

## Testing the Implementation

### Create Test Data
```bash
# Access Django shell
python manage.py shell

# Create employees
from core.models import Employee, Role
Employee.objects.create(
    name="Employee 1",
    email="emp1@example.com",
    employee_id="E001",
    order=1,
    order_gyomu=1,
    role=Role.MEMBER,
    is_rotation_active=True
)
```

### Generate Schedule
```
POST /schedule/generate/
Parameters:
  year=2025
  month=12
```

### View Schedule
```
GET /schedule/preview/2025/12/
```

### Send to Google Calendar
```
POST /schedule/send/2025/12/
```

### Retract Events
```
POST /schedule/retract/2025/12/
```

---

## Important Notes

### Prerequisites
- Google Calendar API enabled
- `credentials.json` configured
- User must authenticate via `/google/auth/` first
- Employees must have valid email addresses

### Data Safety
- `update_or_create()` prevents duplicate entries
- Failed operations don't affect successfully processed entries
- Event IDs stored for idempotent deletion
- 404 errors on deletion treated as successful (no orphaned records)

### User Experience
- Clear success/warning/error messages
- Confirmation dialogs for destructive operations
- Responsive design with Tailwind CSS
- Japanese language labels and messages

### Performance Considerations
- Uses `select_related()` to minimize database queries
- Efficient business day calculation
- Batch operations where possible
- Google API calls made only when necessary

---

## Files Modified

1. **core/models.py** - Added `google_event_id` and `is_sent` fields to ScheduleEntry
2. **core/views.py** - Added 4 new views + 2 helper functions
3. **core/urls.py** - Added 4 new URL patterns
4. **core/templates/core/schedule_preview.html** - New template for schedule display
5. **core/migrations/0005_*.py** - Database migration (auto-generated)

---

## Migration Status
✅ Database migration created and applied successfully
✅ All Python syntax verified
✅ Django system checks passing
✅ Ready for production use
