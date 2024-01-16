from django.urls import path

from . import views

urlpatterns = [
    path("captive_portal_home/", views.wifiphisher_captive_portal_home, name="captive_portal_home"),
]