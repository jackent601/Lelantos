from django.shortcuts import render
from django.http import HttpResponse, HttpRequest
from django.utils import timezone
from . import models 

def index(request: HttpRequest):
    return render(request, "wp3_basic/home.html")
