from django.contrib.auth.models import User
from lelantos_base.models import Session, Location, Module_Session, get_new_valid_session_id
from wifiphisher_broker.models import Wifiphisher_Captive_Portal_Session, Device_Instance, Credential_Result
from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand, CommandError

# Settings
from lelantos.settings import BASE_DIR

# utils
from django.utils import timezone
import pandas as pd
import os

MOCK_DATA_USERNAME='mockData'
MOCK_DATA_PASSWORD='mockData'
MOCK_DATA_EMAIL='mockData@mockData.com'
PATH_TO_MOCK_LOCATIONS=os.path.join(BASE_DIR, 'lelantos_base/mockData/locations.csv')
PATH_TO_MOCK_MODULE_SESSIONS=os.path.join(BASE_DIR, 'lelantos_base/mockData/moduleSessions.csv')
PATH_TO_MOCK_CREDENTIALS=os.path.join(BASE_DIR, 'lelantos_base/mockData/credentialResults.csv')
PATH_TO_MOCK_DEVICES=os.path.join(BASE_DIR, 'lelantos_base/mockData/deviceResults.csv')
PATH_TO_DEMO_IMSI_RESULTS=os.path.join(BASE_DIR, 'lelantos_base/mockData/demoIMSIResults.csv')

def createMockDataUser()->User:
    # Check if exists
    user=User.objects.filter(username=MOCK_DATA_USERNAME).first()
    if user is not None:
        print(f'mock user already exists, name: {user.username}')
        return user
    
    # Create
    user = User.objects.create_user(username=MOCK_DATA_USERNAME,
                                    email=MOCK_DATA_EMAIL,
                                    password=MOCK_DATA_PASSWORD)
    user.save()
    print(f"created mock user, name: {user.username}, password: mockData")
    return user

def updateSessionForLocation(user, locationRow, currentSessionID, currentSession):
    """if new session detected (or no session detected) closes current one and creates new session"""
    # check if need to create new session
    sessionID = locationRow['sessionNum']
    if currentSessionID != sessionID:
        
        # close old one 
        if currentSession is not None:
            currentSession.active=False
            currentSession.end_time=timezone.now()
            currentSession.save()
            # print(f"closed previous session: {currentSession}")
        
        # create new
        currentSession = Session(user=user,
                            session_id=get_new_valid_session_id(),
                            start_time=timezone.now(),
                            src_ip = "x.x.x.x",
                            active = True)
        currentSession.save()
        print(f"created new session: {currentSession}")
        
        # update
    return sessionID, currentSession

def createLocationFromRow(session, row):
    """
    takes a row from mock data locations and creates django location entry. 
    Also returns location ID in case location is associated with module sessions
    """
    # unpack
    _srid = row['srid']
    wkt = row['wkt']
    _locId = row['locationNum']
    
    # create point
    locPoint=GEOSGeometry(f"{wkt}", srid=_srid)
    
    # create location object
    loc=Location(session=session, 
                    name=row['name'],
                    location=locPoint,
                    area=row['area'], 
                    remarks=row['remarks'])
    loc.save()
    print(f"\tcreated location: {loc.name}, srid={_srid}")
    return loc, _locId 

def createModuleSessionFromRow(moduleSessionRow, currentSession, loc):
    """
    takes a row from mock data module sessions and creates django ModuleSession entry. 
    Determines specific module from name to create child model
    returns django model and moduleSessionID in case results are associated with session
    """
    # unpack
    msName=moduleSessionRow['module_name']
    msId=moduleSessionRow['moduleSessionNum']
    # create mock session, based on type (all inherit from base class)
    if msName == "wifiphisher_captive_portal":
        # wifiphisher session
        wpSession=Wifiphisher_Captive_Portal_Session(session=currentSession,
                                                        location=loc,
                                                        module_name=msName,
                                                        start_time=timezone.now(),
                                                        end_time=timezone.now(),
                                                        active=False,
                                                        interface=moduleSessionRow['interface'],
                                                        scenario=moduleSessionRow['scenario'],
                                                        essid=moduleSessionRow['essid'],
                                                        cred_type=moduleSessionRow['cred_type'])
        wpSession.save()
        print(f"\t\tcreated module session: {wpSession.module_name}")
        return wpSession, msId
    else:
        ms=Module_Session(session=currentSession,
                            location=loc,
                            module_name=msName,
                            start_time=timezone.now(),
                            end_time=timezone.now(),
                            active=False)
        ms.save()
        print(f"\t\tcreated module session: {ms.module_name} ")
        return ms, msId

