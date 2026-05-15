/**
 * Admin Enterprise App Logic
 */

const adminApp = {
    // API Endpoints
    apiBase: '/api/v1/admin',
    charts: {},
    crudMode: null,
    crudId: null,
    crudContext: {},

    init() {
        this.checkAuth();
        this.setupNavigation();
        this.setupHashNavigation();
        this.setupMobileDrawer();
        this.safeRun(() => this.setupThemeToggle(), 'theme toggle');
        this.safeRun(() => this.setupCrudForm(), 'crud form');
        this.refreshIcons();
        
        // Initial load
        const hashTarget = this.targetFromHash(window.location.hash);
        if (hashTarget) {
            this.navigateTo(hashTarget);
        } else {
            this.safeRun(() => this.loadOverview(), 'overview');
        }
    },

    safeRun(fn, label) {
        try {
            return fn();
        } catch (error) {
            console.error(`[Admin] Failed to initialize ${label}:`, error);
            return null;
        }
    },

    checkAuth() {
        if (!Auth.check() || !Auth.isAdmin()) {
            alert("Akses ditolak. Anda harus login sebagai admin.");
            window.location.href = '/login.html';
            return;
        }

        // Setup Logout
        document.getElementById('btn-logout').addEventListener('click', (e) => {
            e.preventDefault();
            Auth.logout();
        });
        const user = Auth.user() || {};
        const name = user.full_name || user.name || user.username || 'Admin';
        const profile = document.querySelector('.user-profile span');
        const avatar = document.querySelector('.user-profile div');
        if (profile) profile.textContent = name;
        if (avatar) avatar.textContent = name.slice(0, 1).toUpperCase();
    },

    setupNavigation() {
        document.addEventListener('click', (event) => {
            const item = event.target.closest('.sidebar-item[data-target]');
            if (!item) return;
            event.preventDefault();
            const target = item.dataset.section || item.dataset.target;
            this.navigateTo(target, item);
            if (target) history.replaceState(null, '', `#section-${target}`);
        });
    },

    setupHashNavigation() {
        window.addEventListener('hashchange', () => {
            const target = this.targetFromHash(window.location.hash);
            if (target) this.navigateTo(target);
        });
    },

    targetFromHash(hash) {
        const clean = String(hash || '').replace(/^#/, '');
        if (!clean.startsWith('section-')) return '';
        return clean.replace('section-', '');
    },

    navigateTo(target, activeItem = null) {
        if (!target) return;
        const item = activeItem || document.querySelector(`.sidebar-item[data-section="${target}"], .sidebar-item[data-target="${target}"]`);
        document.querySelectorAll('.sidebar-item[data-target]').forEach(link => link.classList.remove('active'));
        if (item) item.classList.add('active');

        const title = item?.querySelector('span')?.innerText || item?.innerText || target;
        const titleEl = document.getElementById('page-title');
        if (titleEl) titleEl.innerText = title;

        document.querySelectorAll('.dashboard-section, .admin-section').forEach(sec => {
            sec.classList.remove('active');
            sec.hidden = true;
        });

        const section = document.getElementById(`section-${target}`);
        if (section) {
            section.hidden = false;
            section.classList.add('active');
            this.loadSectionData(target);
        }
        this.closeMobileDrawer();
        this.refreshIcons();
    },

    setupMobileDrawer() {
        const toggle = document.getElementById('admin-menu-toggle');
        const overlay = document.getElementById('admin-drawer-overlay');
        if (toggle) toggle.addEventListener('click', () => this.openMobileDrawer());
        if (overlay) overlay.addEventListener('click', () => this.closeMobileDrawer());
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') this.closeMobileDrawer();
        });
    },

    openMobileDrawer() {
        document.getElementById('admin-sidebar')?.classList.add('open');
        document.getElementById('admin-drawer-overlay')?.classList.add('active');
        document.body.classList.add('admin-drawer-open');
    },

    closeMobileDrawer() {
        document.getElementById('admin-sidebar')?.classList.remove('open');
        document.getElementById('admin-drawer-overlay')?.classList.remove('active');
        document.body.classList.remove('admin-drawer-open');
    },

    refreshIcons() {
        if (window.lucide) lucide.createIcons();
    },

    setupThemeToggle() {
        const btn = document.getElementById('theme-toggle');
        if (!btn) return;
        const root = document.documentElement;
        
        // Check local storage
        const savedTheme = localStorage.getItem('qc_admin_theme');
        if (savedTheme) {
            root.setAttribute('data-theme', savedTheme);
        }

        btn.addEventListener('click', () => {
            const current = root.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-theme', newTheme);
            localStorage.setItem('qc_admin_theme', newTheme);
            
            // Re-render charts for theme change
            if(this.charts.trend) this.charts.trend.update();
            if(this.charts.status) this.charts.status.update();
        });
    },

    async fetchAdminData(endpoint) {
        try {
            return await API.get(endpoint);
        } catch (error) {
            console.error(`Error fetching ${endpoint}:`, error);
            return null;
        }
    },

    loadSectionData(target) {
        switch(target) {
            case 'overview': this.loadOverview(); break;
            case 'monitoring': this.loadMonitoring(); break;
            case 'sku': this.loadSku(); break;
            case 'staff': this.loadStaff(); break;
            case 'facility': this.loadFacilityManager(); break;
            case 'reports': this.loadQCReports(); break;
            case 'traceability': this.loadTraceability(); break;
            case 'approval': this.loadApprovals(); break;
            case 'audit': this.loadAuditTrail(); break;
        }
    },

    // --- Data Loaders ---

    async loadOverview() {
        const [res, trendEnvelope, statusEnvelope] = await Promise.all([
            this.fetchAdminData(`${this.apiBase}/analytics/overview`),
            this.fetchAdminData('/dashboard/production-trend'),
            this.fetchAdminData('/dashboard/qc-status'),
        ]);
        if (res) {
            document.getElementById('metric-batches').innerText = res.total_batches_today || 0;
            document.getElementById('metric-qc-done').innerText = res.total_qc_completed || 0;
            document.getElementById('metric-qc-pending').innerText = res.total_qc_pending || 0;
            document.getElementById('metric-alerts').innerText = res.total_open_alerts || 0;
            document.getElementById('alert-badge').innerText = res.total_open_alerts || 0;

            this.initCharts(res, trendEnvelope?.data || [], statusEnvelope?.data || {});
        }
    },

    initCharts(data, trendRows = [], qcStatus = {}) {
        const rootStyles = getComputedStyle(document.documentElement);
        const textColor = rootStyles.getPropertyValue('--text-primary').trim();
        const gridColor = rootStyles.getPropertyValue('--border-color').trim();

        // Trend Chart
        const ctxTrend = document.getElementById('chart-qc-trend');
        if (this.charts.trend) this.charts.trend.destroy();
        
        this.charts.trend = new Chart(ctxTrend, {
            type: 'line',
            data: {
                labels: trendRows.map(row => new Date(row.date).toLocaleDateString('id-ID', { weekday: 'short' })),
                datasets: [{
                    label: 'Batch Produksi',
                    data: trendRows.map(row => row.count || 0),
                    borderColor: '#2563eb',
                    tension: 0.3,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                color: textColor,
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: textColor } },
                    y: { grid: { color: gridColor }, ticks: { color: textColor }, beginAtZero: true }
                }
            }
        });

        // Status Chart
        const ctxStatus = document.getElementById('chart-qc-status');
        if (this.charts.status) this.charts.status.destroy();
        
        this.charts.status = new Chart(ctxStatus, {
            type: 'doughnut',
            data: {
                labels: (qcStatus.items || []).map(item => item.status.toUpperCase()),
                datasets: [{
                    data: (qcStatus.items || []).map(item => item.count || 0),
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#64748b']
                }]
            },
            options: { responsive: true, color: textColor }
        });
    },

    async loadMonitoring() {
        const grid = document.getElementById('monitoring-grid');
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align:center;">Loading devices...</div>';
        
        const res = await this.fetchAdminData(`${this.apiBase}/monitoring/realtime`);
        if (!res) return;

        grid.innerHTML = '';
        if (res.length === 0) {
            grid.innerHTML = this.emptyState('No data available yet', 'Data will appear after staff submit QC activity.');
            return;
        }

        res.forEach(dev => {
            const log = dev.latest_log;
            let tempDisplay = log ? `${log.temperature_c} °C` : '-- °C';
            let statusIcon = 'fa-check-circle';
            let statusColor = 'var(--success-color)';
            
            if (log && !log.is_normal) {
                statusIcon = 'fa-exclamation-triangle';
                statusColor = 'var(--danger-color)';
            } else if (!log) {
                statusIcon = 'fa-question-circle';
                statusColor = 'var(--text-secondary)';
            }

            const card = document.createElement('div');
            card.className = 'metric-card';
            card.innerHTML = `
                <div class="metric-header">
                    <span>${dev.facility_rooms?.name || 'Unassigned'} - ${dev.name}</span>
                    <i data-lucide="${log && !log.is_normal ? 'triangle-alert' : log ? 'circle-check' : 'circle-help'}" class="metric-icon" style="color: ${statusColor}"></i>
                </div>
                <div class="metric-value">${tempDisplay}</div>
                <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:10px;">
                    Ambang Batas: ${dev.threshold_temp} °C
                </div>
            `;
            grid.appendChild(card);
        });
        this.refreshIcons();
    },

    emptyState(title = 'No data available yet', message = 'Data will appear after staff submit QC activity.') {
        return `
            <div class="empty-state" style="grid-column:1/-1">
                <i data-lucide="database"></i>
                <h3>${title}</h3>
                <p>${message}</p>
            </div>
        `;
    },

    async loadStaff() {
        const tbody = document.getElementById('table-staff');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Loading staff...</td></tr>';
        try {
            const staff = await API.get('/staff');
            if (!staff.length) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Belum ada staff.</td></tr>';
                return;
            }
            tbody.innerHTML = staff.map(item => `
                <tr>
                    <td><strong>${item.full_name || item.username || '-'}</strong></td>
                    <td>${item.username || '-'}</td>
                    <td><span class="status-badge status-${item.role === 'admin' ? 'fail' : 'pass'}">${(item.role || 'staff').toUpperCase()}</span></td>
                    <td>
                        <span class="row-actions">
                            <button class="btn-secondary btn-sm" onclick='adminApp.openStaffModal(${this.safeJson(item)})'><i data-lucide="pencil"></i> Edit</button>
                            <button class="btn-danger btn-sm" onclick="adminApp.deleteStaff('${item.id}')"><i data-lucide="trash-2"></i> Hapus</button>
                        </span>
                    </td>
                </tr>
            `).join('');
            this.refreshIcons();
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Gagal memuat staff.</td></tr>';
        }
    },

    async loadFacilityManager() {
        const container = document.getElementById('facility-manager-grid');
        if (!container) return;
        container.innerHTML = '<div class="empty-admin-state">Loading facility...</div>';
        try {
            const rooms = await API.get('/facility/structure');
            if (!rooms.length) {
                container.innerHTML = `
                    <div class="empty-admin-state">
                        <strong>Belum ada ruangan monitoring.</strong><br>
                        Tambahkan ruangan untuk mulai membuat freezer/chiller monitoring.
                    </div>
                `;
                return;
            }
            container.innerHTML = rooms.map(room => `
                <div class="facility-room-card">
                    <div class="facility-room-head">
                        <div>
                            <h3 class="card-title" style="margin:0;">${room.name}</h3>
                            <p class="admin-muted">${room.description || 'Monitoring area'}</p>
                        </div>
                        <span class="row-actions">
                            <button class="btn-primary btn-sm" onclick="adminApp.openDeviceModal(null, '${room.id}')"><i data-lucide="plus"></i> Tambah Unit</button>
                            <button class="btn-secondary btn-sm" onclick='adminApp.openRoomModal(${this.safeJson(room)})'><i data-lucide="pencil"></i> Edit</button>
                            <button class="btn-danger btn-sm" onclick="adminApp.deleteRoom('${room.id}')"><i data-lucide="trash-2"></i> Hapus</button>
                        </span>
                    </div>
                    <ul class="device-list-admin">
                        ${(room.devices || []).length ? (room.devices || []).map(device => `
                            <li>
                                <span><strong>${device.name}</strong><br><span class="admin-muted">${device.type} - ${device.threshold_temp || device.threshold || 0} C</span></span>
                                <span class="row-actions">
                                    <button class="btn-secondary btn-sm" onclick='adminApp.openDeviceModal(${this.safeJson(device)}, "${room.id}")'><i data-lucide="pencil"></i> Edit</button>
                                    <button class="btn-danger btn-sm" onclick="adminApp.deleteDevice('${device.id}')"><i data-lucide="trash-2"></i> Hapus</button>
                                </span>
                            </li>
                        `).join('') : '<li><span class="admin-muted">Belum ada unit di ruangan ini.</span></li>'}
                    </ul>
                </div>
            `).join('');
            this.refreshIcons();
        } catch (error) {
            container.innerHTML = '<div class="empty-admin-state">Gagal memuat facility setup.</div>';
        }
    },

    safeJson(value) {
        return JSON.stringify(value || {}).replace(/'/g, '&apos;');
    },

    formatRange(min, max, unit = '') {
        const hasMin = min !== null && min !== undefined && min !== '';
        const hasMax = max !== null && max !== undefined && max !== '';
        if (!hasMin && !hasMax) return '-';
        return `${hasMin ? min : '-'} - ${hasMax ? max : '-'}${unit ? ` ${unit}` : ''}`;
    },

    setupCrudForm() {
        const form = document.getElementById('crud-form');
        if (!form) return;
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            await this.submitCrudForm();
        });
    },

    openCrudModal(title, mode, fieldsHtml, context = {}) {
        this.crudMode = mode;
        this.crudId = context.id || null;
        this.crudContext = context;
        document.getElementById('crud-title').innerText = title;
        document.getElementById('crud-fields').innerHTML = fieldsHtml;
        document.getElementById('crud-modal').classList.add('active');
        this.refreshIcons();
    },

    closeCrudModal() {
        document.getElementById('crud-modal').classList.remove('active');
        document.getElementById('crud-form').reset();
        this.crudMode = null;
        this.crudId = null;
        this.crudContext = {};
    },

    openStaffModal(staff = null) {
        const item = staff || {};
        this.openCrudModal(item.id ? 'Edit Staff' : 'Tambah Staff', item.id ? 'editStaff' : 'addStaff', `
            <label>Nama Lengkap
                <input id="staff-full-name" value="${item.full_name || item.username || ''}" required>
            </label>
            <label>Username
                <input id="staff-username" value="${item.username || ''}" required>
            </label>
            <label>Role
                <select id="staff-role">
                    <option value="staff" ${item.role === 'staff' ? 'selected' : ''}>QC Staff</option>
                    <option value="admin" ${item.role === 'admin' ? 'selected' : ''}>Admin</option>
                </select>
            </label>
            <label>${item.id ? 'Password Baru (opsional)' : 'Password'}
                <input id="staff-password" type="password" ${item.id ? '' : 'required'} placeholder="${item.id ? 'Kosongkan jika tidak diganti' : 'Minimal 6 karakter'}">
            </label>
        `, { id: item.id });
    },

    openRoomModal(room = null) {
        const item = room || {};
        this.openCrudModal(item.id ? 'Edit Ruangan' : 'Tambah Ruangan', item.id ? 'editRoom' : 'addRoom', `
            <label>Nama Ruangan
                <input id="room-name" value="${item.name || ''}" required>
            </label>
            <label>Deskripsi
                <input id="room-description" value="${item.description || ''}">
            </label>
        `, { id: item.id });
    },

    openDeviceModal(device = null, roomId = '') {
        const item = device || {};
        this.openCrudModal(item.id ? 'Edit Unit Monitoring' : 'Tambah Unit Monitoring', item.id ? 'editDevice' : 'addDevice', `
            <label>Nama Unit
                <input id="device-name" value="${item.name || ''}" required>
            </label>
            <label>Tipe
                <select id="device-type">
                    <option value="chiller" ${item.type === 'chiller' ? 'selected' : ''}>Chiller</option>
                    <option value="freezer" ${item.type === 'freezer' ? 'selected' : ''}>Freezer</option>
                    <option value="undercounter" ${item.type === 'undercounter' ? 'selected' : ''}>Undercounter</option>
                    <option value="room_temp" ${item.type === 'room_temp' ? 'selected' : ''}>Suhu Ruangan</option>
                </select>
            </label>
            <label>Threshold Suhu
                <input id="device-threshold" type="number" step="0.1" value="${item.threshold_temp || item.threshold || 5}" required>
            </label>
        `, { id: item.id, roomId });
    },

    openSkuModal(product = null) {
        const item = product || {};
        this.openCrudModal(item.id ? 'Edit SKU Produk' : 'Tambah SKU Produk', item.id ? 'editSku' : 'addSku', `
            <label>Kode SKU
                <input id="sku-code" value="${item.product_code || item.sku_code || ''}" required>
            </label>
            <label>Nama Produk
                <input id="sku-name" value="${item.product_name || ''}" required>
            </label>
            <label>pH Min
                <input id="sku-ph-min" type="number" step="0.01" value="${item.ph_min ?? ''}">
            </label>
            <label>pH Max
                <input id="sku-ph-max" type="number" step="0.01" value="${item.ph_max ?? ''}">
            </label>
            <label>Brix Min
                <input id="sku-brix-min" type="number" step="0.01" value="${item.brix_min ?? ''}">
            </label>
            <label>Brix Max
                <input id="sku-brix-max" type="number" step="0.01" value="${item.brix_max ?? ''}">
            </label>
            <label>TDS Min
                <input id="sku-tds-min" type="number" step="0.01" value="${item.tds_min ?? ''}">
            </label>
            <label>TDS Max
                <input id="sku-tds-max" type="number" step="0.01" value="${item.tds_max ?? ''}">
            </label>
            <label>Status
                <select id="sku-is-active">
                    <option value="true" ${item.is_active === false ? '' : 'selected'}>Aktif</option>
                    <option value="false" ${item.is_active === false ? 'selected' : ''}>Nonaktif</option>
                </select>
            </label>
        `, { id: item.id });
    },

    numberOrNull(id) {
        const value = document.getElementById(id).value;
        return value === '' ? null : Number(value);
    },

    async submitCrudForm() {
        try {
            if (this.crudMode === 'addStaff' || this.crudMode === 'editStaff') {
                const payload = {
                    full_name: document.getElementById('staff-full-name').value.trim(),
                    username: document.getElementById('staff-username').value.trim(),
                    role: document.getElementById('staff-role').value,
                };
                const password = document.getElementById('staff-password').value;
                if (password) payload.password = password;
                if (this.crudMode === 'addStaff') await API.post('/staff', payload);
                else await API.patch(`/staff/${this.crudId}`, payload);
                await this.loadStaff();
            }

            if (this.crudMode === 'addRoom' || this.crudMode === 'editRoom') {
                const payload = {
                    name: document.getElementById('room-name').value.trim(),
                    description: document.getElementById('room-description').value.trim(),
                };
                if (this.crudMode === 'addRoom') await API.post('/facility/rooms', payload);
                else await API.patch(`/facility/rooms/${this.crudId}`, payload);
                await this.loadFacilityManager();
            }

            if (this.crudMode === 'addDevice' || this.crudMode === 'editDevice') {
                const payload = {
                    name: document.getElementById('device-name').value.trim(),
                    type: document.getElementById('device-type').value,
                    threshold: Number(document.getElementById('device-threshold').value),
                };
                if (this.crudMode === 'addDevice') {
                    payload.room_id = this.crudContext.roomId;
                    await API.post('/facility/devices', payload);
                } else {
                    await API.patch(`/facility/devices/${this.crudId}`, payload);
                }
                await this.loadFacilityManager();
            }

            if (this.crudMode === 'addSku' || this.crudMode === 'editSku') {
                const payload = {
                    product_code: document.getElementById('sku-code').value.trim(),
                    product_name: document.getElementById('sku-name').value.trim(),
                    ph_min: this.numberOrNull('sku-ph-min'),
                    ph_max: this.numberOrNull('sku-ph-max'),
                    brix_min: this.numberOrNull('sku-brix-min'),
                    brix_max: this.numberOrNull('sku-brix-max'),
                    tds_min: this.numberOrNull('sku-tds-min'),
                    tds_max: this.numberOrNull('sku-tds-max'),
                    is_active: document.getElementById('sku-is-active').value === 'true',
                };
                if (this.crudMode === 'addSku') await API.post('/v1/admin/products', payload);
                else await API.patch(`/v1/admin/products/${this.crudId}`, payload);
                await this.loadSku();
            }

            this.closeCrudModal();
        } catch (error) {
            alert(`Gagal menyimpan data: ${error.message}`);
        }
    },

    async deleteStaff(id) {
        if (!confirm('Hapus staff ini?')) return;
        await API.delete(`/staff/${id}`);
        await this.loadStaff();
    },

    async deleteRoom(id) {
        if (!confirm('Hapus ruangan ini? Unit di dalamnya juga bisa terdampak.')) return;
        await API.delete(`/facility/rooms/${id}`);
        await this.loadFacilityManager();
    },

    async deleteDevice(id) {
        if (!confirm('Hapus unit monitoring ini?')) return;
        await API.delete(`/facility/devices/${id}`);
        await this.loadFacilityManager();
    },

    async loadSku() {
        const tbody = document.getElementById('table-sku');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Loading SKU...</td></tr>';
        try {
            const products = await API.get('/v1/admin/products');
            if (!products.length) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Belum ada SKU produk.</td></tr>';
                return;
            }
            tbody.innerHTML = products.map(item => `
                <tr>
                    <td><strong>${item.product_code || item.sku_code || '-'}</strong></td>
                    <td>${item.product_name || '-'}</td>
                    <td>${this.formatRange(item.ph_min, item.ph_max, 'pH')}</td>
                    <td>${this.formatRange(item.brix_min, item.brix_max, '%')}</td>
                    <td>${this.formatRange(item.tds_min, item.tds_max, 'ppm')}</td>
                    <td><span class="status-badge status-${item.is_active === false ? 'pending' : 'pass'}">${item.is_active === false ? 'NONAKTIF' : 'AKTIF'}</span></td>
                    <td>
                        <span class="row-actions">
                            <button class="btn-secondary btn-sm" onclick='adminApp.openSkuModal(${this.safeJson(item)})'><i data-lucide="pencil"></i> Edit</button>
                            <button class="btn-danger btn-sm" onclick="adminApp.deleteSku('${item.id}')"><i data-lucide="trash-2"></i> Hapus</button>
                        </span>
                    </td>
                </tr>
            `).join('');
            this.refreshIcons();
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Gagal memuat SKU.</td></tr>';
        }
    },

    async deleteSku(id) {
        if (!confirm('Hapus SKU produk ini?')) return;
        await API.delete(`/v1/admin/products/${id}`);
        await this.loadSku();
    },

    async loadQCReports() {
        const tbody = document.getElementById('table-qc-reports');
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">Loading reports...</td></tr>';
        
        const statusFilter = document.getElementById('filter-qc-status').value;
        let url = `${this.apiBase}/qc-reports?limit=20`;
        if (statusFilter) url += `&status=${statusFilter}`;

        const res = await this.fetchAdminData(url);
        if (!res || !res.data) return;

        tbody.innerHTML = '';
        if (res.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">Tidak ada laporan.</td></tr>';
            return;
        }

        res.data.forEach(batch => {
            const tr = document.createElement('tr');
            
            const status = batch.status || batch.final_qc_status || 'pending';
            let badgeClass = `status-badge status-${status}`;

            tr.innerHTML = `
                <td>${new Date(batch.created_at).toLocaleString('id-ID')}</td>
                <td><strong>${this.escapeHtml(batch.batch_code || batch.batch_id || batch.display_title || '-')}</strong></td>
                <td>${batch.product_name || batch.product_id || '-'}</td>
                <td>${batch.inspector_name || batch.staff_id || '-'}</td>
                <td><span class="${badgeClass}">${status.toUpperCase()}</span></td>
                <td>${this.renderEvidenceCell(batch)}</td>
            `;
            tbody.appendChild(tr);
        });
        this.refreshIcons();
    },

    renderEvidenceCell(row) {
        const evidence = row.product_photo_url || row.temperature_photo_url || row.barcode_photo_url || row.photo_url || '';
        const storagePath = row.storage_path || '';
        const evidenceUrls = evidence.split(';').filter(Boolean);
        const storagePaths = storagePath.split(';').filter(Boolean);
        if (!evidenceUrls.length && !storagePaths.length) return '-';

        const previewButton = evidenceUrls.length
            ? `<button class="btn-primary" onclick='adminApp.previewImage(${this.safeJson(evidence)})' style="padding: 4px 8px; font-size:0.8rem;"><i data-lucide="image"></i> Preview ${evidenceUrls.length > 1 ? `(${evidenceUrls.length})` : ''}</button>`
            : '';
        const links = evidenceUrls.map((url, index) => (
            `<a href="${this.escapeAttr(url)}" target="_blank" rel="noopener" class="admin-evidence-link">Foto ${index + 1}</a>`
        )).join('');
        const paths = storagePaths.map(path => (
            `<code class="admin-evidence-path">${this.escapeHtml(path)}</code>`
        )).join('');

        return `<div class="admin-evidence-cell">${previewButton}${links}${paths}</div>`;
    },

    escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, char => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[char]));
    },

    escapeAttr(value) {
        return this.escapeHtml(value).replace(/`/g, '&#96;');
    },

    async loadAuditTrail() {
        const tbody = document.getElementById('table-audit-trail');
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Loading audit logs...</td></tr>';
        
        const res = await this.fetchAdminData(`${this.apiBase}/audit-trail?limit=50`);
        if (!res) return;

        tbody.innerHTML = '';
        if (res.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Tidak ada log aktivitas.</td></tr>';
            return;
        }

        res.forEach(log => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${new Date(log.created_at).toLocaleString('id-ID')}</td>
                <td>${log.staff_accounts?.username || 'System'}</td>
                <td><span style="font-family:monospace; background:var(--bg-color); padding:2px 4px; border-radius:4px;">${log.action.toUpperCase()}</span></td>
                <td>${log.entity_type} (${log.entity_id || '-'})</td>
                <td style="font-size:0.8rem; color:var(--text-secondary);">${log.ip_address || '-'}</td>
            `;
            tbody.appendChild(tr);
        });
    },

    async loadTraceability() {
        const tbody = document.getElementById('table-traceability');
        const barcode = document.getElementById('traceability-barcode')?.value?.trim();
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Loading traceability...</td></tr>';
        const url = `${this.apiBase}/traceability?limit=50${barcode ? `&barcode=${encodeURIComponent(barcode)}` : ''}`;
        const res = await this.fetchAdminData(url);
        if (!res) return;
        tbody.innerHTML = '';
        if (res.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Tidak ada data traceability.</td></tr>';
            return;
        }
        res.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${row.barcode_value || '-'}</strong></td>
                <td>${row.batch_code || row.batch_id || '-'}</td>
                <td>${row.product_name || row.product_id || '-'}</td>
                <td>${row.staff_name || row.staff_id || '-'}</td>
                <td>${row.created_at ? new Date(row.created_at).toLocaleString('id-ID') : '-'}</td>
            `;
            tbody.appendChild(tr);
        });
    },

    async loadApprovals() {
        const tbody = document.getElementById('table-approvals');
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Loading approvals...</td></tr>';
        const res = await this.fetchAdminData(`${this.apiBase}/approvals?limit=50`);
        if (!res) return;
        tbody.innerHTML = '';
        if (res.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Tidak ada approval pending.</td></tr>';
            return;
        }
        res.forEach(row => {
            const evidence = row.product_photo_url || row.temperature_photo_url || row.barcode_photo_url;
            const evidenceUrls = (evidence || '').split(';').filter(u => u);
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${row.batch_code || row.batch_id || '-'}</strong></td>
                <td><span class="status-badge status-${row.status || 'pending'}">${(row.approval_status || row.status || 'pending').toUpperCase()}</span></td>
                <td>${row.inspector_name || row.staff_id || '-'}</td>
                <td>${evidence ? `<button class="btn-primary" onclick="adminApp.previewImage('${evidence}')" style="padding: 4px 8px; font-size:0.8rem;"><i data-lucide="image"></i> Lihat ${evidenceUrls.length > 1 ? `(${evidenceUrls.length})` : ''}</button>` : '-'}</td>
                <td>${row.created_at ? new Date(row.created_at).toLocaleString('id-ID') : '-'}</td>
            `;
            tbody.appendChild(tr);
        });
        this.refreshIcons();
    },

    previewImage(url) {
        const urls = url.split(';').filter(u => u);
        const container = document.getElementById('modal-image-container') || document.getElementById('modal-image').parentElement;
        
        if (urls.length > 1) {
            container.innerHTML = urls.map(u => `<img src="${u}" style="width: 100%; border-radius: 8px; margin-bottom: 12px; border: 1px solid var(--border-color);">`).join('');
        } else {
            container.innerHTML = `<img id="modal-image" src="${urls[0]}" style="max-width: 100%; border-radius: 8px;">`;
        }
        
        document.getElementById('image-modal').classList.add('active');
    }
};

window.adminApp = adminApp;

document.addEventListener('DOMContentLoaded', () => {
    adminApp.init();
});
