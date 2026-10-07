from django import forms
from .models import Attendance, Leave

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = [
            "employee",
            "date",
            "status",
        ]
        widgets = {
            "date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }
    def clean(self):
        cleaned_data = super().clean()

        employee = cleaned_data.get("employee")
        date = cleaned_data.get("date")

        if employee and date:
           existing = Attendance.objects.filter(
              employee=employee,
              date=date
            )
        
           if self.instance.pk:
               existing = existing.exclude(pk=self.instance.pk)

           if existing.exists():
               raise forms.ValidationError(
                "Attendance for this employee on this date already exists."
            )
        return cleaned_data
class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = [
            "employee",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
        ]
    widgets = {
        "start_date": forms.DateInput(
            attrs={"type": "date"}
        ),
        "end_date": forms.DateInput(
            attrs={"type": "date"}
        ),
    }

class EmployeeLeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = [
            "leave_type",
            "start_date",
            "end_date",
            "reason",
        ]
        widgets = {
            "start_date": forms.DateInput(
                attrs={"type":"date"}
            ),
            "end_date": forms.DateInput(
                attrs={"type":"date"}
            ),
        }

class EmployeeAttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = [
            "date",
            "status",
        ]

        widgets = {
            "date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }