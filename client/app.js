const App = {
    currentUser: null,
    currentChat: null,
    currentChatType: null,
    conversations: new Map(),
    groups: new Map(),
    typingTimeout: null,

    init() {
        this.bindEvents();
        this.checkAuth();
    },

    bindEvents() {
        // Auth tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchAuthTab(e.target.dataset.tab));
        });

        // Auth forms
        document.getElementById('login-form').addEventListener('submit', (e) => this.handleLogin(e));
        document.getElementById('signup-form').addEventListener('submit', (e) => this.handleSignup(e));

        // Logout
        document.getElementById('logout-btn').addEventListener('click', () => this.handleLogout());

        // Sidebar tabs
        document.querySelectorAll('.sidebar-tab').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchSidebarView(e.target.dataset.view));
        });

        // New chat/group buttons
        document.getElementById('new-chat-btn').addEventListener('click', () => this.showModal('new-chat-modal'));
        document.getElementById('new-group-btn').addEventListener('click', () => this.showModal('new-group-modal'));

        // Modal actions
        document.getElementById('start-chat-btn').addEventListener('click', () => this.startNewChat());
        document.getElementById('create-group-btn').addEventListener('click', () => this.createNewGroup());

        // Cancel buttons
        document.querySelectorAll('.cancel-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.modal').classList.add('hidden');
            });
        });

        // Message form
        document.getElementById('message-form').addEventListener('submit', (e) => this.handleSendMessage(e));

        // Typing indicator
        document.getElementById('message-input').addEventListener('input', () => this.handleTyping());

        // WebSocket events
        ws.on('connected', () => this.onWsConnected());
        ws.on('disconnected', () => this.onWsDisconnected());
        ws.on('message', (msg) => this.onNewMessage(msg));
        ws.on('groupMessage', (msg) => this.onNewGroupMessage(msg));
        ws.on('offlineMessages', (msg) => this.onOfflineMessages(msg));
        ws.on('messageAck', (msg) => this.onMessageAck(msg));
        ws.on('typing', (msg) => this.onTypingIndicator(msg));
        ws.on('readReceipt', (msg) => this.onReadReceipt(msg));
    },

    checkAuth() {
        const token = API.getToken();
        const userData = localStorage.getItem('user_data');

        if (token && userData) {
            this.currentUser = JSON.parse(userData);
            this.showChatScreen();
            ws.connect();
            this.loadConversations();
            this.loadGroups();
        } else {
            this.showAuthScreen();
        }
    },

    switchAuthTab(tab) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.toggle('active', form.id === `${tab}-form`);
        });
    },

    async handleLogin(e) {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        const errorEl = document.getElementById('login-error');

        try {
            errorEl.textContent = '';
            const data = await API.login(email, password);
            API.setToken(data.access_token);
            
            this.currentUser = {
                email: email,
                username: data.username || email.split('@')[0]
            };
            localStorage.setItem('user_data', JSON.stringify(this.currentUser));

            this.showChatScreen();
            ws.connect();
            this.loadConversations();
            this.loadGroups();
        } catch (error) {
            errorEl.textContent = error.message;
        }
    },

    async handleSignup(e) {
        e.preventDefault();
        const username = document.getElementById('signup-username').value;
        const email = document.getElementById('signup-email').value;
        const password = document.getElementById('signup-password').value;
        const errorEl = document.getElementById('signup-error');

        try {
            errorEl.textContent = '';
            await API.signup(username, email, password);
            
            // Auto login after signup
            const data = await API.login(email, password);
            API.setToken(data.access_token);
            
            this.currentUser = { email, username };
            localStorage.setItem('user_data', JSON.stringify(this.currentUser));

            this.showChatScreen();
            ws.connect();
        } catch (error) {
            errorEl.textContent = error.message;
        }
    },

    async handleLogout() {
        ws.disconnect();
        await API.logout();
        this.currentUser = null;
        this.currentChat = null;
        this.conversations.clear();
        this.groups.clear();
        this.showAuthScreen();
    },

    showAuthScreen() {
        document.getElementById('auth-screen').classList.add('active');
        document.getElementById('chat-screen').classList.remove('active');
    },

    showChatScreen() {
        document.getElementById('auth-screen').classList.remove('active');
        document.getElementById('chat-screen').classList.add('active');
        document.getElementById('current-user').textContent = this.currentUser.username;
    },

    switchSidebarView(view) {
        document.querySelectorAll('.sidebar-tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });
        document.getElementById('conversations-list').classList.toggle('active', view === 'chats');
        document.getElementById('groups-list').classList.toggle('active', view === 'groups');
    },

    async loadConversations() {
        try {
            const unread = await API.getUnreadMessages();
            if (unread && Array.isArray(unread)) {
                unread.forEach(msg => {
                    const otherUserId = msg.sender_id;
                    if (!this.conversations.has(otherUserId)) {
                        this.conversations.set(otherUserId, {
                            userId: otherUserId,
                            messages: [],
                            unread: 0
                        });
                    }
                    this.conversations.get(otherUserId).unread++;
                });
            }
            this.renderConversations();
        } catch (error) {
            console.error('Failed to load conversations:', error);
        }
    },

    async loadGroups() {
        try {
            const groups = await API.getMyGroups();
            if (groups && Array.isArray(groups)) {
                groups.forEach(group => {
                    this.groups.set(group.group_id, group);
                });
            }
            this.renderGroups();
        } catch (error) {
            console.error('Failed to load groups:', error);
        }
    },

    renderConversations() {
        const container = document.getElementById('conversations-list');
        container.innerHTML = '';

        if (this.conversations.size === 0) {
            container.innerHTML = '<p style="padding: 20px; color: var(--text-secondary); text-align: center;">No conversations yet</p>';
            return;
        }

        this.conversations.forEach((conv, otherUserId) => {
            const div = document.createElement('div');
            div.className = 'conversation-item';
            div.dataset.userId = otherUserId;
            if (this.currentChat === otherUserId && this.currentChatType === 'direct') {
                div.classList.add('active');
            }
            
            const unreadBadge = conv.unread > 0 ? `<span class="unread-badge">${conv.unread}</span>` : '';
            div.innerHTML = `
                <div class="name">${otherUserId}${unreadBadge}</div>
                <div class="preview">${conv.lastMessage || 'Start a conversation'}</div>
            `;
            div.addEventListener('click', () => this.openChat(otherUserId));
            container.appendChild(div);
        });
    },

    renderGroups() {
        const container = document.getElementById('groups-list');
        container.innerHTML = '';

        if (this.groups.size === 0) {
            container.innerHTML = '<p style="padding: 20px; color: var(--text-secondary); text-align: center;">No groups yet</p>';
            return;
        }

        this.groups.forEach((group, groupId) => {
            const div = document.createElement('div');
            div.className = 'group-item';
            div.dataset.groupId = groupId;
            if (this.currentChat === groupId && this.currentChatType === 'group') {
                div.classList.add('active');
            }
            
            div.innerHTML = `
                <div class="name">${group.group_name}</div>
                <div class="info">${group.member_count || 0} members</div>
            `;
            div.addEventListener('click', () => this.openGroup(groupId));
            container.appendChild(div);
        });
    },

    async openChat(userId) {
        this.currentChat = userId;
        this.currentChatType = 'direct';

        document.getElementById('chat-placeholder').classList.add('hidden');
        document.getElementById('chat-content').classList.remove('hidden');
        document.getElementById('chat-title').textContent = userId;
        document.getElementById('typing-indicator').classList.add('hidden');

        this.renderConversations();

        // Clear unread
        if (this.conversations.has(userId)) {
            this.conversations.get(userId).unread = 0;
            this.renderConversations();
        }

        // Load messages
        try {
            const data = await API.getConversation(userId);
            this.renderMessages(data.messages || []);
        } catch (error) {
            console.error('Failed to load conversation:', error);
            this.renderMessages([]);
        }
    },

    async openGroup(groupId) {
        this.currentChat = groupId;
        this.currentChatType = 'group';

        const group = this.groups.get(groupId);
        
        document.getElementById('chat-placeholder').classList.add('hidden');
        document.getElementById('chat-content').classList.remove('hidden');
        document.getElementById('chat-title').textContent = group ? group.group_name : groupId;
        document.getElementById('typing-indicator').classList.add('hidden');

        this.renderGroups();

        // Load messages
        try {
            const data = await API.getGroupMessages(groupId);
            this.renderMessages(data.messages || [], true);
        } catch (error) {
            console.error('Failed to load group messages:', error);
            this.renderMessages([], true);
        }
    },

    renderMessages(messages, isGroup = false) {
        const container = document.getElementById('messages-container');
        container.innerHTML = '';

        messages.forEach(msg => {
            const isSent = msg.sender_id === this.currentUser.username || 
                           msg.sender_id === this.currentUser.email;
            
            const div = document.createElement('div');
            div.className = `message ${isSent ? 'sent' : 'received'}`;
            
            let senderHtml = '';
            if (isGroup && !isSent) {
                senderHtml = `<div class="sender">${msg.sender_id}</div>`;
            }
            
            const time = new Date(msg.created_at).toLocaleTimeString([], { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
            
            div.innerHTML = `
                ${senderHtml}
                <div class="content">${this.escapeHtml(msg.content)}</div>
                <div class="time">${time}</div>
            `;
            container.appendChild(div);
        });

        container.scrollTop = container.scrollHeight;
    },

    handleSendMessage(e) {
        e.preventDefault();
        const input = document.getElementById('message-input');
        const content = input.value.trim();

        if (!content || !this.currentChat) return;

        if (this.currentChatType === 'direct') {
            ws.sendMessage(this.currentChat, content);
        } else {
            ws.sendGroupMessage(this.currentChat, content);
        }

        // Optimistic UI update
        this.addMessageToUI({
            sender_id: this.currentUser.username,
            content,
            created_at: new Date().toISOString()
        });

        input.value = '';
    },

    addMessageToUI(msg) {
        const container = document.getElementById('messages-container');
        const isSent = msg.sender_id === this.currentUser.username || 
                       msg.sender_id === this.currentUser.email;
        
        const div = document.createElement('div');
        div.className = `message ${isSent ? 'sent' : 'received'}`;
        
        const time = new Date(msg.created_at).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        let senderHtml = '';
        if (this.currentChatType === 'group' && !isSent) {
            senderHtml = `<div class="sender">${msg.sender_id}</div>`;
        }
        
        div.innerHTML = `
            ${senderHtml}
            <div class="content">${this.escapeHtml(msg.content)}</div>
            <div class="time">${time}</div>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    },

    handleTyping() {
        if (!this.currentChat) return;

        clearTimeout(this.typingTimeout);
        
        if (this.currentChatType === 'direct') {
            ws.sendTyping(this.currentChat, null);
        } else {
            ws.sendTyping(null, this.currentChat);
        }

        this.typingTimeout = setTimeout(() => {
            // Typing stopped
        }, 2000);
    },

    showModal(modalId) {
        document.getElementById(modalId).classList.remove('hidden');
    },

    startNewChat() {
        const userId = document.getElementById('new-chat-user-id').value.trim();
        if (!userId) return;

        if (!this.conversations.has(userId)) {
            this.conversations.set(userId, {
                userId,
                messages: [],
                unread: 0
            });
        }

        document.getElementById('new-chat-modal').classList.add('hidden');
        document.getElementById('new-chat-user-id').value = '';
        
        this.renderConversations();
        this.openChat(userId);
    },

    async createNewGroup() {
        const name = document.getElementById('new-group-name').value.trim();
        const membersInput = document.getElementById('new-group-members').value.trim();

        if (!name || !membersInput) return;

        const memberIds = membersInput.split(',').map(id => id.trim()).filter(id => id);

        try {
            const group = await API.createGroup(name, memberIds);
            this.groups.set(group.group_id, group);
            
            document.getElementById('new-group-modal').classList.add('hidden');
            document.getElementById('new-group-name').value = '';
            document.getElementById('new-group-members').value = '';
            
            this.renderGroups();
            this.switchSidebarView('groups');
            this.openGroup(group.group_id);
        } catch (error) {
            console.error('Failed to create group:', error);
            alert('Failed to create group: ' + error.message);
        }
    },

    // WebSocket event handlers
    onWsConnected() {
        document.getElementById('chat-status').textContent = 'Online';
        document.getElementById('chat-status').classList.add('online');
    },

    onWsDisconnected() {
        document.getElementById('chat-status').textContent = 'Offline';
        document.getElementById('chat-status').classList.remove('online');
    },

    onNewMessage(msg) {
        const senderId = msg.sender_id;

        // Add to conversations if not exists
        if (!this.conversations.has(senderId)) {
            this.conversations.set(senderId, {
                userId: senderId,
                messages: [],
                unread: 0
            });
        }

        const conv = this.conversations.get(senderId);
        conv.lastMessage = msg.content;

        // If this is the current open chat, show message
        if (this.currentChat === senderId && this.currentChatType === 'direct') {
            this.addMessageToUI(msg);
            ws.sendReadReceipt(msg.message_id);
        } else {
            conv.unread++;
        }

        this.renderConversations();
    },

    onNewGroupMessage(msg) {
        const groupId = msg.group_id;

        if (this.currentChat === groupId && this.currentChatType === 'group') {
            this.addMessageToUI(msg);
        }
    },

    onOfflineMessages(data) {
        if (data.messages && Array.isArray(data.messages)) {
            data.messages.forEach(msg => {
                if (msg.group_id) {
                    this.onNewGroupMessage(msg);
                } else {
                    this.onNewMessage(msg);
                }
            });
        }
    },

    onMessageAck(msg) {
        console.log('Message acknowledged:', msg.message_id);
    },

    onTypingIndicator(msg) {
        const typingEl = document.getElementById('typing-indicator');
        
        if (this.currentChatType === 'direct' && msg.user_id === this.currentChat) {
            typingEl.querySelector('span').textContent = msg.user_id;
            typingEl.classList.remove('hidden');
            
            clearTimeout(this.hideTypingTimeout);
            this.hideTypingTimeout = setTimeout(() => {
                typingEl.classList.add('hidden');
            }, 3000);
        } else if (this.currentChatType === 'group' && msg.group_id === this.currentChat) {
            typingEl.querySelector('span').textContent = msg.user_id;
            typingEl.classList.remove('hidden');
            
            clearTimeout(this.hideTypingTimeout);
            this.hideTypingTimeout = setTimeout(() => {
                typingEl.classList.add('hidden');
            }, 3000);
        }
    },

    onReadReceipt(msg) {
        console.log('Message read:', msg.message_id, 'by', msg.reader_id);
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
