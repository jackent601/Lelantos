from django.shortcuts import render, redirect
from django.http import HttpRequest
from django.contrib.auth import authenticate, login, logout 
from django.contrib import messages
from lelantos_base.models import Session, Module_Session
from django.utils import timezone

from lelantos_base.management.commands.createMockData import MOCK_DATA_USERNAME

import portal_auth.utils as auth_utils



def login_user(request: HttpRequest, include_messages=True):
    # Catch first visit
    if request.method != "POST":
        return render(request, "portal_auth/login.html")
    
    # Handle login
    username = request.POST["username"]
    password = request.POST["password"]
    _user = authenticate(request, username=username, password=password)
    
    # Catch invalid creds
    if _user is None:
        if include_messages:
            message=messages.error(request, "Invalid login credentials.")
        return redirect('login')
    
    # Log user in & add home-screen message
    login(request, _user)
    _ = auth_utils.start_new_session_for_user(request, _user)
    if include_messages:
        message=messages.success(request, "login succesful, please set session location")
    
    # redirect based on user
    if _user.username==MOCK_DATA_USERNAME:
        return redirect('home')
    else:
        return redirect('setLocation')



def logout_user(request: HttpRequest, include_messages=True):
    if request.user.is_authenticated:
        # Get user's active session
        _user = request.user
        qs = Session.objects.all().filter(user=_user, active=True)
        if len(qs) > 1:
            if include_messages:
                message=messages.error(request, "Multiple sessions were detected, all were closed")
        # Gracefully shutdown and move to inactive (not deleted to maintain audit log)
        for session in qs:
            # Shutdown all possile module processes running
            moduleSessions=Module_Session.objects.all().filter(session=session, active=True)
            for s in moduleSessions:
                ended=s.end_module_session()
                if ended:
                    if include_messages:
                        message=messages.success(request, f"Stopped module (pid: {s.pid})")
                else:
                    if include_messages:
                        message=messages.error(request, 
                                           f"Failed to stop module (pid: {s.pid}), process may have had faulty start, or need manual shutdown")
            
            # End session
            session.active=False
            session.end_time=timezone.now()
            session.save()
        logout(request)
        timestamp=timezone.now().strftime("%m/%d/%Y - %H:%M:%S")
        if include_messages:
            message=messages.success(request, f"logged out, {timestamp}")
        return redirect('home')
    else:
        if include_messages:
            message=messages.error(request, "You are not logged in, cannot log out")
        return redirect('home')
    
        
    