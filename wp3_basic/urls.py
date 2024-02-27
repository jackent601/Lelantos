from django.urls import path

from . import views

urlpatterns = [
    path("home/", views.home, name="home"),
    path("addGeo/", views.addGeo, name = "addGeo")
]