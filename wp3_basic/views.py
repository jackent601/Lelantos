from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest
from django.utils import timezone
from django.contrib import messages
from .models import Location 
from .forms import LocationEntryForm
import portal_auth.utils as auth_utils


def home(request: HttpRequest):
    return render(request, "wp3_basic/home.html")

def addLocation(request: HttpRequest):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access locations")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Form
    if request.method == 'POST':
        form = LocationEntryForm(request.POST)
        
        if not form.is_valid():
            message=messages.error(request, "Invalid form submission. Ensure a location is selected")
            return render(request, "wp3_basic/addLocation.html", {"form": LocationEntryForm()})
            
        new_place = Location(
            session = active_session,
            name = request.POST['locationName'],
            location = request.POST['location'],
            area = request.POST['area'],
            remarks = request.POST['remarks']
            )
        new_place.save()
        print("SAVED!")
        return render(request, "wp3_basic/home.html")
    else:
        return render(request, "wp3_basic/addLocation.html", {"form": LocationEntryForm()})
