from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q

from employees.models import Employee
from .models import Attendance, Leave
from .forms import AttendanceForm, LeaveForm


def is_hr(user):
    return user.groups.filter(name="HR").exists()

@login_required
@user_passes_test(is_hr)
def hr_dashboard(request):

    employees = Employee.objects.all()
    attendance_records = Attendance.objects.select_related(
        "employee"
    ).all()
    leave_requests = Leave.objects.select_related(
        "employee",
    ).all()
    attendance_summary = employees.annotate(
        present_count=Count(
           "attendance_records",
            filter=Q(attendance_records__status="Present"),
            distinct=True
        ),
        absent_count=Count(
           "attendance_records",
            filter=Q(attendance_records__status="Absent"),
            distinct=True
        ),
        leave_count=Count(
           "leave_requests",
            distinct=True
        ),
    )
    context = {
        "employees": employees,
        "attendance_records": attendance_records,
        "attendance_summary": attendance_summary,
        "leave_requests": leave_requests,
        "employee_count": employees.count(),
        "attendance_count": attendance_records.count(),
        "leave_count": leave_requests.count(),
    }
    return render(
        request,
        "hr/hr_dashboard.html",
        context
    )
@login_required
@user_passes_test(is_hr)
def mark_attendance(request):

    if request.method == "POST":
        form = AttendanceForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("hr_dashboard")

    else:
        form = AttendanceForm()

    return render(
        request,
        "hr/mark_attendance.html",
        {"form": form}
    )


@login_required
@user_passes_test(is_hr)
def edit_attendance(request, attendance_id):

    attendance = get_object_or_404(
        Attendance,
        id=attendance_id
    )

    if request.method == "POST":
        form = AttendanceForm(
            request.POST,
            instance=attendance
        )

        if form.is_valid():
            form.save()
            return redirect("hr_dashboard")

    else:
        form = AttendanceForm(instance=attendance)

    return render(
        request,
        "hr/edit_attendance.html",
        {
            "form": form,
            "attendance": attendance
        }
    )

@login_required
def create_leave(request):

    if request.method == "POST":
        form = LeaveForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("hr_dashboard")

    else:
        form = LeaveForm()

    return render(
        request,
        "hr/create_leave.html",
        {"form": form}
    )

@login_required
@user_passes_test(is_hr)
def update_leave_status(request, leave_id):

    leave = get_object_or_404(
        Leave,
        id=leave_id
    )

    if request.method == "POST":
        new_status = request.POST.get("status")

        if new_status in ["Approved", "Rejected"]:
            leave.status = new_status
            leave.save()

    return redirect("hr_dashboard")

@login_required
@user_passes_test(is_hr)
def edit_leave(request, leave_id):

    leave = get_object_or_404(
        Leave,
        id=leave_id
    )

    if request.method == "POST":
        form = LeaveForm(
            request.POST,
            instance=leave
        )

        if form.is_valid():
            form.save()
            return redirect("hr_dashboard")

    else:
        form = LeaveForm(instance=leave)

    return render(
        request,
        "hr/edit_leave.html",
        {
            "form": form,
            "leave": leave
        }
    )