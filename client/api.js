const API = {
    baseUrl: 'http://localhost:8500',
    token: null,
    refreshToken: null,

    setToken(token) {
        this.token = token;
        localStorage.setItem('auth_token', token);
    },

    setRefreshToken(token) {
        this.refreshToken = token;
        localStorage.setItem('refresh_token', token);
    },

    getToken() {
        if (!this.token) {
            this.token = localStorage.getItem('auth_token');
        }
        return this.token;
    },

    getRefreshToken() {
        if (!this.refreshToken) {
            this.refreshToken = localStorage.getItem('refresh_token');
        }
        return this.refreshToken;
    },

    clearToken() {
        this.token = null;
        this.refreshToken = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
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

        const response = await fetch(url, { ...options, headers });
        const data = await response.json().catch(() => ({}));

        if (response.status === 401) {
            this.clearToken();
            window.location.reload();
            throw new Error(data.detail || 'Unauthorized');
        }

        if (!response.ok) {
            const errorMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail) || `Request failed: ${response.status}`;
            throw new Error(errorMsg);
        }

        return data.data !== undefined ? data.data : data;
    },

    async login(username, password) {
        const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(data.detail || data.error?.message || 'Login failed');
        }

        return data.data !== undefined ? data.data : data;
    },

    async signup(username, email, password, firstName, lastName) {
        const response = await fetch(`${this.baseUrl}/api/v1/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username,
                email,
                password,
                first_name: firstName,
                last_name: lastName
            })
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(data.detail || data.error?.message || 'Signup failed');
        }

        return data.data !== undefined ? data.data : data;
    },

    async logout() {
        const refreshToken = this.getRefreshToken();
        try {
            if (refreshToken) {
                await this.request('/api/v1/auth/logout', {
                    method: 'POST',
                    body: JSON.stringify({ refresh_token: refreshToken })
                });
            }
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

    async getConversationsList() {
        return this.request('/api/v1/messages/conversations');
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
    },

    // User lookup
    async lookupUser(username) {
        return this.request(`/api/v1/auth/users/lookup/${encodeURIComponent(username)}`);
    }
};
