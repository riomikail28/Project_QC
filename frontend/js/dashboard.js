/**
 * QC Central Kitchen - Real Data Dashboard Controller
 */

const Dashboard = {
    refreshTimer: null,
    lazyRenderTimer: null,

    async init() {
        await this.loadAll();
        clearInterval(this.refreshTimer);
        this.refreshTimer = setInterval(() => this.loadAll({ silent: true }), 30000);
    },

    async loadAll({ silent = false } = {}) {
        const started = performance.now();
        if (!silent) this.setLoading();
        try {
            // PERFORMANCE_OPTIMIZED: KPI data is rendered first; secondary panels follow after idle/visibility.
            const [summary, trend, qcStatus, monitoring, alerts, todaySummary, schedule] = await Promise.all([
                this.fetchEnvelope('/dashboard/summary'),
                this.fetchEnvelope('/dashboard/production-trend'),
                this.fetchEnvelope('/dashboard/qc-status'),
                this.fetchEnvelope('/dashboard/realtime-monitoring'),
                this.fetchEnvelope('/dashboard/alerts'),
                this.fetchEnvelope('/dashboard/today-summary'),
                this.fetchOptionalEnvelope('/facility/monitoring/schedule/today'),
            ]);

            this.renderTaskNow(summary, todaySummary, schedule);
            this.renderCompactToday(summary, todaySummary, schedule);
            this.renderSummary(summary);
            this.deferSecondaryRender(() => {
                this.renderProductionTrend(trend);
                this.renderQcStatus(qcStatus);
                this.renderMonitoring(monitoring);
                this.renderCriticalIssues(alerts);
                this.renderTodaySummary(todaySummary);
                this.refreshIcons();
            });
            console.info(`[PERFORMANCE_OPTIMIZED] Dashboard load time: ${Math.round(performance.now() - started)}ms`);
        } catch (error) {
            console.error('Failed to load real dashboard data:', error);
            this.renderError();
        }
    },

    async fetchEnvelope(endpoint) {
        const response = await API.getSWR(endpoint, {
            ttlMs: 60000,
            onUpdate: data => this.renderEndpointUpdate(endpoint, data?.data)
        });
        if (!response || response.success !== true) {
            throw new Error(response?.message || `Failed to load ${endpoint}`);
        }
        return response.data;
    },

    async fetchOptionalEnvelope(endpoint) {
        try {
            const response = await API.getSWR(endpoint, {
                ttlMs: 60000,
                onUpdate: data => this.renderEndpointUpdate(endpoint, data?.data)
            });
            if (!response || response.success !== true) return null;
            return response.data;
        } catch (error) {
            console.warn(`Optional dashboard data failed: ${endpoint}`, error);
            return null;
        }
    },

    deferSecondaryRender(callback) {
        clearTimeout(this.lazyRenderTimer);
        const run = () => {
            if (document.visibilityState === 'hidden') {
                this.lazyRenderTimer = setTimeout(run, 250);
                return;
            }
            callback();
        };
        if (window.requestIdleCallback) {
            requestIdleCallback(run, { timeout: 800 });
        } else {
            this.lazyRenderTimer = setTimeout(run, 0);
        }
    },

    renderEndpointUpdate(endpoint, data) {
        if (!data) return;
        if (endpoint === '/dashboard/summary') {
            this.renderSummary(data);
        } else if (endpoint === '/dashboard/production-trend') {
            this.renderProductionTrend(data);
        } else if (endpoint === '/dashboard/qc-status') {
            this.renderQcStatus(data);
        } else if (endpoint === '/dashboard/realtime-monitoring') {
            this.renderMonitoring(data);
        } else if (endpoint === '/dashboard/alerts') {
            this.renderCriticalIssues(data);
        } else if (endpoint === '/dashboard/today-summary') {
            this.renderTodaySummary(data);
        }
        this.refreshIcons();
    },

    setLoading() {
        [
            'totalBatches', 'totalAlerts', 'qcSuccessRate', 'pendingApproval', 'avgFreezerTemp', 'healthValue',
            'taskMonitoringCount', 'taskBatchCount', 'taskRecheckCount', 'taskFindingCount',
            'staffMonitoringDone', 'staffBatchQcDone', 'staffFindingsToday', 'staffPassRate'
        ].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '...';
        });
        this.setHtml('criticalList', '<div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div>');
        this.setHtml('realtimeMonitoringList', '<div class="skeleton skeleton-card"></div>');
        this.setHtml('todaySummaryList', '<div class="skeleton skeleton-card"></div>');
        this.setHtml('qcStatusList', '<span class="status-badge muted">Memuat...</span>');
    },

    renderTaskNow(summary = {}, todaySummary = {}, schedule = {}) {
        const monitoringPending = this.pendingMonitoringDevices(schedule);
        const pendingBatch = Number(
            summary.batch_pending_qc ??
            summary.pending_qc ??
            Math.max(Number(summary.pending_approval || 0), Number(summary.total_batches_today || 0) - Number(todaySummary.qc_submitted || 0))
        );
        const recheckPending = Number(summary.recheck_pending ?? todaySummary.recheck_pending ?? 0);
        const findingOpen = Number(summary.qc_findings_open ?? summary.open_findings ?? todaySummary.qc_findings_open ?? todaySummary.findings_open ?? 0);

        this.text('taskMonitoringCount', `${monitoringPending} Device Belum Dicek`);
        this.text('taskBatchCount', `${Math.max(0, pendingBatch)} Batch`);
        this.text('taskRecheckCount', `${Math.max(0, recheckPending)} Re-check`);
        this.text('taskFindingCount', `${Math.max(0, findingOpen)} Temuan`);
    },

    renderCompactToday(summary = {}, todaySummary = {}, schedule = {}) {
        const completedMonitoring = schedule?.completed_count ?? todaySummary.temperature_logs ?? 0;
        const findingsToday = todaySummary.qc_findings ?? todaySummary.findings ?? todaySummary.photo_findings ?? 0;
        this.text('staffMonitoringDone', completedMonitoring);
        this.text('staffBatchQcDone', todaySummary.qc_submitted ?? 0);
        this.text('staffFindingsToday', findingsToday);
        this.text('staffPassRate', summary.qc_success_rate === null || summary.qc_success_rate === undefined ? '--' : `${summary.qc_success_rate}%`);
    },

    pendingMonitoringDevices(schedule = {}) {
        const statuses = Object.values(schedule?.device_statuses || {});
        if (statuses.length) {
            return statuses.filter(item => {
                const active = item?.active_status;
                return active && active.status !== 'completed';
            }).length;
        }
        const currentSlot = schedule?.current_slot;
        if (!currentSlot || currentSlot.status !== 'pending') return 0;
        const total = Number(currentSlot.total_devices ?? schedule.total_devices ?? 0);
        const completed = Number(currentSlot.completed_count ?? 0);
        return Math.max(0, total - completed);
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
            label.textContent = 'Belum ada data';
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
            label.textContent = 'Kondisi QC Baik';
            label.style.color = '#22c55e';
            progress.style.stroke = '#22c55e';
        } else if (cleanScore >= 70) {
            label.textContent = 'Operasional Stabil';
            label.style.color = '#f59e0b';
            progress.style.stroke = '#f59e0b';
        } else {
            label.textContent = 'Perlu Perhatian';
            label.style.color = '#ef4444';
            progress.style.stroke = '#ef4444';
        }
    },

    renderProductionTrend(rows = []) {
        const chart = document.getElementById('productionTrendChart');
        if (!chart) return;
        if (!rows.length || rows.every(row => Number(row.count || 0) === 0)) {
            chart.classList.add('empty-chart');
            chart.innerHTML = '<div class="empty-state compact">Belum ada data</div>';
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
            list.innerHTML = '<span class="status-badge muted">Belum ada data</span>';
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
            container.innerHTML = '<div class="empty-state compact">Belum ada data</div>';
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
            container.innerHTML = '<div class="empty-state compact">Belum ada data</div>';
            return;
        }
        container.innerHTML = alerts.slice(0, 5).map(alert => `
            <div class="alert-card fail">
                <div class="alert-icon"><i data-lucide="triangle-alert"></i></div>
                <div class="alert-info">
                    <h4>${alert.zone || 'Alert QC'}</h4>
                    <p>${alert.description || 'Suhu abnormal'}${alert.created_at ? ` - ${this.time(alert.created_at)}` : ''}</p>
                </div>
                <div class="alert-status fail">${alert.temperature_c ?? alert.severity ?? 'Open'}</div>
            </div>
        `).join('');
    },

    renderTodaySummary(data = {}) {
        const container = document.getElementById('todaySummaryList');
        if (!container) return;
        if (!data.has_data) {
            container.innerHTML = '<div class="empty-state compact">Belum ada data</div>';
            return;
        }
        const rows = [
            ['camera', 'Foto Inspeksi', `${data.photo_evidence || 0} foto diupload`, 'success'],
            ['clipboard-check', 'QC Terkirim', `${data.qc_submitted || 0} laporan hari ini`, 'success'],
            ['thermometer', 'Log Suhu', `${data.temperature_logs || 0} input suhu`, 'warning'],
            ['qr-code', 'Label Barcode', `${data.barcode_labels || 0} label tercatat`, 'muted'],
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
        if (label) label.textContent = 'Gagal memuat dashboard';
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
            return 'Baru saja';
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
