from django.shortcuts import render, redirect
from django.contrib import messages
# from django.conf import settings
# from django.utils import timezone

from aircrack_ng_broker.models import *
from portal_auth.views import get_session_from_request

# import glob, os, datetime, time, subprocess

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# VIEWS
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 

# HOME
def wifiphisher_captive_portal_home(request):
    # Auth
    active_session, _redirect, _error = get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Devices
    message=messages.error(request, "Captive portal not yet implemented")
    return redirect('home')
