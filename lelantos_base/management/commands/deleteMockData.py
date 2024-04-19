from django.contrib.auth.models import User
from lelantos_base.models import Session, Location, get_new_valid_session_id
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

        
def clearMockData():
    """Delete user and all deletions cascade"""
    User.objects.get(username = MOCK_DATA_USERNAME).delete()
    print(f"deleted mock data user: {MOCK_DATA_USERNAME}")
    
def clearMockDataKeepUser():
    """Deletes content of user but keeps user"""
    mockUser=User.objects.get(username = MOCK_DATA_USERNAME)
    Location.objects.filter(session__user=mockUser)
    for loc in Location.objects.filter(session__user=mockUser):
        loc.delete()
    print(f"deleted mock data for user: {MOCK_DATA_USERNAME}")
    
class Command(BaseCommand):
    help = "Deletes mockData user with all associated (or added) mockData"
    
    def add_arguments(self, parser):

        # Named (optional) arguments
        parser.add_argument(
            "--keepUser",
            action="store_true",
            help="keeps the mock data user",
        )

    def handle(self, *args, **options):
        if options['keepUser']:
            clearMockDataKeepUser()
            self.stdout.write(
                self.style.SUCCESS(f'deleted mock data user: {MOCK_DATA_USERNAME} but kept user')
            )
        else:
            clearMockData()
            self.stdout.write(
                self.style.SUCCESS(f'deleted mock data user: {MOCK_DATA_USERNAME}')
            )
        
            
    
    
    