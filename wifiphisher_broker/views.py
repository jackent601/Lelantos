from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
import portal_auth.utils as auth_utils

# Models
from wifiphisher_broker.models import Wifiphisher_Captive_Portal_Session, get_current_wphisher_sessions

import wifiphisher_broker.config as cnf
import utils.utils as gen_utils
import wifiphisher_broker.utils as wph_utils
import subprocess


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# VIEWS
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 

# HOME
def wifiphisher_captive_portal_home(request, include_messages=True, ctx_only=False, testcase=False):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to run captive portals")
    if _error:
        return _redirect
    if active_session is None:
        if include_messages:
            message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Location
    location = active_session.getMostRecentLocation()
    if location is None:
        if include_messages:
            message=messages.error(request, "Warning: Must set location before running exploits")
        return redirect('setLocation')
    
    wphisher_context={}
    
    # Check if portal already running
    status, _ = get_current_wphisher_sessions(active_session)
    if status:
        if include_messages:
            message=messages.success(request, "Live captive portal session found")
        # return wifiphisher_captive_portal_monitor(request)
        return redirect('captive_portal_monitor')
    
    # Launch Form      
    wphisher_context["captive_portal_status"]=status 

    # Interfaces
    interfaces = gen_utils.get_wifi_interfaces(testcase)
    if len(interfaces) == 0:
        if include_messages:
            message=messages.error(request, "No available interfaces for captive portal session, check platform")
        return redirect('home')   
    wphisher_context["interfaces"]=interfaces  
    
    # Scenarios
    scenarios = wph_utils.get_scenarios()
    if len(scenarios) == 0:
        if include_messages:
            message=messages.error(request, "No available scenarios for captive portal session, check platform")
        return redirect('home')   
    wphisher_context["scenarios"]=scenarios          
    
    # Get historic captures
    wphisher_context["historic_captures"]=Wifiphisher_Captive_Portal_Session.objects.filter(session__user=active_session.user).order_by('-start_time')
    if ctx_only:
        return wphisher_context
    return render(request, 'wifiphisher_broker/captive_portal_home.html', wphisher_context)

