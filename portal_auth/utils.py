from django.shortcuts import redirect
from django.http import HttpRequest
from django.contrib import messages
from wp3_basic.models import Session, get_new_valid_session_id
from django.utils import timezone
from django.contrib.auth.models import User

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