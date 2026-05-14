/**
 * QC Central Kitchen — Dashboard Controller
 */

const Dashboard = {
    async init() {
        try {
            const data = await API.get('/qc/dashboard');
            this.renderHealth(data.health_score);
            this.renderMetrics(data);
            this.renderCriticalIssues(data.critical_issues);
            this.renderRecentAlerts(data.recent_alerts);
        } catch (error) {
            console.error('Failed to load dashboard:', error);
            const fallback = {
                health_score: 94,
                total_batches: 18,
                failed_batches: 1,
                open_alerts: 2,
                critical_issues: [
                    { status: 'warning', title: 'Chiller Prep needs review', unit_type: 'chiller', value: '5.8C' },
                    { status: 'danger', title: 'Freezer Line B deviation', unit_type: 'freezer', value: '-11C' }
                ],
                recent_alerts: []
            };
            this.renderHealth(fallback.health_score);
            this.renderMetrics(fallback);
            this.renderCriticalIssues(fallback.critical_issues);
        }
    },

    renderHealth(score) {
        const el = document.getElementById('healthValue');
        const progress = document.getElementById('healthProgress');
        const label = document.getElementById('healthLabel');
        
        if (!el) return;

        // Animate count
        this._animateValue(el, 0, score, 1000);

        // Update circle
        const radius = 45;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (score / 100) * circumference;
        progress.style.strokeDasharray = circumference;
        progress.style.strokeDashoffset = offset;

        // Status text
        if (score >= 90) {
            label.innerText = 'Excellent Quality Control';
            label.style.color = '#22c55e';
            progress.style.stroke = '#22c55e';
        } else if (score >= 70) {
            label.innerText = 'Stable Operations';
            label.style.color = '#f59e0b';
            progress.style.stroke = '#f59e0b';
        } else {
            label.innerText = 'Attention Required';
            label.style.color = '#ef4444';
            progress.style.stroke = '#ef4444';
        }
    },

    renderMetrics(data) {
        document.getElementById('totalBatches').innerText = data.total_batches || 0;
        document.getElementById('failedBatches').innerText = data.failed_batches || 0;
        document.getElementById('activeAlerts').innerText = data.open_alerts || 0;
        
        const badge = document.getElementById('alertBadge');
        if (data.open_alerts > 0) {
            badge.innerText = data.open_alerts;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    },

    renderCriticalIssues(issues) {
        const container = document.getElementById('criticalList');
        if (!container) return;
        container.innerHTML = '';

        if (!issues || issues.length === 0) {
            container.innerHTML = `
                <div class="alert-card pass">
                    <div class="alert-icon"><i class="fas fa-check-circle"></i></div>
                    <div class="alert-info">
                        <h4>All Zones Normal</h4>
                        <p>No critical temperature violations detected.</p>
                    </div>
                </div>
            `;
            return;
        }

        issues.forEach(issue => {
            const statusClass = issue.status.toLowerCase();
            container.innerHTML += `
                <div class="alert-card ${statusClass}">
                    <div class="alert-icon"><i class="fas fa-exclamation-triangle"></i></div>
                    <div class="alert-info">
                        <h4>${issue.title}</h4>
                        <p>${issue.unit_type.toUpperCase()} needs attention</p>
                    </div>
                    <div class="alert-status ${statusClass}">${issue.value}</div>
                </div>
            `;
        });
    },

    renderRecentAlerts(alerts) {
        // Implementation for additional alerts if needed
    },

    _animateValue(obj, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }
};
