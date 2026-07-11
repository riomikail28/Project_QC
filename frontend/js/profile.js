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
                metaEmployeeId: document.getElementById('metaEmployeeId')?.textContent || '-',
                metaDepartment: document.getElementById('metaDepartment')?.textContent || '-',
                metaShift: document.getElementById('metaShift')?.textContent || '-',
                metaJoinDate: document.getElementById('metaJoinDate')?.textContent || '-',
                performanceGrid: document.getElementById('performanceGrid')?.innerHTML || '',
                emptyActivityHidden: document.getElementById('emptyActivity')?.hidden ?? true,
                activityPagiHtml: document.getElementById('activityPagi')?.innerHTML || '',
                activitySiangHtml: document.getElementById('activitySiang')?.innerHTML || '',
                activitySoreHtml: document.getElementById('activitySore')?.innerHTML || '',
                todayProgressPercent: document.getElementById('todayProgressPercent')?.textContent || '0%',
                todayProgressStatus: document.getElementById('todayProgressStatus')?.textContent || '0 / 3 Selesai',
                todayProgressBarWidth: document.getElementById('todayProgressBar')?.style.width || '0%',
                achieveAccuracyClass: document.getElementById('achieveAccuracy')?.className || 'achievement-item locked',
                achieveStreakClass: document.getElementById('achieveStreak')?.className || 'achievement-item locked',
                achieveEvidenceClass: document.getElementById('achieveEvidence')?.className || 'achievement-item locked',
                perfQcVal: document.getElementById('perfQcVal')?.textContent || '100%',
                perfResponseVal: document.getElementById('perfResponseVal')?.textContent || '84%',
                perfTempVal: document.getElementById('perfTempVal')?.textContent || '93%',
                perfQcBarWidth: document.getElementById('perfQcBar')?.style.width || '100%',
                perfResponseBarWidth: document.getElementById('perfResponseBar')?.style.width || '84%',
                perfTempBarWidth: document.getElementById('perfTempBar')?.style.width || '93%',
                infoName: document.getElementById('infoName')?.textContent || '-',
                infoRole: document.getElementById('infoRole')?.textContent || '-',
                infoDepartment: document.getElementById('infoDepartment')?.textContent || '-',
                infoStatusText: document.getElementById('infoStatus')?.textContent || 'Active',
                infoStatusClass: document.getElementById('infoStatus')?.className || 'status-badge',
                infoLastLogin: document.getElementById('infoLastLogin')?.textContent || '-',
                avatarSmall: document.getElementById('avatarSmall')?.textContent || 'QC',
                avatarInitials: document.getElementById('avatarInitials'),
                bodyClassAdmin: document.body.classList.contains('admin-profile')
            };
            localStorage.setItem('page_cache:staff_profile_v2', JSON.stringify(data));
        } catch (e) {
            console.error('Failed to save profile cache:', e);
        }
    },

    restoreCache() {
        try {
            const dataStr = localStorage.getItem('page_cache:staff_profile_v2');
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
            const setWidth = (id, val) => {
                const el = document.getElementById(id);
                if (el && val !== undefined) el.style.width = val;
            };
            const setClass = (id, val) => {
                const el = document.getElementById(id);
                if (el && val !== undefined) el.className = val;
            };

            setText('displayUsername', data.displayUsername);
            setText('metaEmployeeId', data.metaEmployeeId);
            setText('metaDepartment', data.metaDepartment);
            setText('metaShift', data.metaShift);
            setText('metaJoinDate', data.metaJoinDate);
            setHtml('performanceGrid', data.performanceGrid);
            const empty = document.getElementById('emptyActivity');
            if (empty) empty.hidden = data.emptyActivityHidden;

            setHtml('activityPagi', data.activityPagiHtml);
            setHtml('activitySiang', data.activitySiangHtml);
            setHtml('activitySore', data.activitySoreHtml);
            setText('todayProgressPercent', data.todayProgressPercent);
            setText('todayProgressStatus', data.todayProgressStatus);
            setWidth('todayProgressBar', data.todayProgressBarWidth);

            setClass('achieveAccuracy', data.achieveAccuracyClass);
            setClass('achieveStreak', data.achieveStreakClass);
            setClass('achieveEvidence', data.achieveEvidenceClass);

            setText('perfQcVal', data.perfQcVal);
            setText('perfResponseVal', data.perfResponseVal);
            setText('perfTempVal', data.perfTempVal);
            setWidth('perfQcBar', data.perfQcBarWidth);
            setWidth('perfResponseBar', data.perfResponseBarWidth);
            setWidth('perfTempBar', data.perfTempBarWidth);

            setText('infoName', data.infoName);
            setText('infoRole', data.infoRole);
            setText('infoDepartment', data.infoDepartment);
            setText('infoStatus', data.infoStatusText);
            setClass('infoStatus', data.infoStatusClass);
            setText('infoLastLogin', data.infoLastLogin);

            setText('avatarSmall', data.avatarSmall);
            setText('avatarInitials', data.avatarSmall);
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
        
        const eyebrow = document.getElementById('eyebrowRole');
        if (eyebrow) {
            eyebrow.textContent = isAdmin ? 'QC ENTERPRISE ADMINISTRATOR' : 'QC FIELD STAFF';
        }

        const formattedLastLogin = user.last_login ? new Date(user.last_login).toLocaleString('id-ID', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZoneName: 'short'
        }).replace(/\./g, ':') : 'No login record';

        // Meta Card fields
        this.text('metaEmployeeId', user.employee_id || 'QC-24001');
        this.text('metaDepartment', user.department || 'Quality Control');
        this.text('metaShift', user.shift || 'Morning Shift');
        this.text('metaJoinDate', user.join_date || '12 Jan 2025');

        // Account Information fields
        this.text('infoName', displayName);
        this.text('infoRole', isAdmin ? 'QC Administrator' : 'QC Field Staff');
        this.text('infoDepartment', user.department || 'Quality Control');
        this.text('infoLastLogin', formattedLastLogin);
        this.text('avatarSmall', initials);
        this.text('avatarInitials', initials);

        const statusEl = document.getElementById('infoStatus');
        if (statusEl) {
            const status = user.status || user.account_status || 'Active';
            statusEl.textContent = status;
            statusEl.className = 'status-badge ' + (status.toLowerCase() === 'active' ? 'active' : 'inactive');
        }

        this.applyProfileNavigation(isAdmin);
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

        // Bind Today's Activity Checkboxes
        const ta = data.today_activity || { qc_pagi: false, qc_siang: false, qc_sore: false, progress: 0, status_text: '0 / 3 Selesai' };
        const setCheck = (id, completed) => {
            const el = document.getElementById(id);
            if (el) {
                const iconWrap = el.querySelector('.check-icon');
                if (iconWrap) {
                    if (completed) {
                        iconWrap.className = 'check-icon';
                        iconWrap.innerHTML = '<i class="fas fa-circle-check"></i>';
                    } else {
                        iconWrap.className = 'check-icon incomplete';
                        iconWrap.innerHTML = '<i class="far fa-circle"></i>';
                    }
                }
            }
        };
        setCheck('activityPagi', ta.qc_pagi);
        setCheck('activitySiang', ta.qc_siang);
        setCheck('activitySore', ta.qc_sore);

        this.text('todayProgressPercent', `${ta.progress}%`);
        this.text('todayProgressStatus', ta.status_text);
        const todayBar = document.getElementById('todayProgressBar');
        if (todayBar) todayBar.style.width = `${ta.progress}%`;

        // Bind Achievements Unlocked Status
        const ach = data.achievements || { perfect_accuracy: false, seven_days_streak: false, evidence_master: false };
        const setAchieve = (id, unlocked) => {
            const el = document.getElementById(id);
            if (el) {
                if (unlocked) {
                    el.classList.remove('locked');
                } else {
                    el.classList.add('locked');
                }
            }
        };
        setAchieve('achieveAccuracy', ach.perfect_accuracy);
        setAchieve('achieveStreak', ach.seven_days_streak);
        setAchieve('achieveEvidence', ach.evidence_master);

        // Bind Weekly Performance bars
        const wp = data.weekly_performance || { qc: 100, response: 84, temperature: 93 };
        this.text('perfQcVal', `${wp.qc}%`);
        this.text('perfResponseVal', `${wp.response}%`);
        this.text('perfTempVal', `${wp.temperature}%`);
        
        const fillBar = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.style.width = `${val}%`;
        };
        fillBar('perfQcBar', wp.qc);
        fillBar('perfResponseBar', wp.response);
        fillBar('perfTempBar', wp.temperature);
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
