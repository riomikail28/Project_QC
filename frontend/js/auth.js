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

    isAdmin() {
        const u = this.user();
        return (u && u.role === 'admin') || localStorage.getItem('qc_role') === 'admin';
    }
};
