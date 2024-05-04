import subprocess
import time
from django.db import models
from lelantos_base.models import Session, Module_Session, Model_Result_Instance
from wifiphisher_broker.utils import get_victims_currently_connected, parse_creds_log
import wifiphisher_broker.config as cfg

# It's an 'instance' because mac addresses, and ip constantly change. 
# Regardless by storing it in memory data analytic techniques can be used to interrogate device patterns
# And begin wider assoications
class Device_Instance(Model_Result_Instance):
    # module_session_captured=models.ForeignKey(Module_Session, on_delete=models.CASCADE)
    mac_addr=models.CharField(max_length=200)
    ip=models.CharField(max_length=200)
    private_ip=models.CharField(max_length=200)
    type=models.CharField(max_length=200)
    first_seen=models.CharField(max_length=200)
    
    # All that needs defined to use the inherited netowrk plotting functions
    # are the model's unique identifiers which determine 'nodes'
    uniqueIdentifiers=('mac_addr', 'type')

class Credential_Result(Model_Result_Instance):
    # module_session_captured=models.ForeignKey(Module_Session, on_delete=models.CASCADE)
    device=models.ForeignKey(Device_Instance, on_delete=models.CASCADE)
    ip=models.CharField(max_length=200)
    type=models.CharField(max_length=200)
    username=models.CharField(max_length=200)
    password=models.CharField(max_length=200)
    capture_time=models.CharField(max_length=200)
    
    # All that needs defined to use the inherited netowrk plotting functions
    # are the model's unique identifiers which determine 'nodes'
    uniqueIdentifiers=('username', 'password')

class Wifiphisher_Captive_Portal_Session(Module_Session):
    module_name=cfg.MODULE_NAME
    interface = models.CharField(max_length=200)
    scenario = models.CharField(max_length=200)
    essid = models.CharField(max_length=2000)
    log_file_path = models.CharField(max_length=2000)
    cred_file_path = models.CharField(max_length=200)
    aux_data = models.CharField(max_length=2000)
    cred_type = models.CharField(max_length=2000)
    
    def update_victims(self, dns_masq_path=cfg.DNS_MASQ_PATH, arp_results=None):
        """
        Compares victims that have connected (linux) to all recorded victims (django) for the session and updates django appropriately
        for the session
        """
        dns_victim_list, error = get_victims_currently_connected(self.interface, dns_masq_path=dns_masq_path, arp_results=arp_results)
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
    
    def get_and_update_victims(self, dns_masq_path=cfg.DNS_MASQ_PATH, arp_results=None)->[Device_Instance]:
        "updates victims, returns all victims"
        self.update_victims(dns_masq_path=dns_masq_path, arp_results=arp_results)
        return self.get_victims()
    
    def flush_victim_arp(self)->bool:
        """ Used after ending session to delete arp entries to prime any new sessions shortly after"""
        # Need to wait for potal to fully close
        time.sleep(cfg.ARP_FLUSH_WAIT_TIME)
        victims = self.get_victims()
        for vic in victims:
            vic_ip = vic.ip
            subprocess.run(["sudo", "arp", "-d", vic_ip])
        return True
    
    def update_credentials(self):
        """ Read credential file to see if any new hits, links credentials to devices of the session """
        cred_entries, _err = parse_creds_log(self.cred_file_path, self.cred_type)
        if cred_entries is None or _err:
            return
        for cred in cred_entries:
            # print(f'updating creds: {cred}')
            # Check if cred already present
            vicCred = Credential_Result.objects.filter(module_session_captured=self,
                                                       ip=cred["vic_ip"],
                                                       type=cred["cred_type"],
                                                       username=cred["username"],
                                                       password=cred["password"])
            if len(vicCred) == 0:
                # print("updating creds: new entry ")
                # Not present, create
                newVicCred = Credential_Result(module_session_captured=self,
                                               ip=cred["vic_ip"],
                                               type=cred["cred_type"],
                                               username=cred["username"],
                                               password=cred["password"])
                
                # try to link to device (none if not found)
                vicDev = Device_Instance.objects.filter(module_session_captured=self, ip=cred["vic_ip"]).first()
                if vicDev is not None:
                    # print(f"found device ({vicDev}) associated with credentials")
                    newVicCred.device = vicDev
                newVicCred.save()
                
    def get_cred_results(self)->[Credential_Result]:
        """Returns all credential results that have used on AP during session"""
        return [c for c in Credential_Result.objects.filter(module_session_captured=self)]
    
    def get_and_update_cred_results(self)->[Credential_Result]:
        """Updates and returns all credential results that have used on AP during session"""
        self.update_credentials()
        return self.get_cred_results()
    
    def update(self, dns_masq_path=cfg.DNS_MASQ_PATH, arp_results=None):
        """Updates victims and credentials """
        victims = self.get_and_update_victims(dns_masq_path=dns_masq_path, arp_results=arp_results)
        creds = self.get_and_update_cred_results()
        return victims, creds
    
def get_current_wphisher_sessions(session: Session)->(bool, [Wifiphisher_Captive_Portal_Session]):
    """
    From a global session returns any active wifiphisher session(s)
    """
    active_sessions = Wifiphisher_Captive_Portal_Session.objects.filter(session=session, active=True)
    if len(active_sessions) > 0:
        return True, [active_session for active_session in active_sessions]
    else:
        return False, None
                
