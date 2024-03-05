import json
from django.shortcuts import render, redirect
from django.contrib import messages
import requests

from wp3_basic.models import Session
import portal_auth.utils as auth_utils
import wp3_broker.utils as wp3_api_utils

# Makes a call to expected wp3 api to check wp3 is 'alive'
def check_wp3_api_running(request):
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wp3 scan")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    config_and_status=wp3_api_utils.get_wp3_api_config_map_from_settings(check_server_running=True)    
    if hasattr(active_session, "wp3_authentication_token"):
        config_and_status["api_token"]=active_session.wp3_authentication_token.token
        issued_at_format=active_session.wp3_authentication_token.issued_at.strftime("%m/%d/%Y, %H:%M:%S")
        config_and_status["api_token_issued_at"]=issued_at_format
    
    config_and_status["session"]=active_session
    return render(request, "wp3_broker/server_health.html", config_and_status)

    
def refresh_wp3_api_auth_token_for_session(request):
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wp3 scan")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Refrsh token
    # TODO - what if these get temporarily overwritten?
    api_cfg=wp3_api_utils.get_wp3_api_config_map_from_settings(True)
    new_token, _error = wp3_api_utils.request_and_set_wp3_api_auth_token_for_session(active_session, api_cfg)
    if _error:
        message=messages.error(request, "Failed retrieving wp3 authorization token, check server config")
        return redirect('wp3_server_health')
    issued_at_format=new_token.issued_at.strftime("%m/%d/%Y, %H:%M:%S")
    message=messages.success(request, f"Retrieved and set api token for session, issued at {issued_at_format}")
    return redirect('wp3_server_health')

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# AP CONFIG
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
def wp3_ap_config(request):
    # Handle Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wp3 info")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    api_cfg=wp3_api_utils.get_wp3_api_config_map_from_settings(True)
    resp, _redirect, _error = wp3_api_utils.request_wp3_ap_config(request, active_session, api_cfg)
    if _redirect is not None:
        return _redirect
    if _error:
        # errored but got response, token may be expired
        message=messages.error(request, "Server reachable but could not retrieve AP config, token may have expired, try refreshing")
        message=messages.error(request, f"AP Config request response code: {resp.status_code}, text: {resp.text}")
        return redirect('wp3_server_health')

    return render(request, 'wp3_broker/ap.html', {"ap_config":resp})

def start_wp3_rest_server(request):
    # Handle Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to start wp3")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    msg, success = wp3_api_utils.start_wp3_rest(active_session)
    if success:
        message=messages.success(request, msg)
        return redirect('wp3_server_health')
    else:
        message=messages.error(request, msg)
        return redirect('wp3_server_health') 
