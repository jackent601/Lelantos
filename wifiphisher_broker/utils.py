import os
DNS_MASQ_PATH="/var/lib/misc/dnsmasq.leases" # this will not change in linux

def read_connected_victims_file()->([dict], bool):
    """
    read dnsmasq.leases file to see devices connected
    returns victim_list, error
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
