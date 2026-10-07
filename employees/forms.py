from django import forms
from .models import Employee, Robot

class RobotForm(forms.ModelForm):
    class Meta:
        model = Robot
        fields = ["robot_id", "battery_percentage", "status",]

    status = forms.ChoiceField(
        choices = [
            ("Active", "Active"),
            ("Maintenance", "Maintenance"),
            ("Offline", "Offline"),
        ]
    )
class RobotAdminForm(forms.ModelForm):
    class Meta:
        model = Robot
        fields = ["battery_percentage", "status"]

    status = forms.ChoiceField(
        choices =[
            ("Active","Active"),
            ("Maintainance", "Maintainance"),
            ("Offline", "Offline")
        ]
    )

class EmployeeForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter new password (optional)"
            }
        )
    )
    class Meta:
        model = Employee
        fields = [
            "employee_id",
            "name",
            "email",
            "phone",
            "department",
            "designation",
        ]

        widgets = {
            "employee_id": forms.TextInput(attrs={
                "placeholder": "Enter Employee ID"
            }),
            "name": forms.TextInput(attrs={
                "placeholder": "Enter Employee Name"
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Enter Email"
            }),
            "phone": forms.TextInput(attrs={
                "placeholder": "Enter Phone Number"
            }),
            "department": forms.TextInput(attrs={
                "placeholder": "Enter Department"
            }),
            "designation": forms.TextInput(attrs={
                "placeholder": "Enter Designation"
            }),
        }
