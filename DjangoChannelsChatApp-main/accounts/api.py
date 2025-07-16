from rest_framework import viewsets, permissions, generics
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from accounts.models import Profile
from ChatApp.models import Room, Message
from .serializers import UserSerializer, ProfileSerializer, RoomSerializer, MessageSerializer, RegisterSerializer
from rest_framework.views import APIView
from django.utils import timezone

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
        }, status=status.HTTP_201_CREATED)

class UserStatusAPIView(APIView):
    def get(self, request, username):
        try:
            profile = Profile.objects.get(user__username=username)
            if profile.is_online:
                return Response({"status": "Online", "last_seen": None})
            elif profile.last_seen:
                return Response({"status": "Offline", "last_seen": profile.last_seen.strftime('%Y-%m-%d %H:%M:%S')})
            else:
                return Response({"status": "Offline", "last_seen": None})
        except Profile.DoesNotExist:
            return Response({"status": "Unknown user", "last_seen": None}, status=404)

class MessageStatusAPIView(APIView):
    def get(self, request, message_id):
        try:
            msg = Message.objects.get(id=message_id)
            return Response({"status": msg.status})
        except Message.DoesNotExist:
            return Response({"status": "Unknown message"}, status=404)
