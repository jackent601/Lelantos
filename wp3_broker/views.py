from django.shortcuts import render
from django.conf import settings
import socket

# Makes a call to expected wp3 api to check wp3 is 'alive'
def check_wp3_api_running(request):
    server_running=wp3_api_running()
    return render(request, "wp3_broker/server_health.html", {"server_healthy":server_running})
    
# Utils
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