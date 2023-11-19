from django.db import models
from django.contrib.auth.models import User

class Wifi_Scan(models.Model):
    session_id = models.PositiveIntegerField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    duration_s = models.PositiveIntegerField()
    interface = models.CharField(max_length=200)
    # location = TBD
    
class Wifi_Scan_Beacon_Result(models.Model):
    wifi_scan=models.ForeignKey(Wifi_Scan, on_delete=models.CASCADE)
    bssid=models.CharField(max_length=200)
    first_time_seen=models.CharField(max_length=200)
    last_time_seen=models.CharField(max_length=200)
    channel=models.IntegerField()
    speed=models.IntegerField()
    privacy=models.CharField(max_length=200)
    cipher=models.CharField(max_length=200)
    authentication=models.CharField(max_length=200)
    cipher=models.CharField(max_length=200)
    power=models.IntegerField()
    num_beacons=models.IntegerField()
    num_iv=models.IntegerField()
    lan_ip=models.CharField(max_length=200)
    id_len=models.IntegerField()
    essid=models.CharField(max_length=200)
    key=models.CharField(max_length=200)
    
class Wifi_Scan_Station_Result(models.Model):
    wifi_scan = models.ForeignKey(Wifi_Scan, on_delete=models.CASCADE)
    station_mac=models.CharField(max_length=200)
    first_time_seen=models.CharField(max_length=200)
    last_time_seen=models.CharField(max_length=200)
    power=models.IntegerField()
    num_packets=models.IntegerField()
    bssid=models.CharField(max_length=200)
    probed_essids=models.CharField(max_length=200)
    
