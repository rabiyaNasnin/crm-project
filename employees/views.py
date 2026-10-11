import os
import json
import difflib

from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q

from groq import Groq

from .models import Employee, Robot
from .forms import RobotForm, RobotAdminForm, EmployeeForm
from hr.forms import EmployeeLeaveForm, EmployeeAttendanceForm
from hr.models import Attendance, Leave


GROQ_MODEL = "openai/gpt-oss-120b"


# ---------------------------------------------------------------------------
# Role helpers (used by both the views and the chatbot tool dispatch)
# ---------------------------------------------------------------------------
def is_admin(user):
    return user.is_superuser or user.groups.filter(name="Admin").exists()


def is_hr(user):
    return user.groups.filter(name="HR").exists()


def is_employee(user):
    return user.groups.filter(name="Employee").exists()


# ---------------------------------------------------------------------------
# Plain Groq helper (kept for any non-tool use)
# ---------------------------------------------------------------------------
def ask_groq(prompt):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Data-access functions
# ---------------------------------------------------------------------------
def _parse_date(value, default):
    """Parse a date leniently; fall back to default on anything unusable."""
    if value:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return timezone.datetime.strptime(
                    str(value).strip(), fmt
                ).date()
            except (ValueError, TypeError):
                continue
    return default


def get_attendance(start_date="", end_date="", employee=None, employee_name=""):
    today = timezone.localdate()
    start = _parse_date(start_date, today)
    end = _parse_date(end_date, start)

    if end < start:
        start, end = end, start

    records = Attendance.objects.filter(
        date__range=(start, end)
    ).select_related("employee")

    # Employees can only see their own attendance
    if employee is not None:
        records = records.filter(employee=employee)
    elif employee_name:
        records = records.filter(
            Q(employee__name__icontains=employee_name)
            | Q(employee__employee_id__icontains=employee_name)
        )

    attendance_records = [
        {
            "employee_name": record.employee.name,
            "date": str(record.date),
            "status": record.status,
        }
        for record in records.order_by("date", "employee__name")
    ]

    daily_summary = []
    current_date = start

    while current_date <= end:
        day_records = records.filter(date=current_date)

        daily_summary.append(
            {
                "date": str(current_date),
                "present": day_records.filter(status="Present").count(),
                "absent": day_records.filter(status="Absent").count(),
                "leave": day_records.filter(status="Leave").count(),
                "total_marked": day_records.count(),
            }
        )

        current_date += timezone.timedelta(days=1)

    return {
        "start_date": str(start),
        "end_date": str(end),
        "attendance_records": attendance_records,
        "daily_summary": daily_summary,
    }


def get_employee_data(
    user, employee_name="", department="", employee_id=""
):
    """
    Get employee information from the CRM database.
    Access is controlled based on the logged-in user's role.
    """

    # Employee users can only see their own information
    if is_employee(user) and not is_hr(user) and not is_admin(user):
        employee = Employee.objects.filter(user=user).first()

        if not employee:
            return {"error": "Employee profile not found."}

        return {
            "employees": [
                {
                    "employee_id": employee.employee_id,
                    "name": employee.name,
                    "email": employee.email,
                    "phone": employee.phone,
                    "department": employee.department,
                    "designation": employee.designation,
                }
            ]
        }

    # Admin and HR can search all employees
    employees = Employee.objects.all()

    if employee_name:
        employees = employees.filter(
            Q(name__icontains=employee_name)
            | Q(employee_id__icontains=employee_name)
        )

    if employee_id:
        employees = employees.filter(employee_id__icontains=employee_id)

    if department:
        employees = employees.filter(department__icontains=department)

    employee_list = []

    for employee in employees:
        employee_list.append(
            {
                "employee_id": employee.employee_id,
                "name": employee.name,
                "email": employee.email,
                "phone": employee.phone,
                "department": employee.department,
                "designation": employee.designation,
            }
        )

    return {"employees": employee_list}


