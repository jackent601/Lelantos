from django.conf import settings
from django.utils import timezone

from wp3_basic.models import Session, Wp3_Authentication_Token

import socket
import base64 
import requests
import json

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

def get_wp3_api_auth_token(api_cfg=None)->(str, bool):
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

def get_and_set_wp3_api_auth_token_for_session(session: Session, api_cfg: map)->(Wp3_Authentication_Token, bool):
    """
    uses get_wp3_api_auth_token to get auth token and associates the session with this token to be used for requests
    returns
        token model - Wp3_Authentication_Token
        error       - bool
    """
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
    """
    utility to b64 encode username:password for get_wp3_api_auth_token
    """
    up_string=f'{username}:{password}'
    up_string_bytes=up_string.encode("utf-8") 
    up_base64_bytes=base64.b64encode(up_string_bytes) 
    up_base64=up_base64_bytes.decode("utf-8") 
    return up_base64 