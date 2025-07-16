from rest_framework import serializers
from django.contrib.auth.models import User
from accounts.models import Profile
from ChatApp.models import Room, Message

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    class Meta:
        model = Profile
        fields = ['user', 'bio', 'profile_picture']


class RoomSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    class Meta:
        model = Room
        fields = ['id', 'room_name', 'room_type', 'participants']


class MessageSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)
    sender = UserSerializer(read_only=True)
    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'message', 'timestamp']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
