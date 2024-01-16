from django.db import models
from django.contrib.auth.models import User
from wp3_basic.models import Session

class Wifiphisher_Captive_Portal_Session(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    interface = models.CharField(max_length=200)
    scenario_type = models.CharField(max_length=200)
    aux_data = models.CharField(max_length=2000)
    
# to be moved into 'basic'
# TODO - review ng in the manner
class Credential_Result(models.Model):
    username=models.CharField(max_length=200)
    password=models.CharField(max_length=200)
    capture_time=models.CharField(max_length=200)
    
# It's an 'instance' because mac addresses, and ip constantly change. 
# Regardless by storing it in memory data analytic techniques can be used to interrogate device patterns
# And begin wider assoications
class Device_Instance(models.Model):
    mac_addr=models.CharField(max_length=200)
    ip=models.CharField(max_length=200)
    type=models.CharField(max_length=200)
    
class Wifiphisher_Credential_Result(models.Model):
    wpisher_session=models.ForeignKey(Wifiphisher_Captive_Portal_Session, on_delete=models.CASCADE)
    credential=models.ForeignKey(Credential_Result, on_delete=models.CASCADE)
    
class Wifiphisher_Device_Instance(models.Model):
    wpisher_session=models.ForeignKey(Wifiphisher_Captive_Portal_Session, on_delete=models.CASCADE)
    credential=models.ForeignKey(Credential_Result, on_delete=models.CASCADE)
