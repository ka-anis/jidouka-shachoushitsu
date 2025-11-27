# Schedule Management - Quick Reference Guide

## Overview
This guide explains how to use the four new schedule management views in the Django application.

---

## Step-by-Step Workflow

### 1. Generate Schedule for a Month

**Purpose:** Create schedule entries for all business days in a month, with automatic employee assignment.

**How to use:**
1. Navigate to the Dashboard
2. Select the month and year you want to generate schedules for
3. Click "Generate Schedule" button
4. The system will:
   - Calculate all business days (Monday-Friday)
   - Skip the first 6 business days
   - Assign middle days using employee `order` (３分間スピーチ)
   - Assign last 5 days using employee `order_gyomu` (業務スピーチ)

**URL:** `POST /schedule/generate/`

**Parameters:**
```
year: 2025
month: 12
```

**Result:** Redirects to Schedule Preview page

---

### 2. View Schedule Preview

**Purpose:** Review all schedule entries for a specific month before sending to Google Calendar.

**How to use:**
1. After generating a schedule, you'll automatically be taken to the preview page
2. OR navigate directly to: `GET /schedule/preview/2025/12/`
3. Review all entries and verify:
   - Correct dates
   - Correct employee assignments
   - Correct speech types

**What you see:**
- Date and day of week (月/火/水/木/金)
- Speech type (３分間 or 業務)
- Assigned employee name
- Send status (Pending or Sent ✓)

**Buttons available:**
- Back to Dashboard
- Send to Google Calendar
- Retract (リトラクト)

---

### 3. Send Schedule to Google Calendar

**Purpose:** Create calendar events in Google Calendar for all schedule entries.

**Prerequisites:**
- You must be authenticated with Google Calendar first
- Navigate to `/google/auth/` to authenticate if not already done
- All employees must have valid email addresses

**How to use:**
1. From Schedule Preview page, click "Send to Google Calendar"
2. The system will:
   - Check your Google Calendar authentication
   - Create an event for each scheduled date
   - Add the employee as an attendee
   - Save the event ID for future reference
3. You'll receive a summary:
   - Number of successful events created
   - Any warnings or errors

**What gets created in Google Calendar:**
- **Title:** 朝礼スピーチ - {Employee Name} ({Speech Type})
- **Date:** The scheduled date (all-day event)
- **Description:** Speech type and employee information
- **Attendee:** Employee email (they receive calendar invitation)
- **Timezone:** Asia/Tokyo

**URL:** `POST /schedule/send/2025/12/`

**Result:** Redirects to Schedule Preview with confirmation message

---

### 4. Retract Events (Delete from Google Calendar)

**Purpose:** Remove previously-sent events from Google Calendar and reset local records.

