from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest
from django.contrib.auth import authenticate, login, logout 
from django.contrib import messages

def login_user(request: HttpRequest):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # TODO - create session
            message=messages.success(request, "logged in")
            return redirect('home')
        else:
            message=messages.error(request, "Invalid login credentials.")
            return redirect('login')
    else:
        return render(request, "portal_auth/login.html")

def logout_user(request: HttpRequest):
    # TODO - end session
    logout(request)
    message=messages.success(request, "logged out")
    return redirect('home')