from django.conf import settings
import os

PHISHING_SCENARIOS={"firmware-upgrade":"firmware-upgrade",
                    "oauth-login":"oauth-login",
                    "plugin_update":"plugin_update",
                    "wifi_connect":"wifi_connect"}

WIFIPHISHER_LOG_REL_DIR="wifiphisher_broker/logs/tmp"

WIFIPHISHER_LOG_DIR=os.path.join(settings.BASE_DIR, WIFIPHISHER_LOG_REL_DIR)

SAVE_LOGS=True

MONITOR_UPDATE_RATE=3