from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone

from wp3_basic.models import Session, Wp3_Authentication_Token

import socket
import base64 
import requests
import json

# Makes a call to expected wp3 api to check wp3 is 'alive'
def check_wp3_api_running(request):
    if request.user.is_authenticated:
        config_and_status=get_wp3_api_config_map_from_settings(check_server_running=True)
        
        return render(request, "wp3_broker/server_health.html", config_and_status)
    else:
        message=messages.error(request, "You must be logged in to check wp3 server details")
        return redirect('home')
    
def refresh_wp3_api_auth_token_for_session(request):
    if not request.user.is_authenticated:
        message=messages.error(request, "You must be logged in to access wp3 scan")
        return redirect('home')
    
    # Get user active session to link to auth token
    _user = request.user
    _session = Session.objects.all().filter(user=_user, active=True).first()
    if _session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # TODO - what if these get temporarily overwritten?
    api_cfg=get_wp3_api_config_map_from_settings(True)
    new_token, _error = get_and_set_wp3_api_auth_token_for_session(_session, api_cfg)
    if _error:
        message=messages.error(request, "Failed retrieving wp3 authorization token, check server config")
        return render(request, "wp3_broker/server_health.html", api_cfg)
    issued_at_format=new_token.issued_at.strftime("%m/%d/%Y, %H:%M:%S")
    message=messages.success(request, f"Retrieved and set api token for session, issued at {issued_at_format}")
    return render(request, "wp3_broker/server_health.html", api_cfg)

# Utils
# Health
def wp3_api_running()->bool:
    # Unpack wp3 api settings
    wp3_api_ip=settings.WP3_API_IP
    wp3_api_port=settings.WP3_API_PORT
    
    # try to connect
    s = socket.socket()
    try:
        s.connect((wp3_api_ip, wp3_api_port))
    except socket.error as msg:
        return False
    else:
        return True

# Config
def get_wp3_api_config_map_from_settings(check_server_running=False)->map:
    config_map=settings.WP3_API_DEFAULT_CONFIG_MAP
    if check_server_running:
        server_running=wp3_api_running()
        config_map["server_running"]=server_running
    return settings.WP3_API_DEFAULT_CONFIG_MAP

# Gets wp3 api authorization using api config, returns token, error
def get_wp3_api_auth_token(api_cfg=None)->(str, bool):
    if api_cfg is None:
        api_cfg=get_wp3_api_config_map_from_settings(check_server_running=True)
    
    # username:password authorization
    up_base64=encode_up_combo_base64_ascii(api_cfg["wp3_api_username"], api_cfg["wp3_api_password"])
    auth_header={"Authorization":f"Basic {up_base64}"}
    
    # token service address
    base_addr=api_cfg["wp3_server_address"]
    token_extension=api_cfg["wp3_api_token_extension"]
    addr=f'{base_addr}{token_extension}'
    
    # get token 
    resp = requests.get(addr, headers=auth_header)
    if resp.status_code != 200:
        return "", True
    json_resp=json.loads(resp.text)
    return json_resp["token"], False 

# Gets ad Sets auth token returns (Wp3_Authentication_Token, error)
def get_and_set_wp3_api_auth_token_for_session(session: Session, api_cfg: map)->(Wp3_Authentication_Token, bool):
    # Get auth token to access
    _token, _error = get_wp3_api_auth_token(api_cfg)
    if _error:
        return None, True
    
    # create obj
    if hasattr(session, "wp3_authentication_token"):
        session.wp3_authentication_token.delete()
    wp3_auth_token=Wp3_Authentication_Token(session=session, token=_token, issued_at=timezone.now())
    wp3_auth_token.save()
    return wp3_auth_token, False
       

# wp3 takes 'username:password' base64 encoded to authenticate request to token service
def encode_up_combo_base64_ascii(username: str, password: str):
    up_string=f'{username}:{password}'
    up_string_bytes=up_string.encode("utf-8") 
    up_base64_bytes=base64.b64encode(up_string_bytes) 
    up_base64=up_base64_bytes.decode("utf-8") 
    return up_base64 