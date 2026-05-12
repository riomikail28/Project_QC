/**
 * Admin Enterprise App Logic
 */

const adminApp = {
    // API Endpoints
    apiBase: '/api/v1/admin',
    charts: {},

    init() {
        this.checkAuth();
        this.setupNavigation();
        this.setupThemeToggle();
        
        // Initial load
        this.loadOverview();
    },

    checkAuth() {
        if (!Auth.check() || !Auth.isAdmin()) {
            alert("Akses ditolak. Anda harus login sebagai admin.");
            window.location.href = 'login.html';
            return;
        }

        // Setup Logout
        document.getElementById('btn-logout').addEventListener('click', (e) => {
            e.preventDefault();
            Auth.logout();
        });
    },

    setupNavigation() {
        const items = document.querySelectorAll('.sidebar-item[data-target]');
        items.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                // Update active class
                items.forEach(i => i.classList.remove('active'));
                item.classList.add('active');

                // Update page title
                document.getElementById('page-title').innerText = item.innerText;

                // Hide all sections
                document.querySelectorAll('.dashboard-section').forEach(sec => sec.classList.remove('active'));
                
                // Show target section
                const target = item.getAttribute('data-target');
                const section = document.getElementById(`section-${target}`);
                if(section) {
                    section.classList.add('active');
                    // Load data based on section
                    this.loadSectionData(target);
                }
            });
        });
    },

    setupThemeToggle() {
        const btn = document.getElementById('theme-toggle');
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
            case 'reports': this.loadQCReports(); break;
            case 'audit': this.loadAuditTrail(); break;
            // Add traceability and approval later
        }
    },

    // --- Data Loaders ---

    async loadOverview() {
        const res = await this.fetchAdminData(`${this.apiBase}/analytics/overview`);
        if (res) {
            document.getElementById('metric-batches').innerText = res.total_batches_today || 0;
            document.getElementById('metric-qc-done').innerText = res.total_qc_completed || 0;
            document.getElementById('metric-qc-pending').innerText = res.total_qc_pending || 0;
            document.getElementById('metric-alerts').innerText = res.total_open_alerts || 0;
            document.getElementById('alert-badge').innerText = res.total_open_alerts || 0;

            this.initCharts(res);
        }
    },

    initCharts(data) {
        // Mock data for charts if API doesn't provide history yet
        const rootStyles = getComputedStyle(document.documentElement);
        const textColor = rootStyles.getPropertyValue('--text-primary').trim();
        const gridColor = rootStyles.getPropertyValue('--border-color').trim();

        // Trend Chart
        const ctxTrend = document.getElementById('chart-qc-trend');
        if (this.charts.trend) this.charts.trend.destroy();
        
        this.charts.trend = new Chart(ctxTrend, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Batch Produksi',
                    data: [12, 19, 15, 22, 20, 10, 5],
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
                labels: ['Pass', 'Warning', 'Fail', 'Pending'],
                datasets: [{
                    data: [
                        data.total_qc_completed || 10, 
                        2, 
                        1, 
                        data.total_qc_pending || 5
                    ],
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
            grid.innerHTML = '<p>Belum ada data unit pendingin.</p>';
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
                    <i class="fas ${statusIcon} metric-icon" style="color: ${statusColor}"></i>
                </div>
                <div class="metric-value">${tempDisplay}</div>
                <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:10px;">
                    Ambang Batas: ${dev.threshold_temp} °C
                </div>
            `;
            grid.appendChild(card);
        });
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
            
            let badgeClass = `status-badge status-${batch.final_qc_status}`;
            let evidenceBtn = batch.photo_url 
                ? `<button class="btn-primary" onclick="adminApp.previewImage('${batch.photo_url}')" style="padding: 4px 8px; font-size:0.8rem;"><i class="fas fa-image"></i> Lihat</button>`
                : '-';

            tr.innerHTML = `
                <td>${new Date(batch.created_at).toLocaleString('id-ID')}</td>
                <td><strong>${batch.batch_code}</strong></td>
                <td>${batch.products?.product_name || '-'}</td>
                <td>${batch.staff_accounts?.full_name || batch.staff_accounts?.username || '-'}</td>
                <td><span class="${badgeClass}">${batch.final_qc_status.toUpperCase()}</span></td>
                <td>${evidenceBtn}</td>
            `;
            tbody.appendChild(tr);
        });
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

    previewImage(url) {
        document.getElementById('modal-image').src = url;
        document.getElementById('image-modal').classList.add('active');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    adminApp.init();
});
