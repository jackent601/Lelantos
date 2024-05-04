from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

from aircrack_ng_broker.models import *
import aircrack_ng_broker.config as cfg
import portal_auth.utils as auth_utils
import utils.utils as gen_utils
import glob, os, datetime, time, subprocess

DEFAULT_SCAN_TIME_s=30
MINIMUM_SCAN_TIME_s=15

# Map to track scans to terminate
# from aircrack_ng_broker.config import SCAN_MAP
SCAN_MAP={}

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# VIEWS
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 

# HOME
def ng_wifi_scan_home(request, testcase=False):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, 
                                                            "You must be logged in to access wifi scans")
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
    wifiDevicesDetails=gen_utils.get_wifi_devices(testcase)
    availableDevices=[d["Interface"] for d in wifiDevicesDetails]
    
    # Historic Scans
    historic_scans=Wifi_Scan.objects.filter(session__user=active_session.user).order_by('-start_time')
    ctx={"info":wifiDevicesDetails, "device_list":availableDevices, "historic_scans":historic_scans}
    if testcase:
        # return context only
        return ctx
    return render(request, 'aircrack_ng_broker/wifi_scan.html', ctx)

# RESULTS
def ng_wifi_previous_scans(request, testcase=False):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    historic_scans=Wifi_Scan.objects.all().filter(session__user=active_session.user).order_by('-start_time')
    ctx={"historic_scans":historic_scans}
    if testcase:
        return ctx
    return render(request, 'aircrack_ng_broker/wifi_scan_previous_scans.html', ctx)

def ng_wifi_show_scan_results(request, testcase=False):
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
        return redirect('ng_wifi_previous_scans')
    
    return util_show_scan_results(request, scan_id, testcase)

# RUN SCAN
def ng_wifi_run_scan(request, include_messages=True, testcase=False):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        if include_messages:
            message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Location
    location = active_session.getMostRecentLocation()
    if location is None:
        if include_messages:
            message=messages.error(request, "Warning: Must set location before running exploits")
        return redirect('setLocation')
    
    # Not a post, scan not submitted, show most recent results
    if request.method != "POST":
        # Message to warn not recent
        if include_messages:
            message=messages.error(request, "Scan details not provided, showing most recent results for user.")
        # render recent stuff
        most_recent_id=Wifi_Scan.objects.all().order_by('-start_time').first().id
        # Return
        return util_show_scan_results(request, most_recent_id)
    
    # Scan
    if 'wifiInterfaceSelect' not in request.POST:
        # Message to select interface
        if include_messages:
            message=messages.error(request, "Please select an interface to start scan")
        return ng_wifi_scan_home(request, testcase=testcase)
    interface = request.POST["wifiInterfaceSelect"]
    if 'scanTime' not in request.POST:
        # default 30 seconds
        scanTime=DEFAULT_SCAN_TIME_s
    else:
        scanTime=int(request.POST['scanTime'])
    if scanTime < MINIMUM_SCAN_TIME_s:
        scanTime=MINIMUM_SCAN_TIME_s
        
    # Create scan object for django
    wifi_scan=Wifi_Scan(session=active_session, 
                        location=location, 
                        start_time=timezone.now(), 
                        duration_s=scanTime, 
                        interface=interface,
                        active=True)
    wifi_scan.save()
    
    # Run scan
    _error, errorMsg=ng_wifi_scan(wifi_scan, testcase)
    if _error:
        if include_messages:
            message=messages.error(request, errorMsg)
        return redirect('ng_wifi_scan_home')
    
    ctx={'scan_id':wifi_scan.id, 'refresh_after': 1000*wifi_scan.duration_s}
    if testcase:
        return ctx
    
    return render(request, 'aircrack_ng_broker/wifi_scan_loading.html', {'scan_id':wifi_scan.id, 'refresh_after': 1000*wifi_scan.duration_s})
    
    # return util_show_scan_results(request, wifi_scan.id)

def ng_wifi_scan_stop(request):
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
        message=messages.error(request, "Must select a scan to stop, no scan_id in request params")
        return redirect('ng_wifi_previous_scans')
    wfscan = Wifi_Scan.objects.filter(id=scan_id).first()
    print("printing scan map")
    try:
        proc = SCAN_MAP[wfscan]
    except:
        message=messages.error(request, "Could not find scan process to stop")
        return redirect('ng_wifi_previous_scans')   
    # return redirect('home')
    return scan_loading_finished(request, wfscan, proc)
    

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# UTILS - view utils
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
def util_show_scan_results(request, scan_id, testcase=False):
    
    # Get results from django db
    beaconResults=Wifi_Scan_Beacon_Result.objects.all().filter(module_session_captured__id=scan_id)
    stationResults=Wifi_Scan_Station_Result.objects.all().filter(module_session_captured__id=scan_id)
    ctx={"beaconResults":beaconResults, "stationResults": stationResults}
    if testcase:
        return ctx
    
    return render(request, 'aircrack_ng_broker/wifi_scan_results.html', ctx)
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# UTILS - Devices
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# TODO - this has been moved to utils, delete code
# def get_wifi_devices(testcase=False):
#     """
#     uses airmon-ng to find available devices for scan
#     """
#     # Run airmon
#     p = subprocess.run(["sudo", "airmon-ng"], capture_output=True, text=True)    
#     # Parse output
#     return parse_airmon_ng_console_output(p.stdout)

