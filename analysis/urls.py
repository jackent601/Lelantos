from django.urls import path

from . import views

urlpatterns = [
    path("analysis_home/", views.analysis_home, name="analysis_home"),
    path("analysis_by_creds/", views.analysis_by_creds, name="analysis_by_creds"),
    path("analysis_by_device/", views.analysis_by_dev, name="analysis_by_device"),
    path("analysis_by_specific_cred/", views.analysis_by_specific_cred, name="analysis_by_specific_cred"),
    path("credentialNetwork/", views.credentialNetwork, name="credentialNetwork"),
    path("deviceNetwork/", views.deviceNetwork, name="deviceNetwork"),
]