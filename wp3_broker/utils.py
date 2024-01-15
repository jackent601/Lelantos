from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from wp3_basic.models import Session, Wp3_Authentication_Token, Wp3_Rest_Session
from wp3_broker.wp3_api_config import WP3_SERVER_START_WAIT_TIME

import socket
import base64 
import requests
import json
import subprocess
import time

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# SERVER
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
def wp3_api_running()->bool:
    """
    Using global django settings (which uses settings defined in wp3_api_config.py) check if wp3 api server is running
    checks by attempting to open a socket to server
    returns
        bool - success
    """
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

def get_wp3_api_config_map_from_settings(check_server_running=False)->map:
    """
    returns wp3 api config map defined in global django settings (which uses settings defined in wp3_api_config.py)
    """
    config_map=settings.WP3_API_DEFAULT_CONFIG_MAP
    if check_server_running:
        server_running=wp3_api_running()
        config_map["server_running"]=server_running
    return settings.WP3_API_DEFAULT_CONFIG_MAP

def start_wp3_rest(session: Session, api_cfg=None)->(str, bool):
    # Check if already running
    if wp3_api_running():
        return "Server already running", True
    
    # Check if already an active session (which may have failed)
    failed_wp3_session = Wp3_Rest_Session.objects.all().filter(session=session, active=True)
    for failed_wp3 in failed_wp3_session:
        # TODO - log result
        failed_wp3.end_rest_session()
    
    if api_cfg is None:
        api_cfg=get_wp3_api_config_map_from_settings(check_server_running=False)
    
    # Start Server in background
    rest_server=subprocess.Popen(["sudo",
                                  "wp3",
                                  "--rest", 
                                  "--password",
                                  api_cfg["wp3_api_password"],
                                  "--username",
                                  api_cfg["wp3_api_username"]],
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    
    # Create wp3 session object
    wpS = Wp3_Rest_Session(session=session,
                           start_time=timezone.now(),
                           active=True,
                           pid=rest_server.pid)
    wpS.save()
    
    # Wait and check running
    time.sleep(WP3_SERVER_START_WAIT_TIME)
    if wp3_api_running():
        return "Started wp3 server", True
    else:
        err_msg = str(rest_server.stderr)
        out_msg = str(rest_server.stdout)
        return_err_msg = f'could not start server. stderr: {err_msg}, stdout: {out_msg}'
        return return_err_msg, False


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# API AUTH TOKEN
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
def request_wp3_api_auth_token(api_cfg=None)->(str, bool):
    """
    Retrieves an api authentication token from wp3 using username password combo defined in map passed
    map must have:
        wp3_api_username
        wp3_api_password
        wp3_server_address
        wp3_api_token_extension
    returns:
        token - str
        errpr - bool
    """
    if not wp3_api_running():
        return "", True
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

def request_and_set_wp3_api_auth_token_for_session(session: Session, api_cfg: map)->(Wp3_Authentication_Token, bool):
    """
    Uses get_wp3_api_auth_token to get auth token and associates the session with this token to be used for requests.
    Used to force an api token refresh
    returns
        token model - Wp3_Authentication_Token
        error       - bool
    """
    if not wp3_api_running():
        return "", True
    
    # Get auth token to access
    _token, _error = request_wp3_api_auth_token(api_cfg)
    if _error:
        return None, True
    
    # create obj
    if hasattr(session, "wp3_authentication_token"):
        session.wp3_authentication_token.delete()
    wp3_auth_token=Wp3_Authentication_Token(session=session, token=_token, issued_at=timezone.now())
    wp3_auth_token.save()
    return wp3_auth_token, False

def handle_wp3_api_token(request: HttpRequest, session: Session, api_cfg: map)->(Wp3_Authentication_Token, bool):
    """
    Attempts to retrieve api token associated with session. If none found requests one from wp3 server
    """
    # Check if token set
    token = get_api_token_from_session(session)
    if token is not None:
        return token, False
    
    # Not set, request & set one
    token, _error = request_and_set_wp3_api_auth_token_for_session(session, api_cfg)
    if _error:
        message=messages.error(request, "Failed retrieving wp3 authorization token, check server config")
        return None, True
    
    issued_at_format=token.issued_at.strftime("%m/%d/%Y, %H:%M:%S")
    message=messages.success(request, f"Retrieved and set api token for session, issued at {issued_at_format}")
    return token, False


# wp3 takes 'username:password' base64 encoded to authenticate request to token service
def encode_up_combo_base64_ascii(username: str, password: str):
    """
    utility to b64 encode username:password for get_wp3_api_auth_token
    """
    up_string=f'{username}:{password}'
    up_string_bytes=up_string.encode("utf-8") 
    up_base64_bytes=base64.b64encode(up_string_bytes) 
    up_base64=up_base64_bytes.decode("utf-8") 
    return up_base64 

def get_api_token_from_session(session: Session):
    """
    Retrieves api auth token associated with session, returns none if non associated
    """
    if hasattr(session, "wp3_authentication_token"):
        return session.wp3_authentication_token
    else: 
        return None
    
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# AP CONFIG
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
def request_wp3_ap_config(request: HttpRequest, session: Session, api_cfg: map)->(any, HttpResponse, bool):
    """
    If server is running fetches AP config using auth token (requests token if not present). 
    api cnf passed must have:
        wp3_server_address
        wp3_api_ap_config_extension
    returns:
        response       - json if successful, resp if unsuccesful request, None if server or token invalid
        HttpResponse   - redirect if issues with server
        error          - bool
    """
    # Check server running
    if not wp3_api_running():
        message=messages.error(request, "wp3 Server not reachable, check config/status")
        return None, redirect('wp3_server_health'), True
    
    # Handle Api Token
    token, _error=handle_wp3_api_token(request, session, api_cfg)
    if _error:
        # handle_wp3_api_token adds error message automatically
        return None, redirect('wp3_server_health'), True
    
    # Get AP config from server
    auth_header={"x-access-token":f"{token.token}"}
    
    # AP config address
    base_addr=api_cfg["wp3_server_address"]
    ap_config_extension=api_cfg["wp3_api_ap_config_extension"]
    addr=f'{base_addr}{ap_config_extension}'
    
    # get token 
    resp = requests.get(addr, headers=auth_header)
    if resp.status_code != 200:
        return resp, None, True
    json_resp=json.loads(resp.text)
    return json_resp, None, False
