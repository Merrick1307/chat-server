from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Room, Message
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

@login_required(login_url='/accounts/login/')
def dashboard(request):
    user = request.user
    private_rooms = Room.objects.filter(participants=user, room_type='private')
    group_rooms = Room.objects.filter(participants=user, room_type='group')
    available_groups = Room.objects.filter(room_type='group').exclude(participants=user)

    def get_room_info(room):
        latest_message = Message.objects.filter(room=room).order_by('-timestamp').first()
        if latest_message:
            last_message = latest_message.message
            last_timestamp = latest_message.timestamp
        else:
            last_message = None
            last_timestamp = None
        unread_count = Message.objects.filter(room=room).exclude(is_read=user).count()
        return {
            'room': room,
            'last_message': last_message,
            'last_timestamp': last_timestamp,
            'unread_count': unread_count,
        }

    private_rooms_info = [get_room_info(room) for room in private_rooms]
    group_rooms_info = [get_room_info(room) for room in group_rooms]
    available_groups_info = [get_room_info(room) for room in available_groups]
    users = User.objects.exclude(id=request.user.id)
    return render(request, 'dashboard.html', {
        'private_rooms_info': private_rooms_info,
        'group_rooms_info': group_rooms_info,
        'available_groups_info': available_groups_info,
        'user': user,
        'users': users,
    })

@csrf_exempt
@login_required(login_url='/accounts/login/')
def ajax_create_private_room(request):
    if request.method == 'POST':
        other_username = request.POST.get('other_username', '').strip().lower()
        if not other_username or other_username == request.user.username.lower():
            return JsonResponse({'error': 'You cannot chat with yourself.'}, status=400)
        try:
            other_user = User.objects.get(username__iexact=other_username)
        except User.DoesNotExist:
            return JsonResponse({'error': f"User '{other_username}' not found."}, status=404)
        private_rooms = Room.objects.filter(room_type='private', participants=request.user).filter(participants=other_user)
        for room in private_rooms:
            if room.participants.count() == 2:
                return JsonResponse({'room_name': room.room_name, 'status': 'exists'})
        room_name = f"private_{min(request.user.id, other_user.id)}_{max(request.user.id, other_user.id)}"
        room, created = Room.objects.get_or_create(room_name=room_name, room_type='private')
        room.participants.set([request.user, other_user])
        return JsonResponse({'room_name': room.room_name, 'status': 'created'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
@login_required(login_url='/accounts/login/')
def ajax_create_group_room(request):
    if request.method == 'POST':
        group_name = request.POST.get('group_name', '').strip()
        user_ids = request.POST.getlist('user_ids[]')
        if not group_name:
            return JsonResponse({'error': 'Group name required.'}, status=400)
        if Room.objects.filter(room_name=group_name, room_type='group').exists():
            return JsonResponse({'error': 'Group name already exists.'}, status=400)
        room = Room.objects.create(room_name=group_name, room_type='group')
        room.participants.add(request.user)
        users = User.objects.filter(id__in=user_ids)
        for u in users:
            room.participants.add(u)
        return JsonResponse({'room_name': room.room_name, 'status': 'created'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@require_GET
@login_required(login_url='/accounts/login/')
def api_get_messages(request, room_name):
    try:
        room = Room.objects.get(room_name=room_name)
    except Room.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)
    messages_qs = Message.objects.filter(room=room).order_by('timestamp').exclude(deleted_for=request.user)
    messages_list = []
    for msg in messages_qs:
        messages_list.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'sender_id': msg.sender.id,
            'message': msg.message,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'is_self': msg.sender == request.user,
            'media_url': msg.media.url if msg.media else None,
            'status': msg.status,
        })
    return JsonResponse({'messages': messages_list, 'room_type': room.room_type, 'room_name': room.room_name})