# LAUNCH
def wifiphisher_captive_portal_launch(request, include_messages=True, ctx_only=False):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to run captive portals")
    if _error:
        return _redirect
    if active_session is None:
        if include_messages:
            message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Location
    location = active_session.getMostRecentLocation()
    if location is None:
        if include_messages:
            message=messages.error(request, "Warning: Must set location before running exploits")
        return redirect('setLocation')
    
    # Not a post, scan not submitted, show most recent results
    if request.method != "POST":
        # Message to warn not recent
        if include_messages:
            message=messages.error(request, "Captive Portal details not provided, please submit launch form")
        return redirect('captive_portal_home')
    
    # Check no sessions already running
    status, _ = get_current_wphisher_sessions(active_session)
    if status:
        if include_messages:
            message=messages.error(request, "Captive Portal session(s) already detected! Can not launch another, please end current session first.")
        return redirect('captive_portal_monitor')
    
    # Unpack post req
    interface=str(request.POST['interface'])
    scenario=str(request.POST['scenario'])
    valid_scenarios=wph_utils.get_scenarios()
    if scenario not in valid_scenarios:
        if include_messages:
            message=messages.error(request, f"Scenario: {scenario} not valid, please select valid scenario.")
        return redirect('captive_portal_home')
    essid=str(request.POST['essid'])   
    cred_type = cnf.SCENARIO_CRED_TYPES[scenario]
    
    # Launch process!
    log_path, cred_path = wph_utils.get_new_log_paths(interface, scenario, essid) 
    if ctx_only:
        cp_pid=123456789
    else:
        captive_portal=subprocess.Popen(["sudo",
                                        "wifiphisher",
                                        "-aI", 
                                        interface,
                                        "-kN",
                                        "-nE",
                                        "-dK",
                                        "-e",
                                        essid,
                                        "-p",
                                        scenario,
                                        "--logging",
                                        "--logpath",
                                        log_path,
                                        "-cP",
                                        cred_path],  
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        cp_pid=captive_portal.pid
    # create module session
    wPhSession = Wifiphisher_Captive_Portal_Session(session = active_session,
                                                    location = location,
                                                    start_time = timezone.now(),
                                                    active=True,
                                                    pid=cp_pid,
                                                    interface=interface,
                                                    scenario=scenario,
                                                    essid=essid,
                                                    log_file_path=log_path,
                                                    cred_file_path=cred_path,
                                                    cred_type=cred_type)
    wPhSession.save()
    
    # Redirect to monitor
    if include_messages:
            message=messages.success(request, "Captive Portal session launched!")
    if ctx_only:
        return wPhSession
    return redirect('captive_portal_monitor')
    
# MONITOR
def wifiphisher_captive_portal_monitor(request, include_messages=True, ctx_only=False):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to monitor captive portals")
    if _error:
        return _redirect
    if active_session is None:
        if include_messages:
            message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Get active captive portal session
    status, wphisher_sessions = get_current_wphisher_sessions(active_session)
    if not status or len(wphisher_sessions) < 1:
        if include_messages:
            message=messages.error(request, "No Captive Portal running, launch one to monitor.")
        return redirect('captive_portal_home')
    
    # Handle error case
    if len(wphisher_sessions) > 1:
        if include_messages:
            message=messages.error(request, "Multiple captive portal sessions detected, killing all but 1")
        for s in wphisher_sessions[1:]:
            killed = s.end_module_session()
            s.flush_victim_arp()
            if killed:
                if include_messages:
                    message=messages.success(request, f"Killed pid: {s.pid}")
            else:
                if include_messages:
                    message=messages.error(request, f"Failed to kill pid: {s.pid}, system restart suggested")
    
    wphisher_session = wphisher_sessions[0]
    
    ctx={"monitor": wphisher_session, "credential_type":wphisher_session.cred_type,"update_rate": cnf.MONITOR_UPDATE_RATE}
    if ctx_only:
        return ctx
    
    # Update connected victims
    victims, creds = wphisher_session.update()
    ctx['victims']=victims
    ctx['credentials']=creds
    return render(request, 'wifiphisher_broker/captive_portal_monitor.html', ctx)

def wifiphisher_captive_portal_stop(request, include_messages=True, ctx_only=False, testcase=False):
    """
    Stop all captive portal sessions for user (there should only be 1 anyway)
    """
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access captive portals")
    if _error:
        return _redirect
    if active_session is None:
        if include_messages:
            message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Get active captive portal session
    status, wphisher_sessions = get_current_wphisher_sessions(active_session)
    if not status or len(wphisher_sessions) < 1:
        if include_messages:
            message=messages.success(request, "No Captive Portal running")
    else:
        for s in wphisher_sessions:
            killed = s.end_module_session(testcase)
            if not testcase:
                s.flush_victim_arp()
            if killed:
                if include_messages:
                    message=messages.success(request, f"Killed pid: {s.pid}")
            else:
                if include_messages:
                    message=messages.error(request, f"Failed to kill pid: {s.pid}, system restart suggested")
    return redirect('captive_portal_home')

# RESULTS
def wifiphisher_captive_portal_previous_captures(request, include_messages=True, ctx_only=False):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to run captive portals")
    if _error:
        return _redirect
    if active_session is None:
        if include_messages:
            message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    wphisher_context={}        
    
    # Get historic captures
    wphisher_context["historic_captures"]=Wifiphisher_Captive_Portal_Session.objects.filter(session__user=active_session.user).order_by('-start_time')
    if ctx_only:
        return wphisher_context
    return render(request, 'wifiphisher_broker/captive_portal_previous_captures.html', wphisher_context)

def wifiphisher_captive_portal_results(request, include_messages=True, ctx_only=False):
    """Show previous results from a captive portal session"""
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access captive portals")
    if _error:
        return _redirect
    if active_session is None:
        if include_messages:
            message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    session_id=request.GET.get('session_id', None)
    if session_id is None:
        if include_messages:
            message=messages.error(request, "Must select a session to view it's results, no session_id in request params")
        return redirect('captive_portal_home')    
    
    wphisher_session=Wifiphisher_Captive_Portal_Session.objects.all().filter(id=session_id).first()
    victims=wphisher_session.get_victims()
    creds=wphisher_session.get_cred_results()
    
    ctx={"monitor": wphisher_session, 
                   "victims":victims,
                   "credentials": creds,
                   "credential_type":wphisher_session.cred_type}
    if ctx_only:
        return ctx
    
    return render(request, 'wifiphisher_broker/captive_portal_results.html', ctx)
    
