from django.urls import path

from . import views

urlpatterns = [
    path("ng_wifi_scan_home/", views.ng_wifi_scan_home, name="ng_wifi_scan_home"),
]