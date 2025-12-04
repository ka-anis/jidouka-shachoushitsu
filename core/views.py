import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db import models
from datetime import date, timedelta
from .models import Employee, ScheduleEntry, Role, SpeechType, MonthlyEventBatch
import logging
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from calendar import monthrange
import calendar as cal_module


# =====================================================
# Helper Functions
# =====================================================

def apply_rotation(current_order, assigned_members, did_speak_map):
    """
    Apply rotation logic based on speech history.
    
    Groups members into three categories and merges them in order:
    1. Missed speakers (assigned but did_speak=False) - HIGHEST priority
    2. Unassigned members - MIDDLE priority (preserve original order)
    3. Spoke members (assigned and did_speak=True) - LOWEST priority
    
    Args:
        current_order: List of Employee objects in current order (e.g., by .order field)
        assigned_members: List of Employee objects assigned this month
        did_speak_map: Dict {employee_id: bool} indicating if each assigned member spoke
    
    Returns:
        List of Employee objects in new rotation order
    """
    # Identify the three groups
    assigned_set = set(emp.id for emp in assigned_members)
    missed_speakers = []
    spoke_members = []
    unassigned_members = []
    
    for emp in current_order:
        if emp.id in assigned_set:
            # This employee was assigned
            if did_speak_map.get(emp.id, True):
                # Checkbox was checked (True) or not present -> they spoke
                spoke_members.append(emp)
            else:
                # Checkbox was unchecked (False) -> they didn't speak
                missed_speakers.append(emp)
        else:
            # This employee was NOT assigned
            unassigned_members.append(emp)
    
    # Merge in the required order
    new_rotation = missed_speakers + unassigned_members + spoke_members
    
    return new_rotation


def get_next_month_date(from_date=None):
    """
    Calculate the first day of next month from a given date.
    If from_date is None, uses today.
    Returns a date object (YYYY-MM-01).
    """
    if from_date is None:
        from_date = date.today()
    
    year = from_date.year
    month = from_date.month
    
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
    
    return date(next_year, next_month, 1)


def get_or_create_batch(month_date):
    """
    Get or create a MonthlyEventBatch for the given month.
    Ensures idempotency - no duplicate batches are created.
    
    Args:
        month_date: A date object (preferably YYYY-MM-01)
    
    Returns:
        MonthlyEventBatch instance
    """
    month_start = date(month_date.year, month_date.month, 1)
    batch, created = MonthlyEventBatch.objects.get_or_create(month=month_start)
    return batch


# Create your views here.
def home(request):
    return render(request, "core/home.html", {"message": "Welcome to the Core Home Page!"})


