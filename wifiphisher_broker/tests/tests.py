from django.test import TestCase
from lelantos_base.models import Module_Session, Location, Session
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.test import Client
from django.conf import settings 
import os
from shutil import copyfile

# Functions to test
from wifiphisher_broker.models import Wifiphisher_Captive_Portal_Session
import wifiphisher_broker.views as cp_views
import wifiphisher_broker.utils as cp_utils
import wifiphisher_broker.config as cp_cfg

# test files
TEST_LOG_REL_PATH="wifiphisher_broker/tests/testdataLog.log"
TEST_LOG_ABS_PATH=os.path.join(settings.BASE_DIR, TEST_LOG_REL_PATH)
TEST_CRED_LOG_REL_PATH="wifiphisher_broker/tests/testdataUserCredLog.log"
TEST_CRED_LOG_ABS_PATH=os.path.join(settings.BASE_DIR, TEST_CRED_LOG_REL_PATH)
TEST_WIFI_CRED_LOG_REL_PATH="wifiphisher_broker/tests/testdataWifiPasswordCredLog.log"
TEST_WIFI_CRED_LOG_ABS_PATH=os.path.join(settings.BASE_DIR, TEST_WIFI_CRED_LOG_REL_PATH)
TEST_DNS_MASQ_FILE_REL_PATH="wifiphisher_broker/tests/dnsmasq.leases.test"
TEST_DNS_MASQ_FILE_ABS_PATH=os.path.join(settings.BASE_DIR, TEST_DNS_MASQ_FILE_REL_PATH)
TEST_EXPECTED_DNS_MACS=["mac1", "mac2", "mac3"]
# to check correct 'actively connected' results comparing arp to dnsmasque
#   victim 3 in dnsmasque is not from captive portal interface, hence absent in active victims
#   victim 2 in dnsmasque is not present in arp, hence absent in active victims
#   victim 1 present in arp with captive portal interface, hence present in active victims
#   victim 4 present in arp but not dnsmasque, hence present in active victims with device type UNKNOWN
TEST_ARP_RESULTS="HEADER\n1.2.3.4 HWType mac1 flag1 TestInterface\nip4 HWType mac4 flag4 TestInterface\nip3 HWType mac3 flag3 NotTheCPInterface"
EXPECTED_ARP_MACS=["mac1", "mac4"]

# Prepping data
def copyTestLogData(path):
    """ copies what would be captive portal log to filepath """
    copyfile(TEST_LOG_ABS_PATH, path)
    
def copyTestUserCredLogData(path):
    """ copies what would be captive portal credential log to filepath """
    copyfile(TEST_CRED_LOG_ABS_PATH, path)
    
def copyTestWifiCredLogData(path):
    """ copies what would be captive portal credential log to filepath """
    copyfile(TEST_WIFI_CRED_LOG_ABS_PATH, path)
    
def copyCPUserLogsFromObj(cpObj):
    """ Using paths generated on session object copies data to expected locations """
    copyTestLogData(cpObj.log_file_path)
    copyTestUserCredLogData(cpObj.cred_file_path)
    
def copyCPWifiLogsFromObj(cpObj):
    """ Using paths generated on session object copies data to expected locations """
    copyTestLogData(cpObj.log_file_path)
    copyTestWifiCredLogData(cpObj.cred_file_path)

