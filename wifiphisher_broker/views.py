from django.shortcuts import render, redirect
from django.contrib import messages
# from django.utils import timezone
from portal_auth.views import get_session_from_request

from wifiphisher_broker.wifiphisher_config import PHISHING_SCENARIOS

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
    
    # Check current status
    # status, wphisher_session = get_current_wphisher_session()
    # wphisher_config["captive_portal_status"]=status 
    
    # Prepare Config
    wphisher_config={}
    # Interfaces
    interfaces = get_interfaces()
    if len(interfaces) == 0:
        message=messages.error(request, "No available interfaces for captive portal session, check platform")
        return redirect('home')   
    wphisher_config["interfaces"]=interfaces  
    
    # Scenarios
    scenarios = get_scenarios()
    if len(scenarios) == 0:
        message=messages.error(request, "No available scenarios for captive portal session, check platform")
        return redirect('home')   
    wphisher_config["scenarios"]=scenarios  
      
    return render(request, 'wifiphisher_broker/captive_portal_home.html', wphisher_config)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# UTILS - Devices
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
def get_interfaces()->[str]:
    """
    Lists interfaces appropriate for wifiphisher captive portal. While could be taken from aircrack_ng_broker
    separated in order to keep all packages self-contained dependency wise.
    """
    # TODO - implement properaly
    return ["wlan0", "wlan1"]

def get_scenarios()->[str]:
    """
    Lists scenarios available for wifiphisher captive portal. Declared in wifiphisher config
    TODO - Perhaps could be acertained from the tool itself?
    """
    # TODO - implement properaly
    return PHISHING_SCENARIOS.keys()

# def get_current_wphisher_session():