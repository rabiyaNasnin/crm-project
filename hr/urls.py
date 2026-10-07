from django.urls import path
from .views import hr_dashboard, mark_attendance, create_leave, update_leave_status, edit_attendance, edit_leave


urlpatterns = [
    path("", hr_dashboard, name="hr_dashboard"),
    path("attendance/", mark_attendance, name="mark_attendance"),
    path("leave/", create_leave, name="create_leave"),
    path("leave/<int:leave_id>/update_status/",update_leave_status, name="update_leave_status"),
    path("edit_attendance/<int:attendance_id>/", edit_attendance, name="edit_attendance"),
    path("edit-leave/<int:leave_id>/", edit_leave, name="edit_leave"),
  
]
