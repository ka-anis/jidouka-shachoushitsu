from django.db import migrations
from datetime import date
import calendar

# SAFE to import enums directly
from core.models import Role, SpeechType


def populate_data(apps, schema_editor):
    """
    Populates the database with placeholder Employee and ScheduleEntry data.
    """

    Employee = apps.get_model('core', 'Employee')
    ScheduleEntry = apps.get_model('core', 'ScheduleEntry')

    # --- 1. Create employees ---
    employee_names = [
        
        ("岩村", Role.MEMBER, True),
        ("チャラン", Role.MEMBER, True),
        ("ミヌ", Role.MEMBER, True),
        ("トン", Role.MEMBER, True),
        ("佐藤", Role.MEMBER, True),
        ("相川", Role.MEMBER, True),
        ("田中", Role.SHACHOU_SHITSU, True),
        ("萩原", Role.MEMBER, True),
        ("李", Role.MEMBER, True),
        ("フォック", Role.MEMBER, True),
        ("カルパニ", Role.MEMBER, True),
        ("ビン", Role.MEMBER, True),
        ("小倉", Role.SHACHOU_SHITSU, True),
        ("梶", Role.MEMBER, True),
        ("ラフル", Role.MEMBER, True),
        ("ニキル", Role.MEMBER, True),
        ("石田", Role.MEMBER, True),
        ("リブン", Role.MEMBER, True),
        ("堀", Role.MEMBER, True),
        ("諏佐", Role.MEMBER, True),
        ("根岸", Role.MEMBER, True),
        ("齊藤", Role.MEMBER, True),
        ("ノーラン", Role.MEMBER, True),
        ("キン", Role.MEMBER, True),
        ("ソ", Role.MEMBER, True),
        ("カアン", Role.MEMBER, True),
        ("伊藤", Role.MEMBER, True),
        ("ヤシュ", Role.MEMBER, True),
        ("アンキット", Role.MEMBER, True),
        ("スジョン", Role.MEMBER, True),
    ]

    created_employees = []

    for i, (name, role, is_active) in enumerate(employee_names):
        emp, _ = Employee.objects.get_or_create(
            email=f"user{i}@example.com",
            defaults={
                "name": name,
                "employee_id": f"E{i:04}",
                "role": role,
                "is_rotation_active": is_active,
            }
        )
        created_employees.append(emp)

    # --- 2. Create schedule entries ---
    year, month = 2025, 11
    _, num_days = calendar.monthrange(year, month)

    active_employees = [e for e in created_employees if e.is_rotation_active]

    if not active_employees:
        return

    for day_num in range(1, num_days + 1):
        current_date = date(year, month, day_num)

        if current_date.weekday() < 5:  # Mon–Fri
            ScheduleEntry.objects.create(
                date=current_date,
                speech_type=(
                    SpeechType.THREE_MIN
                    if day_num % 2 == 0
                    else SpeechType.BUSINESS
                ),
                assigned_employee=active_employees[day_num % len(active_employees)],
                is_cancelled=False,
            )


def clear_data(apps, schema_editor):
    Employee = apps.get_model('core', 'Employee')
    ScheduleEntry = apps.get_model('core', 'ScheduleEntry')

    ScheduleEntry.objects.all().delete()
    Employee.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(populate_data, reverse_code=clear_data),
    ]
