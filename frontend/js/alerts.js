/**
 * Alerts Page Logic
 */
const AlertsPage = {
    async init() {
        if (!Auth.check()) window.location.href = 'login.html';
        await this.loadAlerts();
    },

    async loadAlerts() {
        const container = document.getElementById('alertList');
        if (!container) return;

        try {
            const alerts = await API.get('/alerts');
            container.innerHTML = '';

            if (alerts.length === 0) {
                container.innerHTML = `
                    <div class="empty-state" style="text-align: center; padding: 40px;">
                        <i class="fas fa-check-circle" style="font-size: 48px; color: var(--status-pass); margin-bottom: 16px;"></i>
                        <p style="color: var(--text-secondary);">Semua sistem normal. Tidak ada alert aktif.</p>
                    </div>
                `;
                return;
            }

            alerts.forEach(alert => {
                container.innerHTML += this.renderAlertCard(alert);
            });
        } catch (err) {
            UI.toast('Gagal memuat alert', 'error');
        }
    },

    renderAlertCard(alert) {
        const time = Utils.formatTime(alert.created_at);
        const isAdmin = Auth.isAdmin();
        
        const resolveBtn = isAdmin ? `
            <button onclick="AlertsPage.resolve('${alert.id}')" style="width: 100%; padding: 12px; background: rgba(255,255,255,0.05); border: 1px solid var(--glass-border); color: var(--text-primary); border-radius: 12px; font-weight: 600; margin-top: 8px; cursor: pointer; transition: all 0.3s;">
                RESOLVE ISSUE
            </button>
        ` : '';

        return `
            <div class="alert-card fail" style="flex-direction: column; align-items: flex-start; gap: 12px;">
                <div style="display: flex; align-items: center; gap: 12px; width: 100%;">
                    <div class="alert-icon"><i class="fas fa-exclamation-triangle"></i></div>
                    <div class="alert-info">
                        <h4 style="color: var(--status-fail);">${alert.zone || 'Batch Violation'}</h4>
                        <p>${time} • Value: ${alert.temperature_c || alert.description}°C</p>
                    </div>
                    <div class="alert-status fail">CRITICAL</div>
                </div>
                <div style="background: var(--status-fail-bg); padding: 12px; border-radius: 12px; font-size: 13px; border-left: 4px solid var(--status-fail); width: 100%; color: var(--text-secondary);">
                    <strong>Corrective Action:</strong><br>
                    ${this.getSOPAction(alert.zone)}
                </div>
                ${resolveBtn}
            </div>
        `;
    },

    getSOPAction(zone) {
        if (zone?.includes('Chiller')) return 'Pindahkan produk ke chiller cadangan dan periksa kompresor.';
        if (zone?.includes('Freezer')) return 'Jangan buka pintu freezer. Hubungi maintenance segera.';
        return 'Periksa integritas batch dan lakukan pengecekan ulang parameter QC.';
    },

    async resolve(id) {
        try {
            await API.post(`/alerts/${id}/resolve`, {});
            UI.toast('Alert resolved', 'success');
            await this.loadAlerts();
        } catch (err) {
            UI.toast('Gagal menyelesaikan alert', 'error');
        }
    }
};
