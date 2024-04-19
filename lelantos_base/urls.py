from django.urls import path

from . import views

urlpatterns = [
    path("home/", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("setLocation/", views.addLocation, name = "setLocation"),
    path("setLocation/", views.addLocation, name = "previous_locations")
]