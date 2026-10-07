from django.contrib import admin
from .models import Employee, Robot

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        'employee_id',
        'name',
        'email',
        'phone',
        'department',
        'designation',
    )

    search_fields = (
        'employee_id',
        'name',
        'email',

    )

@admin.register(Robot)
class RobotAdmin(admin.ModelAdmin):
        list_display = (
            'robot_id',
            'employee',
            'battery_percentage',
            'status',
            'created_at',
        )

        search_fields = (
            'robot_id',
            'employee__employee_id',
            'employee__name',
        )

        list_filter = (
            'battery_percentage',
            'employee',
        )


# Register your models here.
