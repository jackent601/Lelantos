from django.test import TestCase
from lelantos_base.models import Module_Session, Location, Session
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.test import Client
from aircrack_ng_broker.models import Wifi_Scan, Wifi_Scan_Beacon_Result, Wifi_Scan_Station_Result
from django.conf import settings 
import os
from shutil import copyfile

# disable logging
import logging
logging.disable(logging.CRITICAL)

# Functions to test
import aircrack_ng_broker.views as ng_views

TEST_DATA_REL_PATH="aircrack_ng_broker/tests/testdata.csv"
TEST_DATA_ABS_PATH=os.path.join(settings.BASE_DIR, TEST_DATA_REL_PATH)
def copyTestData(path):
    """ copies what would be scan results output from testdata.csv to filepath """
    copyfile(TEST_DATA_ABS_PATH, path)

def scanPrep(cls):
    """ test data for scan """
    cls.user_username="test"
    cls.user_password="test"
    cls.user = User.objects.create_user("test","test","test")
    # Session
    cls.sesh = Session.objects.create(session_id=1, user=cls.user, start_time=timezone.now(), src_ip="x.x.x.x", active=True)
    cls.c = Client()
    cls.c.login(username=cls.user_username, password=cls.user_password)
    # Location
    testLocPoint=GEOSGeometry(f"POINT (-641025.8565339005 7308772.180542897)", srid=4326)
    cls.loc = Location.objects.create(session=cls.sesh, name="testLoc", location=testLocPoint, area="testArea", remarks="testRemarks")
    # Module Session
    cls.mSesh= Module_Session.objects.create(session=cls.sesh, location=cls.loc, module_name="testModule", start_time=timezone.now(), active=False)
    # Previous Scan
    cls.prevScan = Wifi_Scan.objects.create(session=cls.sesh, 
                                            location=cls.loc, 
                                            start_time=timezone.now(), 
                                            active=False,
                                            duration_s=15,
                                            interface="TestInterface")
    cls.prevScanBeacon1 = Wifi_Scan_Beacon_Result.objects.create(module_session_captured=cls.prevScan,
                                                                 bssid="tBssid1", essid="tEssid1")
    cls.prevScanBeacon2 = Wifi_Scan_Beacon_Result.objects.create(module_session_captured=cls.prevScan,
                                                                 bssid="tBssid2", essid="tEssid12")
    cls.prevScanStation1 = Wifi_Scan_Station_Result.objects.create(module_session_captured=cls.prevScan,
                                                                   station_mac="mac1", probed_essids="e1")
    cls.prevScanStation2 = Wifi_Scan_Station_Result.objects.create(module_session_captured=cls.prevScan,
                                                                   station_mac="mac2", probed_essids="e2")


