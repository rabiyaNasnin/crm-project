import os
from django.contrib.auth.models import User,Group
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.serializers import python
from django.shortcuts import render, get_object_or_404, redirect
from .models import Employee,Robot
from .forms import RobotForm,RobotAdminForm, EmployeeForm
from hr.forms import EmployeeLeaveForm, EmployeeAttendanceForm
from hr.models import Attendance

def home(request):

    if request.user.is_authenticated:

        if request.user.is_superuser or request.user.groups.filter(name="Admin").exists():
            return redirect("dashboard")

        elif request.user.groups.filter(name="HR").exists():
            return redirect("hr_dashboard")

        elif request.user.groups.filter(name="Employee").exists():
            return redirect("employee_dashboard")

    return redirect("login")

def company_login(request):
    if request.method == "POST":
        company_id = request.POST.get("company_id", "")
        company_password = request.POST.get("password", "")

        expected_id = os.environ.get("COMPANY_LOGIN_ID")
        expected_password = os.environ.get("COMPANY_LOGIN_PASSWORD")

        if (
            company_id == expected_id
            and company_password == expected_password
        ):
            request.session["company_access"] = True
            return redirect("dashboard_selection")

        return render(
            request,
            "employees/company_login.html",
            {
                "error": "Invalid company ID or password."
            }
        )

    return render(
        request,
        "employees/company_login.html"
    )
def admin_login(request):
    if not request.session.get("company_access"):
        return redirect("login")

    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            if (
                user.is_superuser
                or user.groups.filter(name="Admin").exists()
            ):
                login(request, user)
                request.session.pop("company_access", None)
                return redirect("dashboard")

            error = "This account is not authorized for the Admin Dashboard."
        else:
            error = "Invalid username or password."

    return render(
        request,
        "employees/admin_login.html",
        {"error": error}
    )

def employee_login(request):
    if not request.session.get("company_access"):
        return redirect("login")

    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            if user.groups.filter(name="Employee").exists():
                login(request, user)
                request.session.pop("company_access", None)
                return redirect("employee_dashboard")

            error = "This account is not authorized for the Employee Dashboard."
        else:
            error = "Invalid username or password."

    return render(
        request,
        "employees/employee_login.html",
        {"error": error}
    )


def hr_login(request):
    if not request.session.get("company_access"):
        return redirect("login")

    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            if user.groups.filter(name="HR").exists():
                login(request, user)
                request.session.pop("company_access", None)
                return redirect("hr_dashboard")

            error = "This account is not authorized for the HR Dashboard."
        else:
            error = "Invalid username or password."

    return render(
        request,
        "employees/hr_login.html",
        {"error": error}
    )

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)

            return redirect("dashboard_selection")
        
        else:
            return render(
                request,
                "employees/login.html",
                {"error": "Invalid username or password"}
            )

    return render(
        request,
        "employees/login.html"
    )
def logout_view(request):
    logout(request)

    request.session["company_access"] = True

    return redirect("dashboard_selection")

def dashboard_selection(request):
    if not request.session.get("company_access"):
        return redirect("login")

    return render(
        request,
        "employees/dashboard_selection.html"
    )


def is_admin(user):
    return user.is_superuser or user.groups.filter(name="Admin").exists()
def is_hr(user):
    return user.groups.filter(name="HR").exists()
def is_employee(user):
    return user.groups.filter(name="Employee").exists()


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

    return render(
        request,
        "employees/dashboard.html",
        context
    )
@login_required
@user_passes_test(is_admin)
def add_employee(request):

    if request.method == "POST":

        form = EmployeeForm(request.POST)

        if form.is_valid():

            password = form.cleaned_data.get("password")

            if not password:
                form.add_error(
                    "password",
                    "Password is required."
                )

            else:
                employee = form.save(commit=False)

                # Create Django User account
                user = User.objects.create_user(
                    username=employee.employee_id,
                    email=employee.email,
                    password=password
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

    return render(
        request,
        "employees/add_employee.html",
        {"form": form}
    )

@login_required
@user_passes_test(is_admin)
def edit_robot(request, robot_id):

    robot = get_object_or_404(
        Robot,
        id=robot_id
    )

    if request.method == "POST":

        form = RobotAdminForm(
            request.POST,
            instance=robot
        )

        if form.is_valid():

            form.save()

            return redirect("dashboard")

    else:

        form = RobotAdminForm(
            instance=robot
        )

    return render(
        request,
        "employees/edit_robot.html",
        {
            "form": form,
            "robot": robot
        }
    )
def edit_employee(request, employee_id):

    employee = get_object_or_404(
        Employee,
        id=employee_id
    )

    if request.method == "POST":

        form = EmployeeForm(
            request.POST,
            instance=employee
        )

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
                        "password is required for an employee without a login account."
                    )
                    return render(
                        request,
                        "employees/edit_employee.html",
                        {
                            "form": form,
                            "employee": employee
                        }
                    )
                user = User.objects.create_user(
                    username=employee.employee_id,
                    email=employee.email,
                    password=password
                )
                employee_group = Group.objects.get(name="Employee")
                user.groups.add(employee_group)
                employee.user = user

            employee.save()

            return redirect("dashboard")

    else:

        form = EmployeeForm(
            instance=employee
        )

    return render(
        request,
        "employees/edit_employee.html",
        {
            "form": form,
            "employee": employee
        }
    )

@login_required
@user_passes_test(is_employee)
def employee_dashboard(request):
    print("LOGGED-IN USER:", request.user, "ID:", request.user.id)

    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    robots = Robot.objects.filter(
        employee=employee
    )

    context = {
        "employee": employee,
        "robots": robots,
    }
    return render(
        request,
        "employees/employee_dashboard.html",
        context
    )

@login_required
@user_passes_test(is_employee)
def create_robot(request):
    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    if request.method == "POST":
        form = RobotForm(request.POST)

        if form.is_valid():
            robot = form.save(commit=False)
            robot.employee = employee
            robot.save()

            return redirect("employee_dashboard")

    else:
        form = RobotForm()

    return render(
        request,
        "employees/create_robot.html",
        {"form": form}
    )  
@login_required
@user_passes_test(is_employee)
def employee_create_leave(request):
    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    if request.method == "POST":
        form = EmployeeLeaveForm(request.POST)

        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = employee
            leave.save()

            return redirect("employee_dashboard")
    else:
        form = EmployeeLeaveForm()

    return render(
        request,
        "employees/create_leave.html",
        {"form": form}
    )  

@login_required
@user_passes_test(is_employee)
def employee_attendance(request):
    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    attendance_records = Attendance.objects.filter(
        employee=employee
    ).order_by("-date")

    return render(
        request,
        "employees/employee_attendance.html",
        {"attendance_records": attendance_records,
        }
    )

@login_required
@user_passes_test(is_employee)
def employee_mark_attendance(request):
    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    if request.method == "POST":
        form = EmployeeAttendanceForm(request.POST)

        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.employee = employee
            attendance.save()

            return redirect("employee_attendance")

    else:
        form = EmployeeAttendanceForm()

    return render(
        request,
        "employees/employee_mark_attendance.html",
        {"form": form}
    )