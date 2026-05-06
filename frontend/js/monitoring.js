/**
 * QC Central Kitchen — Monitoring Controller
 */

const Monitoring = {
    async init() {
        this.loadHistory();
    },

    async submit(payload) {
        return await API.post('/temperature', payload);
    },

    async loadHistory() {
        const list = document.getElementById('historyList');
        try {
            const data = await API.get('/temperature/latest');
            list.innerHTML = '';
            
            if (data.length === 0) {
                list.innerHTML = '<p class="empty-state">No readings recorded yet.</p>';
                return;
            }

            data.forEach(row => {
                const statusClass = row.is_normal ? 'pass' : 'fail';
                const time = new Date(row.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                
                list.innerHTML += `
                    <div class="log-entry">
                        <div class="log-dot ${statusClass}"></div>
                        <div class="log-zone">${row.zone}</div>
                        <div class="log-temp">${row.temperature_c}°C</div>
                        <div class="log-time">${time}</div>
                    </div>
                `;
            });
        } catch (error) {
            list.innerHTML = '<p class="error">Failed to load history.</p>';
        }
    },

    displayResult(res) {
        const container = document.getElementById('resultContainer');
        const data = res.data;
        const statusClass = data.status.toLowerCase();
        
        container.innerHTML = `
            <div class="result-card ${statusClass}">
                <div class="result-info">
                    <strong>${data.room_name} (${data.unit_type})</strong>
                    <p>Status: ${data.status}</p>
                    <p style="color: var(--text-muted)">${data.alert.message}</p>
                </div>
                <div class="result-temp">${data.temperature}°C</div>
            </div>
        `;

        // Refresh list
        this.loadHistory();
    }
};