def _match_choice(model, field, value):
    """
    Map a loosely-typed value onto the exact values actually stored in the
    database for a CharField, so a spelling difference doesn't hide records.

    For example, the robot status may be stored as "Maintainance" while the
    user (or the model) writes "Maintenance". Plain icontains would find
    nothing, so we first try exact, then substring, then fuzzy matching.
    """
    value = (value or "").strip()

    if not value:
        return ""

    actual = [
        v for v in model.objects.values_list(field, flat=True).distinct() if v
    ]

    if not actual:
        return value

    value_lower = value.lower()

    # 1) Exact, case-insensitive.
    for candidate in actual:
        if candidate.lower() == value_lower:
            return candidate

    # 2) Either string contains the other.
    for candidate in actual:
        if value_lower in candidate.lower() or candidate.lower() in value_lower:
            return candidate

    # 3) Fuzzy match, to survive typos like "Maintainance" vs "Maintenance".
    matches = difflib.get_close_matches(
        value_lower,
        [candidate.lower() for candidate in actual],
        n=1,
        cutoff=0.6,
    )
    if matches:
        for candidate in actual:
            if candidate.lower() == matches[0]:
                return candidate

    return value


def get_robot_data(
    robot_id="", employee_name="", status="", battery_max=-1, battery_min=-1
):
    """
    Get robot information from the CRM database.
    This is a read-only function.
    """

    robots = Robot.objects.select_related("employee").all()

    if robot_id:
        robots = robots.filter(robot_id__icontains=robot_id)

    if employee_name:
        robots = robots.filter(
            Q(employee__name__icontains=employee_name)
            | Q(employee__employee_id__icontains=employee_name)
        )

    if status:
        status = _match_choice(Robot, "status", status)
        robots = robots.filter(status__icontains=status)

    if battery_max is not None and battery_max >= 0:
        robots = robots.filter(battery_percentage__lte=battery_max)

    if battery_min is not None and battery_min >= 0:
        robots = robots.filter(battery_percentage__gte=battery_min)

    robot_list = []

    for robot in robots:
        robot_list.append(
            {
                "robot_id": robot.robot_id,
                "employee_id": robot.employee.employee_id,
                "employee_name": robot.employee.name,
                "battery_percentage": robot.battery_percentage,
                "status": robot.status,
                "created_at": robot.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return {"robots": robot_list}


def get_leave_data(
    employee=None,
    employee_name="",
    status="",
    leave_type="",
    start_date="",
    end_date="",
):
    """
    Get leave applications from the CRM database (hr.models.Leave).
    Read-only.
    """
    records = Leave.objects.select_related("employee").all()

    # Employees can only see their own leave (also enforced by the caller).
    if employee is not None:
        records = records.filter(employee=employee)
    elif employee_name:
        records = records.filter(employee__name__icontains=employee_name)

    if status:
        status = _match_choice(Leave, "status", status)
        records = records.filter(status__icontains=status)

    if leave_type:
        leave_type = _match_choice(Leave, "leave_type", leave_type)
        records = records.filter(leave_type__icontains=leave_type)

    # Optional date range: keep leave that overlaps the window.
    if start_date and end_date:
        try:
            start = timezone.datetime.strptime(start_date, "%Y-%m-%d").date()
            end = timezone.datetime.strptime(end_date, "%Y-%m-%d").date()
            records = records.filter(start_date__lte=end, end_date__gte=start)
        except (ValueError, TypeError):
            pass

    leave_records = []
    by_status = {}
    by_type = {}

    for leave in records.order_by("-start_date"):
        leave_records.append(
            {
                "employee_name": leave.employee.name,
                "leave_type": leave.leave_type,
                "reason": leave.reason,
                "status": leave.status,
                "start_date": str(leave.start_date),
                "end_date": str(leave.end_date),
                "applied_on": leave.created_at.strftime("%Y-%m-%d"),
            }
        )
        by_status[leave.status] = by_status.get(leave.status, 0) + 1
        by_type[leave.leave_type] = by_type.get(leave.leave_type, 0) + 1

    return {
        "total": len(leave_records),
        "by_status": by_status,
        "by_type": by_type,
        "leave_records": leave_records,
    }


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------
employee_tool = {
    "type": "function",
    "function": {
        "name": "get_employee_data",
        "description": (
            "Get employee information from the CRM database. "
            "Use this when the user asks about employees, "
            "employee names, employee details, departments, "
            "designations, emails or phone numbers. "
            "Use an empty string for a filter that is not needed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "employee_name": {
                    "type": "string",
                    "description": (
                        "Employee name to search for. "
                        "You may also pass an employee ID here "
                        "(for example emp01). "
                        "Use an empty string when no employee is specified."
                    ),
                },
                "employee_id": {
                    "type": "string",
                    "description": (
                        "Employee ID to search for, such as emp01. "
                        "Use this whenever the user refers to an employee "
                        "by their ID. Use an empty string when not specified."
                    ),
                },
                "department": {
                    "type": "string",
                    "description": (
                        "Department to search for. "
                        "Use an empty string when no department "
                        "is specified."
                    ),
                },
            },
            "required": ["employee_name", "employee_id", "department"],
        },
    },
}

