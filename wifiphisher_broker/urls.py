from django.urls import path
from wifiphisher_broker.config import WIFIPHISHER_LOG_DIR
import os

from . import views

urlpatterns = [
    path("captive_portal_home/", views.wifiphisher_captive_portal_home, name="captive_portal_home"),
     path("captive_portal_launch/", views.wifiphisher_captive_portal_launch, name="captive_portal_launch"),
     path("captive_portal_monitor/", views.wifiphisher_captive_portal_monitor, name="captive_portal_monitor"),
     path("captive_portal_stop/", views.wifiphisher_captive_portal_stop, name="captive_portal_stop"),
     path("captive_portal_previous_captures/", views.wifiphisher_captive_portal_previous_captures, name="captive_portal_previous_captures"),
     path("captive_portal_results/", views.wifiphisher_captive_portal_results, name="captive_portal_results"),
]

# Initialisation (urls imported once)

# Make log dir if not present
if not os.path.isdir(WIFIPHISHER_LOG_DIR):
    # TODO - logger
    print(f'Creating temp directory at {WIFIPHISHER_LOG_DIR} for scan result files')
    os.makedirs(WIFIPHISHER_LOG_DIR)
else:
    print(f'Saving temp wifiphisher logs to {WIFIPHISHER_LOG_DIR}')