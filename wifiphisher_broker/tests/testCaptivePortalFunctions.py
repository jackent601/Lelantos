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
import wifiphisher_broker.config as wp_cfg

TEST_LOG_REL_PATH="wifiphisher_broker/tests/testdataLog.log"
TEST_LOG_ABS_PATH=os.path.join(settings.BASE_DIR, TEST_LOG_REL_PATH)
TEST_CRED_LOG_REL_PATH="wifiphisher_broker/tests/testdataCredLog.log"
TEST_CRED_LOG_ABS_PATH=os.path.join(settings.BASE_DIR, TEST_CRED_LOG_REL_PATH)

def copyTestLogData(path):
    """ copies what would be captive portal log to filepath """
    copyfile(TEST_LOG_ABS_PATH, path)
    
def copyTestCredLogData(path):
    """ copies what would be captive portal credential log to filepath """
    copyfile(TEST_CRED_LOG_ABS_PATH, path)
    
def copyCPLogsFromObj(cpObj):
    """ Using paths generated on session object copies data to expected locations """
    copyTestLogData(cpObj.log_file_path)
    copyTestCredLogData(cpObj.cred_file_path)

def captivePortalPrep(cls):
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
    # Captive Portal Session
    log_path, cred_path = cp_utils.get_new_log_paths("TestInterface", wp_cfg.OAUTH_LOGIN, "TestEssid") 
    cls.prevCP = Wifiphisher_Captive_Portal_Session.objects.create(session=cls.sesh, 
                                                                   location=cls.loc, 
                                                                   start_time=timezone.now(), 
                                                                   active=False,
                                                                   interface="TestInterface",
                                                                   essid="TestEssid",
                                                                   scenario=wp_cfg.OAUTH_LOGIN,
                                                                   cred_type=wp_cfg.CRED_TYPE_USER,
                                                                   log_file_path=log_path,
                                                                   cred_file_path=cred_path)
    copyCPLogsFromObj(cls.prevCP)


class WifiPhisherBroker_TestCase(TestCase):
    """
    Aircrack-ng's wrapper functions
    """
    @classmethod
    def setUpTestData(cls):
        print("WifiPhisherBroker_TestCase- - - - - - - - - - - - - - - - - - - - - -")
        captivePortalPrep(cls)
        
    def test_getPreviousScans_Success(self):
        """ retrieve previous scans from request user context """
        # get base response
        print(self.prevCP.__dict__)
        print("     pass: test_getPreviousScans_Success")
        
  