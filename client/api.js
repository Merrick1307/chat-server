const API = {
    baseUrl: 'http://localhost:8000',
    token: null,

    setToken(token) {
        this.token = token;
        localStorage.setItem('auth_token', token);
    },

    getToken() {
        if (!this.token) {
            this.token = localStorage.getItem('auth_token');
        }
        return this.token;
    },

    clearToken() {
        this.token = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_data');
    },

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.getToken()) {
            headers['Authorization'] = `Bearer ${this.getToken()}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            if (response.status === 401) {
                this.clearToken();
                window.location.reload();
                return null;
            }

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    // Auth endpoints
    async login(email, password) {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }

        return data;
    },

    async signup(username, email, password) {
        return this.request('/auth/signup', {
            method: 'POST',
            body: JSON.stringify({ username, email, password })
        });
    },

    async logout() {
        try {
            await this.request('/auth/logout', { method: 'POST' });
        } finally {
            this.clearToken();
        }
    },

    // Message endpoints
    async sendMessage(recipientId, content, messageType = 'text') {
        return this.request('/api/v1/messages/send', {
            method: 'POST',
            body: JSON.stringify({
                recipient_id: recipientId,
                content,
                message_type: messageType
            })
        });
    },

    async getConversation(userId, limit = 50, offset = 0) {
        return this.request(`/api/v1/messages/conversation/${userId}?limit=${limit}&offset=${offset}`);
    },

    async getUnreadMessages() {
        return this.request('/api/v1/messages/unread');
    },

    async markAsRead(messageId) {
        return this.request(`/api/v1/messages/${messageId}/read`, {
            method: 'POST'
        });
    },

    // Group endpoints
    async createGroup(groupName, memberIds) {
        return this.request('/api/v1/groups', {
            method: 'POST',
            body: JSON.stringify({
                group_name: groupName,
                member_ids: memberIds
            })
        });
    },

    async getMyGroups() {
        return this.request('/api/v1/groups/my');
    },

    async getGroup(groupId) {
        return this.request(`/api/v1/groups/${groupId}`);
    },

    async getGroupMembers(groupId) {
        return this.request(`/api/v1/groups/${groupId}/members`);
    },

    async addGroupMembers(groupId, userIds) {
        return this.request(`/api/v1/groups/${groupId}/members`, {
            method: 'POST',
            body: JSON.stringify({ user_ids: userIds })
        });
    },

    async removeGroupMember(groupId, userId) {
        return this.request(`/api/v1/groups/${groupId}/members/${userId}`, {
            method: 'DELETE'
        });
    },

    async getGroupMessages(groupId, limit = 50, offset = 0) {
        return this.request(`/api/v1/groups/${groupId}/messages?limit=${limit}&offset=${offset}`);
    }
};
