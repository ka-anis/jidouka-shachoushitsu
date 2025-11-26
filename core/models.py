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

