from django.test import TestCase
from django.contrib.auth.models import User
from lelantos_base.models import Session
from django.test import Client
from django.utils import timezone
from django.conf import settings
from importlib import import_module

# functions to test
from portal_auth.utils import start_new_session_for_user, get_session_from_request
from portal_auth.views import login_user, logout_user

def authPrep(cls):
    """ only user needed for portal auth funcs """
    cls.user_username="test"
    cls.user_password="test"
    cls.user = User.objects.create_user("test","test","test")
    # Session
    cls.sesh = Session.objects.create(session_id=1, user=cls.user, start_time=timezone.now(), src_ip="x.x.x.x", active=True)
    cls.c = Client()

class PortalAuth_TestCase(TestCase):
    """
    Utilities for handling portal authentication for users
    """
    @classmethod
    def setUpTestData(cls):
        print("PortalAuth_TestCase - - - - - - - - - - - - - - - - - - - - - - - - -")
        authPrep(cls)
    
    def test_getSessionFromRequest(self):
        """ uses user in request to find session """
        # log user in to authenticate
        self.c.login(username=self.user_username, password=self.user_password)
        # attach user to request
        egReq=HttpRequest()
        egReq.user=self.user
        # get sessions
        userSession, _redirect, err = get_session_from_request(egReq)
        # no error
        self.assertEqual(err, False)
        # no redirect
        self.assertEqual(_redirect, None)
        # expected session
        self.assertEqual(userSession.src_ip, "x.x.x.x")
        print("     pass: test_getSessionFromRequest")
        
    def test_startNewSessionforUser(self):
        """ closes existing session, opens a new one """
        # start session
        egReq=HttpRequest()
        egReq.META["REMOTE_ADDR"]="1.2.3.4"
        newSession = start_new_session_for_user(egReq, self.user)
        # user had an existing session so check new one creates
        userSessions = Session.objects.filter(user=self.user)
        self.assertEqual(len(userSessions), 2)
        # check old session from x.x.x.x closed
        closedSession = userSessions.filter(active=False).first()
        self.assertEqual(closedSession.src_ip, "x.x.x.x")
        # Check new active session
        self.assertEqual(newSession.active, True)
        self.assertEqual(newSession.src_ip, "1.2.3.4")
        print("     pass: test_startNewSessionforUser")
        
    def test_loginUser_ValidCredentials(self):
        """ closes existing session, opens a new one """
        # send login request
        egReq=HttpRequest()
        engine = import_module(settings.SESSION_ENGINE)
        session_key = None
        egReq.session = engine.SessionStore(session_key)
        egReq.POST['username']="test"
        egReq.POST['password']="test"
        egReq.META["REMOTE_ADDR"]="5.6.7.8"
        egReq.method="POST"
        resp = login_user(egReq, False)
        self.assertEqual(resp.url, "/setLocation/")
        print("     pass: test_loginUser_ValidCredentials")
        
    def test_loginUser_InValidCredentials(self):
        """ closes existing session, opens a new one """
        # send login request
        egReq=HttpRequest()
        engine = import_module(settings.SESSION_ENGINE)
        session_key = None
        egReq.session = engine.SessionStore(session_key)
        egReq.POST['username']="test"
        egReq.POST['password']="wrong"
        egReq.META["REMOTE_ADDR"]="5.6.7.8"
        egReq.method="POST"
        resp = login_user(egReq, False)
        self.assertEqual(resp.url, "/login/")
        print("     pass: test_loginUser_InValidCredentials")
        
    def test_loginUser_GetRequest(self):
        """ closes existing session, opens a new one """
        # send login request
        egReq=HttpRequest()
        engine = import_module(settings.SESSION_ENGINE)
        session_key = None
        egReq.session = engine.SessionStore(session_key)
        egReq.POST['username']="test"
        egReq.POST['password']="test"
        egReq.META["REMOTE_ADDR"]="5.6.7.8"
        egReq.method="GET"
        resp = login_user(egReq, False)
        # Get request re-renders login
        self.assertEqual(resp.headers, {'Content-Type': 'text/html; charset=utf-8'})
        print("     pass: test_loginUser_GetRequest")
        
    
    def test_logout(self):
        # log user in to authenticate
        self.c.login(username=self.user_username, password=self.user_password)
        # attach user to request
        egReq=HttpRequest()
        engine = import_module(settings.SESSION_ENGINE)
        session_key = None
        egReq.session = engine.SessionStore(session_key)
        egReq.user=self.user
        # logout
        resp = logout_user(egReq, False)
        # Check session marked as inactive and is correct session
        userSessions=Session.objects.filter(user=self.user)
        self.assertEqual(1, len(userSessions))
        closedSession=userSessions.first()
        self.assertEqual(closedSession.active, False)
        self.assertEqual(closedSession.src_ip, "x.x.x.x")
        print("     pass: test_logout")
        
