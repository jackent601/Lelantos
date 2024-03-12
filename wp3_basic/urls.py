from django.urls import path

from . import views

urlpatterns = [
    path("home/", views.home, name="home"),
    path("setLocation/", views.addLocation, name = "setLocation"),
    path("setLocation/", views.addLocation, name = "previous_locations")
]