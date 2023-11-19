from django.shortcuts import render
from django.contrib import messages
from django.conf import settings
import glob, os, datetime, time, subprocess

# VIEWS
def ng_wifi_scan_home(request):
    wifiDevicesDetails=get_wifi_devices()
    availableDevices=[d["Interface"] for d in wifiDevicesDetails]
    return render(request, 'aircrack_ng_broker/wifi_scan.html', {"info":wifiDevicesDetails, "device_list":availableDevices})

def ng_wifi_scan_results(request):
    # Not a post, scan not submitted, show most recent results
    if request.method != "POST":
        # Message to warn not recent
        message=messages.error(request, "Scan details not provided, showing most recent results for user.")
        # render recent stuff
        # Return
        return render(request, 'aircrack_ng_broker/wifi_scan_results.html')
    
    # Post -> scan requested, get details
    if 'wifiInterfaceSelect' not in request.POST:
        # Message to select interface
        message=messages.error(request, "Please select an interface to start scan")
        return ng_wifi_scan_home(request)
    interface = request.POST["wifiInterfaceSelect"]
    if 'scanTime' not in request.POST:
        # default 30 seconds
        scanTime=30
    else:
        scanTime=request.POST['scanTime']
    
    # Run scan
    scanResults=ng_wifi_scan(interface, 15)
    return render(request, 'aircrack_ng_broker/wifi_scan_results.html', {"scanResults":scanResults})

# UTILS
# ADMIN
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

# SCAN
def ng_wifi_scan(interface_name: str, scan_time: int)->(bool, str, int):
    """
    Uses airmon/airodump to scan wifi.
    Returns success (bool), error message (str), scan id (int)
    """
    
    # time stamp & filename
    ts=datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    filenamePrefix=f'{ts}_{interface_name}'
    filePathPrefix=os.path.join(settings.AIRCRACK_SCAN_RESULTS_PATH, filenamePrefix)
    filePathPattern=f'{filePathPrefix}*'
    
    # Create Django scan object
    
    # First start interface monitoring, no effect if alreay in monitor mode
    monitor_on = subprocess.run(["sudo", "airmon-ng", "start", interface_name])
    if monitor_on.returncode != 0:
        return False, f"Could not set {interface_name} to monitor", None
    monitor_interface=interface_name+"mon" if interface_name[-3:] != "mon" else interface_name
    
    # Run scan, need to use popen as command wont exit
    scan = subprocess.Popen(["sudo", "airodump-ng", monitor_interface, "-w", filePathPrefix, "--output-format", "csv"], close_fds=True)
    time.sleep(scan_time)
    scan.terminate()
    scan.kill()
    monitor_off = subprocess.run(["sudo", "airmon-ng", "stop", monitor_interface])
    
    # Read & Save results
    resultFilePath = [f for f in glob.glob(filePathPattern)]
    assert len(resultFilePath)==1, f"tmp dir must not have been cleaned, multiple scan files found matching pattern: {filePathPattern}"
    resultFilePath=resultFilePath[0]
    with open(resultFilePath, "r") as resFile:
        results=resFile.read()
        
    # TODO - Save scan results!
    
    # Clean tmp file
    os.remove(resultFilePath)
    
    return True, results, None

def saveAiroDumpResults(results):
    """
    To save memory/time not using pandas instead reading and parsing file string directly
    Router Schema
        BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key

    Station schema
        Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs
    """
    # Get Routers vs Stations
    routerEntries, stationEntries = results.split('Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs')
    
    for stationEntry in stationEntries.split('\n'):
        if len(stationEntry) != 0:
            elements=[elem.lstrip() for elem in stationEntry.split(",")]
            if len(elements)>=7:
                # Save entry
                pass
            else:
                # TODO - LOG!!
                pass

    
    



