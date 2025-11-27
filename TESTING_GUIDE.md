# Testing & Database Management Guide

## Current Status

### Production Database
- **Location:** `backups/db_production_copy.sqlite3`
- **Status:** Backed up and safe
- **Contents:** Full production employee and schedule data

### Test Database
- **Location:** `db.sqlite3` (in project root)
- **Status:** Clean and ready for testing
- **Contents:** 5 test employees with valid email addresses

---

## Test Employees

The following test employees are configured in the test database:

| # | Name | Email | Order | Order Gyomu | Role |
|---|------|-------|-------|-------------|------|
| 1 | メンバー１ | khaled.gad@ejust.edu.eg | 1 | 1 | MEMBER |
| 2 | メンバー２ | gad.khaled00@gmail.com | 2 | 2 | MEMBER |
| 3 | メンバー３ | k-mahrous@ar-system.co.jp | 3 | 3 | MEMBER |
| 4 | テスト４ | test.employee4@example.com | 4 | 4 | MEMBER |
| 5 | テスト５ | test.employee5@example.com | 5 | 5 | MEMBER |

All employees have `is_rotation_active=True` and are ready for scheduling.

---

## Testing Workflow

### 1. Generate a Schedule
```bash
# Start the Django server
python manage.py runserver
```

Then navigate to:
```
http://localhost:8000/dashboard/
```

Click the "送信" (Send) button to:
1. Redirect to the current month's send endpoint
2. View the schedule preview page
3. Confirm you have the 5 test employees available

### 2. Generate Schedule for a Month
Go to `/schedule/preview/2025/12/` (or current month) and:
1. Use the generate form to create schedule entries
2. Verify that entries are created for all business days
3. Confirm the assignment rules:
   - First 6 business days: No assignment
   - Middle days: Assigned using `order` field
   - Last 5 days: Assigned using `order_gyomu` field

### 3. Send to Google Calendar
From the preview page, click "Send to Google Calendar":
1. Authenticate with Google (via `/google/auth/` if needed)
2. Events are created with the test employees as attendees
3. You'll receive a success message with the count

### 4. Verify in Google Calendar
Check that events appear in your Google Calendar with:
- Correct dates
- Employee names in the title
- Employee emails as attendees

### 5. Retract Events
Click "Retract (リトラクト)" to:
1. Delete events from Google Calendar
2. Clear the event IDs from the database
3. Reset the send status

---

## Restoring Production Database

When you're done testing and want to restore the full production database:

### Option 1: Using Terminal
```bash
cd /home/k-mahrous/workspace/jidouka
rm db.sqlite3
cp backups/db_production_copy.sqlite3 db.sqlite3
python manage.py migrate
```

### Option 2: Using Python Script
```python
import shutil
import os

# Navigate to project directory
os.chdir('/home/k-mahrous/workspace/jidouka')

# Remove test database
if os.path.exists('db.sqlite3'):
    os.remove('db.sqlite3')

# Restore production database
shutil.copy('backups/db_production_copy.sqlite3', 'db.sqlite3')

print("✓ Production database restored!")
```

### Option 3: Manual Backup/Restore
Before you finish testing, run:
```bash
# Backup the test database (if you want to keep it)
cp db.sqlite3 backups/db_test_copy.sqlite3

# Restore production
cp backups/db_production_copy.sqlite3 db.sqlite3
```

---

## Database Backup Location

```
/home/k-mahrous/workspace/jidouka/backups/
├── db_production_copy.sqlite3     # Original production database
└── db_test_copy.sqlite3           # Optional: test database backup
```

---

## Troubleshooting

### Issue: "Database is locked"
**Solution:** Restart the Django server
```bash
# Stop the server (Ctrl+C)
# Then restart:
python manage.py runserver
```

### Issue: Google authentication fails
**Solution:** Authenticate again
```
http://localhost:8000/google/auth/
```

### Issue: Employees don't appear in schedule
**Solution:** Verify employees are marked as active
```bash
python manage.py shell
from core.models import Employee
Employee.objects.filter(is_rotation_active=False).update(is_rotation_active=True)
```

### Issue: Want fresh test data
**Solution:** Reload test employees
```bash
python manage.py load_test_employees
```

This will:
1. Clear all existing employees
2. Reload the 5 test employees
3. Preserve schedule entries

---

## Database File Sizes

You can check database sizes with:
```bash
ls -lh db.sqlite3
ls -lh backups/db_production_copy.sqlite3
```

Both should be approximately the same size (original vs backup).

---

## Important Notes

1. **Never delete `backups/db_production_copy.sqlite3`** - This is your safety net
2. **Test data is temporary** - It will be lost when you restore production
3. **Google Calendar events are real** - They'll actually appear in your calendar
4. **Email addresses must be valid** - Google Calendar API validates emails
5. **Timestamps are GMT+9 (Asia/Tokyo)** - Events created in this timezone

---

## Quick Commands Reference

```bash
# Load test employees
python manage.py load_test_employees

# Start development server
python manage.py runserver

# Access Django shell
python manage.py shell

# Run migrations
python manage.py migrate

# Check test data
python manage.py shell << 'EOF'
from core.models import Employee
print(f"Employees: {Employee.objects.count()}")
EOF
```

---

## Next Steps After Testing

1. ✅ Test schedule generation
2. ✅ Test Google Calendar integration
3. ✅ Test retract functionality
4. ✅ Verify dashboard buttons work correctly
5. 📋 Document any issues found
6. 🔄 Restore production database
7. 🚀 Deploy to production

---

**Last Updated:** 2025-11-27
**Test Database Version:** 1.0
**Production Backup:** Safe at `backups/db_production_copy.sqlite3`
