from typing import Optional
import orjson
import asyncio
from uuid import uuid4
from datetime import datetime, timezone

from fastapi.websockets import WebSocket, WebSocketDisconnect

from app.websocket.manager import WebSocketManager
from app.cache import WebSocketCacheService
from app.services.messaging import MessageService, GroupService, GroupMessageService


class WebSocketHandler:
    """Handles WebSocket message routing and processing."""
    
    # Message type constants
    MSG_SEND = "message.send"
    MSG_GROUP_SEND = "message.group.send"
    MSG_READ = "message.read"
    MSG_TYPING = "typing"
    MSG_PING = "ping"
    
    # Server message types
    MSG_NEW = "message.new"
    MSG_GROUP_NEW = "message.group.new"
    MSG_OFFLINE = "messages.offline"
    MSG_PONG = "pong"
    MSG_ERROR = "error"
    MSG_ACK = "message.ack"
    
    def __init__(
        self,
        manager: WebSocketManager,
        cache: WebSocketCacheService,
        message_service: MessageService,
        group_service: GroupService,
        group_message_service: GroupMessageService,
    ):
        self.manager = manager
        self.cache = cache
        self.message_service = message_service
        self.group_service = group_service
        self.group_message_service = group_message_service
    
    async def handle_message(self, user_id: str, websocket: WebSocket, raw_message: str, **kwargs) -> None:
        """Route incoming WebSocket message to appropriate handler."""
        try:
            data = orjson.loads(raw_message)
            msg_type = data.get("type", "")
            
            handlers = {
                self.MSG_SEND: self._handle_direct_message,
                self.MSG_GROUP_SEND: self._handle_group_message,
                self.MSG_READ: self._handle_read_receipt,
                self.MSG_TYPING: self._handle_typing,
                self.MSG_PING: self._handle_ping,
            }
            
            handler = handlers.get(msg_type)
            if handler:
                await handler(user_id, websocket, data, **kwargs)
            else:
                await self._send_error(websocket, "UNKNOWN_TYPE", f"Unknown message type: {msg_type}")
                
        except orjson.JSONDecodeError:
            await self._send_error(websocket, "INVALID_JSON", "Invalid JSON format")
        except Exception as e:
            await self._send_error(websocket, "INTERNAL_ERROR", str(e))
    
    async def _handle_direct_message(self, sender_id: str, websocket: WebSocket, data: dict, **kwargs) -> None:
        """Handle direct message send."""
        recipient_id = data.get("recipient_id")
        content = data.get("content", "")
        message_type = data.get("message_type", "text")
        
        if not recipient_id:
            await self._send_error(websocket, "MISSING_RECIPIENT", "recipient_id is required")
            return
        
        if not content:
            await self._send_error(websocket, "EMPTY_CONTENT", "Message content cannot be empty")
            return
        
        message_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        is_online = await self.manager.is_user_online(recipient_id)
        
        sender_username = await self.message_service.get_username_by_id(sender_id)
        
        outgoing_message = {
            "type": self.MSG_NEW,
            "message_id": message_id,
            "sender_id": sender_id,
            "sender_username": sender_username,
            "content": content,
            "message_type": message_type,
            "created_at": timestamp
        }
        
        if is_online:
            delivered = await self.manager.send_to_user(recipient_id, outgoing_message)
            asyncio.create_task(self.message_service.save_direct_message(
                message_id, sender_id, recipient_id, content, message_type,
                delivered_at=timestamp if delivered else None
            ))
            await self._send_ack(websocket, message_id, delivered=delivered)
        else:
            await self.message_service.save_direct_message(
                message_id, sender_id, recipient_id, content, message_type
            )
            await self.cache.queue_offline_message(recipient_id, message_id, "direct")
            await self._send_ack(websocket, message_id, delivered=False, queued=True)
    
    async def _handle_group_message(self, sender_id: str, websocket: WebSocket, data: dict, **kwargs) -> None:
        """Handle group message send."""
        group_id = data.get("group_id")
        content = data.get("content", "")
        message_type = data.get("message_type", "text")
        
        if not group_id:
            await self._send_error(websocket, "MISSING_GROUP", "group_id is required")
            return
        
        if not content:
            await self._send_error(websocket, "EMPTY_CONTENT", "Message content cannot be empty")
            return
        
        member_ids = await self.group_service.get_group_members(group_id)
        if sender_id not in member_ids:
            await self._send_error(websocket, "NOT_MEMBER", "You are not a member of this group")
            return
        
        message_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        outgoing_message = {
            "type": self.MSG_GROUP_NEW,
            "message_id": message_id,
            "group_id": group_id,
            "sender_id": sender_id,
            "content": content,
            "message_type": message_type,
            "created_at": timestamp
        }
        
        online_members, offline_members = await self.cache.get_online_users_from_list(member_ids)
        
        delivered_to, _ = await self.manager.broadcast_to_group(
            online_members, outgoing_message, exclude_user=sender_id
        )
        
        for offline_user_id in offline_members:
            if offline_user_id != sender_id:
                await self.cache.queue_offline_message(offline_user_id, message_id, "group", group_id)
        
        asyncio.create_task(self.group_message_service.save_group_message(
            message_id, group_id, sender_id, content, message_type
        ))
        
        await self._send_ack(websocket, message_id, delivered=len(delivered_to) > 0, delivered_count=len(delivered_to))
    
    async def _handle_read_receipt(self, user_id: str, websocket: WebSocket, data: dict, **kwargs) -> None:
        """Handle message read receipt."""
        message_id = data.get("message_id")
        
        if not message_id:
            await self._send_error(websocket, "MISSING_MESSAGE_ID", "message_id is required")
            return
        
        await self.message_service.mark_as_read(message_id, user_id)
        
        sender_id = await self.message_service.get_message_sender(message_id)
        if sender_id and sender_id != user_id:
            read_notification = {
                "type": "message.read.receipt",
                "message_id": message_id,
                "reader_id": user_id,
                "read_at": datetime.now(timezone.utc).isoformat()
            }
            await self.manager.send_to_user(sender_id, read_notification)
    
    async def _handle_typing(self, user_id: str, websocket: WebSocket, data: dict, **kwargs) -> None:
        """Handle typing indicator."""
        recipient_id = data.get("recipient_id")
        group_id = data.get("group_id")
        is_typing = data.get("is_typing", True)
        
        typing_message = {
            "type": self.MSG_TYPING,
            "user_id": kwargs.get("username"),
            "is_typing": is_typing
        }
        
        if recipient_id:
            await self.manager.send_to_user(recipient_id, typing_message)
        elif group_id:
            typing_message["group_id"] = group_id
            member_ids = await self.group_service.get_group_members(group_id)
            await self.manager.send_to_users(member_ids, typing_message, exclude_user=user_id)
    
    async def _handle_ping(self, user_id: str, websocket: WebSocket, data: dict, **kwargs) -> None:
        """Handle heartbeat ping."""
        await self.manager.refresh_heartbeat(user_id)
        await websocket.send_text(orjson.dumps({"type": self.MSG_PONG}).decode())
    
    async def deliver_offline_messages(self, user_id: str, websocket: WebSocket) -> None:
        """Deliver queued offline messages when user connects."""
        queued = await self.cache.get_offline_queue(user_id)
        
        if not queued:
            return
        
        messages = []
        for item in queued:
            message_id = item.get("message_id")
            msg_type = item.get("type")
            
            if msg_type == "direct":
                msg = await self.message_service.get_message(message_id)
                if msg:
                    msg["type"] = "direct"
                    msg["created_at"] = msg["created_at"].isoformat() if msg.get("created_at") else None
            elif msg_type == "group":
                msg = await self.group_message_service.get_group_message(message_id)
                if msg:
                    msg["type"] = "group"
                    msg["created_at"] = msg["created_at"].isoformat() if msg.get("created_at") else None
            else:
                continue
            
            if msg:
                messages.append(msg)
        
        if messages:
            batch_message = {
                "type": self.MSG_OFFLINE,
                "messages": messages,
                "count": len(messages)
            }
            await websocket.send_text(orjson.dumps(batch_message).decode())
            
            for msg in messages:
                if msg.get("type") == "direct":
                    await self.message_service.mark_as_delivered(msg.get("message_id"))
            
            await self.cache.clear_offline_queue(user_id)
    
    async def _send_error(self, websocket: WebSocket, code: str, message: str) -> None:
        """Send error message to client."""
        await websocket.send_text(orjson.dumps({
            "type": self.MSG_ERROR,
            "code": code,
            "message": message
        }).decode())
    
    async def _send_ack(
        self, 
        websocket: WebSocket, 
        message_id: str, 
        delivered: bool = False,
        queued: bool = False,
        delivered_count: int = 0
    ) -> None:
        """Send message acknowledgment to sender."""
        ack = {
            "type": self.MSG_ACK,
            "message_id": message_id,
            "delivered": delivered,
            "queued": queued,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if delivered_count:
            ack["delivered_count"] = delivered_count
        await websocket.send_text(orjson.dumps(ack).decode())
