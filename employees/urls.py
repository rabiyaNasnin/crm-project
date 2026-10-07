from django.urls import path
from .views import home, dashboard, employee_dashboard, create_robot, employee_create_leave, employee_attendance, employee_mark_attendance, company_login, add_employee, edit_employee, edit_robot, dashboard_selection, admin_login, employee_login, hr_login, logout_view


urlpatterns = [
    path("", home, name="home"),
    path("login/", company_login, name="login"),
    path("admin-login/", admin_login, name="admin_login"),
    path("employee-login/", employee_login, name="employee_login"),
    path("hr-login/", hr_login, name="hr_login"),
    path("logout/", logout_view, name="logout"),
    path("dashboard-selection/", dashboard_selection, name="dashboard_selection"),
    path("admin-dashboard/", dashboard, name="dashboard"),
    path("employee/", employee_dashboard, name="employee_dashboard"),#employee dashboard url
    path("employee/leave/", employee_create_leave, name="employee_create_leave"),
    path("employee/create-robot/", create_robot, name="create_robot"),
    path("employee/attendance/",employee_attendance, name="employee_attendance"),
    path("employee/mark-attendance/", employee_mark_attendance, name="employee_mark_attendance"),
    path("add-employee/", add_employee, name="add_employee"),
    path("edit-employee/<int:employee_id>/", edit_employee, name="edit_employee"),
    path("employee/edit-robot/<int:robot_id>/", edit_robot, name="edit_robot"),
]