def dashboard_view(request):
    """
    Dashboard view that loads employee lists and batch info for current & next months.
    
    Context variables:
    - top_zone: All employees ordered by 'order' (3分間スピーチ)
    - bottom_zone: Member employees ordered by 'order_gyomu' (業務スピーチ)
    - google_authenticated: Whether user has authenticated with Google Calendar
    - current_year, current_month, next_year, next_month: Date info
    - current_batch_exists, current_batch_sent: Current month batch status
    - next_batch_exists, next_batch_sent: Next month batch status
    """
    # Top zone: order by `order` (3分間スピーチ ordering)
    all_employees = Employee.objects.all().order_by("order", "id")
    # Bottom zone: order by `order_gyomu` (業務スピーチ ordering)
    member_employees = Employee.objects.filter(role=Role.MEMBER).order_by("order_gyomu", "id")

    def build_entry(emp):
        return {
            "id": emp.id,
            "name": emp.name,
            "is_rotation_active": emp.is_rotation_active,
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

    # Calculate current and next month dates
    today = date.today()
    current_year = today.year
    current_month = today.month
    current_month_start = date(current_year, current_month, 1)
    next_month_start = get_next_month_date(current_month_start)

    # Load batch info for BOTH current and next month
    current_batch = MonthlyEventBatch.objects.filter(month=current_month_start).first()
    next_batch = MonthlyEventBatch.objects.filter(month=next_month_start).first()

    # Determine next month's year and month for template
    next_year = next_month_start.year
    next_month = next_month_start.month

    context.update({
        'current_year': current_year,
        'current_month': current_month,
        'next_year': next_year,
        'next_month': next_month,
        # Current month batch status
        'current_batch_exists': bool(current_batch),
        'current_batch_sent': bool(current_batch.is_sent) if current_batch else False,
        # Next month batch status
        'next_batch_exists': bool(next_batch),
        'next_batch_sent': bool(next_batch.is_sent) if next_batch else False,
    })

    return render(request, "core/dashboard.html", context) 


# =====================================================
# Redirect helpers for dashboard buttons
# =====================================================
def send_to_calendar_redirect(request):
    """
    Redirect from dashboard 送信 button to month's send view.
    
    Query parameters:
    - year: target year (optional, defaults to current)
    - month: target month (optional, defaults to current)
    """
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year is None or month is None:
        today = date.today()
        year = int(year) if year else today.year
        month = int(month) if month else today.month
    else:
        year = int(year)
        month = int(month)
    
    return redirect('send_to_calendar_month', year=year, month=month)


def retract_schedule_redirect(request):
    """
    Redirect from dashboard リトラクト button to month's retract view.
    
    Query parameters:
    - year: target year (optional, defaults to current)
    - month: target month (optional, defaults to current)
    """
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year is None or month is None:
        today = date.today()
        year = int(year) if year else today.year
        month = int(month) if month else today.month
    else:
        year = int(year)
        month = int(month)
    
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
# Add Member View
# =====================================================
def add_member_view(request):
    """
    Handle GET (display form) and POST (create employee) for adding new members.
    Validates email uniqueness and name requirement.
    """
    if request.method == "GET":
        return render(request, "core/add_member.html")
    
    elif request.method == "POST":
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        # Validation: empty name
        if not name:
            messages.error(request, "氏名を入力してください。")
            return render(request, "core/add_member.html", {
                "name": name,
                "email": email,
                "is_active": is_active,
            })
        
        # Validation: duplicate email
        if Employee.objects.filter(email=email).exists():
            messages.error(request, "このメールアドレスは既に登録されています。")
            return render(request, "core/add_member.html", {
                "name": name,
                "email": email,
                "is_active": is_active,
            })
        
        # Validation: email format (basic check)
        if not email or '@' not in email:
            messages.error(request, "有効なメールアドレスを入力してください。")
            return render(request, "core/add_member.html", {
                "name": name,
                "email": email,
                "is_active": is_active,
            })
        
        try:
            # Get the next order values
            max_order = Employee.objects.aggregate(models.Max('order'))['order__max'] or -1
            max_order_gyomu = Employee.objects.aggregate(models.Max('order_gyomu'))['order_gyomu__max'] or -1
            
            # Create employee
            employee = Employee.objects.create(
                name=name,
                email=email,
                employee_id=f"EMP{Employee.objects.count() + 1:03d}",
                order=max_order + 1,
                order_gyomu=max_order_gyomu + 1,
                is_rotation_active=is_active,
                role=Role.MEMBER,
            )
            
            messages.success(request, f"{name}さんを追加しました！")
            return redirect("dashboard")
        
        except Exception as e:
            messages.error(request, f"エラーが発生しました: {str(e)}")
            return render(request, "core/add_member.html", {
                "name": name,
                "email": email,
                "is_active": is_active,
            })


# =====================================================
# Remove member (modal + submit)
# =====================================================
logger = logging.getLogger(__name__)


def remove_member_modal(request):
    """
    GET: return modal fragment for AJAX or full-page fallback.
    """
    if request.method != 'GET':
        return redirect('dashboard')

    # If AJAX request, return fragment
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'core/_remove_member_modal.html')

    # Full page fallback
    return render(request, 'core/remove_member.html')


