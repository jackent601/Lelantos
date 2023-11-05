from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest
from django.contrib.auth import authenticate, login, logout 
from django.contrib import messages
from wp3_basic.models import Session, get_new_valid_session_id
from django.utils import timezone
from django.conf import settings
from wp3_broker.views import wp3_api_running

def login_user(request: HttpRequest):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        _user = authenticate(request, username=username, password=password)
        if _user is not None:
            # Login
            login(request, _user)
            
            # Create session
            _src_ip=request.META["REMOTE_ADDR"]
            _start_time=timezone.now()
            _session_id=get_new_valid_session_id()
            session=Session(user=_user, session_id=_session_id, src_ip=_src_ip, start_time=_start_time, active=True)
            session.save()  
            message=messages.success(request, f"logged in, session id: {_session_id}") 
            
            # Check Server
            if wp3_api_running():
                message=messages.success(request, "wp3 server is running") 
            else:
                message=messages.error(request, "wp3 server is not running, start server or check server config")
                        
            return redirect('home')
        else:
            message=messages.error(request, "Invalid login credentials.")
            return redirect('login')
    else:
        return render(request, "portal_auth/login.html")

def logout_user(request: HttpRequest):
    if request.user.is_authenticated:
        # Get user's active session
        _user = request.user
        qs = Session.objects.all().filter(user=_user, active=True)
        if len(qs) > 1:
            message=messages.error(request, "Multiple sessions were detected, all were closed")
        # Gracefully shutdown and move to inactive (not deleted to maintain audit log)
        for session in qs:
            print(session)
            session.active=False
            session.end_time=timezone.now()
            session.save()
            # TODO - shutdown wp3 jobs once made
        logout(request)
        message=messages.success(request, "logged out")
        return redirect('home')
    else:
        message=messages.error(request, "You are not logged in, cannot log out")
        return redirect('home')