# def parse_airmon_ng_console_output(consoleOutput: str, skip=3, up_to_minus=2, separator="\t"):
#     """
#     This can be used to parse the console output from airmon-ng, which has the following schema:
#     '''HEADERS \n  [<Entries>]'''
#     each <Entries> has PHY, Interface, '', Driver, Chipset, TAB separated when in normal mode
#     the '' entry isnt present in monitor mode. This is handled accordingly
#     """
#     result=[]
#     entries = consoleOutput.split("\n")[skip:-up_to_minus]
#     for e in entries:
#         vals=e.split(separator)
#         if len(vals) == 4:
#             result.append(
#                 {
#                     "Phy":vals[0],
#                     "Interface":vals[1],
#                     "Driver":vals[2],
#                     "Chipset":vals[3]
#                 }
#             )
#         elif len(vals) == 5 and vals[2] == '':
#             result.append(
#                 {
#                     "Phy":vals[0],
#                     "Interface":vals[1],
#                     "Driver":vals[3],
#                     "Chipset":vals[4]
#                 }
#             )
#         else:
#             raise "unexpected format in airmon-ng console output, check validation schema"
#     return result

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# UTILS - Scanning
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
def ng_wifi_scan(scanObj: Wifi_Scan, testcase=False):
    """
    Uses airmon/airodump to scan wifi.
    Returns error (bool), error message (str), scan
    """
    # Unpack details
    interface_name=scanObj.interface
    
    # time stamp & filename
    ts=datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    filenamePrefix=f'{ts}_{interface_name}'
    filePathPrefix=os.path.join(cfg.AIRCRACK_SCAN_RESULTS_PATH, filenamePrefix)
    filePathPattern=f'{filePathPrefix}*'
    
    # First start interface monitoring, no effect if alreay in monitor mode
    if not testcase:
        monitor_on = subprocess.run(["sudo", "airmon-ng", "start", interface_name])
        if monitor_on.returncode != 0:
            return True, f"Could not set {interface_name} to monitor"
    monitor_interface=interface_name+"mon" if interface_name[-3:] != "mon" else interface_name
    
    scanObj.monitor_interface=monitor_interface
    scanObj.filePathPattern=filePathPattern
    scanObj.save()
    
    # Run scan, need to use popen as command wont exit
    if not testcase:
        scanProc=subprocess.Popen(["sudo", "airodump-ng", monitor_interface, "-w", filePathPrefix, "--output-format", "csv"], 
                              close_fds=True)
    else:
        scanProc=testScanProc()
    
    # Add to map for tracking
    SCAN_MAP[scanObj]=scanProc
    return False, None

def scan_loading_finished(request, scanObj, scanProc, testcase=False):
    
    # time.sleep(scan_time)
    # End scan once duration reached
    scanProc.terminate()
    scanProc.kill()
    
    # End module session
    scanObj.end_time=timezone.now()
    scanObj.active=False
    scanObj.save()
    
    # Reset monitor
    if not testcase:
        subprocess.run(["sudo", "airmon-ng", "stop", scanObj.monitor_interface])
    
    # Read & Save results
    resultFilePath = [f for f in glob.glob(scanObj.filePathPattern)]
    assert len(resultFilePath)==1, f"tmp dir must not have been cleaned, multiple (or no) scan files found matching pattern: {scanObj.filePathPattern}"
    resultFilePath=resultFilePath[0]
    with open(resultFilePath, "r") as resFile:
        results=resFile.read()
    # Save scan results
    beaconResults, stationResults = saveAiroDumpResults(results, scanObj)
    # Clean tmp file
    os.remove(resultFilePath)
    if testcase:
        return beaconResults, stationResults
    return util_show_scan_results(request, scanObj.id)

def saveAiroDumpResults(results: str, scanObj: Wifi_Scan):
    """
    To save memory/time not using pandas instead reading and parsing file string directly
    Router Schema
        BSSID, First time seen, Last time seen, channel, Speed, Privacy, 
        Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key

    Station schema
        Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs
    """
    # Get Routers vs Stations
    if cfg.STATION_HEADERS_STRING in results:
        beaconEntries, stationEntries=results.split(cfg.STATION_HEADERS_STRING)
    else:
        beaconEntries=results
        stationEntries=None
        
    # Save Beacons (read from index 2 to remove blank line and header)
    beaconResults=[]
    for beaconEntry in beaconEntries.split('\n')[2:]:
        if len(beaconEntry) != 0:
            elements=[elem.lstrip() for elem in beaconEntry.split(",")]
            if len(elements)>=15:
                beaconResult=Wifi_Scan_Beacon_Result(
                    module_session_captured=scanObj,
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
                beaconResults.append(beaconResult)
        
    # Save Stations
    stationResults=[]
    if stationEntries is not None:
        for stationEntry in stationEntries.split('\n'):
            if len(stationEntry) != 0:
                elements=[elem.lstrip() for elem in stationEntry.split(",")]
                if len(elements)>=7:
                    stationResult=Wifi_Scan_Station_Result(
                        module_session_captured=scanObj,
                        station_mac=elements[0],
                        first_time_seen=elements[1],
                        last_time_seen=elements[2],
                        power=int(elements[3]),
                        num_packets=int(elements[4]),
                        bssid=elements[5],
                        probed_essids=elements[6:]
                    )
                    stationResult.save()
                    stationResults.append(stationResult)
    return beaconResults, stationResults

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# UTILS - Dependency injection for testing scanning interface
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
class testScanProc():
    def terminate(self):
        pass
    def kill(self):
        pass