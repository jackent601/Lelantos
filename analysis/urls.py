from django.urls import path

from . import views

urlpatterns = [
    path("analysis_home/", views.analysis_home, name="analysis_home"),
]