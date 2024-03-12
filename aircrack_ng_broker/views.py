from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

from aircrack_ng_broker.models import *
import portal_auth.utils as auth_utils

import glob, os, datetime, time, subprocess

DEFAULT_SCAN_TIME_s=30
MINIMUM_SCAN_TIME_s=15

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# VIEWS
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 

# HOME
def ng_wifi_scan_home(request):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Location
    location = active_session.getMostRecentLocation()
    if location is None:
        message=messages.error(request, "Warning: Must set location before running exploits")
        return redirect('setLocation')
    
    # Devices
    wifiDevicesDetails=get_wifi_devices()
    availableDevices=[d["Interface"] for d in wifiDevicesDetails]
    
    # Historic Scans
    # TODO - carosel type thing?
    historic_scans=Wifi_Scan.objects.all().filter(session__user=active_session.user).order_by('-start_time')
    return render(request, 'aircrack_ng_broker/wifi_scan.html', {"info":wifiDevicesDetails, 
                                                                 "device_list":availableDevices, 
                                                                 "historic_scans":historic_scans})

# RESULTS
def ng_wifi_show_scan_results(request):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Scan
    scan_id=request.GET.get('scan_id', None)
    if scan_id is None:
        message=messages.error(request, "Must select a scan to view it's results, no scan_id in request params")
        return redirect('ng_wifi_scan_home')
    
    return util_show_scan_results(request, scan_id)

# RUN SCAN
def ng_wifi_run_scan(request):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Not a post, scan not submitted, show most recent results
    if request.method != "POST":
        # Message to warn not recent
        message=messages.error(request, "Scan details not provided, showing most recent results for user.")
        # render recent stuff
        most_recent_id=Wifi_Scan.objects.all().order_by('-start_time').first().id
        # Return
        return util_show_scan_results(request, most_recent_id)
    
    # Scan
    if 'wifiInterfaceSelect' not in request.POST:
        # Message to select interface
        message=messages.error(request, "Please select an interface to start scan")
        return ng_wifi_scan_home(request)
    interface = request.POST["wifiInterfaceSelect"]
    # TODO move to scan model
    if 'scanTime' not in request.POST:
        # default 30 seconds
        scanTime=DEFAULT_SCAN_TIME_s
    else:
        scanTime=int(request.POST['scanTime'])
    if scanTime < MINIMUM_SCAN_TIME_s:
        scanTime=MINIMUM_SCAN_TIME_s
        
    # Create scan object for django
    wifi_scan=Wifi_Scan(session=active_session, start_time=timezone.now(), duration_s=scanTime, interface=interface)
    wifi_scan.save()
    
    # Run scan
    _error, errorMsg=ng_wifi_scan(wifi_scan)
    if _error:
        message=messages.error(request, errorMsg)
        return redirect('ng_wifi_scan_home')
    
    return util_show_scan_results(request, wifi_scan.id)

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# UTILS - view utils
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
def util_show_scan_results(request, scan_id):
    
    # Get results from django db
    beaconResults=Wifi_Scan_Beacon_Result.objects.all().filter(wifi_scan__id=scan_id)
    stationResults=Wifi_Scan_Station_Result.objects.all().filter(wifi_scan__id=scan_id)
    
    return render(request, 'aircrack_ng_broker/wifi_scan_results.html', {"beaconResults":beaconResults, "stationResults": stationResults})


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# UTILS - Devices
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
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

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# UTILS - Scanning
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
def ng_wifi_scan(scanObj: Wifi_Scan)->(bool, str, Wifi_Scan):
    """
    Uses airmon/airodump to scan wifi.
    Returns error (bool), error message (str), scan
    """
    # Unpack details
    interface_name=scanObj.interface
    scan_time=scanObj.duration_s
    
    # time stamp & filename
    ts=datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    filenamePrefix=f'{ts}_{interface_name}'
    filePathPrefix=os.path.join(settings.AIRCRACK_SCAN_RESULTS_PATH, filenamePrefix)
    filePathPattern=f'{filePathPrefix}*'
    
    # First start interface monitoring, no effect if alreay in monitor mode
    monitor_on = subprocess.run(["sudo", "airmon-ng", "start", interface_name])
    if monitor_on.returncode != 0:
        return True, f"Could not set {interface_name} to monitor"
    monitor_interface=interface_name+"mon" if interface_name[-3:] != "mon" else interface_name
    
    # Run scan, need to use popen as command wont exit
    scanProc=subprocess.Popen(["sudo", "airodump-ng", monitor_interface, "-w", filePathPrefix, "--output-format", "csv"], close_fds=True)
    time.sleep(scan_time)
    scanProc.terminate()
    scanProc.kill()
    
    # Reset monitor
    monitor_off = subprocess.run(["sudo", "airmon-ng", "stop", monitor_interface])
    
    # Read & Save results
    resultFilePath = [f for f in glob.glob(filePathPattern)]
    assert len(resultFilePath)==1, f"tmp dir must not have been cleaned, multiple scan files found matching pattern: {filePathPattern}"
    resultFilePath=resultFilePath[0]
    with open(resultFilePath, "r") as resFile:
        results=resFile.read()
        
    # Save scan results
    saveAiroDumpResults(results, scanObj)
    
    # Clean tmp file
    os.remove(resultFilePath)
    
    return False, None

def saveAiroDumpResults(results: str, scanObj: Wifi_Scan):
    """
    To save memory/time not using pandas instead reading and parsing file string directly
    Router Schema
        BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key

    Station schema
        Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs
    """
    # Get Routers vs Stations
    STATION_HEADERS_STRING='Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs'
    if STATION_HEADERS_STRING in results:
        beaconEntries, stationEntries=results.split(STATION_HEADERS_STRING)
    else:
        beaconEntries=results
        stationEntries=None
        
    # Save Beacons (read from index 2 to remove blank line and header)
    for beaconEntry in beaconEntries.split('\n')[2:]:
        if len(beaconEntry) != 0:
            elements=[elem.lstrip() for elem in beaconEntry.split(",")]
            if len(elements)>=15:
                beaconResult=Wifi_Scan_Beacon_Result(
                    wifi_scan=scanObj,
                    bssid=elements[0],
                    first_time_seen=elements[1],
                    last_time_seen=elements[2],
                    channel=int(elements[3]),
                    speed=int(elements[4]),
                    privacy=elements[5],
                    cipher=elements[6],
                    authentication=elements[7],
                    power=int(elements[8]),
                    num_beacons=int(elements[9]),
                    num_iv=int(elements[10]),
                    lan_ip=elements[11],
                    id_len=int(elements[12]),
                    essid=elements[13],
                    key=elements[14],
                )
                beaconResult.save()
            else:
                # TODO - LOG!!
                pass
        
    # Save Stations
    if stationEntries is not None:
        for stationEntry in stationEntries.split('\n'):
            if len(stationEntry) != 0:
                elements=[elem.lstrip() for elem in stationEntry.split(",")]
                if len(elements)>=7:
                    stationResult=Wifi_Scan_Station_Result(
                        wifi_scan=scanObj,
                        station_mac=elements[0],
                        first_time_seen=elements[1],
                        last_time_seen=elements[2],
                        power=int(elements[3]),
                        num_packets=int(elements[4]),
                        bssid=elements[5],
                        probed_essids=elements[6:]
                    )
                    stationResult.save()
                else:
                    # TODO - LOG!!
                    pass


