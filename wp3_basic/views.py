from django.shortcuts import render
from django.http import HttpResponse, HttpRequest
from django.utils import timezone
from . import models 

def index(request: HttpRequest):
    _src_ip=request.META["REMOTE_ADDR"]
    _start_time=timezone.now()
    _session_id=models.get_new_valid_session_id()
    
    s=models.ActiveSession(session_id=_session_id, src_ip=_src_ip, start_time=_start_time)
    #s.save()
    
    # _resp=f"Creating new active session with the following -> {s}"
    return render(request, "wp3_basic/home.html", {"session":s})
