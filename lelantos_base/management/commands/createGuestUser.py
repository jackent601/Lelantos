from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

DEFAULT_USERNAME='guest'
DEFAULT_PASSWORD='guest'
DEFAULT_EMAIL='guest@guest.com'

def createDefaultUser()->User:
    # Check if exists
    user=User.objects.filter(username=DEFAULT_USERNAME).first()
    if user is not None:
        print(f'default user already exists, name: {user.username}')
        return user
    
    # Create
    user = User.objects.create_user(username=DEFAULT_USERNAME,
                                    email=DEFAULT_EMAIL,
                                    password=DEFAULT_PASSWORD)
    user.save()
    print(f"created default user, name: {user.username}, password: guest")
    return user

class Command(BaseCommand):
    help = "Creates guest user for app"

    def handle(self, *args, **options):
        createDefaultUser()
        self.stdout.write(
            self.style.SUCCESS('guest user ready')
        )
        
            
    
    
    