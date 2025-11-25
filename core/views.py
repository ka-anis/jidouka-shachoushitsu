import os
from django.shortcuts import render, redirect
from django.http import HttpResponse
import csv
from datetime import date, timedelta
from .models import Employee, ScheduleEntry, Role
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

# Create your views here.
def home(request):
    return render(request, "core/home.html", {"message": "Welcome to the Core Home Page!"})


def dashboard_view(request):
    all_employees = Employee.objects.all().order_by("id")
    member_employees = Employee.objects.filter(role=Role.MEMBER).order_by("id")

    def build_entry(emp):
        return {
            "id": emp.id,
            "name": emp.name,
            "is_rotation_active": emp.is_rotation_active,  # <-- correct
            "days_passed": emp.days_since_last_speech(),
            "speech_date": emp.next_speech_date(),
            "calendar": "",
        }

    context = {
        "top_zone": [build_entry(e) for e in all_employees],
        "bottom_zone": [build_entry(e) for e in member_employees],
    }

    return render(request, "core/dashboard.html", context)







def mc_schedule_view(request):
    """Display MC schedule from the database."""
    # Fetch schedule entries from the database
    schedule_entries = ScheduleEntry.objects.select_related('assigned_employee').order_by('date')
    
    # The MC is not explicitly modeled yet. For now, we can get a distinct list of employees.
    # This part will need to be updated once the "MC" role is clearly defined in the models.
    mc_employees = Employee.objects.filter(is_rotation_active=True) # Assuming MCs are active in rotation

    # Green shades for MC column (5 shades matching 5 MC people, from dark to light)
    # Match dashboard green shades
    green_shades = ["bg-green-900", "bg-green-800", "bg-green-700", "bg-green-600", "bg-green-500"]

    # The complex color and role logic was tied to the static data.
    # We now pass the real data and can handle presentation logic in the template.
    # A simplified structure is created here.
    schedule_data = []
    for i, entry in enumerate(schedule_entries):
        schedule_data.append({
            "date_display": entry.date.strftime("%m/%d"),
            "member": entry.assigned_employee.name if entry.assigned_employee else "N/A",
            "mc": "", # MC logic needs to be defined based on your business rules
            "role": entry.assigned_employee.get_role_display() if entry.assigned_employee else "",
            "color_class": "bg-teal-900", # Default color
            "mc_color_class": green_shades[i % len(green_shades)],
        })

    context = {
        "schedule_data": schedule_data,
        "mc_names": [e.name for e in mc_employees],
    }

    return render(request, "core/mc_schedule.html", context)


def download_mc_schedule_csv(request):
    """Download MC schedule from database as a CSV file"""
    schedule_entries = ScheduleEntry.objects.select_related('assigned_employee').order_by('date')

    # Create CSV response
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mc_schedule.csv"'

    # Write BOM for Excel UTF-8 support
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['日付', 'メンバー', 'MC'])

    for entry in schedule_entries:
        writer.writerow([
            entry.date.strftime("%Y-%m-%d"),
            entry.assigned_employee.name if entry.assigned_employee else "N/A",
            "" # MC logic needs to be defined
        ])

    return response

def send_to_calendar(request):
    # As a demo I need this function  to send a google calendar even to a single user. 
    return HttpResponse("Sent to Google Calendar!")




os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # allow HTTP for local dev

CLIENT_SECRETS_FILE = "credentials.json"
REDIRECT_URI = "http://localhost:8000/google/callback/"


# ---------------------------------------------------
# 1) Redirect YOU to Google to authenticate
# ---------------------------------------------------
def google_auth(request):

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=['https://www.googleapis.com/auth/calendar'],
        redirect_uri=REDIRECT_URI,
    )

    authorization_url, state = flow.authorization_url(
        access_type='offline',            # IMPORTANT: gives long-lasting refresh token
        include_granted_scopes='true',
        prompt='consent'                  # forces Google to show the screen every time
    )

    request.session['state'] = state

    return redirect(authorization_url)


# ---------------------------------------------------
# 2) Google redirects HERE after you click Allow
# ---------------------------------------------------
def google_callback(request):

    state = request.session['state']

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=['https://www.googleapis.com/auth/calendar'],
        redirect_uri=REDIRECT_URI,
        state=state,
    )

    flow.fetch_token(authorization_response=request.build_absolute_uri())

    creds = flow.credentials

    # Save credentials in the session
    request.session['google_credentials'] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "token_uri": creds.token_uri,
        "scopes": creds.scopes,
    }

    return HttpResponse("Authentication successful. You are now connected to Google Calendar.")


from django.http import HttpResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def test_create_event(request):

    creds_data = request.session.get("google_credentials")
    if not creds_data:
        return HttpResponse(" Not authenticated. Go to /google/auth/ first.")

    creds = Credentials(
        token=creds_data["token"],
        refresh_token=creds_data["refresh_token"],
        token_uri=creds_data["token_uri"],
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
        scopes=creds_data["scopes"]
    )

    service = build("calendar", "v3", credentials=creds)

    event_data = {
        "summary": "朝礼スピーチ試し",
        "start": {"date": "2025-12-01", "timeZone": "GMT+9"},
        "end":   {"date": "2025-12-02", "timeZone": "GMT+9"},
        "attendees": [
            {"email": "khaled.gad@ejust.edu.eg"},
            {"email": "k-mahrous@ar-system.co.jp"},
            # {"email": "m-ogura@ar-system.co.jp"},
            # {"email": "k-oya@ar-system.co.jp"},
        ],
    }

    event = service.events().insert(calendarId="primary", body=event_data).execute()
    return HttpResponse(f"✔ Event created: {event.get('htmlLink')}")





