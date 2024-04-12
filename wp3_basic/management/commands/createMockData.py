from django.contrib.auth.models import User
from wp3_basic.models import Session, Location, get_new_valid_session_id
from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand, CommandError

# Settings
from wp3_portal.settings import BASE_DIR

# utils
from django.utils import timezone
import pandas as pd
import os

MOCK_DATA_USERNAME='mockData'
MOCK_DATA_PASSWORD='mockData'
MOCK_DATA_EMAIL='mockData@mockData.com'
PATH_TO_MOCK_LOCATIONS=os.path.join(BASE_DIR, 'wp3_basic/mockData/locations.csv')

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
    
def createMockSessionsAndLocations(user: User):
    mockData = pd.read_csv(PATH_TO_MOCK_LOCATIONS)
    
    currentSessionID = None
    _session = None
    
    for index, row in mockData.iterrows():
        
        # check if need to create new session
        sessionID = row['sessionNum']
        if currentSessionID != sessionID:
            
            # close old one 
            if _session is not None:
                _session.active=False
                _session.end_time=timezone.now()
                _session.save()
                print(f"closed previous session: {_session}")
            
            # create new
            _session = Session(user=user,
                               session_id=get_new_valid_session_id(),
                               start_time=timezone.now(),
                               src_ip = "x.x.x.x",
                               active = True)
            _session.save()
            print(f"created new session: {_session}")
            
            # update
            currentSessionID=sessionID
        
        # unpack
        _srid = row['srid']
        wkt = row['wkt']
        _name = row['name']
        _area = row['area']
        _remarks = row['remarks']
        
        # create point
        locPoint=GEOSGeometry(f"{wkt}", srid=_srid)
        
        # create location object
        loc=Location(session=_session, 
                     name=_name,
                     location=locPoint,
                     area=_area, 
                     remarks=_remarks)
        loc.save()
        print(f"created location: {wkt}, srid={_srid}")
        
def clearMockData():
    """Delete user and all deletions cascade"""
    User.objects.get(username = MOCK_DATA_USERNAME).delete()
    print(f"deleted mock data user: {MOCK_DATA_USERNAME}")
    
        
def createMockData():
    user = createMockDataUser()
    createMockSessionsAndLocations(user)
    print("Mock Data Initialised")
    
class Command(BaseCommand):
    help = "Creates mockData user with mockData populated"

    def handle(self, *args, **options):
        user = createMockDataUser()
        createMockSessionsAndLocations(user)
        print("Mock Data Initialised")
        self.stdout.write(
            self.style.SUCCESS('Mock Data User Created (username:mockData, password:mockData) with mock data initialised')
        )
        
            
    
    
    