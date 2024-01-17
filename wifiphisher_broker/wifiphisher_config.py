from django.conf import settings
import os

PHISHING_SCENARIOS={"firmware-upgrade":"firmware-upgrade",
                    "oauth-login":"oauth-login",
                    "plugin_update":"plugin_update",
                    "wifi_connect":"wifi_connect"}

WIFIPHISHER_REL_LOG_DIR="wifiphisher_broker/logs/tmp"

WIFIPHISHER_LOG_DIR_PATH=os.path.join(settings.BASE_DIR, WIFIPHISHER_REL_LOG_DIR)