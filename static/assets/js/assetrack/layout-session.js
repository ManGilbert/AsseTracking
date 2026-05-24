// AsseTrack Layout Session Manager
// Handles API authentication, session management, and UI updates

class AsseTrackSession {
    constructor() {
        this.apiBase = '/api';
        this.token = localStorage.getItem('assetrack_access_token');
        this.refreshToken = localStorage.getItem('assetrack_refresh_token');
        this.user = null;
        this.notifications = [];
        this.inactivityLimitMs = 60 * 60 * 1000;
        this.inactivityTimer = null;
        this.init();
    }

    init() {
        this.loadUserFromStorage();
        this.setupEventListeners();
        this.setupInactivityTimeout();
        this.updateUI();
        this.startTokenRefreshTimer();
        this.startAccessControlRefresh();
    }

    loadUserFromStorage() {
        const userData = localStorage.getItem('assetrack_user');
        if (userData) {
            try {
                this.user = JSON.parse(userData);
            } catch (e) {
                console.error('Failed to parse user data:', e);
                this.logout();
            }
        } else if (window.currentUser) {
            this.user = window.currentUser;
        }
    }

    setupEventListeners() {
        // Logout button
        const logoutLink = document.getElementById('layoutLogoutLink');
        if (logoutLink) {
            logoutLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.logout();
            });
        }

        // Mark notifications as read
        const markReadBtn = document.getElementById('layoutMarkNotificationsRead');
        if (markReadBtn) {
            markReadBtn.addEventListener('click', () => {
                this.markNotificationsAsRead();
            });
        }
    }

    setupInactivityTimeout() {
        const reset = () => {
            clearTimeout(this.inactivityTimer);
            this.inactivityTimer = setTimeout(() => {
                sessionStorage.setItem(
                    'assetrack_session_message',
                    'Your session has expired due to inactivity. Please log in again.'
                );
                this.logout();
            }, this.inactivityLimitMs);
        };

        ['click', 'keydown', 'mousemove', 'scroll', 'touchstart'].forEach((eventName) => {
            window.addEventListener(eventName, reset, { passive: true });
        });
        reset();
    }

    async authenticate(username, password) {
        try {
            const response = await fetch(`${this.apiBase}/auth/token/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password })
            });

            if (!response.ok) {
                throw new Error('Authentication failed');
            }

            const data = await response.json();
            this.setTokens(data.access, data.refresh);
            await this.loadUserProfile();
            return true;
        } catch (error) {
            console.error('Authentication error:', error);
            return false;
        }
    }

    setTokens(access, refresh) {
        this.token = access;
        this.refreshToken = refresh;
        localStorage.setItem('assetrack_access_token', access);
        localStorage.setItem('assetrack_refresh_token', refresh);

        // Set expiration (assuming 1 hour for access token)
        const expiresAt = Date.now() + (60 * 60 * 1000);
        localStorage.setItem('assetrack_session_expires_at', expiresAt.toString());
    }

    async loadUserProfile() {
        try {
            const response = await this.apiCall('/users/me/');
            if (response) {
                this.user = response;
                localStorage.setItem('assetrack_user', JSON.stringify(response));
                this.updateUI();
            }
        } catch (error) {
            console.error('Failed to load user profile:', error);
        }
    }

    async apiCall(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.apiBase}${endpoint}`;

        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            }
        };
        if (this.token) {
            defaultOptions.headers.Authorization = `Bearer ${this.token}`;
        }
        if (!['GET', 'HEAD', 'OPTIONS'].includes((options.method || 'GET').toUpperCase())) {
            const csrfToken = this.getCookie('csrftoken');
            if (csrfToken) defaultOptions.headers['X-CSRFToken'] = csrfToken;
        }

        const mergedOptions = { ...defaultOptions, ...options };
        if (mergedOptions.headers['Content-Type'] === 'multipart/form-data') {
            delete mergedOptions.headers['Content-Type'];
        }

        let response = await fetch(url, mergedOptions);

        if (response.status === 401 && this.refreshToken) {
            // Try to refresh token
            if (await this.refreshAccessToken()) {
                mergedOptions.headers['Authorization'] = `Bearer ${this.token}`;
                response = await fetch(url, mergedOptions);
            } else {
                this.logout();
                return null;
            }
        }

        if (!response.ok) {
            throw new Error(`API call failed: ${response.status}`);
        }

        return await response.json();
    }

    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }

    async refreshAccessToken() {
        try {
            const response = await fetch(`${this.apiBase}/auth/token/refresh/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ refresh: this.refreshToken })
            });

            if (!response.ok) {
                throw new Error('Token refresh failed');
            }

            const data = await response.json();
            this.setTokens(data.access, this.refreshToken);
            return true;
        } catch (error) {
            console.error('Token refresh failed:', error);
            return false;
        }
    }

    startTokenRefreshTimer() {
        // Refresh token 5 minutes before expiry
        setInterval(() => {
            const expiresAt = localStorage.getItem('assetrack_session_expires_at');
            if (expiresAt && Date.now() > (Number(expiresAt) - 5 * 60 * 1000)) {
                this.refreshAccessToken();
            }
        }, 60 * 1000); // Check every minute
    }

    logout() {
        this.token = null;
        this.refreshToken = null;
        this.user = null;
        this.notifications = [];

        localStorage.removeItem('assetrack_access_token');
        localStorage.removeItem('assetrack_refresh_token');
        localStorage.removeItem('assetrack_user');
        localStorage.removeItem('assetrack_session_expires_at');

        // Redirect to login
        const message = sessionStorage.getItem('assetrack_session_message');
        sessionStorage.removeItem('assetrack_session_message');
        window.location.href = message ? `/login/?message=${encodeURIComponent(message)}` : '/login/';
    }

    updateUI() {
        if (!this.user) return;

        // Update user info in dropdown (if not using Django templates)
        const userNameEl = document.getElementById('layoutUserName');
        const userEmailEl = document.getElementById('layoutUserEmail');
        const userRoleEl = document.getElementById('layoutUserRole');

        if (userNameEl) userNameEl.textContent = this.user.full_name || this.user.username;
        if (userEmailEl) userEmailEl.textContent = this.user.email;
        if (userRoleEl) userRoleEl.textContent = this.user.role;

        // Load notifications
        this.loadNotifications();
    }

    startAccessControlRefresh() {
        if (!window.currentUser) return;
        this.refreshAccessControl();
        setInterval(() => this.refreshAccessControl(), 20000);
    }

    async refreshAccessControl() {
        try {
            const response = await fetch(`${this.apiBase}/access-control/me/`, {
                headers: {'Content-Type': 'application/json'}
            });
            if (!response.ok) return;
            const access = await response.json();
            const permissions = new Set(access.permissions || []);
            window.currentUser.permissions = access.permissions || [];
            document.querySelectorAll('[data-required-permission]').forEach((item) => {
                item.hidden = !permissions.has(item.dataset.requiredPermission);
            });
            document.querySelectorAll('.nxl-navbar > .nxl-item.nxl-hasmenu').forEach((group) => {
                const permissionItems = Array.from(group.querySelectorAll('[data-required-permission]'));
                if (permissionItems.length) {
                    group.hidden = permissionItems.every((item) => item.hidden);
                }
            });
        } catch (error) {
            console.error('Failed to refresh access control:', error);
        }
    }

    async loadNotifications() {
        try {
            const notifications = await this.apiCall('/notifications/');
            if (notifications) {
                this.notifications = notifications.results || notifications;
                this.updateNotificationUI();
            }
        } catch (error) {
            console.error('Failed to load notifications:', error);
        }
    }

    updateNotificationUI() {
        const badge = document.getElementById('layoutNotificationBadge');
        const list = document.getElementById('layoutNotificationList');

        if (!badge || !list) return;

        const unreadCount = this.notifications.filter(n => !n.is_read).length;

        if (unreadCount > 0) {
            badge.textContent = unreadCount;
            badge.classList.remove('d-none');
        } else {
            badge.classList.add('d-none');
        }

        // Update notification list
        list.innerHTML = '';
        if (this.notifications.length === 0) {
            list.innerHTML = '<div class="notifications-item"><div class="notifications-desc"><span class="font-body text-muted">No notifications yet.</span></div></div>';
        } else {
            this.notifications.slice(0, 5).forEach(notification => {
                const item = document.createElement('div');
                item.className = 'notifications-item';
                item.innerHTML = `
                    <div class="notifications-desc">
                        <span class="font-body">${notification.message}</span>
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="notifications-date text-muted">${new Date(notification.created_at).toLocaleDateString()}</div>
                        </div>
                    </div>
                `;
                list.appendChild(item);
            });
        }
    }

    async markNotificationsAsRead() {
        try {
            const unreadNotifications = this.notifications.filter(n => !n.is_read);
            for (const notification of unreadNotifications) {
                await this.apiCall(`/notifications/${notification.id}/mark_as_read/`, { method: 'POST' });
            }
            await this.loadNotifications();
        } catch (error) {
            console.error('Failed to mark notifications as read:', error);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.asseTrackSession = new AsseTrackSession();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AsseTrackSession;
}
