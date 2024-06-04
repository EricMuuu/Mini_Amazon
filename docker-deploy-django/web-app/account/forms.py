from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth.forms import AuthenticationForm
from .models import *
from django.core.exceptions import ValidationError


class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone = forms.CharField(max_length=10, required=True)
    email = forms.EmailField(max_length=254, required=True)
    address_name = forms.CharField(max_length=100, required=True, label='Address Name')
    address_x = forms.IntegerField(required=True, label='Address X Coordinate')
    address_y = forms.IntegerField(required=True, label='Address Y Coordinate')


    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'phone', 'address_name', 'address_x', 'address_y')


    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                username=user.username,
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                phone=self.cleaned_data['phone'],
                email=self.cleaned_data['email'],
            )
            UserAddress.objects.create(
                user=UserProfile.objects.get(user=user),
                name=self.cleaned_data['address_name'],
                address_x=self.cleaned_data['address_x'],
                address_y=self.cleaned_data['address_y']
            )
        return user

# User Login
class UserAuthenticationForm(AuthenticationForm):
    class Meta:
        model = User
        fields = ['username', 'password']

class EditProfileForm(UserChangeForm):
    class Meta:
        model = UserProfile
        fields=['email','first_name','last_name','password']

    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=10, required=True)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone']

class AddAddressForm(forms.ModelForm):
    class Meta:
        model = UserAddress
        fields = ['name', 'address_x', 'address_y']
    name = forms.CharField(required=True)
    address_x = forms.IntegerField(required=True)
    address_y = forms.IntegerField(required=True)