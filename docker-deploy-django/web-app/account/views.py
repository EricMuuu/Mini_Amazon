from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .forms import *
from django.http import *
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth import authenticate, logout
from django.contrib.auth import login as auth_login

from django.urls import reverse
from account.models import UserProfile
from django.db.models import Q
from account.views import *

# Create your views here.
@csrf_exempt
def user_register(request):
    user_form = UserRegistrationForm(request.POST or None)

    if request.method == 'POST':
        if user_form.is_valid():
            user = user_form.save(commit=False)
            password = user_form.cleaned_data['password1']
            user.set_password(password)
            user.save()

            # Check if a UserProfile already exists for this user
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'username': user.username,
                    'first_name': user_form.cleaned_data['first_name'],
                    'last_name': user_form.cleaned_data['last_name'],
                    'phone': user_form.cleaned_data['phone'],
                    'email': user_form.cleaned_data['email'],
                }
            )

            # No need to check for duplicates as UserAddress is not unique per user
            UserAddress.objects.create(
                user=profile,
                name=user_form.cleaned_data['address_name'],
                address_x=user_form.cleaned_data['address_x'],
                address_y=user_form.cleaned_data['address_y']
            )

            # Authenticate and login user
            user = authenticate(username=user.username, password=password)
            if user:
                auth_login(request, user)
                messages.success(request, "You have successfully registered")
                return redirect('login')

        else:
            print("User Form Errors:", user_form.errors)

    return render(request, 'account/register.html', {'user_form': user_form})




# Allow users to sign-in -> authentication
@csrf_exempt
def user_login(request):
    if request.method == 'POST':
        form = UserAuthenticationForm(request, data = request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            print("User authenticated:", user is not None)
            if user is not None:
                auth_login(request, user)
                print("User logged in")
                return redirect('dashboard')
    else:
        form = UserAuthenticationForm()

    return render(request, 'account/login.html', {'form': form})

# Allow user to logout in the dashboard
@login_required
@csrf_exempt    
def user_logout(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    else:
        return render(request, 'account/dashboard.html')

@login_required
@csrf_exempt
def userprofile(request):
    user_profile = UserProfile.objects.get(user=request.user)
    context = {
        'user': request.user,
        'user_profile': user_profile
    }
    return render(request, 'account/userprofile.html', context)


@login_required
@csrf_exempt
def edit_user_profile(request):
    if request.method == 'POST':
        user_form = EditProfileForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=request.user.userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            # Save the User form
            updated_user = user_form.save()
            # Sync the fields from User to UserProfile if they are updated
            profile_instance = profile_form.instance
            if 'first_name' in user_form.changed_data:
                profile_instance.first_name = updated_user.first_name
            if 'last_name' in user_form.changed_data:
                profile_instance.last_name = updated_user.last_name
            if 'email' in user_form.changed_data:
                profile_instance.email = updated_user.email
            # Save the UserProfile form
            profile_form.save()
            return redirect('dashboard')
    else:
        user_form = EditProfileForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.userprofile)
    return render(request, 'account/edit_user_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

@login_required
@csrf_exempt
def dashboard_view(request):
    user_profile = UserProfile.objects.get(user=request.user)
    return render(request, 'account/dashboard.html', {'user_profile': user_profile})

#TODO: add edit address feature
@login_required
@csrf_exempt
def add_address(request):
    user_profile = UserProfile.objects.get(user=request.user)
    if request.method == 'POST':
        form = AddAddressForm(request.POST)
        if form.is_valid():
            # Create a UserProfile object
            UserAddress.objects.create(
                user=user_profile,
                name=form.cleaned_data['name'],
                address_x=form.cleaned_data['address_x'],
                address_y=form.cleaned_data['address_y'],
            )
            messages.success(request, "You have successfully added a new address")
            return redirect('dashboard')
    else:
        form = AddAddressForm()
    
    return render(request, 'account/add_address.html', {'form': form})

