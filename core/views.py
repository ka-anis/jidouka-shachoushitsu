import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from datetime import date, timedelta
from .models import Employee, ScheduleEntry, Role
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# Create your views here.
def home(request):
    return render(request, "core/home.html", {"message": "Welcome to the Core Home Page!"})


def dashboard_view(request):
    # Top zone: order by `order` (3分間スピーチ ordering)
    all_employees = Employee.objects.all().order_by("order", "id")
    # Bottom zone: order by `order_gyomu` (業務スピーチ ordering)
    member_employees = Employee.objects.filter(role=Role.MEMBER).order_by("order_gyomu", "id")

    def build_entry(emp):
        return {
            "id": emp.id,
            "name": emp.name,
            "is_rotation_active": emp.is_rotation_active,  # <-- correct
            "order": getattr(emp, 'order', None),
            "order_gyomu": getattr(emp, 'order_gyomu', None),
            "days_passed": emp.days_since_last_speech(),
            "speech_date": emp.next_speech_date(),
            "speech_type": None,
            "calendar": "",
        }

    context = {
        "top_zone": [build_entry(e) for e in all_employees],
        "bottom_zone": [build_entry(e) for e in member_employees],
    }

    return render(request, "core/dashboard.html", context) 




 


def mc_schedule_view(request):
    """Display MC schedule from the database."""
    
    schedule_entries = ScheduleEntry.objects.select_related('assigned_employee').order_by('date')
    
    mc_employees = Employee.objects.filter(is_rotation_active=True) 

    green_shades = ["bg-green-900", "bg-green-800", "bg-green-700", "bg-green-600", "bg-green-500"]

    schedule_data = []
    for i, entry in enumerate(schedule_entries):
        schedule_data.append({
            "date_display": entry.date.strftime("%m/%d"),
            "member": entry.assigned_employee.name if entry.assigned_employee else "N/A",
            "mc": "", 
            "role": entry.assigned_employee.get_role_display() if entry.assigned_employee else "",
            "color_class": "bg-teal-900", # Default color
            "mc_color_class": green_shades[i % len(green_shades)],
        })

    context = {
        "schedule_data": schedule_data,
        "mc_names": [e.name for e in mc_employees],
    }

    return render(request, "core/mc_schedule.html", context)

def send_to_calendar(request):
    return render(request, "core/send_to_calendar.html")




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
            # {"email": "k-mahrous@ar-system.co.jp"},
        ],
    }

    event = service.events().insert(calendarId="primary", body=event_data).execute()
    return HttpResponse(f"✔ Event created: {event.get('htmlLink')}")




def move_up(request, employee_id):
    emp = get_object_or_404(Employee, id=employee_id)
    # Find employee with the highest order value less than current
    above = Employee.objects.filter(order__lt=emp.order).order_by("-order").first()
    if above:
        emp.order, above.order = above.order, emp.order
        emp.save()
        above.save()
    
    # Return JSON for AJAX requests, otherwise redirect
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Order updated'})
    return redirect("dashboard")

def move_down(request, employee_id):
    emp = get_object_or_404(Employee, id=employee_id)
    below = Employee.objects.filter(order__gt=emp.order).order_by("order").first()
    if below:
        emp.order, below.order = below.order, emp.order
        emp.save()
        below.save()
    
    # Return JSON for AJAX requests, otherwise redirect
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Order updated'})
    return redirect("dashboard")


def move_up_gyomu(request, employee_id):
    emp = get_object_or_404(Employee, id=employee_id)
    # Find employee with the highest order_gyomu value less than current
    above = Employee.objects.filter(order_gyomu__lt=emp.order_gyomu).order_by("-order_gyomu").first()
    if above:
        emp.order_gyomu, above.order_gyomu = above.order_gyomu, emp.order_gyomu
        emp.save()
        above.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Order updated'})
    return redirect("dashboard")


def move_down_gyomu(request, employee_id):
    emp = get_object_or_404(Employee, id=employee_id)
    below = Employee.objects.filter(order_gyomu__gt=emp.order_gyomu).order_by("order_gyomu").first()
    if below:
        emp.order_gyomu, below.order_gyomu = below.order_gyomu, emp.order_gyomu
        emp.save()
        below.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Order updated'})
    return redirect("dashboard")


def toggle_active(request, employee_id):
    if request.method == "POST":
        employee = get_object_or_404(Employee, id=employee_id)
        employee.is_rotation_active = not employee.is_rotation_active
        employee.save()
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))  # redirect back