@require_http_methods(["POST"])
def remove_member_submit(request):
    """
    POST: validate email, remove employee, rebalance orders, nullify schedule entries.
    Supports AJAX JSON responses or full-page fallback with messages.
    """
    email = request.POST.get('email', '').strip().lower()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not email:
        msg = '有効なメールアドレスを入力してください。'
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': msg}, status=400)
        messages.error(request, msg)
        return redirect('remove_member_modal')

    try:
        employee = Employee.objects.filter(email__iexact=email).first()
        if not employee:
            msg = 'このメールアドレスは登録されていません。'
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': msg}, status=404)
            messages.error(request, msg)
            return redirect('remove_member_modal')

        # log admin and timestamp
        admin = getattr(request, 'user', None)
        admin_repr = getattr(admin, 'username', 'anonymous') if admin else 'anonymous'
        logger.info(f"Removing employee {employee.email} by admin={admin_repr}")

        # Remove / delete employee
        emp_id = employee.id
        employee.delete()

        # Nullify schedule entries that referenced this employee
        ScheduleEntry.objects.filter(assigned_employee_id=emp_id).update(
            assigned_employee=None,
            is_sent=False,
            google_event_id=None
        )

        # Recompute order (3分間) for all employees preserving relative order
        all_emps = list(Employee.objects.all().order_by('order', 'id'))
        for idx, e in enumerate(all_emps, start=1):
            if e.order != idx:
                e.order = idx
                e.save()

        # Recompute order_gyomu for members
        gyomu_emps = list(Employee.objects.filter(role=Role.MEMBER).order_by('order_gyomu', 'id'))
        for idx, e in enumerate(gyomu_emps, start=1):
            if e.order_gyomu != idx:
                e.order_gyomu = idx
                e.save()

        success_msg = 'メンバーを削除しました。'
        if is_ajax:
            return JsonResponse({'status': 'success', 'message': success_msg})

        messages.success(request, success_msg)
        return redirect('dashboard')

    except Exception as e:
        logger.exception('Error removing member')
        err_msg = 'メンバー削除中にエラーが発生しました。'
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': err_msg}, status=500)
        messages.error(request, err_msg)
        return redirect('remove_member_modal')


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
    - A batch can only be generated once per month (use get_or_create_batch)
    - If batch is already sent, do NOT allow regeneration
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

    # Enforce batch rules: prevent regeneration of sent batches
    month_start = date(year, month, 1)
    batch = get_or_create_batch(month_start)
    
    if batch.is_sent:
        messages.error(request, "この月は既に送信済みのため、スケジュールの作成はできません。")
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
                'batch': batch,
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
                    'batch': batch,
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
                    'batch': batch,
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

    # Batch info to control send/retract
    month_start = date(year, month, 1)
    from .models import MonthlyEventBatch
    batch = MonthlyEventBatch.objects.filter(month=month_start).first()

    context = {
        'year': year,
        'month': month,
        'month_display': f'{year}-{month:02d}',
        'schedule_data': schedule_data,
        'batch_exists': bool(batch),
        'batch_sent': bool(batch.is_sent) if batch else False,
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
    
    Enforces that batches can only be sent once per month.
    If batch.is_sent is True, rejects the request and shows error message.
    
    Also applies rotation logic based on did_speak checkboxes from Kakunin Gamen.

    POST parameters: year, month, did_speak_<date> (checkboxes)
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

    month_start = date(year, month, 1)
    batch = MonthlyEventBatch.objects.filter(month=month_start).first()
    
    if not batch:
        messages.error(request, "スケジュールが生成されていません。先にスケジュールを作成してください。")
        return redirect('schedule_preview', year=year, month=month)
    
    # ENFORCE: Batch can only be sent once per month
    if batch.is_sent:
        messages.error(request, "この月は既に送信済みです。再度の送信はできません。")
        return redirect('schedule_preview', year=year, month=month)

    # Load schedule entries linked to this batch
    schedule_entries = ScheduleEntry.objects.filter(
        batch=batch,
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

    # Mark batch as sent only if we successfully sent at least some events
    if sent_count > 0:
        batch.is_sent = True
        batch.save()

    # ==========================================
    # ROTATION LOGIC: Apply after sending
    # ==========================================
    try:
        # Parse did_speak checkboxes from POST data
        # Format: did_speak_<YYYY-MM-DD> = employee_name
        did_speak_map = {}  # {employee_id: did_speak_bool}
        
        # Get all schedule entries for this month to map dates to employees
        all_entries = ScheduleEntry.objects.filter(
            batch=batch,
            assigned_employee__isnull=False
        ).select_related('assigned_employee')
        
        # Debug: Log POST keys
        logging.debug(f"POST keys for rotation: {list(request.POST.keys())}")
        
        for entry in all_entries:
            date_str = entry.date.strftime('%Y-%m-%d')
            checkbox_key = f'did_speak_{date_str}'
            # If checkbox exists in POST, employee spoke. If missing, they didn't.
            spoke = checkbox_key in request.POST
            did_speak_map[entry.assigned_employee.id] = spoke
            logging.debug(f"Employee {entry.assigned_employee.name} ({entry.assigned_employee.id}): {checkbox_key} -> {spoke}")
        
        # Get list of assigned members for this month
        assigned_members = set(
            Employee.objects.filter(
                id__in=[e.assigned_employee.id for e in all_entries]
            )
        )
        
        logging.debug(f"Assigned members: {[e.name for e in assigned_members]}")
        logging.debug(f"did_speak_map: {did_speak_map}")
        
        # Determine which field to update based on speech type
        # For now, we'll update BOTH order and order_gyomu to maintain consistency
        # Get current rotation for 3-minute speeches
        three_min_employees = list(
            Employee.objects.filter(is_rotation_active=True).order_by('order', 'id')
        )
        
        # Get current rotation for business speeches
        gyomu_employees = list(
            Employee.objects.filter(role=Role.MEMBER, is_rotation_active=True).order_by('order_gyomu', 'id')
        )
        
        logging.debug(f"3-min employees before: {[(e.id, e.name, e.order) for e in three_min_employees]}")
        logging.debug(f"Gyomu employees before: {[(e.id, e.name, e.order_gyomu) for e in gyomu_employees]}")
        
        # Apply rotation for 3-minute speeches
        if three_min_employees:
            new_order_3min = apply_rotation(three_min_employees, assigned_members, did_speak_map)
            logging.debug(f"3-min employees after apply_rotation: {[(e.id, e.name) for e in new_order_3min]}")
            for idx, emp in enumerate(new_order_3min, start=1):
                emp.order = idx
                emp.save()
            logging.debug(f"3-min employees saved with new order")
        
        # Apply rotation for business speeches
        if gyomu_employees:
            new_order_gyomu = apply_rotation(gyomu_employees, assigned_members, did_speak_map)
            logging.debug(f"Gyomu employees after apply_rotation: {[(e.id, e.name) for e in new_order_gyomu]}")
            for idx, emp in enumerate(new_order_gyomu, start=1):
                emp.order_gyomu = idx
                emp.save()
            logging.debug(f"Gyomu employees saved with new order")
        
        messages.success(request, "ローテーション更新完了しました。")
    
    except Exception as e:
        messages.warning(request, f"ローテーション更新中にエラーが発生しました: {str(e)}")

    messages.success(request, f"{sent_count}件　登録完了")
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
    Resets batch.is_sent to False so the schedule can be resent if needed.

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

    month_start = date(year, month, 1)
    batch = MonthlyEventBatch.objects.filter(month=month_start).first()
    if not batch:
        messages.error(request, "この月の送信情報が見つかりません。")
        return redirect('schedule_preview', year=year, month=month)

    # Load schedule entries for this batch that were sent
    schedule_entries = ScheduleEntry.objects.filter(
        batch=batch,
        google_event_id__isnull=False
    )

    deleted_count = 0
    error_count = 0

    for entry in schedule_entries:
        try:
            if entry.google_event_id:
                # Delete from calendar where it was created
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

    # After deletion, reset batch.is_sent to False so schedule can be resent
    batch.is_sent = False
    batch.save()

    messages.success(request, f"{deleted_count}件　削除完了")
    if error_count > 0:
        messages.warning(request, f"{error_count} events failed to retract.")

    return redirect('schedule_preview', year=year, month=month)






