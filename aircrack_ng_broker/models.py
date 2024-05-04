from django.db import models
from lelantos_base.models import Module_Session, Model_Result_Instance
import aircrack_ng_broker.config as cfg

# Track wifi scanning session
class Wifi_Scan(Module_Session):
    module_name=cfg.MODULE_NAME
    duration_s = models.PositiveIntegerField()
    interface = models.CharField(max_length=200)
    monitor_interface = models.CharField(max_length=200, null=True)
    filePathPattern = models.CharField(max_length=200, null=True)

# Beacon results from scans
# Inherits from Model_Result_Instance to plot results
class Wifi_Scan_Beacon_Result(Model_Result_Instance):
    module_session_captured=models.ForeignKey(Module_Session, on_delete=models.CASCADE)
    bssid=models.CharField(max_length=200)
    first_time_seen=models.CharField(max_length=200, null=True)
    last_time_seen=models.CharField(max_length=200, null=True)
    channel=models.IntegerField(null=True)
    speed=models.IntegerField(null=True)
    privacy=models.CharField(max_length=200, null=True)
    cipher=models.CharField(max_length=200, null=True)
    authentication=models.CharField(max_length=200, null=True)
    power=models.IntegerField(null=True)
    num_beacons=models.IntegerField(null=True)
    num_iv=models.IntegerField(null=True)
    lan_ip=models.CharField(max_length=200, null=True)
    id_len=models.IntegerField(null=True)
    essid=models.CharField(max_length=200)
    key=models.CharField(max_length=200, null=True)
    uniqueIdentifiers=('bssid', 'essid')
    
    
class Wifi_Scan_Station_Result(Model_Result_Instance):
    module_session_captured = models.ForeignKey(Module_Session, on_delete=models.CASCADE)
    station_mac=models.CharField(max_length=200)
    first_time_seen=models.CharField(max_length=200, null=True)
    last_time_seen=models.CharField(max_length=200, null=True)
    power=models.IntegerField(null=True)
    num_packets=models.IntegerField(null=True)
    bssid=models.CharField(max_length=200, null=True)
    probed_essids=models.CharField(max_length=200)
    uniqueIdentifiers=('station_mac', 'probed_essids')
        
