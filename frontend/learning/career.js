const CareerRecommendation = {
    async init() {
        if (!Auth.check()) {
            window.location.href = '/staff/login.html';
            return;
        }
        await this.load();
    },

    async load() {
        try {
            const response = await API.get('/learning/career-recommendation');
            const data = response.data || {};
            this.renderPrimary(data.primary || {});
            this.renderScores(data.scores || {});
            this.renderRecommendations(data.recommendations || []);
        } catch (error) {
            document.getElementById('careerGrid').innerHTML = `
                <div class="career-card">
                    <h3>Rekomendasi belum tersedia</h3>
                    <p>${this.escape(error.message || 'Lengkapi skor learning, simulation, dan quiz terlebih dahulu.')}</p>
                </div>
            `;
        }
    },

    renderPrimary(primary) {
        document.getElementById('primaryCareer').textContent = primary.title || '-';
        document.getElementById('primaryMatch').textContent = `${primary.match_percent || 0}% match`;
    },

    renderScores(scores) {
        document.getElementById('careerLearningScore').textContent = `${scores.learning || 0}%`;
        document.getElementById('careerSimulationScore').textContent = `${scores.simulation || 0}%`;
        document.getElementById('careerQuizScore').textContent = `${scores.quiz || 0}%`;
    },

    renderRecommendations(items) {
        const grid = document.getElementById('careerGrid');
        if (!items.length) {
            grid.innerHTML = '<div class="career-card">Belum ada rekomendasi.</div>';
            return;
        }
        grid.innerHTML = items.map((item, index) => `
            <article class="career-card ${index === 0 ? 'primary-career' : ''}">
                <div class="career-card-head">
                    <h3>${this.escape(item.title)}</h3>
                    <strong>${item.match_percent || 0}%</strong>
                </div>
                <div class="progress-track"><div style="width:${Math.max(0, Math.min(100, Number(item.match_percent) || 0))}%"></div></div>
                <ul>
                    ${(item.reasons || []).map(reason => `<li>${this.escape(reason)}</li>`).join('')}
                </ul>
            </article>
        `).join('');
    },

    escape(value) {
        return String(value ?? '').replace(/[&<>"']/g, char => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[char]));
    }
};

document.addEventListener('DOMContentLoaded', () => CareerRecommendation.init());
