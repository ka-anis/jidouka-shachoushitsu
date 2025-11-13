from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, "core/home.html", {"message": "Welcome to the Core Home Page!"})


def dashboard_view(request):
    # Generate 65 static members (5 top / 30 middle / 30 bottom)
    family_names = [
        "佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村", "小林", "加藤",
        "吉田", "山田", "佐々木", "山口", "松本", "井上", "木村", "林", "斎藤", "清水",
    ]
    given_names = ["太郎", "花子", "次郎", "一郎", "二郎", "三子", "健", "菜々", "誠", "彩"]

    mc_names = ["佐藤", "高橋", "中村", "小林", "加藤", "吉田"]

    members = []
    total = 65
    from datetime import date, timedelta

    base_date = date(2025, 11, 13)
    for i in range(total):
        family = family_names[i % len(family_names)]
        given = given_names[i % len(given_names)]
        name = f"{family}{given}"
        # assign zones: first 5 -> top (Active), next 30 -> middle (休み), last 30 -> bottom (予定)
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

