from django.db import models
from lelantos_base.models import Module_Session
import aircrack_ng_broker.config as cfg

class Wifi_Scan(Module_Session):
    """
    Module_Session wrapper for wifi-scans, declaring interface to use for scan
    and scan duration
    """
    module_name=cfg.MODULE_NAME
    duration_s = models.PositiveIntegerField()
    interface = models.CharField(max_length=200)
    
# TODO - Move to basic
class Wifi_Scan_Beacon_Result(models.Model):
    wifi_scan=models.ForeignKey(Module_Session, on_delete=models.CASCADE)
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
    
class Wifi_Scan_Station_Result(models.Model):
    wifi_scan = models.ForeignKey(Module_Session, on_delete=models.CASCADE)
    station_mac=models.CharField(max_length=200)
    first_time_seen=models.CharField(max_length=200)
    last_time_seen=models.CharField(max_length=200)
    power=models.IntegerField()
    num_packets=models.IntegerField()
    bssid=models.CharField(max_length=200)
    probed_essids=models.CharField(max_length=200)
    
