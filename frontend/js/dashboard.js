/**
 * QC Central Kitchen - Real Data Dashboard Controller
 */

const Dashboard = {
    refreshTimer: null,
    lazyRenderTimer: null,

    async init() {
        const hasCache = this.restoreCache();
        await this.loadAll({ silent: hasCache });
        clearInterval(this.refreshTimer);
        this.refreshTimer = setInterval(() => this.loadAll({ silent: true }), 30000);

        // Prefetch facility structure and inspection products for other pages
        if (window.requestIdleCallback) {
            requestIdleCallback(() => {
                API.getCached('/facility/structure', 600000).catch(() => {});
                API.getCached('/inspection/products', 1800000).catch(() => {});
            });
        } else {
            setTimeout(() => {
                API.getCached('/facility/structure', 600000).catch(() => {});
                API.getCached('/inspection/products', 1800000).catch(() => {});
            }, 1000);
        }
    },

    saveCache() {
        try {
            const data = {
                taskMonitoringCount: document.getElementById('taskMonitoringCount')?.textContent || '',
                taskBatchCount: document.getElementById('taskBatchCount')?.textContent || '',
                taskRecheckCount: document.getElementById('taskRecheckCount')?.textContent || '',
                taskFindingCount: document.getElementById('taskFindingCount')?.textContent || '',
                
                staffMonitoringDone: document.getElementById('staffMonitoringDone')?.textContent || '',
                staffBatchQcDone: document.getElementById('staffBatchQcDone')?.textContent || '',
                staffFindingsToday: document.getElementById('staffFindingsToday')?.textContent || '',
                staffPassRate: document.getElementById('staffPassRate')?.textContent || '',
                
                healthValue: document.getElementById('healthValue')?.textContent || '0',
                healthLabel: document.getElementById('healthLabel')?.textContent || '',
                healthProgressOffset: document.getElementById('healthProgress')?.style.strokeDashoffset || '',
                healthProgressStroke: document.getElementById('healthProgress')?.style.stroke || '',
                
                totalBatches: document.getElementById('totalBatches')?.textContent || '0',
                totalAlerts: document.getElementById('totalAlerts')?.textContent || '0',
                qcSuccessRate: document.getElementById('qcSuccessRate')?.textContent || '--',
                pendingApproval: document.getElementById('pendingApproval')?.textContent || '0',
                avgFreezerTemp: document.getElementById('avgFreezerTemp')?.textContent || '--',
                alertBadge: document.getElementById('alertBadge')?.textContent || '0',
                alertBadgeStyle: document.getElementById('alertBadge')?.style.display || 'none',
                
                productionTrendChart: document.getElementById('productionTrendChart')?.innerHTML || '',
                qcStatusPieBackground: document.getElementById('qcStatusPie')?.style.background || '',
                qcStatusList: document.getElementById('qcStatusList')?.innerHTML || '',
                realtimeMonitoringList: document.getElementById('realtimeMonitoringList')?.innerHTML || '',
                criticalList: document.getElementById('criticalList')?.innerHTML || '',
                todaySummaryList: document.getElementById('todaySummaryList')?.innerHTML || '',
                dashboardFindingsGrid: document.getElementById('dashboardFindingsGrid')?.innerHTML || '',
                findings: this.findings || [],
                
                userInitial: document.getElementById('userInitial')?.textContent || 'QC',
            };
            localStorage.setItem('page_cache:staff_dashboard', JSON.stringify(data));
        } catch (e) {
            console.error('Failed to save staff dashboard cache:', e);
        }
    },

    restoreCache() {
        try {
            const dataStr = localStorage.getItem('page_cache:staff_dashboard');
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

            setText('taskMonitoringCount', data.taskMonitoringCount);
            setText('taskBatchCount', data.taskBatchCount);
            setText('taskRecheckCount', data.taskRecheckCount);
            setText('taskFindingCount', data.taskFindingCount);
            
            setText('staffMonitoringDone', data.staffMonitoringDone);
            setText('staffBatchQcDone', data.staffBatchQcDone);
            setText('staffFindingsToday', data.staffFindingsToday);
            setText('staffPassRate', data.staffPassRate);
            
            setText('healthValue', data.healthValue);
            setText('healthLabel', data.healthLabel);
            const progress = document.getElementById('healthProgress');
            if (progress) {
                if (data.healthProgressOffset) progress.style.strokeDashoffset = data.healthProgressOffset;
                if (data.healthProgressStroke) progress.style.stroke = data.healthProgressStroke;
            }
            
            setText('totalBatches', data.totalBatches);
            setText('totalAlerts', data.totalAlerts);
            setText('qcSuccessRate', data.qcSuccessRate);
            setText('pendingApproval', data.pendingApproval);
            setText('avgFreezerTemp', data.avgFreezerTemp);
            
            const badge = document.getElementById('alertBadge');
            if (badge) {
                badge.textContent = data.alertBadge || '0';
                badge.style.display = data.alertBadgeStyle || 'none';
            }
            
            setHtml('productionTrendChart', data.productionTrendChart);
            const pie = document.getElementById('qcStatusPie');
            if (pie && data.qcStatusPieBackground) pie.style.background = data.qcStatusPieBackground;
            
            setHtml('qcStatusList', data.qcStatusList);
            setHtml('realtimeMonitoringList', data.realtimeMonitoringList);
            setHtml('criticalList', data.criticalList);
            setHtml('todaySummaryList', data.todaySummaryList);
            setHtml('dashboardFindingsGrid', data.dashboardFindingsGrid);
            if (data.findings) this.findings = data.findings;
            
            setText('userInitial', data.userInitial);
            
            this.refreshIcons();
            return true;
        } catch (e) {
            console.error('Failed to restore staff dashboard cache:', e);
            return false;
        }
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
                this.loadAnnouncementBadge();
                this.loadFindings();
                this.refreshIcons();
                this.saveCache();
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
        this.saveCache();
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
        this.setHtml('dashboardFindingsGrid', '<div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div>');
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

    async loadAnnouncementBadge() {
        try {
            const announcements = await API.get('/staff/announcements');
            const count = announcements?.length || 0;
            const badge = document.getElementById('announcementBadge');
            if (badge) {
                badge.textContent = count;
                badge.style.display = count > 0 ? 'grid' : 'none';
            }
        } catch (error) {
            console.error('Failed to load announcement badge:', error);
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

    async loadFindings() {
        try {
            const findings = await API.get('/qc/findings');
            this.findings = findings || [];
            this.renderFindings(this.findings);
        } catch (error) {
            console.error('Failed to load findings feed:', error);
            const grid = document.getElementById('dashboardFindingsGrid');
            if (grid) {
                grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: var(--muted); padding: 20px;">Gagal memuat feed temuan.</div>';
            }
        }
    },

    renderFindings(findings = []) {
        const grid = document.getElementById('dashboardFindingsGrid');
        if (!grid) return;
        if (!findings.length) {
            grid.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 40px 24px; color: var(--muted, #64748b);">
                    <i class="fas fa-check-circle" style="font-size: 48px; color: #10b981; margin-bottom: 12px;"></i>
                    <p style="margin: 0; font-weight: 600;">Tidak ada temuan QC aktif saat ini.</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = findings.map(f => {
            const statusLabel = {
                'OPEN': 'Open',
                'IN_PROGRESS': 'In Progress',
                'CLOSED': 'Closed',
                'NOTED': 'Noted'
            }[f.status] || 'Open';

            const statusClass = {
                'OPEN': 'fail',
                'IN_PROGRESS': 'warning',
                'CLOSED': 'pass',
                'NOTED': 'info'
            }[f.status] || 'fail';

            const photoUrls = String(f.photo_url || '').split(';');
            const firstPhoto = photoUrls.find(url => url.trim()) || '';

            let displayReason = f.reason || '';
            let analysisText = '';
            if (displayReason.includes('[Analisis:')) {
                const parts = displayReason.split('[Analisis:');
                displayReason = parts[0].trim();
                analysisText = parts[1].replace(']', '').trim();
            }

            const imgHtml = firstPhoto
                ? `<img src="${firstPhoto}" alt="Temuan" style="width: 100%; height: 110px; object-fit: cover; border-radius: 0; display: block;">`
                : `<div style="width: 100%; height: 110px; background: #f1f5f9; display: flex; align-items: center; justify-content: center; color: #94a3b8;">
                       <i class="fas fa-camera" style="font-size: 24px;"></i>
                   </div>`;

            const dateStr = new Date(f.created_at).toLocaleDateString('id-ID', {
                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });

            return `
                <article class="task-now-card" onclick="Dashboard.openFindingAction('${f.id}')" style="min-height: auto; padding: 0; overflow: hidden; display: flex; flex-direction: column; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; text-align: left;">
                    ${imgHtml}
                    <div style="padding: 12px; display: flex; flex-direction: column; gap: 6px; flex: 1;">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 4px;">
                            <span class="status-badge ${statusClass}" style="padding: 2px 6px; font-size: 10px; font-weight: 800; border-radius: 6px; text-transform: uppercase;">${statusLabel}</span>
                            <span style="font-size: 10px; color: var(--muted, #64748b);">${dateStr}</span>
                        </div>
                        <h4 style="font-size: 13px; font-weight: 800; margin: 0; color: #1e293b; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-align: left;">${this.escapeHtml(displayReason)}</h4>
                        ${analysisText ? `<p style="font-size: 11px; margin: 0; padding: 4px 6px; background: #f8fafc; border-left: 2px solid #6366f1; color: #475569; border-radius: 0 4px 4px 0; font-style: italic; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-align: left;"><strong>Analisis:</strong> ${this.escapeHtml(analysisText)}</p>` : ''}
                        <div style="margin-top: auto; font-size: 11px; color: var(--muted, #64748b); display: flex; align-items: center; gap: 4px; border-top: 1px solid #f1f5f9; padding-top: 6px;">
                            <i class="fas fa-user-circle" style="color: #94a3b8; font-size: 12px;"></i>
                            <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${this.escapeHtml(f.staff_name || 'QC Staff')}</span>
                        </div>
                    </div>
                </article>
            `;
        }).join('');
    },

    escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    },

    openFindingAction(findingId) {
        const f = (this.findings || []).find(item => item.id === findingId);
        if (!f) return;

        let displayReason = f.reason || '';
        let analysisText = '';
        if (displayReason.includes('[Analisis:')) {
            const parts = displayReason.split('[Analisis:');
            displayReason = parts[0].trim();
            analysisText = parts[1].replace(']', '').trim();
        }

        const dateStr = new Date(f.created_at).toLocaleDateString('id-ID', {
            month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });

        const contentHtml = `
            <div style="display: flex; flex-direction: column; gap: 16px;">
                <div style="font-size: 13px; color: #64748b;">
                    <strong>Dilaporkan:</strong> ${this.escapeHtml(f.staff_name || 'QC Staff')} pada ${dateStr}
                </div>
                <div style="padding: 12px; background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;">
                    <div style="font-size: 12px; font-weight: 700; color: #475569; text-transform: uppercase; margin-bottom: 4px;">Detail Temuan</div>
                    <div style="font-size: 14px; color: #1e293b; font-weight: 600; line-height: 1.4;">${this.escapeHtml(displayReason)}</div>
                </div>
                
                <form id="finding-update-form" onsubmit="event.preventDefault(); Dashboard.saveFindingUpdate('${f.id}')" style="display: flex; flex-direction: column; gap: 16px;">
                    <div>
                        <label style="font-size: 13px; font-weight: 700; color: #475569; display: block; margin-bottom: 8px;">Ubah Status Temuan</label>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                            <label style="border: 1px solid #cbd5e1; border-radius: 10px; padding: 12px; text-align: center; cursor: pointer; display: block; font-size: 13px; font-weight: 600; background: ${f.status === 'IN_PROGRESS' ? '#eff6ff' : '#ffffff'}; border-color: ${f.status === 'IN_PROGRESS' ? '#2563eb' : '#cbd5e1'}; color: ${f.status === 'IN_PROGRESS' ? '#2563eb' : '#475569'};">
                                <input type="radio" name="findingStatus" value="IN_PROGRESS" ${f.status === 'IN_PROGRESS' ? 'checked' : ''} style="display:none;" onchange="Dashboard.updateStatusSelection(this)">
                                In Progress
                            </label>
                            <label style="border: 1px solid #cbd5e1; border-radius: 10px; padding: 12px; text-align: center; cursor: pointer; display: block; font-size: 13px; font-weight: 600; background: ${f.status === 'CLOSED' ? '#f0fdf4' : '#ffffff'}; border-color: ${f.status === 'CLOSED' ? '#16a34a' : '#cbd5e1'}; color: ${f.status === 'CLOSED' ? '#16a34a' : '#475569'};">
                                <input type="radio" name="findingStatus" value="CLOSED" ${f.status === 'CLOSED' ? 'checked' : ''} style="display:none;" onchange="Dashboard.updateStatusSelection(this)">
                                Closed
                            </label>
                            <label style="border: 1px solid #cbd5e1; border-radius: 10px; padding: 12px; text-align: center; cursor: pointer; display: block; font-size: 13px; font-weight: 600; background: ${f.status === 'NOTED' ? '#f5f3ff' : '#ffffff'}; border-color: ${f.status === 'NOTED' ? '#6366f1' : '#cbd5e1'}; color: ${f.status === 'NOTED' ? '#6366f1' : '#475569'};">
                                <input type="radio" name="findingStatus" value="NOTED" ${f.status === 'NOTED' ? 'checked' : ''} style="display:none;" onchange="Dashboard.updateStatusSelection(this)">
                                Noted
                            </label>
                        </div>
                    </div>
                    
                    <div>
                        <label for="finding-analysis-input" style="font-size: 13px; font-weight: 700; color: #475569; display: block; margin-bottom: 6px;">Hasil Analisis</label>
                        <textarea id="finding-analysis-input" rows="3" style="width: 100%; border: 1px solid #cbd5e1; border-radius: 12px; padding: 12px; font-size: 14px; color: #1e293b; outline: none; transition: border-color 0.2s;" placeholder="Tulis hasil analisis kejadian qc temuan di sini...">${this.escapeHtml(analysisText)}</textarea>
                    </div>
                    
                    <button type="submit" id="btnSaveFinding" class="btn-primary" style="width: 100%; min-height: 48px; border-radius: 12px; font-size: 14px; font-weight: 700; cursor: pointer; border: none; background: #2563eb; color: white;">Simpan Analisis</button>
                </form>
            </div>
        `;

        if (window.UI && typeof UI.showSheet === 'function') {
            UI.showSheet('Tindak Lanjut Temuan QC', contentHtml);
        } else {
            console.warn('UI Bottom Sheet not available');
        }
    },

    updateStatusSelection(radio) {
        const labels = radio.closest('div').querySelectorAll('label');
        labels.forEach(label => {
            const input = label.querySelector('input');
            if (input.checked) {
                if (input.value === 'IN_PROGRESS') {
                    label.style.background = '#eff6ff';
                    label.style.borderColor = '#2563eb';
                    label.style.color = '#2563eb';
                } else if (input.value === 'CLOSED') {
                    label.style.background = '#f0fdf4';
                    label.style.borderColor = '#16a34a';
                    label.style.color = '#16a34a';
                } else if (input.value === 'NOTED') {
                    label.style.background = '#f5f3ff';
                    label.style.borderColor = '#6366f1';
                    label.style.color = '#6366f1';
                }
            } else {
                label.style.background = '#ffffff';
                label.style.borderColor = '#cbd5e1';
                label.style.color = '#475569';
            }
        });
    },

    async saveFindingUpdate(findingId) {
        const form = document.getElementById('finding-update-form');
        const selectedRadio = form?.querySelector('input[name="findingStatus"]:checked');
        const notes = document.getElementById('finding-analysis-input')?.value || '';
        const submitBtn = document.getElementById('btnSaveFinding');

        if (!selectedRadio) {
            if (window.showToast) window.showToast('Pilih status temuan terlebih dahulu.', 'error');
            return;
        }

        const status = selectedRadio.value;
        const originalBtnText = submitBtn.innerHTML;

        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Menyimpan...';

            const response = await API.patch(`/qc/findings/${findingId}`, {
                status: status,
                analysis_notes: notes
            });

            if (response && response.success) {
                if (window.showToast) window.showToast('✓ Temuan berhasil diperbarui', 'success');
                if (window.UI && typeof UI.hideSheet === 'function') {
                    UI.hideSheet();
                }
                this.loadFindings();
            } else {
                if (window.showToast) window.showToast(response.message || 'Gagal memperbarui temuan.', 'error');
            }
        } catch (error) {
            console.error('Failed to update finding:', error);
            if (window.showToast) window.showToast('Gagal memperbarui temuan.', 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        }
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
