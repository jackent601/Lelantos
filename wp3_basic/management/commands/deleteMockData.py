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

        
def clearMockData():
    """Delete user and all deletions cascade"""
    User.objects.get(username = MOCK_DATA_USERNAME).delete()
    print(f"deleted mock data user: {MOCK_DATA_USERNAME}")
    
class Command(BaseCommand):
    help = "Deletes mockData user with all associated (or added) mockData"

    def handle(self, *args, **options):
        clearMockData()
        self.stdout.write(
            self.style.SUCCESS(f'deleted mock data user: {MOCK_DATA_USERNAME}')
        )
        
            
    
    
    