def captivePortalPrep(cls, username="test", id=1):
    """ test data for scan """
    cls.user_username=username
    cls.user_password="test"
    cls.user = User.objects.create_user(username,"test","test")
    # Session
    cls.sesh = Session.objects.create(session_id=id, user=cls.user, start_time=timezone.now(), src_ip="x.x.x.x", active=True)
    cls.c = Client()
    cls.c.login(username=username, password=cls.user_password)
    # Location
    testLocPoint=GEOSGeometry(f"POINT (-641025.8565339005 7308772.180542897)", srid=4326)
    cls.loc = Location.objects.create(session=cls.sesh, name="testLoc", location=testLocPoint, area="testArea", remarks="testRemarks")
    # Module Session
    cls.mSesh= Module_Session.objects.create(session=cls.sesh, location=cls.loc, module_name="testModule", start_time=timezone.now(), active=False)
    # Captive Portal Session (user credential captures)
    log_path, cred_path = cp_utils.get_new_log_paths("TestInterface", cp_cfg.OAUTH_LOGIN, "TestEssid") 
    cls.prevCPUserCreds = Wifiphisher_Captive_Portal_Session.objects.create(session=cls.sesh, 
                                                                   location=cls.loc, 
                                                                   start_time=timezone.now(), 
                                                                   active=False,
                                                                   interface="TestInterface",
                                                                   essid="TestEssid",
                                                                   scenario=cp_cfg.OAUTH_LOGIN,
                                                                   cred_type=cp_cfg.CRED_TYPE_USER,
                                                                   log_file_path=log_path,
                                                                   cred_file_path=cred_path)
    # Captive Portal Session (user credential captures)
    wifi_log_path, wifi_cred_path = cp_utils.get_new_log_paths("TestInterface", cp_cfg.FIRMWARE_UPGRADE, "TestEssidWifi") 
    cls.prevCPWifiCreds = Wifiphisher_Captive_Portal_Session.objects.create(session=cls.sesh, 
                                                                   location=cls.loc, 
                                                                   start_time=timezone.now(), 
                                                                   active=False,
                                                                   interface="TestInterface",
                                                                   essid="TestEssidWifi",
                                                                   scenario=cp_cfg.FIRMWARE_UPGRADE,
                                                                   cred_type=cp_cfg.CRED_TYPE_WPA_PASSWORD,
                                                                   log_file_path=wifi_log_path,
                                                                   cred_file_path=wifi_cred_path)
    copyCPWifiLogsFromObj(cls.prevCPWifiCreds)
    copyCPUserLogsFromObj(cls.prevCPUserCreds)