def createDeviceFromRow(moduleSession, device):
    """
    takes a row from mock data devices and creates django Device_Instance entry. 
    returns django model and deviceId in case credential results are associated with device
    """
    dev=Device_Instance(
        module_session_captured=moduleSession,
        mac_addr=device['mac_addr'],
        ip=device['ip'],
        private_ip=device['private_ip'],
        type=device['type'],
        first_seen=device['first_seen'],
    )
    dev.save()
    print(f"\t\t\tcreated device instance: ip={dev.ip}, mac={dev.mac_addr}")
    return dev, device['deviceNum']

def createCredentialResultFromRow(moduleSession, dev, credential):
    """takes a row from mock credentials and create django Credential_Result entry"""
    cred = Credential_Result(
        module_session_captured=moduleSession,
        device=dev,
        type=credential['type'],
        username=credential['username'],
        password=credential['password'],
        capture_time=timezone.now()
    )
    cred.save()
    print(f"\t\t\t\tcreated credential result: type={cred.type}, username={cred.username}, password={cred.password}")
    
def createDemoIMSIFromIMSIRow(moduleSession, imsiRow):
    """takes a row from mock credentials and create django Credential_Result entry"""
    from lelantos_base.models import Demo_IMSI_Result
    imsi = Demo_IMSI_Result(module_session_captured=moduleSession, imsi=imsiRow['IMSI'])
    imsi.save()
    print(f"\t\t\tcreated demo imsi result: imsi={imsi.imsi}")

def createMockDataFromUser(user: User, loadDemoImsi=False):
    mockLocations = pd.read_csv(PATH_TO_MOCK_LOCATIONS)
    mockModuleSessions = pd.read_csv(PATH_TO_MOCK_MODULE_SESSIONS)
    mockDevices = pd.read_csv(PATH_TO_MOCK_DEVICES)
    mockCredentials = pd.read_csv(PATH_TO_MOCK_CREDENTIALS)
    if loadDemoImsi:
        demoIMSIs = pd.read_csv(PATH_TO_DEMO_IMSI_RESULTS)
        print(demoIMSIs)
    
    currentSessionID = None
    currentSession = None
    
    for _, row in mockLocations.iterrows():
        
        # update session 
        currentSessionID, currentSession = updateSessionForLocation(user, row, currentSessionID, currentSession)

        # Create New Location
        loc, locId = createLocationFromRow(currentSession, row)
        
        # create any module sessions for this location
        for _, _moduleSession in mockModuleSessions.query('locationNum == @locId').iterrows():
            ms, msId = createModuleSessionFromRow(_moduleSession, currentSession, loc)
            
            # create any device instances associated with module session
            for _, device in mockDevices.query('moduleSessionNum == @msId').iterrows():
                dev, devId = createDeviceFromRow(ms, device)
                
                # create any credential results associated with device instance
                for _, credential in mockCredentials.query('deviceNum == @devId').iterrows():
                    credResult = createCredentialResultFromRow(ms, dev, credential)
            
            # if demo-ing create ismi results at this loaction
            if loadDemoImsi:
                for _, imsiResult in demoIMSIs.query('moduleSessionNum == @msId').iterrows():
                    createDemoIMSIFromIMSIRow(ms, imsiResult)

def clearMockData():
    """Delete user and all deletions cascade"""
    User.objects.get(username = MOCK_DATA_USERNAME).delete()
    print(f"deleted mock data user: {MOCK_DATA_USERNAME}")
    
        
def createMockData(includeIMSI):
    user = createMockDataUser()
    createMockDataFromUser(user, includeIMSI)
    print("Mock Data Initialised")
    
class Command(BaseCommand):
    help = "Creates mockData user with mockData populated"

    def add_arguments(self, parser):

        # Named (optional) arguments
        parser.add_argument(
            "--includeDemoIMSI",
            action="store_true",
            help="include demo imsi data",
        )

    def handle(self, *args, **options):
        createMockData(options['includeDemoIMSI'])
        self.stdout.write(
            self.style.SUCCESS('Mock Data User Created (username:mockData, password:mockData) with mock data initialised')
        )
        
            
    
    
    