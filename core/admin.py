from django.contrib import admin
from .models import Employee, ScheduleEntry, CalendarEvent

# Register your models here.
admin.site.register(Employee)
admin.site.register(ScheduleEntry)
admin.site.register(CalendarEvent)