class WifiPhisherBroker_Utils_TestCase(TestCase):
    """
    wifi-phishers utils functions used to parse logs in order to create and match django models
    """
    @classmethod
    def setUpTestData(cls):
        print("WifiPhisherBroker_Utils_TestCase- - - - - - - - - - - - - - - - - - -")
        captivePortalPrep(cls)
        
    @classmethod
    def tearDownClass(cls):
        os.remove(cls.prevCPUserCreds.log_file_path)
        os.remove(cls.prevCPUserCreds.cred_file_path)
        os.remove(cls.prevCPWifiCreds.log_file_path)
        os.remove(cls.prevCPWifiCreds.cred_file_path)
        
    def test_readDnsMasqFile_Success(self):
        """ reads dns masque to get deatiled info on all devices that have connected at some point  """
        victimlist, err = cp_utils.read_dnsmasq_file(dns_masq_path=TEST_DNS_MASQ_FILE_ABS_PATH)
        self.assertEqual(False, err)
        # 3 victims in test file
        self.assertEqual(3, len(victimlist))
        retrievedMacs = [v['vic_mac'] for v in victimlist]
        for m in TEST_EXPECTED_DNS_MACS:
            if m not in retrievedMacs:
                self.fail(f"expected mac {m} not in retrieved macs: {retrievedMacs}")
        print("     pass: test_getPreviousScans_Success")
        
    def test_readDnsMasqFile_IndexOOB(self):
        """ reads dns masque file but with misconfigured index declared  """
        victimlist, err = cp_utils.read_dnsmasq_file(dns_masq_path=TEST_DNS_MASQ_FILE_ABS_PATH, macIndex=10)
        self.assertEqual(True, err)
        self.assertEqual(None, victimlist)
        print("     pass: test_readDnsMasqFile_IndexOOB")
        
    def test_getArpResultsForIFace(self):
        """ reads 'arp results' and cross checks for captive portal interface  """
        active_arp_entries = cp_utils.get_arp_results_for_iface("TestInterface", TEST_ARP_RESULTS)
        # two victims for interface (see test data comments)
        self.assertEqual(2, len(active_arp_entries))
        retrievedArpMacs=[d['vic_mac'] for d in active_arp_entries]
        self.checkActiveMacs(retrievedArpMacs)
        print("     pass: test_getArpResultsForIFace")
        
    def test_getVictimsCurrentlyConnected(self):
        """ uses the above two functions to cross check and retrieve rich data for ONLY actively connected devices """
        active_victims, err = cp_utils.get_victims_currently_connected("TestInterface", TEST_DNS_MASQ_FILE_ABS_PATH, TEST_ARP_RESULTS)
        # only one victim for interface (see test data comments)
        self.assertEqual(False, err)
        self.assertEqual(2, len(active_victims))
        # check types including 'greedy algorithm' for victim 4 absent in dns masque
        types=[v['vic_dev_type'] for v in active_victims]
        for t in ["devicetype1", "unknown"]:
            if t not in types:
                self.fail(f"type {t} not in retrieved types: {types}")
        # check macs
        retrievedMacs=[v['vic_mac'] for v in active_victims]
        self.checkActiveMacs(retrievedMacs)
        print("     pass: test_getVictimsCurrentlyConnected")
        
    def checkActiveMacs(self, retrievedMacs):
        """ Util for expected retrieved active macs """
        for m in EXPECTED_ARP_MACS:
            if m not in retrievedMacs:
                self.fail(f"mac {m} not in retrieved macs: {retrievedMacs}")
                
    def test_parseCredsLog_UserCredentials(self):
        """ uses regex to match wifiphishers logs and retrieve the victim credential dictionary """
        results, err = cp_utils.parse_creds_log(self.prevCPUserCreds.cred_file_path, self.prevCPUserCreds.cred_type)
        # despite two entries only one will match regex
        self.assertEqual(1, len(results))
        victim=results[0]
        # victim 1 details
        self.assertEqual("1.2.3.4", victim['vic_ip'])
        self.assertEqual("TestVictim1", victim['username'])
        self.assertEqual("TestVictimPassword1", victim['password'])
        print("     pass: test_parseCredsLog_UserCredentials")
        
    def test_parseCredsLog_WifiCredentials(self):
        """ uses regex to match wifiphishers logs and retrieve the victim credential dictionary for wpa passwords """
        results, err = cp_utils.parse_creds_log(self.prevCPWifiCreds.cred_file_path, self.prevCPWifiCreds.cred_type)
        # despite two entries only one will match regex
        self.assertEqual(1, len(results))
        victim=results[0]
        # victim 1 details
        self.assertEqual("1.2.3.4", victim['vic_ip'])
        self.assertEqual("", victim['username'])
        self.assertEqual("TestWPAPassword", victim['password'])
        print("     pass: test_parseCredsLog_WifiCredentials")
        
