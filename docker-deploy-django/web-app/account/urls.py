from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.user_register, name='register'),
    path('login/', views.user_login, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.user_logout, name='logout'),
    path('userprofile/', views.userprofile, name='userprofile'),
    path('userprofile/edit_user_profile/', views.edit_user_profile, name='edit_user_profile'),
    path('add-address/', views.add_address, name='add_address'),
]