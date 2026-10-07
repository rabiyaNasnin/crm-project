from django.db import models
from employees.models import Employee

class Attendance(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="attendance_records"
    )


    date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('Present', 'Present'),
            ('Absent', 'Absent'),
            ('Leave', 'Leave'),
        
        ]    
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.name} - {self.date} - {self.status}"

class Leave(models.Model):
    LEAVE_TYPES = [
            ('Casual', 'Casual Leave'),
            ('Sick', 'Sick Leave'),
            ('Annual', 'Annual Leave'),
            ('Other', 'Other'),
        ]
    STATUS_CHOICES = [
            ('Pending', 'Pending'),
            ('Approved', 'Approved'),
            ('Rejected', 'Rejected'),
        ]
    employee = models.ForeignKey(
            Employee,
            on_delete=models.PROTECT,
            related_name="leave_requests"
        )
    leave_type = models.CharField(
            max_length=20,
            choices=LEAVE_TYPES
        )

    start_date = models.DateField()
    end_date = models.DateField()

    reason = models.TextField(blank=True)

    status = models.CharField(
            max_length=20,
            choices=STATUS_CHOICES,
            default='Pending'
        )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
            return f"{self.employee.name} - {self.leave_type}"
            
