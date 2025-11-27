"""
URL configuration for jidouka project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home , name="home"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("mc-schedule/", views.mc_schedule_view, name="mc_schedule"),
    path("google/auth/", views.google_auth, name="google_auth"),
    path("google/callback/", views.google_callback, name="google_callback"),
    path("send-to-calendar/", views.send_to_calendar, name="send_to_calendar"),
    path("google/test-create/", views.test_create_event, name="test_create_event"),
    path('employee/<int:employee_id>/up/', views.move_up, name='employee-move-up'),
    path('employee/<int:employee_id>/down/', views.move_down, name='employee-move-down'),
    path('employee/<int:employee_id>/up-gyomu/', views.move_up_gyomu, name='employee-move-up-gyomu'),
    path('employee/<int:employee_id>/down-gyomu/', views.move_down_gyomu, name='employee-move-down-gyomu'),
    path('employee/<int:employee_id>/toggle-active/', views.toggle_active, name='employee-toggle-active'),
    
]
