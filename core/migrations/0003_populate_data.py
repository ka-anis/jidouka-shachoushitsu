from django.db import migrations
from datetime import date
import calendar

# SAFE to import enums directly
from core.models import Role, SpeechType


def populate_data(apps, schema_editor):
    """
    Populates the database with ACTUAL Employee and ScheduleEntry data.
    """

    Employee = apps.get_model('core', 'Employee')

    # --- 1. Create employees ---
    employee_data = [
        (1, "岩村", Role.MEMBER, True, "g-iwamura@ar-system.co.jp", 1),
        (2, "チャラン", Role.MEMBER, True, "charan-supriya@ar-system.co.jp", 2),
        (3, "ミヌ", Role.MEMBER, True, "m-kim@ar-system.co.jp", 3),
        (4, "トン", Role.MEMBER, True, "v.t.nguyen@ar-system.co.jp", 4),
        (5, "佐藤", Role.MEMBER, True, "t-sato@ar-system.co.jp", 5),
        (6, "相川", Role.MEMBER, True, "s-aikawa@ar-system.co.jp", 6),
        (7, "田中", Role.SHACHOU_SHITSU, True, "m-tanaka@ar-system.co.jp", 7),
        (8, "萩原", Role.MEMBER, True, "m-hagiwara@ar-system.co.jp", 8),
        (9, "李", Role.MEMBER, True, "d-lee@ar-system.co.jp", 9),
        (10, "フォック", Role.MEMBER, True, "m.phuoc.le@ar-system.co.jp", 10),
        (11, "カルパニ", Role.MEMBER, True, "k-udawela@ar-system.co.jp", 11),
        (12, "ビン", Role.MEMBER, True, "ho.van.binh@ar-system.co.jp", 12),
        (13, "小倉", Role.SHACHOU_SHITSU, True, "m-ogura@ar-system.co.jp", 13),
        (14, "梶", Role.MEMBER, True, "n-kaji@ar-system.co.jp", 14),
        (15, "ラフル", Role.MEMBER, True, "r.r.sinha@ar-system.co.jp", 15),
        (16, "ニキル", Role.MEMBER, True, "n.g.pangaonkar@ar-system.co.jp", 16),
        (17, "石田", Role.MEMBER, True, "t-ishida@ar-system.co.jp", 17),
        (18, "リブン", Role.MEMBER, True, "w-lee@ar-system.co.jp", 18),
        (19, "堀", Role.MEMBER, True, "t-hori@ar-system.co.jp", 19),
        (20, "諏佐", Role.MEMBER, True, "k-susa@ar-system.co.jp", 20),
        (21, "根岸", Role.MEMBER, True, "t-negishi@ar-system.co.jp", 21),
        (22, "齊藤", Role.MEMBER, True, "t-saito@ar-system.co.jp", 22),
        (23, "ノーラン", Role.MEMBER, True, "f.w-nolan@ar-system.co.jp", 23),
        (24, "キン", Role.MEMBER, True, "p-khin@ar-system.co.jp", 24),
        (25, "ソ", Role.MEMBER, True, "g-so@ar-system.co.jp", 25),
        (26, "カアン", Role.MEMBER, True, "bui.khang@ar-system.co.jp", 26),
        (27, "伊藤", Role.MEMBER, True, "f-ito@ar-system.co.jp", 27),
        (28, "ヤシュ", Role.MEMBER, True, "yash-j@ar-system.co.jp", 28),
        (29, "アンキット", Role.MEMBER, True, "ankit-m@ar-system.co.jp", 29),
        (30, "スジョン", Role.MEMBER, True, "s-kim@ar-system.co.jp", 30),
        (31, "坂本", Role.MEMBER, False, "j-sakamoto@ar-system.co.jp", 31),
        (32, "オム", Role.MEMBER, False, "om.a@ar-system.co.jp", 32),
    ]


    for emp_id, name, role, is_active, email, order in employee_data:
        Employee.objects.create(
            employee_id=str(emp_id),
            name=name,
            role=role,
            is_rotation_active=is_active,
            email=email,
            order=order
        )


def clear_data(apps, schema_editor):
    """
    Clears the data populated by populate_data function.
    """
    Employee = apps.get_model('core', 'Employee')
    Employee.objects.all().delete()

class Migration(migrations.Migration): 

    dependencies = [
        ('core', '0002_populate_data'),
    ]

    operations = [
        migrations.RunPython(populate_data, reverse_code=clear_data),
    ]