class AircrackNgBroker_TestCase(TestCase):
    """
    Aircrack-ng's wrapper functions
    """
    @classmethod
    def setUpTestData(cls):
        print("AircrackNgBroker_TestCase - - - - - - - - - - - - - - - - - - - - - -")
        scanPrep(cls)
        
    def test_getPreviousScans_Success(self):
        """ retrieve previous scans from request user context """
        # get base response
        req=HttpRequest()
        req.user=self.user
        ctx = ng_views.ng_wifi_previous_scans(req, True)
        # unpack context
        prevScans=ctx['historic_scans']
        # 1 previous scan
        self.assertEqual(1, len(prevScans))
        # check user and duration
        prevScan=prevScans[0]
        self.assertEqual(self.user, prevScan.session.user)
        self.assertEqual(15, prevScan.duration_s)
        print("     pass: test_getPreviousScans_Success")
        
    def test_getHomePageContextFromRequest_Success(self):
        """ successful request to available devices and previous scans for home page """
        # get base response
        req=HttpRequest()
        req.user=self.user
        ctx = ng_views.ng_wifi_scan_home(req, True, True)
        # unpack context
        availableDevices=ctx['device_list']
        prevScans=ctx['historic_scans']
        # 1 available device for test named testInterface
        self.assertEqual(1, len(availableDevices))
        self.assertEqual("TestInterface",availableDevices[0])
        # 1 previous scan
        self.assertEqual(1, len(prevScans))
        print("     pass: test_getHomePageContextFromRequest_Success")
        
    def test_showScanResultsByID(self):
        """ display previous scan results from scan_id in request """
        # get base response
        req=HttpRequest()
        req.user=self.user
        req.GET['scan_id']=self.prevScan.id
        ctx = ng_views.ng_wifi_show_scan_results(req, True)
        # get results
        beaconResults=ctx['beaconResults']
        stationResults=ctx['stationResults']
        # check beacon values
        self.assertEqual(2, len(beaconResults))
        retrievedBeaconBssids = [b.bssid for b in beaconResults]
        expectedBeaconBssids = ["tBssid1", "tBssid2"]
        for b in expectedBeaconBssids:
            if b not in retrievedBeaconBssids:
                self.fail(f"{b} not in retrieved bssids: {retrievedBeaconBssids}")
        for b in retrievedBeaconBssids:
            if b not in expectedBeaconBssids:
                self.fail(f"{b} not in expected bssids: {expectedBeaconBssids}")
        # check station values
        stationResults=ctx['stationResults']
        self.assertEqual(2, len(stationResults))
        retrievedStationMacs = [s.station_mac for s in stationResults]
        expectedStationMacs = ["mac1", "mac2"]
        for m in expectedStationMacs:
            if m not in retrievedStationMacs:
                self.fail(f"{m} not in retrieved macs: {retrievedStationMacs}")
        for m in retrievedStationMacs:
            if m not in expectedStationMacs:
                self.fail(f"{m} not in expected macs: {retrievedStationMacs}")
        print("     pass: test_showScanResultsByID")   
            
    def test_ngWifiScanStart(self):
        """ Running a scan based on scan object (created from form input tested in next test) """
        # clean scan-map for test
        ng_views.SCAN_MAP={}
        # start scan
        err, errMsg = ng_views.ng_wifi_scan(self.prevScan, True)
        # check no errors
        self.assertEqual(err, False)
        self.assertEqual(errMsg, None)
        # check added to map
        scanProc = ng_views.SCAN_MAP[self.prevScan]
        self.assertNotEqual(scanProc, None)
        # check tracking info updated on object
        scanObj = Wifi_Scan.objects.filter(session__user=self.user).first()
        # interface set to monitor mode
        self.assertEqual(scanObj.monitor_interface, "TestInterfacemon")
        # file pattern for this interface
        if "_TestInterface*" not in scanObj.filePathPattern:
            self.fail("log file pattern not as expected")
        # clean scan-map for test
        ng_views.SCAN_MAP={}
        print("     pass: test_ngWifiScanStart")  
        
    def test_ngWifiRunScanInputForm(self): 
        """ Running a scan based on form input from web-server """
        # clean scan-map
        ng_views.SCAN_MAP={}
        # construct request
        req=HttpRequest()
        req.user=self.user
        req.method="POST"
        req.POST['wifiInterfaceSelect']="interfaceFromForm"
        # start
        ctx = ng_views.ng_wifi_run_scan(req, include_messages=False, ctx_only=True, testcase=True)
        # check scan object created
        scansCreated=Wifi_Scan.objects.filter(interface="interfaceFromForm")
        self.assertEqual(1, len(scansCreated))
        scanCreated=scansCreated[0]
        # check added to scan-map
        scanProc=ng_views.SCAN_MAP[scanCreated]
        self.assertNotEqual(scanProc, None)
        # clean scan-map for test
        ng_views.SCAN_MAP={}
        print("     pass: test_ngWifiRunScanInputForm")  
        
    def test_ngWifiRunScanInputForm_NoInterface(self): 
        """ Running a scan based on form input from web-server, fails as no interface in form data """
        # clean scan-map
        ng_views.SCAN_MAP={}
        # construct request
        req=HttpRequest()
        req.user=self.user
        req.method="POST"
        # start
        ctx = ng_views.ng_wifi_run_scan(req, include_messages=False, ctx_only=True, testcase=True)
        # check is a redirect (historic_scans key from home page context)
        if "historic_scans" not in ctx.keys():
            self.fail("not redirected correctly")
        print("     pass: test_ngWifiRunScanInputForm_NoInterface") 
        
    def test_ngWifiRunScanInputForm_GetReq(self): 
        """ Running a scan based on form input from web-server, fails as not post request """
        # clean scan-map
        ng_views.SCAN_MAP={}
        # construct request
        req=HttpRequest()
        req.user=self.user
        req.method="GET"
        req.POST['wifiInterfaceSelect']="interfaceFromForm"
        # start
        ctx = ng_views.ng_wifi_run_scan(req, include_messages=False, ctx_only=True, testcase=True)
        # check is a redirect
        self.assertIsInstance(ctx, HttpResponse)
        print("     pass: test_ngWifiRunScanInputForm_GetReq")
        
    def test_ParseScanResults(self):
        """ parses testdata to check results unpacked successfully """
        # Read test data
        with open(TEST_DATA_ABS_PATH, "r") as resFile:
            testData=resFile.read()
        # Parse results
        beaconResults, stationResults = ng_views.saveAiroDumpResults(testData, self.prevScan)
        # check results
        self.checkTestDataResultsContent(stationResults, beaconResults, self.prevScan)
        print("     pass: test_ParseScanResults")  
    
    def test_StopScan(self):
        """ Stop a running scan and check results are correctly parsed and fetched """
        req=HttpRequest()
        req.user=self.user
        ng_views.SCAN_MAP={}
        # first start a scan (tested above)
        err, errMsg = ng_views.ng_wifi_scan(self.prevScan, True)
        scanProc = ng_views.SCAN_MAP[self.prevScan]
        scanObj = Wifi_Scan.objects.filter(session__user=self.user).first()
        # copy test data to output path
        copyTestData(scanObj.filePathPattern)
        # stop scan (getting results from scan)
        beaconResults, stationResults = ng_views.scan_loading_finished(req, self.prevScan, scanProc, True)
        # check results
        self.checkTestDataResultsContent(stationResults, beaconResults, self.prevScan)
        # clean scan-map for test
        ng_views.SCAN_MAP={}
        print("     pass: test_StopScan")  
                
    def checkTestDataResultsContent(self, stationResults, beaconResults, wifiScan):
        """ Checks the testdata is parsed correctly """
        # Expect 2 results from each
        self.assertEqual(2, len(beaconResults))
        self.assertEqual(2, len(stationResults))
        # check content of each
        expectedMacs=["resultMac1", "resultMac2"]
        receivedMacs=[r.station_mac for r in stationResults]
        for mac in expectedMacs:
            if mac not in receivedMacs:
                self.fail(f"{mac} not found in results")
        for station in stationResults:
            if station.module_session_captured != wifiScan:
                self.fail("result tied to wrong module session")
        expectedBeacons=["resultBssid1", "resultBssid2"]
        receivedBeacons=[b.bssid for b in beaconResults]
        for bssid in expectedBeacons:
            if bssid not in receivedBeacons:
                self.fail(f"{bssid} not found in results")
        for beacon in beaconResults:
            if beacon.module_session_captured != wifiScan:
                self.fail("result tied to wrong module session")
        