robot_tool = {
    "type": "function",
    "function": {
        "name": "get_robot_data",
        "description": (
            "Get robot information from the CRM database. "
            "Use this when the user asks about robots, "
            "robot IDs, robot owners, battery percentage, "
            "robot status, or when a robot was created. "
            "Use an empty string for a filter that is not needed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "robot_id": {
                    "type": "string",
                    "description": (
                        "Robot ID to search for. "
                        "Use an empty string when not specified."
                    ),
                },
                "employee_name": {
                    "type": "string",
                    "description": (
                        "Employee name who owns the robot. "
                        "Use an empty string when not specified."
                    ),
                },
                "status": {
                    "type": "string",
                    "description": (
                        "Robot status such as Active or Maintenance. "
                        "Use an empty string when not specified."
                    ),
                },
                "battery_max": {
                    "type": "integer",
                    "description": (
                        "Maximum battery percentage to filter robots. "
                        "If the user asks for robots below a percentage, "
                        "use that percentage. "
                        "If the user does not ask for a battery filter, "
                        "use -1."
                    ),
                },
                "battery_min": {
                    "type": "integer",
                    "description": (
                        "Minimum battery percentage to filter robots. "
                        "For example, use 50 when the user asks "
                        "for robots with 50% or above battery. "
                        "If there is no minimum battery filter, use -1."
                    ),
                },
            },
            "required": [
                "robot_id",
                "employee_name",
                "status",
                "battery_max",
                "battery_min",
            ],
        },
    },
}

# NOTE: employee_name must live INSIDE "properties" or the model can never use it.
attendance_tool = {
    "type": "function",
    "function": {
        "name": "get_attendance",
        "description": (
            "Get attendance records from the CRM database for a specific "
            "date or date range. Use this when the user asks who was "
            "present, absent or on leave, or about a particular "
            "employee's attendance."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": (
                        "Start date in YYYY-MM-DD format. "
                        "Leave empty to use today."
                    ),
                },
                "end_date": {
                    "type": "string",
                    "description": (
                        "End date in YYYY-MM-DD format. "
                        "Leave empty to use the start date."
                    ),
                },
                "employee_name": {
                    "type": "string",
                    "description": (
                        "The employee name mentioned in the question. "
                        "Use an empty string if no employee is specified."
                    ),
                },
            },
            "required": [],
        },
    },
}