class WifiPhisherBroker_Models_TestCase(TestCase):
    """
    wifiphishers model methods, they use the above utils but also, and improtantly, cross check against stored django models
    """
    @classmethod
    def setUpTestData(cls):
        print("WifiPhisherBroker_Models_TestCase - - - - - - - - - - - - - - - - - -")
        captivePortalPrep(cls, "modeltest", 2)
        
    @classmethod
    def tearDownClass(cls):
        os.remove(cls.prevCPUserCreds.log_file_path)
        os.remove(cls.prevCPUserCreds.cred_file_path)
        os.remove(cls.prevCPWifiCreds.log_file_path)
        os.remove(cls.prevCPWifiCreds.cred_file_path)
        
    def test_ModelUpdate_UserCredentials(self):
        """ update is what runs all the cross checking above, creates django models, and matches to devices"""  
        victims, creds = self.prevCPUserCreds.update(dns_masq_path=TEST_DNS_MASQ_FILE_ABS_PATH, arp_results=TEST_ARP_RESULTS)
        # Two victims, but only one credential
        self.assertEqual(1, len(creds))
        self.assertEqual(2, len(victims))
        # check credential unpacked properly and linked to victim
        cred=creds[0]        
        self.assertEqual("TestVictim1", cred.username)
        self.assertEqual("TestVictimPassword1", cred.password)
        victimdev=cred.device
        self.assertEqual("mac1", victimdev.mac_addr)
        self.assertEqual("1.2.3.4", victimdev.ip)
        print("     pass: test_ModelUpdate_UserCredentials")
        
    def test_ModelUpdate_WifiCredentials(self):
        """ update is what runs all the cross checking above, creates django models, and matches to devices"""  
        victims, creds = self.prevCPWifiCreds.update(dns_masq_path=TEST_DNS_MASQ_FILE_ABS_PATH, arp_results=TEST_ARP_RESULTS)
        # Two victims, but only one credential
        self.assertEqual(1, len(creds))
        self.assertEqual(2, len(victims))
        # check credential unpacked properly and linked to victim (no username for wpa-password)
        cred=creds[0]        
        self.assertEqual("", cred.username)
        self.assertEqual("TestWPAPassword", cred.password)
        victimdev=cred.device
        self.assertEqual("mac1", victimdev.mac_addr)
        self.assertEqual("1.2.3.4", victimdev.ip)
        print("     pass: test_ModelUpdate_WifiCredentials")
        
