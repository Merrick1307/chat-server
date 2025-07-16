from django.db import models
from django.contrib.auth.models import User


class Room(models.Model):
    room_name = models.CharField(max_length=255, unique=True)
    room_type = models.CharField(max_length=10)
    participants = models.ManyToManyField(User, related_name='chat_rooms')

    def __str__(self):
        return f"{self.room_name} ({self.room_type})"


class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.ManyToManyField(User, related_name='read_messages', blank=True)
    delivered_to = models.ManyToManyField(User, related_name='delivered_messages', blank=True)
    deleted_for = models.ManyToManyField(User, related_name='deleted_messages', blank=True)
    media = models.FileField(upload_to='chat_media/', null=True, blank=True)
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')

    def __str__(self):
        return f"{self.sender} in {self.room}: {str(self.message)[:20] if self.message else ''}"
