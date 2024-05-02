from django.urls import path
import os
from aircrack_ng_broker.config import AIRCRACK_SCAN_RESULTS_PATH

from . import views

urlpatterns = [
    path("ng_wifi_scan_home/", views.ng_wifi_scan_home, name="ng_wifi_scan_home"),
    path("ng_wifi_run_scan/", views.ng_wifi_run_scan, name="ng_wifi_run_scan"),
    path("ng_wifi_previous_scans/", views.ng_wifi_previous_scans, name="ng_wifi_previous_scans"),
    path("ng_wifi_show_scan_results/", views.ng_wifi_show_scan_results, name="ng_wifi_show_scan_results"),
]


# Initialisation (urls imported once)

# Make dir if not present
if not os.path.isdir(AIRCRACK_SCAN_RESULTS_PATH):
    os.makedirs(AIRCRACK_SCAN_RESULTS_PATH)