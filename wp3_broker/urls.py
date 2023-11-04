from django.urls import path

from . import views

urlpatterns = [
    path("wp3_server_health/", views.check_wp3_api_running, name="wp3_server_health"),
]