import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from datetime import date, timedelta
from .models import Employee, ScheduleEntry, Role, SpeechType
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from calendar import monthrange
import calendar as cal_module


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

    # Check if user is authenticated with Google
    google_authenticated = "google_credentials" in request.session

    context = {
        "top_zone": [build_entry(e) for e in all_employees],
        "bottom_zone": [build_entry(e) for e in member_employees],
        "google_authenticated": google_authenticated,
    }

    return render(request, "core/dashboard.html", context) 


# =====================================================
# Redirect helpers for dashboard buttons
# =====================================================
def send_to_calendar_redirect(request):
    """
    Redirect from dashboard 送信 button to current month's send view.
    Determines current month and redirects to schedule send endpoint.
    """
    today = date.today()
    year = today.year
    month = today.month
    return redirect('send_to_calendar_month', year=year, month=month)


def retract_schedule_redirect(request):
    """
    Redirect from dashboard リトラクト button to current month's retract view.
    Determines current month and redirects to schedule retract endpoint.
    """
    today = date.today()
    year = today.year
    month = today.month
    return redirect('retract_schedule', year=year, month=month)




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
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    # Store state in session - CRITICAL for CSRF protection
    request.session['oauth_state'] = state
    request.session.save()  # Explicitly save the session

    return redirect(authorization_url)


# ---------------------------------------------------
# 2) Google redirects HERE after you click Allow
# ---------------------------------------------------
@csrf_exempt
def google_callback(request):
    # Retrieve the state we saved in google_auth
    state = request.session.get('oauth_state')
    
    if not state:
        messages.error(request, "Session expired. Please try authenticating again.")
        return redirect('google_auth')

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=['https://www.googleapis.com/auth/calendar'],
        redirect_uri=REDIRECT_URI,
        state=state,
    )

    try:
        flow.fetch_token(authorization_response=request.build_absolute_uri())
    except Exception as e:
        messages.error(request, f"Failed to authenticate with Google: {str(e)}")
        return redirect('google_auth')

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
    
    # Clean up state from session
    if 'oauth_state' in request.session:
        del request.session['oauth_state']
    request.session.save()

    messages.success(request, "Google Calendar authentication successful!")
    return redirect('dashboard')



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


# =====================================================
# STEP 1: Generate Schedule View
# =====================================================
def _get_business_days(year, month):
    """
    Returns a list of all business days (Monday-Friday) in the given month.
    """
    first_day, num_days = monthrange(year, month)
    business_days = []
    
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        # 0=Monday, 6=Sunday
        if current_date.weekday() < 5:  # Monday to Friday
            business_days.append(current_date)
    
    return business_days


