/**
 * QC Central Kitchen - Real Data Dashboard Controller
 */

const Dashboard = {
    refreshTimer: null,

    async init() {
        await this.loadAll();
        clearInterval(this.refreshTimer);
        this.refreshTimer = setInterval(() => this.loadAll({ silent: true }), 30000);
    },

    async loadAll({ silent = false } = {}) {
        if (!silent) this.setLoading();
        try {
            const [summary, trend, qcStatus, monitoring, alerts, todaySummary] = await Promise.all([
                this.fetchEnvelope('/dashboard/summary'),
                this.fetchEnvelope('/dashboard/production-trend'),
                this.fetchEnvelope('/dashboard/qc-status'),
                this.fetchEnvelope('/dashboard/realtime-monitoring'),
                this.fetchEnvelope('/dashboard/alerts'),
                this.fetchEnvelope('/dashboard/today-summary'),
            ]);

            this.renderSummary(summary);
            this.renderProductionTrend(trend);
            this.renderQcStatus(qcStatus);
            this.renderMonitoring(monitoring);
            this.renderCriticalIssues(alerts);
            this.renderTodaySummary(todaySummary);
            this.refreshIcons();
        } catch (error) {
            console.error('Failed to load real dashboard data:', error);
            this.renderError();
        }
    },

    async fetchEnvelope(endpoint) {
        const response = await API.get(endpoint);
        if (!response || response.success !== true) {
            throw new Error(response?.message || `Failed to load ${endpoint}`);
        }
        return response.data;
    },

    setLoading() {
        ['totalBatches', 'totalAlerts', 'qcSuccessRate', 'pendingApproval', 'avgFreezerTemp', 'healthValue'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '...';
        });
        this.setHtml('criticalList', '<div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div>');
        this.setHtml('realtimeMonitoringList', '<div class="skeleton skeleton-card"></div>');
        this.setHtml('todaySummaryList', '<div class="skeleton skeleton-card"></div>');
        this.setHtml('qcStatusList', '<span class="status-badge muted">Loading...</span>');
    },

    renderSummary(data = {}) {
        this.text('totalBatches', data.total_batches_today ?? 0);
        this.text('totalAlerts', data.total_alerts ?? 0);
        this.text('qcSuccessRate', data.qc_success_rate === null || data.qc_success_rate === undefined ? '--' : `${data.qc_success_rate}%`);
        this.text('pendingApproval', data.pending_approval ?? 0);
        this.text('avgFreezerTemp', data.avg_freezer_temperature === null || data.avg_freezer_temperature === undefined ? '--' : `${data.avg_freezer_temperature}`);
        this.renderHealth(data.health_score);

        const badge = document.getElementById('alertBadge');
        if (badge) {
            const count = Number(data.total_alerts || 0);
            badge.textContent = count;
            badge.style.display = count > 0 ? 'grid' : 'none';
        }
    },

    renderHealth(score) {
        const value = document.getElementById('healthValue');
        const progress = document.getElementById('healthProgress');
        const label = document.getElementById('healthLabel');
        if (!value || !progress || !label) return;

        if (score === null || score === undefined) {
            value.textContent = '--';
            label.textContent = 'No data available yet';
            label.style.color = '#64748b';
            progress.style.strokeDashoffset = 283;
            progress.style.stroke = '#94a3b8';
            return;
        }

        const cleanScore = Math.max(0, Math.min(100, Number(score)));
        value.textContent = Math.round(cleanScore);
        const radius = 45;
        const circumference = 2 * Math.PI * radius;
        progress.style.strokeDasharray = circumference;
        progress.style.strokeDashoffset = circumference - (cleanScore / 100) * circumference;

        if (cleanScore >= 90) {
            label.textContent = 'Excellent Quality Control';
            label.style.color = '#22c55e';
            progress.style.stroke = '#22c55e';
        } else if (cleanScore >= 70) {
            label.textContent = 'Stable Operations';
            label.style.color = '#f59e0b';
            progress.style.stroke = '#f59e0b';
        } else {
            label.textContent = 'Attention Required';
            label.style.color = '#ef4444';
            progress.style.stroke = '#ef4444';
        }
    },

    renderProductionTrend(rows = []) {
        const chart = document.getElementById('productionTrendChart');
        if (!chart) return;
        if (!rows.length || rows.every(row => Number(row.count || 0) === 0)) {
            chart.classList.add('empty-chart');
            chart.innerHTML = '<div class="empty-state compact">No data available yet</div>';
            return;
        }

        chart.classList.remove('empty-chart');
        const max = Math.max(...rows.map(row => Number(row.count || 0)), 1);
        chart.innerHTML = rows.map(row => {
            const height = Math.max(8, Math.round((Number(row.count || 0) / max) * 100));
            const label = new Date(row.date).toLocaleDateString('id-ID', { weekday: 'short' });
            return `<div class="trend-bar-wrap"><span class="trend-bar" style="height:${height}%"></span><small>${label}</small><strong>${row.count || 0}</strong></div>`;
        }).join('');
    },

    renderQcStatus(data = {}) {
        const list = document.getElementById('qcStatusList');
        const pie = document.getElementById('qcStatusPie');
        if (!list || !pie) return;

        const items = data.items || [];
        const total = Number(data.total || 0);
        if (!total) {
            list.innerHTML = '<span class="status-badge muted">No data available yet</span>';
            pie.style.background = 'conic-gradient(#cbd5e1 0 100%)';
            return;
        }

        const colors = { pass: '#10b981', warning: '#f59e0b', fail: '#ef4444', pending: '#64748b' };
        let cursor = 0;
        const segments = items.map(item => {
            const pct = (Number(item.count || 0) / total) * 100;
            const segment = `${colors[item.status] || '#64748b'} ${cursor}% ${cursor + pct}%`;
            cursor += pct;
            return segment;
        }).join(', ');
        pie.style.background = `conic-gradient(${segments})`;
        list.innerHTML = items.map(item => {
            const pct = Math.round((Number(item.count || 0) / total) * 100);
            return `<span class="status-badge ${this.statusTone(item.status)}">${item.status.toUpperCase()} ${pct}% (${item.count})</span>`;
        }).join('');
    },

    renderMonitoring(rows = []) {
        const container = document.getElementById('realtimeMonitoringList');
        if (!container) return;
        if (!rows.length) {
            container.innerHTML = '<div class="empty-state compact">No data available yet</div>';
            return;
        }
        container.innerHTML = rows.slice(0, 5).map(row => `
            <div class="monitor-row">
                <div class="alert-icon ${row.is_normal ? 'pass' : 'fail'}"><i data-lucide="${this.deviceIcon(row.device_type)}"></i></div>
                <div>
                    <strong>${row.device || row.room || 'Temperature Point'}</strong>
                    <p class="card-label">${row.room || 'QC Area'}${row.recorded_at ? ` - ${this.time(row.recorded_at)}` : ''}</p>
                </div>
                <div class="temp-value">${row.temperature_c ?? '--'}C</div>
            </div>
        `).join('');
    },

    renderCriticalIssues(alerts = []) {
        const container = document.getElementById('criticalList');
        if (!container) return;
        if (!alerts.length) {
            container.innerHTML = '<div class="empty-state compact">No data available yet</div>';
            return;
        }
        container.innerHTML = alerts.slice(0, 5).map(alert => `
            <div class="alert-card fail">
                <div class="alert-icon"><i data-lucide="triangle-alert"></i></div>
                <div class="alert-info">
                    <h4>${alert.zone || 'QC Alert'}</h4>
                    <p>${alert.description || 'Temperature abnormal'}${alert.created_at ? ` - ${this.time(alert.created_at)}` : ''}</p>
                </div>
                <div class="alert-status fail">${alert.temperature_c ?? alert.severity ?? 'Open'}</div>
            </div>
        `).join('');
    },

    renderTodaySummary(data = {}) {
        const container = document.getElementById('todaySummaryList');
        if (!container) return;
        if (!data.has_data) {
            container.innerHTML = '<div class="empty-state compact">No data available yet</div>';
            return;
        }
        const rows = [
            ['camera', 'Photo inspection', `${data.photo_evidence || 0} evidence uploaded`, 'success'],
            ['clipboard-check', 'QC submitted', `${data.qc_submitted || 0} report hari ini`, 'success'],
            ['thermometer', 'Temperature logs', `${data.temperature_logs || 0} input suhu`, 'warning'],
            ['qr-code', 'Barcode labels', `${data.barcode_labels || 0} label tercatat`, 'muted'],
        ];
        container.innerHTML = rows.map(([icon, title, subtitle, tone]) => `
            <div class="alert-card">
                <div class="alert-icon"><i data-lucide="${icon}"></i></div>
                <div class="alert-info"><h4>${title}</h4><p>${subtitle}</p></div>
                <span class="status-badge ${tone}">Live</span>
            </div>
        `).join('');
    },

    renderError() {
        this.text('healthValue', '--');
        const label = document.getElementById('healthLabel');
        if (label) label.textContent = 'Dashboard API error';
        const errorHtml = '<div class="empty-state compact error">Gagal memuat data real. Coba refresh atau cek koneksi.</div>';
        ['criticalList', 'realtimeMonitoringList', 'todaySummaryList'].forEach(id => this.setHtml(id, errorHtml));
    },

    statusTone(status) {
        return { pass: 'success', warning: 'warning', fail: 'danger', pending: 'muted' }[status] || 'muted';
    },

    deviceIcon(type) {
        if (type === 'freezer') return 'snowflake';
        if (type === 'chiller') return 'thermometer';
        return 'activity';
    },

    time(value) {
        try {
            return new Date(value).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
        } catch {
            return 'Just now';
        }
    },

    text(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    },

    setHtml(id, value) {
        const el = document.getElementById(id);
        if (el) el.innerHTML = value;
    },

    refreshIcons() {
        if (window.lucide) lucide.createIcons();
    },
};
