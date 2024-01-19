from django.db import models
from django.contrib.auth.models import User
from wp3_basic.models import Session, Module_Session
from wifiphisher_broker.utils import read_connected_victims_file

MODULE_NAME="wifiphisher_captive_portal"

# to be moved into 'basic'
# TODO - review ng in the manner
class Credential_Result(models.Model):
    module_session_captured=models.ForeignKey(Module_Session, on_delete=models.CASCADE)
    username=models.CharField(max_length=200)
    password=models.CharField(max_length=200)
    capture_time=models.CharField(max_length=200)
    
# It's an 'instance' because mac addresses, and ip constantly change. 
# Regardless by storing it in memory data analytic techniques can be used to interrogate device patterns
# And begin wider assoications
class Device_Instance(models.Model):
    module_session_captured=models.ForeignKey(Module_Session, on_delete=models.CASCADE)
    mac_addr=models.CharField(max_length=200)
    ip=models.CharField(max_length=200)
    private_ip=models.CharField(max_length=200)
    type=models.CharField(max_length=200)

class Wifiphisher_Captive_Portal_Session(Module_Session):
    module_name=MODULE_NAME
    interface = models.CharField(max_length=200)
    scenario = models.CharField(max_length=200)
    essid = models.CharField(max_length=2000)
    log_file_path = models.CharField(max_length=2000)
    cred_file_path = models.CharField(max_length=2000)
    aux_data = models.CharField(max_length=2000)
    
    def update_victims(self):
        """
        Compares victims that have connected (linux) to all recorded victims (django) for the session and updates django appropriately
        for the session
        """
        dns_victim_list, error = read_connected_victims_file()
        if error:
            return
        for victim in dns_victim_list:
            # Check if victim already present
            vicDev = Device_Instance.objects.filter(module_session_captured=self,
                                                    mac_addr=victim["vic_mac"],
                                                    ip=victim["vic_ip"],
                                                    type=victim["vic_dev_type"])
            if len(vicDev) == 0:
                # Not present, create
                newVicDev = Device_Instance(module_session_captured=self,
                                            mac_addr=victim["vic_mac"],
                                            ip=victim["vic_ip"],
                                            type=victim["vic_dev_type"])
                
                newVicDev.save()
    
    def get_victims(self)->[Device_Instance]:
        """Returns all devices that have connected to AP during session"""
        return [d for d in Device_Instance.objects.filter(module_session_captured=self)]
    
    def get_and_update_victims(self)->[Device_Instance]:
        "updates victims, returns all victims"
        self.update_victims()
        return self.get_victims()
                
    
class Wifiphisher_Credential_Result(models.Model):
    wpisher_session=models.ForeignKey(Wifiphisher_Captive_Portal_Session, on_delete=models.CASCADE)
    credential=models.ForeignKey(Credential_Result, on_delete=models.CASCADE)
    
class Wifiphisher_Device_Instance(models.Model):
    wpisher_session=models.ForeignKey(Wifiphisher_Captive_Portal_Session, on_delete=models.CASCADE)
    device_instance=models.ForeignKey(Device_Instance, on_delete=models.CASCADE)

