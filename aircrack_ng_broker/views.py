from django.shortcuts import render
import subprocess 

# VIEWS
def ng_wifi_scan_home(request):
    wifiDevicesDetails=get_wifi_devices()
    availableDevices=[d["Interface"] for d in wifiDevicesDetails]
    return render(request, 'aircrack_ng_broker/wifi_scan.html', {"info":wifiDevicesDetails, "device_list":availableDevices})

def ng_wifi_scan_results(request):
    return render(request, 'aircrack_ng_broker/wifi_scan_results.html')

# UTILS
def get_wifi_devices():
    """
    uses airmon-ng to find available devices for scan
    """
    # Run airmon
    p = subprocess.run(["sudo", "airmon-ng"], capture_output=True, text=True)    
    # Parse output
    return parse_airmon_ng_console_output(p.stdout)

def parse_airmon_ng_console_output(consoleOutput: str, skip=3, up_to_minus=2, separator="\t")->[dict]:
    """
    At time of writing (14/11/2023) airmon-ng output took the following schema:
    
    ''
    HEADERS
    ''
    [<Entries>]
    ''
    ''
    each <Entries> was PHY, Interface, '', Driver, Chipset, TAB separated when in normal mode
    the '' entry isnt present in monitor mode. This is handled
    
    This can be used to parse the console output
    """
    result=[]
    entries = consoleOutput.split("\n")[skip:-up_to_minus]
    for e in entries:
        vals=e.split(separator)
        if len(vals) == 4:
            result.append(
                {
                    "Phy":vals[0],
                    "Interface":vals[1],
                    "Driver":vals[2],
                    "Chipset":vals[3]
                }
            )
        elif len(vals) == 5 and vals[2] == '':
            result.append(
                {
                    "Phy":vals[0],
                    "Interface":vals[1],
                    "Driver":vals[3],
                    "Chipset":vals[4]
                }
            )
        else:
            raise "unexpected format in airmon-ng console output, check validation schema"
    return result

def ng_wifi_scan(interface_name: str):
    # First start interface monitoring, no effect if alreay in monitor mode
    monitor_on = subprocess.run(["sudo", "airmon-ng", "start", interface_name])
    if monitor_on.returncode != 0:
        raise f"Could not set {interface_name} to monitor"
    monitor_interface=[interface_name+"mon" if interface_name[-4] != "mon" else interface_name]
    # Run scan, need to use popen as command wont exit
    # TODO - date stamp
    scan = subprocess.Popen(["sudo", "airodump-ng", monitor_interface, "-w", "devScan", "--output-format", "csv"])

