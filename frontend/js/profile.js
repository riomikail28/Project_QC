const ProfilePage = {
    async init() {
        if (window.lucide) lucide.createIcons();
        if (!Auth.check()) {
            window.location.href = 'login.html';
            return;
        }
        await this.load();
    },

    async load() {
        document.body.classList.add('is-loading');
        try {
            const [me, summary] = await Promise.all([
                API.get('/profile/me'),
                API.get('/profile/activity-summary'),
            ]);
            this.renderIdentity(me.data || Auth.user() || {});
            this.renderSummary(summary.data || {});
        } catch (error) {
            this.renderIdentity(Auth.user() || {});
            this.renderError(error);
        } finally {
            document.body.classList.remove('is-loading');
            if (window.lucide) lucide.createIcons();
        }
    },

    renderIdentity(user) {
        const displayName = user.full_name || user.name || user.username || 'Unknown user';
        const initials = displayName.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase() || 'QC';
        const role = user.role || 'staff';
        const isAdmin = role === 'admin';

        document.body.classList.toggle('admin-profile', isAdmin);
        this.text('displayUsername', displayName);
        this.text('roleSubtitle', isAdmin ? 'QC Enterprise Administrator' : 'QC Field Staff');
        this.text('fullName', displayName);
        this.text('roleInfo', role.toUpperCase());
        this.text('departmentInfo', user.department || 'No department data');
        this.text('displayShift', user.shift || 'No shift data');
        this.text('lastLogin', user.last_login ? new Date(user.last_login).toLocaleString('id-ID') : 'No login record');
        this.text('avatarSmall', initials);
        this.text('avatarInitials', initials);
        this.text('accountId', user.id || '-');

        const roleEl = document.getElementById('displayRole');
        if (roleEl) {
            roleEl.innerText = isAdmin ? 'ADMIN' : 'STAFF';
            roleEl.className = 'role-pill ' + (isAdmin ? 'admin' : 'staff');
        }
        ['openAdminBtn', 'adminNavLink'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.hidden = !isAdmin;
        });
    },

    renderSummary(data) {
        const grid = document.getElementById('performanceGrid');
        const empty = document.getElementById('emptyActivity');
        if (!grid || !empty) return;

        if (!data.has_activity) {
            empty.hidden = false;
        } else {
            empty.hidden = true;
        }

        const accuracy = data.accuracy === null || data.accuracy === undefined ? '0%' : `${data.accuracy}%`;
        const stats = [
            ['fa-clipboard-check', 'QC Submitted', data.qc_submitted || 0, Math.min(100, data.qc_submitted || 0), ''],
            ['fa-image', 'Upload Evidence', data.upload_evidence || 0, Math.min(100, data.upload_evidence || 0), ''],
            ['fa-temperature-half', 'Temperature Logs', data.temperature_logs || 0, Math.min(100, data.temperature_logs || 0), 'warning'],
            ['fa-bullseye', 'Accuracy', accuracy, data.accuracy || 0, 'success'],
        ];
        grid.innerHTML = stats.map(([icon, label, value, progress, tone]) => `
            <div class="mini-stat">
                <span class="stat-icon"><i class="fas ${icon}"></i></span>
                <span class="card-label">${label}</span>
                <strong>${value}</strong>
                <div class="progress ${tone}"><span style="width:${progress}%"></span></div>
            </div>
        `).join('');
    },

    renderError(error) {
        const grid = document.getElementById('performanceGrid');
        if (grid) {
            grid.innerHTML = `<div class="empty-state"><i data-lucide="database"></i><h3>Unable to load data</h3><p>${this.escape(error.message || 'Retry')}</p></div>`;
        }
    },

    text(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    },

    escape(value) {
        return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
    }
};

document.addEventListener('DOMContentLoaded', () => ProfilePage.init());
