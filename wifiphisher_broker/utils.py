import subprocess
import oscrypto
from django.contrib import messages

# Models
from wp3_basic.models import Session

import wifiphisher_broker.wifiphisher_config as cnf

import os, datetime


DNS_MASQ_PATH="/var/lib/misc/dnsmasq.leases" # this will not change in linux

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# Victim Tracking
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
def read_dnsmasq_file()->([dict], bool):
    """
    read dnsmasq.leases file to see devices which have connected at some point
    returns victim_list, error.
    This is semi-persistent so needs cross referenced against active arp results to see if a 'live' connection
    """
    if (not os.path.isfile('/var/lib/misc/dnsmasq.leases')):
        return None, True
    victim_list=[]
    with open(DNS_MASQ_PATH, "r") as dnsmasq_leases:
        for line in dnsmasq_leases:
            line = line.split()
            if not line:
                return None, True
            mac_address = line[1].strip()
            ip_address = line[2].strip()
            device_type = line[3].strip()
            victim_list.append({"vic_mac":mac_address, "vic_ip":ip_address, "vic_dev_type":device_type})
    return victim_list, False

def get_arp_results_for_iface(iface_filter: str)->([dict]):
    """
    Checks current arp table to check which victims are actively connected (by filtering on iface).
    A victim live connected at anypoint during the session is recorded
    """
    # Run process
    arp_results = subprocess.run(["sudo", "arp"], capture_output=True, text=True).stdout
    arp_entries = arp_results.split("\n")
    # first line is header
    active_arp_entries = []
    for entry in arp_entries[1:]:
        # Get elems
        elems = entry.split()
        if len(elems) == 0:
            continue
        # Iface always last element, (when less than 5 elements in list, incomplete arp result showing not connected)
        iface = elems[-1]
        if iface == iface_filter and len(elems) == 5:
            active_arp_entries.append({"vic_ip":elems[0], "HWtype":elems[1], "vic_mac":elems[2], "flags":elems[3],"Iface":elems[4]})
    return active_arp_entries  

def get_victims_currently_connected(iface_filter: str)->([dict], bool):
    """
    Uses read_dnsmasq_file to get detailed info on devices which 'have' connected at some point
    Uses get_arp_results_for_iface and cross checks ip addr's to find victims 'actively' connected
    Its also 'greedy' so if dnsmasq has failed the actively connected device is still added, just without the
    device details provided by dnsmasq
    """
    # Get info
    victim_list, _err = read_dnsmasq_file()
    if _err:
        return None, True
    arp_data = get_arp_results_for_iface(iface_filter)
    
    # Run cross-checks on active arp
    active_arp_ips = [arp["vic_ip"] for arp in arp_data]
    dnsmasq_ips = [dns["vic_ip"] for dns in victim_list]
    active_victims = [vic for vic in victim_list if vic["vic_ip"] in active_arp_ips]
    
    # Run back-up if dnsmasq faulty
    for arp in arp_data:
        if arp["vic_ip"] not in dnsmasq_ips:
            arp["vic_dev_type"] = "unknown"
            active_victims.append(arp)
    return active_victims, False
     

def get_scenarios()->[str]:
    """
    Lists scenarios available for wifiphisher captive portal. Declared in wifiphisher config
    TODO - Perhaps could be acertained from the tool itself?
    """
    # TODO - implement properaly
    return cnf.PHISHING_SCENARIOS.keys()
    
def get_new_log_paths(interface, scenario, essid):
    """
    Uses config to determine log file names, these files are used to store info into django
    """
    ts=datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    filename_prefix=f'{ts}_{interface}_{scenario}_{essid}'
    log_path=os.path.join(cnf.WIFIPHISHER_LOG_DIR, f"{filename_prefix}.log")
    cred_path=os.path.join(cnf.WIFIPHISHER_LOG_DIR, f"{filename_prefix}_cred.log")
    return log_path, cred_path
    
def handle_active_sessions(request, sessions):
    """
    Helper function for useful messages on home page.
    
    Additionally Captive portal (in v1) is not designed to have multiple sessions running, this programmatically closes
    if multiple are found and provides debug
    """
    if len(sessions) > 1:
        message=messages.error(request, "Multiple captive portal sessions detected, killing all")
        for s in sessions[1:]:
            killed = s.end_module_session()
            s.flush_victim_arp()
            if killed:
                message=messages.success(request, f"Killed pid: {s.pid}")
            else:
                message=messages.error(request, f"Failed to kill pid: {s.pid}, suggested to restart system")
    else:
        message=messages.success(request, f"Captive portal session running with interface: {s.interface}, scenario: {s.scenario}, ESSID: {s.essid} detected, killing all")