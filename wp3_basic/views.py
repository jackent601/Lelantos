from django.shortcuts import render
from django.http import HttpResponse, HttpRequest
from django.utils import timezone
from .models import TestGEO 
from .forms import LocationEntryForm


def home(request: HttpRequest):
    return render(request, "wp3_basic/home.html")

def addGeo(request: HttpRequest):
    if request.method == 'POST':
        form = LocationEntryForm(request.POST)
        if form.is_valid():
            new_place = TestGEO(
                name = request.POST['locationName'],
                location = request.POST['location'],
                address = request.POST['address'],
                city = request.POST['city']
                )
            new_place.save()
            print("SAVED!")
        return render(request, "wp3_basic/home.html")
    else:
        return render(request, "wp3_basic/addGeo.html", {"form": LocationEntryForm()})