@require_http_methods(["POST"])
def generate_schedule(request):
    """
    Generate schedule entries for a given month.
    
    POST parameters: year, month
    
    Rules:
    - First 6 business days: no assignment
    - Last 5 business days: assigned using order_gyomu (業務スピーチ)
    - Middle business days: assigned using order (３分間スピーチ)
    """
    try:
        year = int(request.POST.get('year'))
        month = int(request.POST.get('month'))
    except (ValueError, TypeError):
        messages.error(request, "Invalid year or month.")
        return redirect('dashboard')
    
    # Get all business days in the month
    business_days = _get_business_days(year, month)
    
    if len(business_days) == 0:
        messages.error(request, f"No business days in {year}-{month:02d}.")
        return redirect('dashboard')
    
    # Split into groups
    first_six = business_days[:6]
    last_five = business_days[-5:] if len(business_days) >= 5 else []
    middle_days = business_days[6:-5] if len(business_days) > 11 else []
    
    # Get employees ordered for rotation
    three_min_employees = Employee.objects.filter(is_rotation_active=True).order_by('order', 'id')
    gyomu_employees = Employee.objects.filter(role=Role.MEMBER, is_rotation_active=True).order_by('order_gyomu', 'id')
    
    # Create schedule entries
    created_count = 0
    
    # First 6 business days: no assignment (or skip)
    for day in first_six:
        ScheduleEntry.objects.update_or_create(
            date=day,
            defaults={
                'speech_type': SpeechType.THREE_MIN,
                'assigned_employee': None,
                'is_cancelled': False,
                'is_sent': False,
                'google_event_id': None,
            }
        )
        created_count += 1
    
    # Middle business days: assign using order (３分間スピーチ)
    if three_min_employees.exists():
        for idx, day in enumerate(middle_days):
            emp_idx = idx % len(three_min_employees)
            employee = three_min_employees[emp_idx]
            ScheduleEntry.objects.update_or_create(
                date=day,
                defaults={
                    'speech_type': SpeechType.THREE_MIN,
                    'assigned_employee': employee,
                    'is_cancelled': False,
                    'is_sent': False,
                    'google_event_id': None,
                }
            )
            created_count += 1
    
    # Last 5 business days: assign using order_gyomu (業務スピーチ)
    if gyomu_employees.exists():
        for idx, day in enumerate(last_five):
            emp_idx = idx % len(gyomu_employees)
            employee = gyomu_employees[emp_idx]
            ScheduleEntry.objects.update_or_create(
                date=day,
                defaults={
                    'speech_type': SpeechType.BUSINESS,
                    'assigned_employee': employee,
                    'is_cancelled': False,
                    'is_sent': False,
                    'google_event_id': None,
                }
            )
            created_count += 1
    
    messages.success(request, f"Generated schedule for {year}-{month:02d}. ({created_count} entries)")
    return redirect('schedule_preview', year=year, month=month)


# =====================================================
# STEP 2: Schedule Preview View
# =====================================================
@require_http_methods(["GET"])
def schedule_preview(request, year, month):
    """
    Display the generated schedule for the selected month.
    
    GET parameters: year, month
    """
    try:
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        messages.error(request, "Invalid year or month.")
        return redirect('dashboard')
    
    # Get all business days for this month
    business_days = _get_business_days(year, month)
    
    # Load schedule entries for this month
    schedule_entries = ScheduleEntry.objects.filter(
        date__year=year,
        date__month=month
    ).select_related('assigned_employee').order_by('date')
    
    # Group by date for display
    schedule_data = []
    entry_map = {entry.date: entry for entry in schedule_entries}
    
    for day in business_days:
        entry = entry_map.get(day)
        schedule_data.append({
            'date': day,
            'date_display': day.strftime('%Y-%m-%d'),
            'day_name': ['月', '火', '水', '木', '金'][day.weekday()],
            'speech_type': entry.speech_type if entry else None,
            'speech_type_display': entry.get_speech_type_display() if entry else 'N/A',
            'assigned_employee': entry.assigned_employee.name if entry and entry.assigned_employee else 'N/A',
            'is_sent': entry.is_sent if entry else False,
        })
    schedule_data = schedule_data[6:]
    context = {
        'year': year,
        'month': month,
        'month_display': f'{year}-{month:02d}',
        'schedule_data': schedule_data,
    }
    
    return render(request, 'core/schedule_preview.html', context)


