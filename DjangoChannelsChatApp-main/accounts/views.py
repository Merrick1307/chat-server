from django.shortcuts import render, redirect
from django.contrib.auth import logout, authenticate, login # Import authenticate and login
from django.contrib import messages

# Create your views here.

def user_login(request):
    """
    Handles user login: processes form data, authenticates, and logs in the user.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome, {username}! You are now logged in.")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'login.html')

from django.contrib.auth.models import User
def user_register(request):
    """
    Handles user registration: creates a new user if passwords match and username is unique.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            user = User.objects.create_user(username=username, password=password1)
            messages.success(request, "Registration successful. Please log in.")
            return redirect('login')
    return render(request, 'register.html')

def user_logout(request):
    """
    This function handles user logout.
    It uses Django's built-in logout function.
    """
    logout(request) # Log out the current user
    messages.info(request, "You have been logged out.") # Optional: add a success message
    return redirect('login') # Redirect to the login page after logout
