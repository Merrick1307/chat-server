const App = {
    currentUser: null,
    currentChat: null,
    currentChatType: null,
    conversations: new Map(),
    groups: new Map(),
    typingTimeout: null,
    isAdmin: false,
    adminUsersPage: 0,
    adminGroupsPage: 0,
    pendingDelete: null,

    init() {
        this.bindEvents();
        this.bindAdminEvents();
        this.bindPasswordResetEvents();
        this.checkAuth();
    },

    decodeJwt(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => 
                '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
            ).join(''));
            return JSON.parse(jsonPayload);
        } catch (e) {
            return null;
        }
    },

    bindEvents() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchAuthTab(e.target.dataset.tab));
        });
        document.getElementById('login-form').addEventListener('submit', (e) => this.handleLogin(e));
        document.getElementById('signup-form').addEventListener('submit', (e) => this.handleSignup(e));
        document.getElementById('logout-btn').addEventListener('click', () => this.handleLogout());
        document.querySelectorAll('.sidebar-tab').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchSidebarView(e.target.dataset.view));
        });
        document.getElementById('new-chat-btn').addEventListener('click', () => this.showModal('new-chat-modal'));
        document.getElementById('new-group-btn').addEventListener('click', () => this.showModal('new-group-modal'));
        document.getElementById('start-chat-btn').addEventListener('click', () => this.startNewChat());
        document.getElementById('create-group-btn').addEventListener('click', () => this.createNewGroup());
        document.querySelectorAll('.cancel-btn').forEach(btn => {
            btn.addEventListener('click', (e) => e.target.closest('.modal').classList.add('hidden'));
        });
        document.getElementById('message-form').addEventListener('submit', (e) => this.handleSendMessage(e));
        document.getElementById('message-input').addEventListener('input', () => this.handleTyping());

        ws.on('connected', () => this.onWsConnected());
        ws.on('disconnected', () => this.onWsDisconnected());
        ws.on('message', (msg) => this.onNewMessage(msg));
        ws.on('groupMessage', (msg) => this.onNewGroupMessage(msg));
        ws.on('offlineMessages', (msg) => this.onOfflineMessages(msg));
        ws.on('messageAck', (msg) => this.onMessageAck(msg));
        ws.on('typing', (msg) => this.onTypingIndicator(msg));
        ws.on('readReceipt', (msg) => this.onReadReceipt(msg));
    },

    bindPasswordResetEvents() {
        document.getElementById('forgot-password-link').addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('login-form').classList.remove('active');
            document.getElementById('forgot-password-form').classList.add('active');
        });

        document.getElementById('back-to-login-link').addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('forgot-password-form').classList.remove('active');
            document.getElementById('login-form').classList.add('active');
        });

        document.getElementById('forgot-password-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('forgot-email').value;
            const errorEl = document.getElementById('forgot-error');
            const successEl = document.getElementById('forgot-success');

            try {
                errorEl.textContent = '';
                successEl.classList.add('hidden');
                await API.requestPasswordReset(email);
                successEl.textContent = 'If an account exists with this email, a reset link has been sent.';
                successEl.classList.remove('hidden');
            } catch (error) {
                errorEl.textContent = error.message;
            }
        });
    },

    bindAdminEvents() {
        document.getElementById('admin-logout-btn')?.addEventListener('click', () => this.handleLogout());

        document.querySelectorAll('.admin-nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchAdminView(e.target.dataset.view));
        });

        document.getElementById('user-search')?.addEventListener('input', 
            this.debounce(() => this.loadAdminUsers(), 300)
        );

        document.getElementById('users-prev-btn')?.addEventListener('click', () => {
            if (this.adminUsersPage > 0) {
                this.adminUsersPage--;
                this.loadAdminUsers();
            }
        });

        document.getElementById('users-next-btn')?.addEventListener('click', () => {
            this.adminUsersPage++;
            this.loadAdminUsers();
        });

        document.getElementById('groups-prev-btn')?.addEventListener('click', () => {
            if (this.adminGroupsPage > 0) {
                this.adminGroupsPage--;
                this.loadAdminGroups();
            }
        });

        document.getElementById('groups-next-btn')?.addEventListener('click', () => {
            this.adminGroupsPage++;
            this.loadAdminGroups();
        });

        document.getElementById('refresh-online-btn')?.addEventListener('click', () => this.loadOnlineUsers());
        document.getElementById('refresh-tokens-btn')?.addEventListener('click', () => this.loadResetTokens());

        document.getElementById('admin-create-group-btn')?.addEventListener('click', () => 
            this.showModal('admin-create-group-modal')
        );

        document.getElementById('admin-create-group-submit')?.addEventListener('click', () => 
            this.createAdminGroup()
        );

        document.getElementById('confirm-delete-btn')?.addEventListener('click', () => this.confirmDelete());
    },

    debounce(func, wait) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    },

    checkAuth() {
        const token = API.getToken();
        const userData = localStorage.getItem('user_data');

        if (token && userData) {
            this.currentUser = JSON.parse(userData);
            const payload = this.decodeJwt(token);
            this.isAdmin = payload?.role === 'admin';

            if (this.isAdmin) {
                this.showAdminScreen();
            } else {
                this.showChatScreen();
                ws.connect();
                this.loadConversations();
                this.loadGroups();
            }
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
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const errorEl = document.getElementById('login-error');

        try {
            errorEl.textContent = '';
            const data = await API.login(username, password);
            API.setToken(data.access_token);
            API.setRefreshToken(data.refresh_token);

            const payload = this.decodeJwt(data.access_token);
            this.isAdmin = payload?.role === 'admin';

            this.currentUser = {
                user_id: data.user_id,
                username: username,
                role: payload?.role || 'user'
            };
            localStorage.setItem('user_data', JSON.stringify(this.currentUser));

            if (this.isAdmin) {
                this.showAdminScreen();
            } else {
                this.showChatScreen();
                ws.connect();
                this.loadConversations();
                this.loadGroups();
            }
        } catch (error) {
            errorEl.textContent = error.message;
        }
    },

    async handleSignup(e) {
        e.preventDefault();
        const username = document.getElementById('signup-username').value;
        const email = document.getElementById('signup-email').value;
        const firstName = document.getElementById('signup-firstname').value;
        const lastName = document.getElementById('signup-lastname').value;
        const password = document.getElementById('signup-password').value;
        const errorEl = document.getElementById('signup-error');

        try {
            errorEl.textContent = '';
            const data = await API.signup(username, email, password, firstName, lastName);
            API.setToken(data.access_token);
            API.setRefreshToken(data.refresh_token);

            this.currentUser = {
                user_id: data.user_id,
                username: username
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
            const conversations = await API.getConversationsList();
            if (conversations && Array.isArray(conversations)) {
                conversations.forEach(conv => {
                    this.conversations.set(conv.partner_id, {
                        recipientId: conv.partner_id,
                        username: conv.username,
                        displayName: conv.display_name || conv.username,
                        lastMessage: conv.last_message,
                        lastMessageAt: conv.last_message_at,
                        unread: conv.unread_count || 0,
                        messages: []
                    });
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

        this.conversations.forEach((conv, oderId) => {
            const div = document.createElement('div');
            div.className = 'conversation-item';
            div.dataset.oderId = oderId;
            if (this.currentChat === oderId && this.currentChatType === 'direct') {
                div.classList.add('active');
            }
            
            const displayName = conv.displayName || conv.username || oderId;
            const unreadBadge = conv.unread > 0 ? `<span class="unread-badge">${conv.unread}</span>` : '';
            div.innerHTML = `
                <div class="name">${this.escapeHtml(displayName)}${unreadBadge}</div>
                <div class="preview">${conv.lastMessage || 'Start a conversation'}</div>
            `;
            div.addEventListener('click', () => this.openChat(oderId));
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

    async openChat(recipientId) {
        this.currentChat = recipientId;
        this.currentChatType = 'direct';

        document.getElementById('chat-placeholder').classList.add('hidden');
        document.getElementById('chat-content').classList.remove('hidden');
        document.getElementById('typing-indicator').classList.add('hidden');

        const conv = this.conversations.get(recipientId);
        const chatTitle = conv ? (conv.displayName || conv.username || recipientId) : recipientId;
        document.getElementById('chat-title').textContent = chatTitle;

        this.renderConversations();

        if (conv) {
            conv.unread = 0;
            this.renderConversations();
        }

        try {
            const data = await API.getConversation(recipientId);
            const messages = data.messages || [];
            this.renderMessages(messages);
            
            // Mark unread messages as read
            for (const msg of messages) {
                if (msg.sender_id !== this.currentUser.user_id && !msg.read_at) {
                    API.markAsRead(msg.message_id).catch(() => {});
                }
            }
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
            const isSent = msg.sender_id === this.currentUser.user_id;
            
            const div = document.createElement('div');
            div.className = `message ${isSent ? 'sent' : 'received'}`;
            
            let senderHtml = '';
            if (isGroup && !isSent) {
                senderHtml = `<div class="sender">${msg.sender_username || msg.sender_id}</div>`;
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

        this.addMessageToUI({
            sender_id: this.currentUser.user_id,
            content,
            created_at: new Date().toISOString()
        });

        input.value = '';
    },

    addMessageToUI(msg) {
        const container = document.getElementById('messages-container');
        const isSent = msg.sender_id === this.currentUser.user_id;
        
        const div = document.createElement('div');
        div.className = `message ${isSent ? 'sent' : 'received'}`;
        
        const time = new Date(msg.created_at).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        let senderHtml = '';
        if (this.currentChatType === 'group' && !isSent) {
            const senderName = msg.sender_username || msg.sender_id;
            senderHtml = `<div class="sender">${this.escapeHtml(senderName)}</div>`;
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

        this.typingTimeout = setTimeout(() => {}, 2000);
    },

    showModal(modalId) {
        document.getElementById(modalId).classList.remove('hidden');
    },

    async startNewChat() {
        const usernameInput = document.getElementById('new-chat-user-id');
        const username = usernameInput.value.trim();
        const errorEl = document.getElementById('new-chat-error');
        
        if (!username) return;

        try {
            errorEl.textContent = '';
            errorEl.classList.add('hidden');
            
            const user = await API.lookupUser(username);
            
            if (!this.conversations.has(user.user_id)) {
                this.conversations.set(user.user_id, {
                    recipientId: user.user_id,
                    username: user.username,
                    displayName: user.display_name,
                    messages: [],
                    unread: 0
                });
            }

            document.getElementById('new-chat-modal').classList.add('hidden');
            usernameInput.value = '';
            
            this.renderConversations();
            this.openChat(user.user_id);
        } catch (error) {
            errorEl.textContent = error.message || 'User not found';
            errorEl.classList.remove('hidden');
        }
    },

    async createNewGroup() {
        const name = document.getElementById('new-group-name').value.trim();
        const membersInput = document.getElementById('new-group-members').value.trim();

        if (!name || !membersInput) return;

        const usernames = membersInput.split(',').map(u => u.trim()).filter(u => u);

        try {
            // Look up UUIDs for each username
            const memberIds = [];
            for (const username of usernames) {
                const user = await API.lookupUser(username);
                memberIds.push(user.user_id);
            }

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

        if (!this.conversations.has(senderId)) {
            this.conversations.set(senderId, {
                recipientId: senderId,
                username: msg.sender_username || senderId,
                displayName: msg.sender_username || senderId,
                messages: [],
                unread: 0
            });
        }

        const conv = this.conversations.get(senderId);
        conv.lastMessage = msg.content;

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
    },

    showAdminScreen() {
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        document.getElementById('admin-screen').classList.add('active');
        this.loadAdminDashboard();
    },

    switchAdminView(view) {
        document.querySelectorAll('.admin-nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });
        document.querySelectorAll('.admin-view').forEach(v => {
            v.classList.toggle('active', v.id === `admin-${view}`);
        });

        if (view === 'dashboard') this.loadAdminDashboard();
        else if (view === 'users') this.loadAdminUsers();
        else if (view === 'groups') this.loadAdminGroups();
        else if (view === 'online') this.loadOnlineUsers();
        else if (view === 'tokens') this.loadResetTokens();
    },

    async loadAdminDashboard() {
        try {
            const stats = await API.getAdminStats();
            document.getElementById('stat-users').textContent = stats.total_users || 0;
            document.getElementById('stat-groups').textContent = stats.total_groups || 0;
            document.getElementById('stat-messages').textContent = stats.total_direct_messages || 0;
            document.getElementById('stat-group-messages').textContent = stats.total_group_messages || 0;
            document.getElementById('stat-online').textContent = stats.online_users || 0;
            document.getElementById('stat-connections').textContent = stats.active_connections || 0;
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    },

    async loadAdminUsers() {
        try {
            const search = document.getElementById('user-search')?.value || '';
            const limit = 20;
            const offset = this.adminUsersPage * limit;
            const data = await API.getAdminUsers(limit, offset, search);
            
            const tbody = document.getElementById('users-table-body');
            tbody.innerHTML = data.users.map(user => `
                <tr>
                    <td>${this.escapeHtml(user.username)}</td>
                    <td>${this.escapeHtml(user.email)}</td>
                    <td>${this.escapeHtml(user.first_name)} ${this.escapeHtml(user.last_name)}</td>
                    <td><span class="role-badge ${user.role}">${user.role}</span></td>
                    <td>${new Date(user.created_at).toLocaleDateString()}</td>
                    <td class="actions">
                        <button class="btn-sm btn-view" onclick="App.viewUserDetail('${user.id}')">View</button>
                        <button class="btn-sm btn-role" onclick="App.toggleUserRole('${user.id}', '${user.role}')">
                            ${user.role === 'admin' ? 'Demote' : 'Promote'}
                        </button>
                        <button class="btn-sm btn-delete" onclick="App.promptDeleteUser('${user.id}', '${this.escapeHtml(user.username)}')">Delete</button>
                    </td>
                </tr>
            `).join('');

            document.getElementById('users-page-info').textContent = `Page ${this.adminUsersPage + 1}`;
            document.getElementById('users-prev-btn').disabled = this.adminUsersPage === 0;
            document.getElementById('users-next-btn').disabled = !data.has_more;
        } catch (error) {
            console.error('Failed to load users:', error);
        }
    },

    async viewUserDetail(userId) {
        try {
            const user = await API.getAdminUserDetail(userId);
            const content = document.getElementById('user-detail-content');
            content.innerHTML = `
                <div class="user-detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Username</span>
                        <span class="detail-value">${this.escapeHtml(user.username)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Email</span>
                        <span class="detail-value">${this.escapeHtml(user.email)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Name</span>
                        <span class="detail-value">${this.escapeHtml(user.first_name)} ${this.escapeHtml(user.last_name)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Role</span>
                        <span class="detail-value">${user.role}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Messages Sent</span>
                        <span class="detail-value">${user.message_count}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Groups</span>
                        <span class="detail-value">${user.group_count}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Created</span>
                        <span class="detail-value">${new Date(user.created_at).toLocaleString()}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Updated</span>
                        <span class="detail-value">${user.updated_at ? new Date(user.updated_at).toLocaleString() : 'Never'}</span>
                    </div>
                </div>
            `;
            this.showModal('user-detail-modal');
        } catch (error) {
            alert('Failed to load user details: ' + error.message);
        }
    },

    async toggleUserRole(userId, currentRole) {
        const newRole = currentRole === 'admin' ? 'user' : 'admin';
        if (!confirm(`Change user role to ${newRole}?`)) return;

        try {
            await API.updateUserRole(userId, newRole);
            this.loadAdminUsers();
        } catch (error) {
            alert('Failed to update role: ' + error.message);
        }
    },

    promptDeleteUser(userId, username) {
        this.pendingDelete = { type: 'user', id: userId };
        document.getElementById('confirm-delete-message').textContent = 
            `Are you sure you want to delete user "${username}"? This action cannot be undone.`;
        this.showModal('confirm-delete-modal');
    },

    promptDeleteGroup(groupId, groupName) {
        this.pendingDelete = { type: 'group', id: groupId };
        document.getElementById('confirm-delete-message').textContent = 
            `Are you sure you want to delete group "${groupName}"? All messages will be lost.`;
        this.showModal('confirm-delete-modal');
    },

    async confirmDelete() {
        if (!this.pendingDelete) return;

        try {
            if (this.pendingDelete.type === 'user') {
                await API.deleteAdminUser(this.pendingDelete.id);
                this.loadAdminUsers();
            } else if (this.pendingDelete.type === 'group') {
                await API.deleteAdminGroup(this.pendingDelete.id);
                this.loadAdminGroups();
            }
            document.getElementById('confirm-delete-modal').classList.add('hidden');
            this.pendingDelete = null;
        } catch (error) {
            alert('Delete failed: ' + error.message);
        }
    },

    async loadAdminGroups() {
        try {
            const limit = 20;
            const offset = this.adminGroupsPage * limit;
            const data = await API.getAdminGroups(limit, offset);
            
            const tbody = document.getElementById('groups-table-body');
            tbody.innerHTML = data.groups.map(group => `
                <tr>
                    <td>${this.escapeHtml(group.group_name)}</td>
                    <td>${group.member_count}</td>
                    <td>${new Date(group.created_at).toLocaleDateString()}</td>
                    <td class="actions">
                        <button class="btn-sm btn-view" onclick="App.viewGroupDetail('${group.group_id}')">View</button>
                        <button class="btn-sm btn-delete" onclick="App.promptDeleteGroup('${group.group_id}', '${this.escapeHtml(group.group_name)}')">Delete</button>
                    </td>
                </tr>
            `).join('');

            document.getElementById('groups-page-info').textContent = `Page ${this.adminGroupsPage + 1}`;
            document.getElementById('groups-prev-btn').disabled = this.adminGroupsPage === 0;
            document.getElementById('groups-next-btn').disabled = !data.has_more;
        } catch (error) {
            console.error('Failed to load groups:', error);
        }
    },

    async viewGroupDetail(groupId) {
        try {
            const group = await API.getAdminGroupDetail(groupId);
            const content = document.getElementById('user-detail-content');
            content.innerHTML = `
                <div class="user-detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Group Name</span>
                        <span class="detail-value">${this.escapeHtml(group.group_name)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Created By</span>
                        <span class="detail-value">${this.escapeHtml(group.creator_username)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Members</span>
                        <span class="detail-value">${group.member_count}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Messages</span>
                        <span class="detail-value">${group.message_count}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Created</span>
                        <span class="detail-value">${new Date(group.created_at).toLocaleString()}</span>
                    </div>
                </div>
                <h3 style="margin-top: 1rem;">Members</h3>
                <ul style="list-style: none; padding: 0;">
                    ${group.members.map(m => `
                        <li style="padding: 0.5rem; background: var(--bg-primary); margin: 0.25rem 0; border-radius: 4px;">
                            ${this.escapeHtml(m.username)} (${m.role})
                        </li>
                    `).join('')}
                </ul>
            `;
            this.showModal('user-detail-modal');
        } catch (error) {
            alert('Failed to load group details: ' + error.message);
        }
    },

    async loadOnlineUsers() {
        try {
            const data = await API.getOnlineUsers();
            const container = document.getElementById('online-users-list');
            
            if (data.online_users.length === 0) {
                container.innerHTML = '<p>No users currently online.</p>';
                return;
            }

            container.innerHTML = data.online_users.map(user => `
                <div class="online-user-card">
                    <span class="online-indicator"></span>
                    <div>
                        <strong>${this.escapeHtml(user.username)}</strong>
                        <div style="font-size: 0.85rem; color: var(--text-secondary);">
                            ${this.escapeHtml(user.first_name)} ${this.escapeHtml(user.last_name)}
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Failed to load online users:', error);
        }
    },

    async createAdminGroup() {
        const name = document.getElementById('admin-group-name').value.trim();
        const membersInput = document.getElementById('admin-group-members').value.trim();
        const errorEl = document.getElementById('admin-group-error');

        if (!name) {
            errorEl.textContent = 'Group name is required';
            errorEl.classList.remove('hidden');
            return;
        }

        try {
            errorEl.classList.add('hidden');
            const memberIds = [];
            
            if (membersInput) {
                const usernames = membersInput.split(',').map(u => u.trim()).filter(u => u);
                for (const username of usernames) {
                    const user = await API.lookupUser(username);
                    if (user) memberIds.push(user.user_id);
                }
            }

            await API.createAdminGroup(name, memberIds);
            document.getElementById('admin-create-group-modal').classList.add('hidden');
            document.getElementById('admin-group-name').value = '';
            document.getElementById('admin-group-members').value = '';
            this.loadAdminGroups();
        } catch (error) {
            errorEl.textContent = error.message;
            errorEl.classList.remove('hidden');
        }
    },

    async loadResetTokens() {
        try {
            const data = await API.getResetTokens();
            const tbody = document.getElementById('tokens-table-body');
            const noTokensMsg = document.getElementById('no-tokens-msg');
            
            if (data.tokens.length === 0) {
                tbody.innerHTML = '';
                noTokensMsg.classList.remove('hidden');
                return;
            }
            
            noTokensMsg.classList.add('hidden');
            tbody.innerHTML = data.tokens.map(token => {
                const ttlClass = token.ttl_seconds > 1800 ? 'ttl-high' : 
                                 token.ttl_seconds > 600 ? 'ttl-medium' : 'ttl-low';
                const ttlDisplay = this.formatTTL(token.ttl_seconds);
                const expiresAt = new Date(Date.now() + token.ttl_seconds * 1000).toLocaleString();
                
                return `
                    <tr>
                        <td><code>${token.token_hash.substring(0, 16)}...</code></td>
                        <td><code>${token.user_id.substring(0, 8)}...</code></td>
                        <td>
                            <span class="ttl-badge ${ttlClass}">${ttlDisplay}</span>
                            <br><small>Expires: ${expiresAt}</small>
                        </td>
                        <td class="actions">
                            <button class="btn-sm btn-delete" onclick="App.invalidateToken('${token.token_hash}')">Invalidate</button>
                        </td>
                    </tr>
                `;
            }).join('');
        } catch (error) {
            console.error('Failed to load reset tokens:', error);
        }
    },

    formatTTL(seconds) {
        if (seconds >= 3600) {
            const hours = Math.floor(seconds / 3600);
            const mins = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${mins}m`;
        } else if (seconds >= 60) {
            return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
        }
        return `${seconds}s`;
    },

    async invalidateToken(tokenHash) {
        if (!confirm('Invalidate this reset token? The user will need to request a new one.')) return;
        
        try {
            await API.invalidateResetToken(tokenHash);
            this.loadResetTokens();
        } catch (error) {
            alert('Failed to invalidate token: ' + error.message);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
