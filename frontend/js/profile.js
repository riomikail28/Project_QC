const ProfilePage = {
    async init() {
        if (window.lucide) lucide.createIcons();
        if (!Auth.check()) {
            window.location.href = 'login.html';
            return;
        }
        const hasCache = this.restoreCache();
        if (hasCache) {
            document.body.classList.remove('is-loading');
        }
        await this.load({ silent: hasCache });
    },

    async load({ silent = false } = {}) {
        if (!silent) document.body.classList.add('is-loading');
        try {
            const [me, summary] = await Promise.all([
                API.getSWR('/profile/me', {
                    ttlMs: 3600000,
                    onUpdate: data => {
                        const user = data?.data || data || {};
                        Auth.persistUser(user);
                        this.renderIdentity(user);
                        this.saveCache();
                    }
                }),
                API.getSWR('/profile/activity-summary', {
                    ttlMs: 30000,
                    onUpdate: data => {
                        this.renderSummary(data?.data || data || {});
                        this.saveCache();
                    }
                }),
            ]);
            const user = me?.data || me || Auth.user() || {};
            Auth.persistUser(user);
            this.renderIdentity(user);
            this.renderSummary(summary?.data || summary || {});
            this.saveCache();
        } catch (error) {
            this.renderIdentity(Auth.user() || {});
            this.renderError(error);
        } finally {
            document.body.classList.remove('is-loading');
            if (window.lucide) lucide.createIcons();
        }
    },

    saveCache() {
        try {
            const data = {
                displayUsername: document.getElementById('displayUsername')?.textContent || '',
                roleSubtitle: document.getElementById('roleSubtitle')?.textContent || '',
                displayRoleText: document.getElementById('displayRole')?.innerText || 'STAFF',
                displayRoleClass: document.getElementById('displayRole')?.className || 'role-pill staff',
                displayShift: document.getElementById('displayShift')?.textContent || 'No shift data',
                fullName: document.getElementById('fullName')?.textContent || '-',
                roleInfo: document.getElementById('roleInfo')?.textContent || '-',
                departmentInfo: document.getElementById('departmentInfo')?.textContent || '-',
                statusInfo: document.getElementById('statusInfo')?.textContent || 'Active',
                lastLogin: document.getElementById('lastLogin')?.textContent || 'No login record',
                avatarSmall: document.getElementById('avatarSmall')?.textContent || 'QC',
                avatarInitials: document.getElementById('avatarInitials')?.textContent || 'QC',
                performanceGrid: document.getElementById('performanceGrid')?.innerHTML || '',
                emptyActivityHidden: document.getElementById('emptyActivity')?.hidden ?? true,
                bodyClassAdmin: document.body.classList.contains('admin-profile')
            };
            localStorage.setItem('page_cache:staff_profile', JSON.stringify(data));
        } catch (e) {
            console.error('Failed to save profile cache:', e);
        }
    },

    restoreCache() {
        try {
            const dataStr = localStorage.getItem('page_cache:staff_profile');
            if (!dataStr) return false;
            const data = JSON.parse(dataStr);
            
            const setText = (id, val) => {
                const el = document.getElementById(id);
                if (el && val !== undefined) el.textContent = val;
            };
            const setHtml = (id, val) => {
                const el = document.getElementById(id);
                if (el && val !== undefined) el.innerHTML = val;
            };

            setText('displayUsername', data.displayUsername);
            setText('roleSubtitle', data.roleSubtitle);
            const roleEl = document.getElementById('displayRole');
            if (roleEl) {
                roleEl.innerText = data.displayRoleText || 'STAFF';
                roleEl.className = data.displayRoleClass || 'role-pill staff';
            }
            setText('displayShift', data.displayShift);
            setText('fullName', data.fullName);
            setText('roleInfo', data.roleInfo);
            setText('departmentInfo', data.departmentInfo);
            setText('statusInfo', data.statusInfo);
            setText('lastLogin', data.lastLogin);
            setText('avatarSmall', data.avatarSmall);
            setText('avatarInitials', data.avatarInitials);
            setHtml('performanceGrid', data.performanceGrid);
            const empty = document.getElementById('emptyActivity');
            if (empty) empty.hidden = data.emptyActivityHidden;
            
            document.body.classList.toggle('admin-profile', data.bodyClassAdmin);
            
            if (window.lucide) lucide.createIcons();
            return true;
        } catch (e) {
            console.error('Failed to restore profile cache:', e);
            return false;
        }
    },

    renderIdentity(user) {
        const displayName = user.full_name || user.name || user.username || 'Unknown user';
        const initials = displayName.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase() || 'QC';
        const role = Auth.normalizeRole(user.role || Auth.role());
        const isAdmin = Auth.canAccessAdmin(role);

        document.body.classList.toggle('admin-profile', isAdmin);
        this.text('displayUsername', displayName);
        this.text('roleSubtitle', isAdmin ? 'QC Enterprise Administrator' : 'QC Field Staff');
        this.text('fullName', displayName);
        this.text('roleInfo', role.toUpperCase());
        this.text('departmentInfo', user.department || 'No department data');
        this.text('statusInfo', user.status || user.account_status || 'Active');
        this.text('displayShift', user.shift || 'No shift data');
        this.text('lastLogin', user.last_login ? new Date(user.last_login).toLocaleString('id-ID') : 'No login record');
        this.text('avatarSmall', initials);
        this.text('avatarInitials', initials);
        this.applyProfileNavigation(isAdmin);

        const roleEl = document.getElementById('displayRole');
        if (roleEl) {
            roleEl.innerText = isAdmin ? role.toUpperCase() : 'STAFF';
            roleEl.className = 'role-pill ' + (isAdmin ? 'admin' : 'staff');
        }
        Auth.applyRoleVisibility(role);
    },

    applyProfileNavigation(isAdmin) {
        document.querySelectorAll('[data-staff-nav]').forEach(element => {
            element.hidden = Boolean(isAdmin);
            element.style.display = isAdmin ? 'none' : '';
        });
        const brand = document.querySelector('.nav-brand');
        if (brand && isAdmin) brand.setAttribute('href', '/admin/admin_panel.html');
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
