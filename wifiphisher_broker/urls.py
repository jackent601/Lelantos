from django.urls import path
from wifiphisher_broker.wifiphisher_config import WIFIPHISHER_LOG_DIR_PATH
import os

from . import views

urlpatterns = [
    path("captive_portal_home/", views.wifiphisher_captive_portal_home, name="captive_portal_home"),
]

# Initialisation (urls imported once)

# Make log dir if not present
if not os.path.isdir(WIFIPHISHER_LOG_DIR_PATH):
    # TODO - logger
    print(f'Creating temp directory at {WIFIPHISHER_LOG_DIR_PATH} for scan result files')
    os.makedirs(WIFIPHISHER_LOG_DIR_PATH)
else:
    print(f'Saving temp wifiphisher logs to {WIFIPHISHER_LOG_DIR_PATH}')