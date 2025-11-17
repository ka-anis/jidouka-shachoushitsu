from django.db import models

# Create your models here.
class Role(models.TextChoices):
    MEMBER = "MEMBER", "メンバー"
    SHACHOU_SHITSU = "SHACHOU_SHITSU", "社長室"

# Employee model 
class Employee(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    employee_id = models.CharField(max_length=10, unique=True)

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    is_rotation_active = models.BooleanField(default=True)

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

