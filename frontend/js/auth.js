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
            return JSON.parse(user);
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
        return String(user.role || localStorage.getItem('qc_role') || 'staff').toLowerCase();
    },

    isAdmin() {
        return ['admin', 'super_admin'].includes(this.role());
    },

    applyRoleVisibility() {
        const canAccessAdmin = this.isAdmin();
        document.querySelectorAll('[data-admin-only], #adminNavLink, #openAdminBtn').forEach(element => {
            element.hidden = !canAccessAdmin;
            element.setAttribute('aria-hidden', canAccessAdmin ? 'false' : 'true');
        });
    }
};

document.addEventListener('DOMContentLoaded', () => Auth.applyRoleVisibility());
