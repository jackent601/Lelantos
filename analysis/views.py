from django.shortcuts import render, redirect
from django.http import HttpRequest
from django.contrib.auth import authenticate, login, logout 
from django.contrib import messages
from wp3_basic.models import Session, get_new_valid_session_id, Module_Session
from django.utils import timezone
from django.contrib.auth.models import User

import portal_auth.utils as auth_utils
from analysis.forms import LocationAnalysisForm

# Create your views here.
def analysis_home(request):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    message=messages.success(request, "Analysis!")
    # return redirect('home')
    return render(request, "analysis/analysis.html", {"form": LocationAnalysisForm()})
    
