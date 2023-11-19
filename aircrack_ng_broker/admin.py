from django.contrib import admin

from .models import Wifi_Scan, Wifi_Scan_Beacon_Result, Wifi_Scan_Station_Result

admin.site.register(Wifi_Scan)
admin.site.register(Wifi_Scan_Beacon_Result)
admin.site.register(Wifi_Scan_Station_Result)
