from django.shortcuts import render, redirect
from django.http import HttpRequest
from django.contrib.auth import authenticate, login, logout 
from django.contrib import messages
from wp3_basic.models import Session, get_new_valid_session_id
from django.utils import timezone
from django.contrib.auth.models import User

from wp3_broker.utils import wp3_api_running

def login_user(request: HttpRequest):
    # Catch first visit
    if request.method != "POST":
        return render(request, "portal_auth/login.html")
    
    # Handle login
    username = request.POST["username"]
    password = request.POST["password"]
    _user = authenticate(request, username=username, password=password)
    
    # Catch invalid creds
    if _user is None:
        message=messages.error(request, "Invalid login credentials.")
        return redirect('login')
    
    login(request, _user)
    new_session = start_new_session_for_user(request, _user)
    started_at=new_session.start_time.strftime("%m/%d/%Y - %H:%M:%S")
    message=messages.success(request, f"logged in, session id: {new_session.session_id}, started: {started_at}") 
    
    # Check Server
    if wp3_api_running():
        message=messages.success(request, "wp3 server is running") 
    else:
        message=messages.error(request, "wp3 server is not running, start server or check server config")
    return redirect('home')



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
        timestamp=timezone.now().strftime("%m/%d/%Y - %H:%M:%S")
        message=messages.success(request, f"logged out, {timestamp}")
        return redirect('home')
    else:
        message=messages.error(request, "You are not logged in, cannot log out")
        return redirect('home')
    
    
# Utils
def get_session_from_request(request: HttpRequest, error_msg="You must be logged in to access this"):
    """
    gets all active sessions associated with a user from request
    return:
        Session                - session, if found
        HttpResponse(Redirect) - optional, if session invalid
        Bool                   - error, if invalid
    """
    # Catch Invalid
    if not request.user.is_authenticated:
        message=messages.error(request, error_msg)
        return None, redirect('home'), True
    
    # Valid user, get session
    active_sessions = Session.objects.all().filter(user=request.user, active=True).first()
    return active_sessions, None, False

def start_new_session_for_user(request: HttpRequest, user: User)->Session:
    """
    Creates a new session for a user from a request. Also sets any existing session to inactive.
    A user should only ever have 1 active session at a time
    returns:
        Session    - None if error
    """
    # Close existing sessions
    qs = Session.objects.all().filter(user=user, active=True)
    if len(qs) > 0:
        for session in qs:
            session.active=False
            session.end_time=timezone.now()
            session.save()
    # Now create new sessions
    _src_ip=request.META["REMOTE_ADDR"]
    _start_time=timezone.now()
    _session_id=get_new_valid_session_id()
    session=Session(user=user, session_id=_session_id, src_ip=_src_ip, start_time=_start_time, active=True)
    session.save()  
    return session
    
        
    