**How to use:**
1. From Schedule Preview page, click "Retract (リトラクト)" button
2. Confirm the action (it's destructive)
3. The system will:
   - Delete events from your Google Calendar
   - Clear the event ID from the database
   - Mark entries as "not sent"

**Warning:** This action will delete the Google Calendar events. You can generate and send new ones after.

**URL:** `POST /schedule/retract/2025/12/`

**Result:** Redirects to Schedule Preview with confirmation message

---

## Assignment Rules

### First 6 Business Days
- **No assignment** - Used for buffer/prep time
- Speech type: ３分間 (but no employee assigned)

### Middle Business Days (7 to n-5)
- **Assignment:** Using employee `order` field
- **Speech Type:** ３分間 (3-minute speech)
- **Rotation:** Cycles through all active employees in order

### Last 5 Business Days
- **Assignment:** Using employee `order_gyomu` field
- **Speech Type:** 業務 (Business speech)
- **Rotation:** Cycles through MEMBER role employees only

### Rotation Logic
- Employees are cycled based on their position in the sequence
- Uses modulo operator for cycling through the list
- Example: If 3 employees for middle days and 8 dates:
  - Day 7 → Employee 1
  - Day 8 → Employee 2
  - Day 9 → Employee 3
  - Day 10 → Employee 1 (cycles back)
  - Day 11 → Employee 2
  - etc.

---

## Employee Management Requirements

### For Middle Days (３分間スピーチ)
- Employee must have `is_rotation_active = True`
- Employee must have an `order` value (sorted ascending)
- No role restriction

### For Last 5 Days (業務スピーチ)
- Employee must have `role = MEMBER`
- Employee must have `is_rotation_active = True`
- Employee must have an `order_gyomu` value (sorted ascending)

### For Google Calendar
- Employee must have a valid email address
- Email must be unique in the system

---

## Workflow Examples

### Example 1: First Time Setup
```
1. Dashboard → Adjust employee order for 3-minute speeches
2. Dashboard → Adjust employee order_gyomu for business speeches
3. Toggle is_rotation_active for employees to participate
4. Schedule Preview → Generate schedule for December 2025
5. Schedule Preview → Review all entries
6. Schedule Preview → Send to Google Calendar
7. Google Calendar → Verify events created correctly
```

### Example 2: Make Changes After Sending
```
1. Schedule Preview → Click "Retract (リトラクト)"
2. Confirm the action → Events deleted from Google
3. Dashboard → Adjust employee order if needed
4. Schedule Preview → Generate schedule again (or edit in preview)
5. Schedule Preview → Send to Google Calendar again
```

### Example 3: Monthly Workflow
```
Month Start:
1. Generate schedule for the month
2. Review in preview page
3. Send to Google Calendar
4. Employees receive invitations

Mid-Month Adjustments:
1. If changes needed, retract the schedule
2. Make adjustments
3. Regenerate and send again

Next Month:
1. Repeat the process for the new month
```

---

## Google Calendar Integration

### What Happens When You Send
1. **Authentication Check:** System verifies you're logged in with Google
2. **Event Creation:** For each schedule entry:
   - Unique event created with date and employee info
   - Employee receives calendar invitation
   - Event ID saved in database
3. **Status Tracking:** System records event ID and marks as "sent"

### What Happens When You Retract
1. **Lookup:** System finds all events sent in this month
2. **Deletion:** Each event is deleted from Google Calendar
3. **Cleanup:** Event IDs cleared from database, status reset

### If Something Goes Wrong
- **Missing email:** Entry is skipped with warning
- **API error:** Entry is skipped, you can try again
- **Already deleted:** System cleans up the local record
- **Partial failure:** Successfully sent events stay, failed ones are retried

---

## Troubleshooting

### "Not authenticated with Google Calendar"
**Solution:** 
1. Click the message link or go to `/google/auth/`
2. Authorize the application with your Google account
3. Return to the preview page
4. Try sending again

### "Some employees have no email"
**Solution:**
1. Go to Dashboard
2. Add email addresses for employees without one
3. Save changes
4. Try sending again

### Events created but not assigned to employee
**Solution:**
1. Verify employee has valid email in the system
2. Check the event on Google Calendar
3. The employee email should appear in event details
4. They can accept or decline the invitation

### Can't generate schedule
**Solution:**
1. Verify year and month values are correct
2. Make sure employees have `is_rotation_active = True`
3. Check that employees have proper `order` and `order_gyomu` values
4. Try with a month that has many business days (not all holidays)

---

## Important Notes

1. **Backup:** Schedule entries are stored in the database - they won't be lost if you retract from Google
2. **Idempotent:** Sending the same schedule multiple times won't create duplicates
3. **Safe Deletion:** Retracting clears Google events but preserves database records
4. **No Manual Editing:** Always use Generate/Retract/Send workflow, don't manually edit calendar
5. **Timezone:** All events are created in Asia/Tokyo timezone

---

## Command Line Usage (Advanced)

### Generate schedule via Python shell
```python
from core.views import _get_business_days
from core.models import ScheduleEntry, Employee, Role, SpeechType

# Generate entries for December 2025
year, month = 2025, 12
business_days = _get_business_days(year, month)

# Manual creation (normally done via the view)
for day in business_days[:6]:
    ScheduleEntry.objects.create(
        date=day,
        speech_type=SpeechType.THREE_MIN,
        assigned_employee=None
    )
```

### Check schedule status
```python
from core.models import ScheduleEntry
from datetime import date

# Check sent vs pending
sent = ScheduleEntry.objects.filter(is_sent=True, date__gte=date.today()).count()
pending = ScheduleEntry.objects.filter(is_sent=False, date__gte=date.today()).count()
print(f"Sent: {sent}, Pending: {pending}")
```

---

## Support & Questions

For more information, refer to:
- `IMPLEMENTATION_SUMMARY.md` - Technical implementation details
- Django admin interface - Edit entries directly if needed
- Google Calendar API docs - For Google Calendar specific questions
