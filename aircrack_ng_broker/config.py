from django.conf import settings
import os

MODULE_NAME="aircrack_ng_wifi_scan"
AIRCRACK_REL_SCAN_DIR="aircrack_ng_broker/scan_results/tmp"
AIRCRACK_SCAN_RESULTS_PATH=os.path.join(settings.BASE_DIR, AIRCRACK_REL_SCAN_DIR)

# Parsing scan output
STATION_HEADERS_STRING='Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs'