leave_tool = {
    "type": "function",
    "function": {
        "name": "get_leave_data",
        "description": (
            "Get leave applications from the CRM database. "
            "Use this when the user asks about leave, leave applications, "
            "how many people are on leave, approved/rejected/pending leave, "
            "or the reason for a leave request. "
            "No date range is required - call it with empty strings to get "
            "a total count or a full list. "
            "Use an empty string for any filter that is not needed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": (
                        "Leave status: Approved, Rejected or Pending. "
                        "Use an empty string when not specified."
                    ),
                },
                "leave_type": {
                    "type": "string",
                    "description": (
                        "Leave type: Casual, Sick, Annual or Other. "
                        "Use an empty string when not specified."
                    ),
                },
                "employee_name": {
                    "type": "string",
                    "description": (
                        "Employee name to search for. "
                        "Use an empty string when not specified."
                    ),
                },
                "start_date": {
                    "type": "string",
                    "description": (
                        "Optional start date in YYYY-MM-DD format. "
                        "Use an empty string when no date range is given."
                    ),
                },
                "end_date": {
                    "type": "string",
                    "description": (
                        "Optional end date in YYYY-MM-DD format. "
                        "Use an empty string when no date range is given."
                    ),
                },
            },
            "required": [
                "status",
                "leave_type",
                "employee_name",
                "start_date",
                "end_date",
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# Chatbot core
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are the CRM AI Assistant. "
    "Use the provided tools whenever the user asks for CRM data "
    "(employees, robots, attendance, or leave applications). "
    "Answer ONLY using the data returned by the tools. "
    "Never invent, guess, or assume CRM data. "
    "If a tool returns no records, say so plainly. "
    "When you list several names or items in one line, separate them "
    "with commas (for example: 'kumar shankar, rahul george, gil nasnin'). "
    "Never run names together without a comma between them. "
    "If the user asks for a count or total (for example 'how many leave "
    "applications'), call the relevant tool and give the number directly. "
    "Do NOT ask for a date range unless the tool genuinely requires one. "
    "For any question that is not about CRM data, just answer it normally. "
    "You must always give the user a useful answer and never reply with "
    "nothing. If a lookup comes back empty, say what you searched for and "
    "what you can look up instead."
)


def _resolve_employee_name(prompt, provided_name=""):
    """Fall back to scanning the prompt for a known employee name."""
    if provided_name and provided_name.strip():
        return provided_name.strip()

    prompt_lower = prompt.lower()
    for emp in Employee.objects.all():
        if emp.name.lower() in prompt_lower:
            return emp.name
        if emp.employee_id.lower() in prompt_lower:
            return emp.employee_id

    return ""


def _dispatch_tool_call(user, tool_call, prompt):
    """Run one tool call and return its result as a plain dict."""
    function_name = tool_call.function.name

    try:
        function_args = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        function_args = {}

    if function_name == "get_employee_data":
        return get_employee_data(
            user=user,
            employee_name=function_args.get("employee_name", ""),
            department=function_args.get("department", ""),
            employee_id=function_args.get("employee_id", ""),
        )

    if function_name == "get_robot_data":
        return get_robot_data(
            robot_id=function_args.get("robot_id", ""),
            employee_name=function_args.get("employee_name", ""),
            status=function_args.get("status", ""),
            battery_max=function_args.get("battery_max", -1),
            battery_min=function_args.get("battery_min", -1),
        )

    if function_name == "get_leave_data":
        employee_filter = None

        # Employees can only see their own leave applications
        if is_employee(user) and not is_hr(user) and not is_admin(user):
            employee_filter = Employee.objects.filter(user=user).first()

            if employee_filter is None:
                return {"error": "Employee profile not found."}

            # Lock the lookup to the logged-in employee's own records.
            return get_leave_data(
                employee=employee_filter,
                status=function_args.get("status", ""),
                leave_type=function_args.get("leave_type", ""),
                start_date=function_args.get("start_date", ""),
                end_date=function_args.get("end_date", ""),
            )

        employee_name = _resolve_employee_name(
            prompt, function_args.get("employee_name", "")
        )

        return get_leave_data(
            employee_name=employee_name,
            status=function_args.get("status", ""),
            leave_type=function_args.get("leave_type", ""),
            start_date=function_args.get("start_date", ""),
            end_date=function_args.get("end_date", ""),
        )

    if function_name == "get_attendance":
        employee_filter = None

        # Employees can only access their own attendance
        if is_employee(user) and not is_hr(user) and not is_admin(user):
            employee_filter = Employee.objects.filter(user=user).first()

            if employee_filter is None:
                return {"error": "Employee profile not found."}

        employee_name = _resolve_employee_name(
            prompt, function_args.get("employee_name", "")
        )

        return get_attendance(
            start_date=function_args.get("start_date"),
            end_date=function_args.get("end_date"),
            employee=employee_filter,
            employee_name=employee_name,
        )

    return {"error": f"Unknown tool: {function_name}"}


def _execute_tool_call(user, tool_call, prompt):
    """Wrap tool dispatch so a single bad call can never break the chat."""
    try:
        return _dispatch_tool_call(user, tool_call, prompt)
    except Exception as exc:
        return {
            "error": (
                "The tool '"
                + tool_call.function.name
                + "' could not run: "
                + str(exc)
                + ". Answer using whatever information you already have."
            )
        }


def run_crm_chatbot(user, prompt):
    """
    Full tool-calling loop: let the model ask for CRM data, run every tool
    it requests, feed the results back, and let the model write the final
    answer. This is what lets the bot answer ANY question, not just the
    handful of hard-coded cases.
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    tools = [attendance_tool, employee_tool, robot_tool, leave_tool]

    for _ in range(6):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
        except Exception as exc:
            return (
                "Sorry, I could not reach the assistant just now ("
                + str(exc)
                + "). Please try again."
            )

        message = response.choices[0].message

        # No tool needed -> the model already answered.
        if not message.tool_calls:
            if message.content and message.content.strip():
                return message.content
            break

        # Record the assistant's tool request(s).
        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in message.tool_calls
                ],
            }
        )

        # Run EVERY requested tool (not just the last one).
        for tool_call in message.tool_calls:
            result = _execute_tool_call(user, tool_call, prompt)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": json.dumps(result, default=str),
                }
            )

    # The model kept calling tools, or produced nothing. Ask once more for a
    # plain final answer with tools disabled, so the user always gets a reply.
    try:
        final = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="none",
        )
        content = final.choices[0].message.content
        if content and content.strip():
            return content
    except Exception:
        pass

    return "Sorry, I could not complete that request. Please try rephrasing it."


# ---------------------------------------------------------------------------
# Chatbot views
# ---------------------------------------------------------------------------
@login_required
def chatbot(request):
    answer = None

    if request.method == "POST":
        prompt = request.POST.get("prompt", "").strip()

        if prompt:
            try:
                answer = run_crm_chatbot(request.user, prompt)
            except Exception as exc:  # keep the page usable on any failure
                answer = f"Sorry, something went wrong: {exc}"

    return render(
        request,
        "employees/chatbot.html",
        {
            "answer": answer,
        },
    )


@login_required
def chatbot_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=405)

    prompt = request.POST.get("prompt", "").strip()

    if not prompt:
        return JsonResponse({"error": "Please enter a question."}, status=400)

    try:
        answer = run_crm_chatbot(request.user, prompt)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)

    return JsonResponse({"answer": answer})


# ---------------------------------------------------------------------------
# Auth / dashboard views
# ---------------------------------------------------------------------------
def home(request):
    if request.user.is_authenticated:
        response = redirect_for_role(request.user)
        if response:
            return response
        logout(request)

    return redirect("login")


def redirect_for_role(user):
    """Send each authenticated account to its role's dashboard."""
    if is_admin(user):
        return redirect("dashboard")
    if is_hr(user):
        return redirect("hr_dashboard")
    if is_employee(user):
        return redirect("employee_dashboard")
    return None


def login_view(request):
    if request.user.is_authenticated:
        response = redirect_for_role(request.user)
        if response:
            return response
        logout(request)

    if request.method == "POST":
        username = request.POST.get("user_id", "").strip()
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            response = redirect_for_role(user)
            if response is None:
                return render(request, "employees/login.html", {
                    "error": "This account does not have an assigned role."
                })
            login(request, user)
            return response

        return render(
            request,
            "employees/login.html",
            {"error": "Invalid user ID or password."},
        )

    return render(request, "employees/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def password_change_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect("password_change_done")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "employees/password_change.html", {"form": form})


@login_required
def password_change_done(request):
    return render(request, "employees/password_change_done.html")


@login_required
@user_passes_test(is_admin)
def dashboard(request):
    employees = Employee.objects.all()
    robots = Robot.objects.select_related("employee").all()

    context = {
        "employees": employees,
        "robots": robots,
        "employee_count": employees.count(),
        "robot_count": robots.count(),
    }

    return render(request, "employees/dashboard.html", context)


@login_required
@user_passes_test(is_admin)
def add_employee(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST)

        if form.is_valid():
            password = form.cleaned_data.get("password")

            if not password:
                form.add_error("password", "Password is required.")

            else:
                employee = form.save(commit=False)

                # Create Django User account
                user = User.objects.create_user(
                    username=employee.employee_id,
                    email=employee.email,
                    password=password,
                )

                # Add user to Employee group
                employee_group = Group.objects.get(name="Employee")
                user.groups.add(employee_group)

                # Connect User with Employee
                employee.user = user
                employee.save()

                return redirect("dashboard")

    else:
        form = EmployeeForm()

    return render(request, "employees/add_employee.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def edit_robot(request, robot_id):
    robot = get_object_or_404(Robot, id=robot_id)

    if request.method == "POST":
        form = RobotAdminForm(request.POST, instance=robot)

        if form.is_valid():
            form.save()
            return redirect("dashboard")

    else:
        form = RobotAdminForm(instance=robot)

    return render(
        request,
        "employees/edit_robot.html",
        {
            "form": form,
            "robot": robot,
        },
    )


def edit_employee(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)

    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)

        if form.is_valid():
            password = form.cleaned_data.get("password")

            employee = form.save(commit=False)

            # Update linked User account
            if employee.user:
                employee.user.email = employee.email

                # Change password only if a new password was entered
                if password:
                    employee.user.set_password(password)

                employee.user.save()
            else:
                if not password:
                    form.add_error(
                        "password",
                        "password is required for an employee without a login account.",
                    )
                    return render(
                        request,
                        "employees/edit_employee.html",
                        {
                            "form": form,
                            "employee": employee,
                        },
                    )

                user = User.objects.create_user(
                    username=employee.employee_id,
                    email=employee.email,
                    password=password,
                )
                employee_group = Group.objects.get(name="Employee")
                user.groups.add(employee_group)
                employee.user = user

            employee.save()

            return redirect("dashboard")

    else:
        form = EmployeeForm(instance=employee)

    return render(
        request,
        "employees/edit_employee.html",
        {
            "form": form,
            "employee": employee,
        },
    )


@login_required
@user_passes_test(is_employee)
def employee_dashboard(request):
    employee = get_object_or_404(Employee, user=request.user)

    robots = Robot.objects.filter(employee=employee)

    context = {
        "employee": employee,
        "robots": robots,
    }
    return render(request, "employees/employee_dashboard.html", context)


@login_required
@user_passes_test(is_employee)
def create_robot(request):
    employee = get_object_or_404(Employee, user=request.user)

    if request.method == "POST":
        form = RobotForm(request.POST)

        if form.is_valid():
            robot = form.save(commit=False)
            robot.employee = employee
            robot.save()

            return redirect("employee_dashboard")

    else:
        form = RobotForm()

    return render(request, "employees/create_robot.html", {"form": form})


@login_required
@user_passes_test(is_employee)
def employee_create_leave(request):
    employee = get_object_or_404(Employee, user=request.user)

    if request.method == "POST":
        form = EmployeeLeaveForm(request.POST)

        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = employee
            leave.save()

            return redirect("employee_dashboard")
    else:
        form = EmployeeLeaveForm()

    return render(request, "employees/create_leave.html", {"form": form})


@login_required
@user_passes_test(is_employee)
def employee_attendance(request):
    employee = get_object_or_404(Employee, user=request.user)

    attendance_records = Attendance.objects.filter(employee=employee).order_by(
        "-date"
    )

    return render(
        request,
        "employees/employee_attendance.html",
        {
            "attendance_records": attendance_records,
        },
    )


@login_required
@user_passes_test(is_employee)
def employee_mark_attendance(request):
    employee = get_object_or_404(Employee, user=request.user)

    if request.method == "POST":
        form = EmployeeAttendanceForm(request.POST)

        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.employee = employee
            attendance.save()

            return redirect("employee_attendance")

    else:
        form = EmployeeAttendanceForm()

    return render(request, "employees/employee_mark_attendance.html", {"form": form})
