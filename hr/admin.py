from django.contrib import admin
from .models import Attendance

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'date',
        'status',
        'created_at',
    )

    list_filter = (
        'status',
        'date',
    )

    search_fields = (
        'employee__employee_id',
        'employee__name',
    )

# Register your models here.