class WifiPhisherBroker_Views_TestCase(TestCase):
    """
    wifiphishers model methods, they use the above utils but also, and improtantly, cross check against stored django models
    """
    @classmethod
    def setUpTestData(cls):
        print("WifiPhisherBroker_Models_TestCase - - - - - - - - - - - - - - - - - -")
        captivePortalPrep(cls, "viewsTest", 3)
        
    @classmethod
    def tearDownClass(cls):
        os.remove(cls.prevCPUserCreds.log_file_path)
        os.remove(cls.prevCPUserCreds.cred_file_path)
        os.remove(cls.prevCPWifiCreds.log_file_path)
        os.remove(cls.prevCPWifiCreds.cred_file_path)
        
    def test_WifiphisherCaptivePortalHome(self):
        """ update is what runs all the cross checking above, creates django models, and matches to devices"""  
        req=HttpRequest()
        req.user=self.user 
        ctx = cp_views.wifiphisher_captive_portal_home(req, False, True, True)
        # unpack and check context
        status=ctx['captive_portal_status']
        # no running sessions
        self.assertEqual(status, False)
        # only test interface
        interfaces=ctx['interfaces']
        self.assertEqual(1, len(interfaces))
        self.assertEqual("TestInterface", interfaces[0])
        # test user has two previous scans
        prevSession=ctx['historic_captures']
        self.assertEqual(2, len(prevSession))
        print("     pass: test_WifiphisherCaptivePortalHome")
        
    def test_WifiphisherCaptivePortalLaunch_Fail_GetReq(self):
        """ failed cp launch due to get not post request """  
        req=HttpRequest()
        req.user=self.user 
        req.method="GET"
        resp = cp_views.wifiphisher_captive_portal_launch(req, False, True)
        # check redirect to home
        self.assertIsInstance(resp, HttpResponse)
        self.assertEqual(resp.url, "/captive_portal_home/")
        print("     pass: test_WifiphisherCaptivePortalLaunch_Fail_GetReq")
        
    def test_WifiphisherCaptivePortalLaunch_Fail_AlreadyActiveSession(self):
        """ failed cp launch as cp already running """  
        req=HttpRequest()
        req.user=self.user 
        req.method="POST"
        # set session to active
        egSesh = Wifiphisher_Captive_Portal_Session.objects.filter(session=self.sesh).first()
        egSesh.active=True
        egSesh.save()
        resp = cp_views.wifiphisher_captive_portal_launch(req, False, True)
        # check redirect to monitor
        self.assertIsInstance(resp, HttpResponse)
        self.assertEqual(resp.url, "/captive_portal_monitor/")
        print("     pass: test_WifiphisherCaptivePortalLaunch_Fail_AlreadyActiveSession")
        
    def test_WifiphisherCaptivePortalLaunch_Success(self):
        """ cp launch """  
        req=HttpRequest()
        req.user=self.user 
        req.method="POST"
        req.POST['interface']="NewInterface"
        req.POST['scenario']=cp_cfg.OAUTH_LOGIN
        req.POST['essid']="testEssid"
        newCPSession = cp_views.wifiphisher_captive_portal_launch(req, False, True)
        # check new cp-session and tied to this sesh
        self.assertIsInstance(newCPSession, Wifiphisher_Captive_Portal_Session)
        self.assertEqual(self.sesh, newCPSession.session)
        print("     pass: test_WifiphisherCaptivePortalLaunch_Success")
        
    def test_WifiphisherCaptivePortalMonitor_Fail_NoSessions(self):
        """ cp launch """  
        req=HttpRequest()
        req.user=self.user 
        req.method="GET"
        resp = cp_views.wifiphisher_captive_portal_monitor(req, False, True)
        # no session, redirect
        self.assertIsInstance(resp, HttpResponse)
        self.assertEqual(resp.url, "/captive_portal_home/")
        print("     pass: test_WifiphisherCaptivePortalMonitor_Fail_NoSessions")
        
    def test_WifiphisherCaptivePortalMonitor_Success(self):
        """ cp monitor """  
        req=HttpRequest()
        req.user=self.user 
        req.method="GET"
        # set active session
        egSesh = Wifiphisher_Captive_Portal_Session.objects.filter(session=self.sesh).first()
        egSesh.active=True
        egSesh.save()
        ctx = cp_views.wifiphisher_captive_portal_monitor(req, False, True)
        # check correct instance retrieved
        self.assertEqual(ctx['monitor'], egSesh)
        print("     pass: test_WifiphisherCaptivePortalMonitor_Success")
        
    def test_WifiphisherCaptivePortalStop(self):
        """ cp stop """  
        req=HttpRequest()
        req.user=self.user 
        req.method="GET"
        # set active session
        egSesh = Wifiphisher_Captive_Portal_Session.objects.filter(session=self.sesh).first()
        egSesh.active=True
        egSesh.save()
        # request stop
        _ = cp_views.wifiphisher_captive_portal_stop(req, False, True, True)
        # check correct instance stopped
        egSesh.refresh_from_db()
        self.assertEqual(egSesh.active, False)
        print("     pass: test_WifiphisherCaptivePortalStop")
        
    def test_wifiphisherCaptivePortalResults(self):
        """ fetches results from id """  
        # first create results for session
        _, _ = self.prevCPUserCreds.update(dns_masq_path=TEST_DNS_MASQ_FILE_ABS_PATH, arp_results=TEST_ARP_RESULTS)
        # fetch request
        req=HttpRequest()
        req.user=self.user 
        req.method="GET"
        req.GET['session_id']=self.prevCPUserCreds.id
        ctx = cp_views.wifiphisher_captive_portal_results(req, False, True)
        creds=ctx['credentials']
        victims=ctx['victims']
        # check results as expected
        # Two victims, but only one credential
        self.assertEqual(1, len(creds))
        self.assertEqual(2, len(victims))
        # check credential unpacked properly and linked to victim
        cred=creds[0]        
        self.assertEqual("TestVictim1", cred.username)
        self.assertEqual("TestVictimPassword1", cred.password)
        victimdev=cred.device
        self.assertEqual("mac1", victimdev.mac_addr)
        self.assertEqual("1.2.3.4", victimdev.ip)
        print("     pass: test_wifiphisherCaptivePortalResults")
        
    def test_wifiphisherCaptivePortalPreviousCaptures(self):
        """ all previous cp sessions for user """
        # fetch request
        req=HttpRequest()
        req.user=self.user 
        req.method="GET"
        ctx = cp_views.wifiphisher_captive_portal_previous_captures(req, False, True)
        # class has two session
        self.assertEqual(len(ctx['historic_captures']), 2)
        print("     pass: test_wifiphisherCaptivePortalPreviousCaptures")
        
