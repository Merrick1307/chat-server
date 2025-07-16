# ChatApp/urls.py

from django.urls import path, include
from . import views
from .views import ajax_create_private_room, ajax_create_group_room

urlpatterns = [
    path('', include('accounts.urls')),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create_private_room/', views.ajax_create_private_room, name='create_private_room'),
    path('ajax_create_private_room/', ajax_create_private_room, name='ajax_create_private_room'),
    path('create_group_room/', views.ajax_create_group_room, name='create_group_room'),
    path('ajax_create_group_room/', ajax_create_group_room, name='ajax_create_group_room'),
    path('chat/api/messages/<str:room_name>/', views.api_get_messages, name='api_get_messages'),
]