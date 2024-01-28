from django.conf import settings
import os, re

MODULE_NAME="wifiphisher_captive_portal"
ARP_FLUSH_WAIT_TIME=3 # time to wait before flushing arp after session close

DNS_MASQ_PATH="/var/lib/misc/dnsmasq.leases" # this will not change in linux

# Declare scenarios available
FIRMWARE_UPGRADE="firmware-upgrade"
OAUTH_LOGIN="oauth-login"
PLUGIN_UPDATE="plugin_update"
WIFI_CONNECT="wifi_connect"

# Map scenario -> command (currently direct mapping)
PHISHING_SCENARIOS={FIRMWARE_UPGRADE:FIRMWARE_UPGRADE,
                    OAUTH_LOGIN:OAUTH_LOGIN,
                    PLUGIN_UPDATE:PLUGIN_UPDATE,
                    WIFI_CONNECT:WIFI_CONNECT}

# Cred finding
CRED_TYPE_USER="user-credentials"
CRED_USER_REGEX_PATTERN=re.compile(r"POST request from (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) with wfphshr-.+=(.+)&wfphshr-password=(.+)")
CRED_TYPE_WPA_PASSWORD="wifi-password"
CRED_WPA_REGEX_PATTERN=re.compile(r"POST request from (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) with wfphshr-wpa-password=(.+)")

# Maps scenario -> cred type
SCENARIO_CRED_TYPES={FIRMWARE_UPGRADE:CRED_TYPE_WPA_PASSWORD,
                     OAUTH_LOGIN:CRED_TYPE_USER,
                     PLUGIN_UPDATE:"NA",
                     WIFI_CONNECT:CRED_TYPE_WPA_PASSWORD}

WIFIPHISHER_LOG_REL_DIR="wifiphisher_broker/logs/tmp"

WIFIPHISHER_LOG_DIR=os.path.join(settings.BASE_DIR, WIFIPHISHER_LOG_REL_DIR)

SAVE_LOGS=True

MONITOR_UPDATE_RATE=3