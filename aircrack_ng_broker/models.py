from django.db import models
from lelantos_base.models import Module_Session, Device_Instance, Model_Result_Instance
import aircrack_ng_broker.config as cfg

# Track wifi scanning session
class Wifi_Scan(Module_Session):
    module_name=cfg.MODULE_NAME
    duration_s = models.PositiveIntegerField()
    interface = models.CharField(max_length=200)

# Beacon results from scans
# Inherits from Model_Result_Instance to plot results
class Wifi_Scan_Beacon_Result(Model_Result_Instance):
    module_session_captured=models.ForeignKey(Module_Session, on_delete=models.CASCADE)
    bssid=models.CharField(max_length=200)
    first_time_seen=models.CharField(max_length=200)
    last_time_seen=models.CharField(max_length=200)
    channel=models.IntegerField()
    speed=models.IntegerField()
    privacy=models.CharField(max_length=200)
    cipher=models.CharField(max_length=200)
    authentication=models.CharField(max_length=200)
    power=models.IntegerField()
    num_beacons=models.IntegerField()
    num_iv=models.IntegerField()
    lan_ip=models.CharField(max_length=200)
    id_len=models.IntegerField()
    essid=models.CharField(max_length=200)
    key=models.CharField(max_length=200)
    uniqueIdentifiers=('bssid', 'essid')
    
    
class Wifi_Scan_Station_Result(Model_Result_Instance):
    module_session_captured = models.ForeignKey(Module_Session, on_delete=models.CASCADE)
    station_mac=models.CharField(max_length=200)
    first_time_seen=models.CharField(max_length=200)
    last_time_seen=models.CharField(max_length=200)
    power=models.IntegerField()
    num_packets=models.IntegerField()
    bssid=models.CharField(max_length=200)
    probed_essids=models.CharField(max_length=200)
    uniqueIdentifiers=('station_mac', 'probed_essids')
        
