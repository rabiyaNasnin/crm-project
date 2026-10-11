from django.urls import path
from .views import(
       home, dashboard, employee_dashboard, 
       create_robot, employee_create_leave, 
       employee_attendance, employee_mark_attendance, 
       add_employee, edit_employee,
       edit_robot, login_view, logout_view, password_change_view,
       password_change_done,
       chatbot,
       chatbot_api,
)


urlpatterns = [
    path("", home, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("password/change/", password_change_view, name="password_change"),
    path("password/change/done/", password_change_done, name="password_change_done"),
    path("admin-dashboard/", dashboard, name="dashboard"),
    path("employee/", employee_dashboard, name="employee_dashboard"),#employee dashboard url
    path("employee/leave/", employee_create_leave, name="employee_create_leave"),
    path("employee/create-robot/", create_robot, name="create_robot"),
    path("employee/attendance/",employee_attendance, name="employee_attendance"),
    path("employee/mark-attendance/", employee_mark_attendance, name="employee_mark_attendance"),
    path("add-employee/", add_employee, name="add_employee"),
    path("edit-employee/<int:employee_id>/", edit_employee, name="edit_employee"),
    path("employee/edit-robot/<int:robot_id>/", edit_robot, name="edit_robot"),
    path("chatbot/", chatbot, name="chatbot"),
    path("chatbot-api/", chatbot_api, name="chatbot_api"),
]
