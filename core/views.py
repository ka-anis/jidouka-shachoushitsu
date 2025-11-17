from django.shortcuts import render
from django.http import HttpResponse
import csv
from datetime import date, timedelta

# Create your views here.
def home(request):
    return render(request, "core/home.html", {"message": "Welcome to the Core Home Page!"})


def dashboard_view(request):
    # Generate 65 static members (5 top / 30 middle / 30 bottom)

    placeholder_names = [
        "岩村",
        "チャラン",
        "ミヌ",
        "トン",
        "佐藤",
        "相川",
        "田中",
        "萩原",
        "李",
        "フォック",
        "カルパニ",
        "ビン",
        "小倉",
        "梶",
        "ラフル",
        "ニキル",
        "石田",
        "リブン",
        "堀",
        "諏佐",
        "根岸",
        "齊藤",
        "ノーラン",
        "キン",
        "ソ",
        "カアン",
        "伊藤",
    ]

    # Use first 6 placeholder names after the first entry for MC placeholders
    mc_names = placeholder_names[1:7]

    members = []
    total = 65
    from datetime import date, timedelta

    base_date = date(2025, 11, 13)
    for i in range(total):
        name = placeholder_names[i % len(placeholder_names)]
        if i < 5:
            status = "Active"
        elif i < 35:
            status = "休み"
        else:
            status = "予定"

        member = {
            "status": status,
            "id": i + 1,
            "name": name,
            "days_passed": (i * 3) % 60,
            "mc": mc_names[i % len(mc_names)],
            "speech_date": (base_date + timedelta(days=i)).isoformat(),
            "speech_experience": "あり" if i % 3 == 0 else "なし",
            "calendar": "〇" if i % 4 == 0 else ("×" if i % 4 == 1 else "△"),
        }
        members.append(member)

    # slice into bands
    top_members = members[:5]
    middle_members = members[5:35]
    bottom_members = members[35:65]

    context = {
        "members": members,
        "top_members": top_members,
        "middle_members": middle_members,
        "bottom_members": bottom_members,
    }

    return render(request, "core/dashboard.html", context)


def mc_schedule_view(request):
    """Display MC schedule and member assignment in a color-coded table"""
    # Static schedule data
    mc_names = ["大矢", "池上", "堀越", "黒澤", "森野"]

    placeholder_names = [
        "岩村",
        "チャラン",
        "ミヌ",
        "トン",
        "佐藤",
        "相川",
        "田中",
        "萩原",
        "李",
        "フォック",
        "カルパニ",
        "ビン",
        "小倉",
        "梶",
        "ラフル",
        "ニキル",
        "石田",
        "リブン",
        "堀",
        "諏佐",
        "根岸",
        "齊藤",
        "ノーラン",
        "キン",
        "ソ",
        "カアン",
        "伊藤",
    ]

    # Generate dates for the schedule - calculate days in month
    base_date = date(2025, 11, 1)

# Get last day of the month (Original Logic)
    if base_date.month == 12:
        last_day = date(base_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(base_date.year, base_date.month + 1, 1) - timedelta(days=1)

    days_in_month = last_day.day
    schedule_data = []

    # --- MODIFIED ITERATION LOGIC STARTS HERE ---
    for day_number in range(days_in_month):
        current_date = base_date + timedelta(days=day_number)
        
        # Check if the current date is a working day (Monday=0 to Friday=4)
        # The weekday() method returns 5 for Saturday and 6 for Sunday.
        if current_date.weekday() < 5: 
            # Only append the date if it's Mon-Fri
            schedule_data.append(current_date)

    # Green shades for MC column (5 shades matching 5 MC people, from dark to light)
    # Match dashboard green shades
    green_shades = ["bg-green-900", "bg-green-800", "bg-green-700", "bg-green-600", "bg-green-500"]

    for i in range(days_in_month):
        member_name = placeholder_names[i % len(placeholder_names)]
        # Determine role and color class based on position
        # Match dashboard colors: green-800/90 for top, #7a3f2b (brown) for middle, teal-900/95 for bottom
        if i == 0:
            # Entry 1: Red with 社長
            role = "社長"
            color_class = "bg-red-600"
            member = "中村"
            mc = ""
            mc_color_class = green_shades[0]  # MC column starts with first green shade from shachou
        elif i < 6:
            # Entries 2-6: Brown (matching dashboard middle band)
            role = "メンバー"
            color_class = green_shades[(i - 1) % len(green_shades)] # Match dashboard middle band brown
            member = mc_names[(i - 1) % len(mc_names)]
            mc = ""
            # Use the same shade index as the MC name index
            mc_color_class = green_shades[(i - 1) % len(green_shades)]
        elif i < (days_in_month - 5):
            # Middle entries: Teal (matching dashboard bottom band)
            role = "メンバー"
            color_class = "bg-teal-900"  # Match dashboard bottom band teal
            member = member_name
            mc = mc_names[(i - 1) % len(mc_names)]
            # Use the same shade index as the MC name index
            mc_color_class = green_shades[(i - 1) % len(green_shades)]
        else:
            # Last 5 entries: Brown (matching dashboard middle band)
            role = "メンバー"
            color_class = "bg-[#7a3f2b]"  # Match dashboard middle band brown
            member = member_name
            mc = mc_names[(i - 1) % len(mc_names)]
            # Use the same shade index as the MC name index
            mc_color_class = green_shades[(i - 1) % len(green_shades)]

        schedule_data.append({
            "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            "date_display": (base_date + timedelta(days=i)).strftime("%m/%d"),
            "member": member,
            "mc": mc,
            "role": role,
            "color_class": color_class,
            "mc_color_class": mc_color_class,
        })

    context = {
        "schedule_data": schedule_data,
        "mc_names": mc_names,
    }

    return render(request, "core/mc_schedule.html", context)


def download_mc_schedule_csv(request):
    """Download MC schedule as CSV file"""
    # Same static data as in the view
    mc_names = ["大矢", "池上", "堀越", "黒澤", "森野"]
    placeholder_names = [
        "岩村",
        "チャラン",
        "ミヌ",
        "トン",
        "佐藤",
        "相川",
        "田中",
        "萩原",
        "李",
        "フォック",
        "カルパニ",
        "ビン",
        "小倉",
        "梶",
        "ラフル",
        "ニキル",
        "石田",
        "リブン",
        "堀",
        "諏佐",
        "根岸",
        "齊藤",
        "ノーラン",
        "キン",
        "ソ",
        "カアン",
        "伊藤",
    ]
    base_date = date(2025, 11, 1)
    # Get last day of the month
    if base_date.month == 12:
        last_day = date(base_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(base_date.year, base_date.month + 1, 1) - timedelta(days=1)

    days_in_month = last_day.day
    schedule_data = []

    for i in range(days_in_month):
        if i == 0:
            member = "placeholder_names[i % len(placeholder_names)]"
            mc = ""
        else:
            member = placeholder_names[i % len(placeholder_names)]
            mc = mc_names[(i - 1) % len(mc_names)]

        schedule_data.append({
            "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            "member": member,
            "mc": mc,
        })

    # Create CSV response
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mc_schedule.csv"'

    # Write BOM for Excel UTF-8 support
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['日付', 'メンバー', 'MC'])

    for entry in schedule_data:
        writer.writerow([entry['date'], entry['member'], entry['mc']])

    return response

