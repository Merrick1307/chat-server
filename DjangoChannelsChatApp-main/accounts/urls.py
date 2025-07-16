# accounts/urls.py (Correct)

from django.urls import path, include
from . import views
from rest_framework import routers
from .api import UserViewSet, ProfileViewSet, RoomViewSet, MessageViewSet
from .api import RegisterAPIView, UserStatusAPIView, MessageStatusAPIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'profiles', ProfileViewSet)
router.register(r'rooms', RoomViewSet)
router.register(r'messages', MessageViewSet)

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_register, name='register'),
    path('api/', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/register/', RegisterAPIView.as_view(), name='api_register'),
    path('api/user-status/<str:username>/', UserStatusAPIView.as_view(), name='user_status'),
    path('api/message-status/<int:message_id>/', MessageStatusAPIView.as_view(), name='message_status'),
]