# =====================================================
# STEP 3: Send to Google Calendar View
# =====================================================
def _get_google_service(request):
    """
    Get Google Calendar service from session credentials.
    Returns None if not authenticated.
    """
    creds_data = request.session.get('google_credentials')
    if not creds_data:
        return None
    
    try:
        creds = Credentials(
            token=creds_data.get("token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data.get("token_uri"),
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
            scopes=creds_data.get("scopes")
        )
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        return None


@require_http_methods(["GET","POST"])
def send_schedule_to_calendar(request, year, month):
    """
    Send all schedule entries for the selected month to Google Calendar.
    
    POST parameters: year, month
    """
    try:
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        messages.error(request, "Invalid year or month.")
        return redirect('dashboard')
    
    # Check if user is authenticated with Google
    service = _get_google_service(request)
    if not service:
        messages.error(request, "Not authenticated with Google Calendar. Please authenticate first.")
        return redirect('google_auth')
    
    # Load schedule entries for this month
    schedule_entries = ScheduleEntry.objects.filter(
        date__year=year,
        date__month=month,
        assigned_employee__isnull=False
    ).select_related('assigned_employee')
    
    sent_count = 0
    error_count = 0
    
    for entry in schedule_entries:
        try:
            # Validate email
            if not entry.assigned_employee.email:
                messages.warning(request, f"{entry.assigned_employee.name} has no email.")
                error_count += 1
                continue
            
            # Create event with just speech type as title
            event_title = entry.get_speech_type_display()  # Just "業務" or "３分間"
            
            event_data = {
                "summary": event_title,
                "start": {"date": entry.date.isoformat(), "timeZone": "Asia/Tokyo"},
                "end": {"date": (entry.date + timedelta(days=1)).isoformat(), "timeZone": "Asia/Tokyo"},
                "attendees": [
                    {"email": entry.assigned_employee.email}
                ],
            }
            
            # DON'T FORGET TO CHANGE THE ID WHEN Setting up a new user
            event = service.events().insert(calendarId="c_d4fadaaa8d92cb15033ceef352f6e8685947cad7f3cb52af359e4a814dccc6da@group.calendar.google.com", body=event_data, sendNotifications=False).execute()
            event_id = event.get('id')
            
            # Save event ID and mark as sent
            entry.google_event_id = event_id
            entry.is_sent = True
            entry.save()
            sent_count += 1
            
        except HttpError as e:
            messages.warning(request, f"Failed to create event for {entry.date}: {str(e)}")
            error_count += 1
        except Exception as e:
            messages.warning(request, f"Error for {entry.date}: {str(e)}")
            error_count += 1
    
    messages.success(request, f" {sent_count}件　登録完了")
    if error_count > 0:
        messages.warning(request, f"{error_count} events failed to send.")
    
    return redirect('schedule_preview', year=year, month=month)


# =====================================================
# STEP 4: Retract (Delete from Google Calendar) View
# =====================================================
@require_http_methods(["POST"])
def retract_schedule(request, year, month):
    """
    Delete previously-sent Google Calendar events for the selected month.
    
    POST parameters: year, month
    """
    try:
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        messages.error(request, "Invalid year or month.")
        return redirect('dashboard')
    
    # Check if user is authenticated with Google
    service = _get_google_service(request)
    if not service:
        messages.error(request, "Not authenticated with Google Calendar. Please authenticate first.")
        return redirect('google_auth')
    
    # Load schedule entries for this month that have been sent
    schedule_entries = ScheduleEntry.objects.filter(
        date__year=year,
        date__month=month,
        is_sent=True,
        google_event_id__isnull=False
    )
    
    deleted_count = 0
    error_count = 0
    
    for entry in schedule_entries:
        try:
            if entry.google_event_id:
                # Delete from attendee's calendar (where it was created)
                service.events().delete(
                    # DON'T FORGET TO CHANGE THE ID WHEN Setting up a new user  
                    calendarId="c_d4fadaaa8d92cb15033ceef352f6e8685947cad7f3cb52af359e4a814dccc6da@group.calendar.google.com",
                    eventId=entry.google_event_id
                ).execute()
                
                # Clear event ID and mark as not sent
                entry.google_event_id = None
                entry.is_sent = False
                entry.save()
                deleted_count += 1
        except HttpError as e:
            if e.resp.status == 404:
                # Event already deleted on Google side, just clear locally
                entry.google_event_id = None
                entry.is_sent = False
                entry.save()
                deleted_count += 1
            else:
                messages.warning(request, f"Failed to delete event for {entry.date}: {str(e)}")
                error_count += 1
        except Exception as e:
            messages.warning(request, f"Error for {entry.date}: {str(e)}")
            error_count += 1
    
    messages.success(request, f"{deleted_count}件　　削除完了")
    if error_count > 0:
        messages.warning(request, f"{error_count} events failed to retract.")
    
    return redirect('schedule_preview', year=year, month=month)






