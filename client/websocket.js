class ChatWebSocket {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.pingInterval = null;
        this.handlers = {};
    }

    connect() {
        const token = API.getToken();
        if (!token) {
            console.error('No auth token available');
            return;
        }

        const wsUrl = `ws://localhost:8000/ws?token=${token}`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            this.setupHandlers();
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.scheduleReconnect();
        }
    }

    setupHandlers() {
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.startPing();
            this.emit('connected');
        };

        this.ws.onclose = (event) => {
            console.log('WebSocket closed:', event.code, event.reason);
            this.stopPing();
            this.emit('disconnected');
            
            if (event.code !== 4001) {
                this.scheduleReconnect();
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.emit('error', error);
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        };
    }

    handleMessage(message) {
        const { type } = message;
        
        switch (type) {
            case 'message.new':
                this.emit('message', message);
                break;
            case 'message.group.new':
                this.emit('groupMessage', message);
                break;
            case 'messages.offline':
                this.emit('offlineMessages', message);
                break;
            case 'message.ack':
                this.emit('messageAck', message);
                break;
            case 'message.read':
                this.emit('readReceipt', message);
                break;
            case 'typing':
                this.emit('typing', message);
                break;
            case 'pong':
                break;
            case 'error':
                console.error('Server error:', message.error);
                this.emit('serverError', message);
                break;
            default:
                console.log('Unknown message type:', type);
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.error('WebSocket not connected');
        }
    }

    sendMessage(recipientId, content, messageType = 'text') {
        this.send({
            type: 'message.send',
            recipient_id: recipientId,
            content,
            message_type: messageType
        });
    }

    sendGroupMessage(groupId, content, messageType = 'text') {
        this.send({
            type: 'message.group.send',
            group_id: groupId,
            content,
            message_type: messageType
        });
    }

    sendReadReceipt(messageId) {
        this.send({
            type: 'message.read',
            message_id: messageId
        });
    }

    sendTyping(recipientId = null, groupId = null) {
        this.send({
            type: 'typing',
            recipient_id: recipientId,
            group_id: groupId
        });
    }

    startPing() {
        this.pingInterval = setInterval(() => {
            this.send({ type: 'ping' });
        }, 30000);
    }

    stopPing() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnect attempts reached');
            this.emit('maxReconnectReached');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }

    disconnect() {
        this.stopPing();
        if (this.ws) {
            this.ws.close(1000, 'User logout');
            this.ws = null;
        }
    }

    on(event, handler) {
        if (!this.handlers[event]) {
            this.handlers[event] = [];
        }
        this.handlers[event].push(handler);
    }

    off(event, handler) {
        if (!this.handlers[event]) return;
        this.handlers[event] = this.handlers[event].filter(h => h !== handler);
    }

    emit(event, data) {
        if (!this.handlers[event]) return;
        this.handlers[event].forEach(handler => handler(data));
    }

    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

const ws = new ChatWebSocket();
