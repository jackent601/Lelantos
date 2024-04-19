from django.contrib.auth.models import User
from lelantos_base.models import Location, Module_Session
from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand

# Settings
from lelantos.settings import BASE_DIR

# utils
import pandas as pd
import os

MOCK_DATA_USERNAME='mockData'
PATH_TO_MOCK_LOCATIONS=os.path.join(BASE_DIR, 'lelantos_base/mockData/locations.csv')
PATH_TO_DEMO_IMSI_RESULTS=os.path.join(BASE_DIR, 'lelantos_base/mockData/demoIMSIResults.csv')

def getMockDataUser()->User:
    """getMockDataUser"""
    return User.objects.get(username = MOCK_DATA_USERNAME)

def getLocationFromRow(row):
    """
    getLocationFromRow
    """
    # unpack
    _srid = row['srid']
    wkt = row['wkt']
    
    # create point
    locPoint=GEOSGeometry(f"{wkt}", srid=_srid)
    
    # get location object
    loc=Location.objects.filter(name=row['name'],location=locPoint,area=row['area'],remarks=row['remarks']).first()

    return loc
    
def createDemoIMSIFromIMSIRow(moduleSession, imsiRow):
    """takes a row from mock credentials and create django Credential_Result entry"""
    from lelantos_base.models import Demo_IMSI_Result
    imsi = Demo_IMSI_Result(module_session_captured=moduleSession, imsi=imsiRow['IMSI'])
    imsi.save()
    print(f"created demo imsi result: imsi={imsi.imsi}")

def addDemoIMSIData():
    mockLocations = pd.read_csv(PATH_TO_MOCK_LOCATIONS)  
    demoIMSIs = pd.read_csv(PATH_TO_DEMO_IMSI_RESULTS)

    for _, row in demoIMSIs.iterrows():
        
        # get location row from imsi row
        locId=row['locationNum']
        locRow=mockLocations.query('locationNum == @locId').iloc[0]
        loc=getLocationFromRow(locRow)
        
        # get session from row
        ms=Module_Session.objects.filter(location=loc, module_name='demo_IMSI').first()
        
        # Add IMSI
        createDemoIMSIFromIMSIRow(ms, row)
    
class Command(BaseCommand):
    help = "Creates mockData user with mockData populated"

    def handle(self, *args, **options):
        addDemoIMSIData()
        self.stdout.write(
            self.style.SUCCESS('Demo IMSI Data added for mockData User')
        )
        
            
    
    
    