from django.db import models
from datetime import date

# Create your models here.
class Role(models.TextChoices):
    MEMBER = "MEMBER", "メンバー"
    SHACHOU_SHITSU = "SHACHOU_SHITSU", "社長室"

# Employee model 
class Employee(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    employee_id = models.CharField(max_length=10, unique=True)
    order = models.IntegerField(default=0)
    order_gyomu = models.IntegerField(default=0)

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    is_rotation_active = models.BooleanField(default=True)


    def days_since_last_speech(self):
        last_entry = (
            ScheduleEntry.objects
            .filter(assigned_employee=self, is_cancelled=False)
            .order_by('-date')
            .first()
        )

        if not last_entry:
            return None  # or return 0 / "No speeches yet"

        delta = date.today() - last_entry.date
        return delta.days

    def next_speech_date(self):
        next_entry = (
            ScheduleEntry.objects
            .filter(assigned_employee=self, is_cancelled=False, date__gt=date.today())
            .order_by('date')
            .first()
        )

        if not next_entry:
            return None

        return next_entry.date
    
    def __str__(self):
        return self.name


# MonthlyEventBatch model
class MonthlyEventBatch(models.Model):
    """
    Tracks event creation batches per month.
    The `month` field should always be the first day of the month (YYYY-MM-01).
    Only one row per month is allowed (unique).
    """
    month = models.DateField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"Batch {self.month.isoformat()} sent={self.is_sent}"


# ScheduleEntry model 
class SpeechType(models.TextChoices):
    BUSINESS = "BUSINESS", "業務"
    THREE_MIN = "THREE_MIN", "３分間"

class ScheduleEntry(models.Model):
    date = models.DateField(unique=True)
    speech_type = models.CharField(max_length=20, choices=SpeechType.choices)

    assigned_employee = models.ForeignKey(
        Employee, null=True, blank=True, on_delete=models.SET_NULL
    )
    is_cancelled = models.BooleanField(default=False)
    google_event_id = models.CharField(max_length=200, blank=True, null=True)
    is_sent = models.BooleanField(default=False)

    # Link to the MonthlyEventBatch so generated-but-unsent entries persist across navigation
    batch = models.ForeignKey(
        MonthlyEventBatch, null=True, blank=True, on_delete=models.SET_NULL, related_name='entries'
    )

    class Meta:
        ordering = ['date']




# CalendarEvent model
class CalendarEvent(models.Model):

    google_calendar_event_id = models.CharField(max_length=200, unique=True)
    calendar_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    schedule_entry = models.OneToOneField(
        ScheduleEntry, on_delete=models.CASCADE
    )

