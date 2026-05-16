/**
 * QC Central Kitchen — Authentication Handler
 * Manages user sessions and login state.
 */

const Auth = {
    async login(username, password) {
        try {
            const data = await API.post('/staff/login', { username, password });
            if (data && data.token) {
                localStorage.setItem('qc_token', data.token);
                localStorage.setItem('qc_user', JSON.stringify(data));
                if (data.role) {
                    localStorage.setItem('qc_role', data.role);
                }
                return data;
            }
            return null;
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    },

    async logout() {
        try {
            await API.post('/staff/logout', {});
        } catch (e) {
            // ignore errors
        }
        localStorage.removeItem('qc_token');
        localStorage.removeItem('qc_user');
        localStorage.removeItem('qc_role');
        window.location.href = '/login.html';
    },

    check() {
        return !!localStorage.getItem('qc_token');
    },

    user() {
        const user = localStorage.getItem('qc_user');
        if (user) {
            try {
                return JSON.parse(user);
            } catch (error) {
                localStorage.removeItem('qc_user');
            }
        }

        const token = localStorage.getItem('qc_token');
        if (!token) {
            return null;
        }

        try {
            const payload = token.split('.')[1];
            const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
            return decoded;
        } catch (error) {
            return null;
        }
    },

    role() {
        const user = this.user() || {};
        return this.normalizeRole(user.role || localStorage.getItem('qc_role'));
    },

    normalizeRole(role) {
        return String(role || 'staff').trim().toLowerCase();
    },

    isAdmin() {
        return ['admin', 'super_admin'].includes(this.role());
    },

    canAccessAdmin(role) {
        return ['admin', 'super_admin'].includes(this.normalizeRole(role));
    },

    applyRoleVisibility(roleOverride) {
        const canAccessAdmin = roleOverride === undefined ? this.isAdmin() : this.canAccessAdmin(roleOverride);
        document.querySelectorAll('[data-admin-only], #adminNavLink, #openAdminBtn').forEach(element => {
            element.hidden = !canAccessAdmin;
            element.style.display = canAccessAdmin ? '' : 'none';
            element.setAttribute('aria-hidden', canAccessAdmin ? 'false' : 'true');
        });
    },

    persistUser(user) {
        if (!user || typeof user !== 'object') return;
        const current = this.user() || {};
        const merged = { ...current, ...user };
        localStorage.setItem('qc_user', JSON.stringify(merged));
        localStorage.setItem('qc_role', this.normalizeRole(merged.role));
    },

    async refreshSessionRole() {
        if (!this.check() || !window.API || typeof API.get !== 'function') {
            this.applyRoleVisibility('staff');
            return null;
        }
        this.applyRoleVisibility(this.role());
        try {
            const response = await API.get('/profile/me');
            const user = response?.data || response || {};
            this.persistUser(user);
            this.applyRoleVisibility(user.role);
            return user;
        } catch (error) {
            this.applyRoleVisibility(this.role());
            return null;
        }
    }
};

document.addEventListener('DOMContentLoaded', () => Auth.refreshSessionRole());
