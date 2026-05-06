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
                return true;
            }
            return false;
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    },

    logout() {
        localStorage.removeItem('qc_token');
        localStorage.removeItem('qc_user');
        window.location.href = 'login.html';
    },

    check() {
        return !!localStorage.getItem('qc_token');
    },

    user() {
        const user = localStorage.getItem('qc_user');
        return user ? JSON.parse(user) : null;
    },

    isAdmin() {
        const u = this.user();
        return u && u.role === 'admin';
    }
};
