const ITDV = {
    modules: [],
    simulations: [],
    quizzes: [],

    async init() {
        if (!Auth.check()) {
            window.location.href = '/staff/login.html';
            return;
        }
        await Promise.all([
            this.loadModules(),
            this.loadProgress(),
            this.loadSimulations(),
            this.loadQuizzes()
        ]);
        document.getElementById('certificateBtn').addEventListener('click', () => this.generateCertificate());
        if (window.lucide) lucide.createIcons();
    },

    async loadModules() {
        const response = await API.get('/learning/modules');
        this.modules = response.data || [];
        const grid = document.getElementById('moduleGrid');
        grid.innerHTML = this.modules.map(module => `
            <article class="module-card ${module.completed ? 'completed' : ''}">
                <div class="module-meta">
                    <span>${this.escape(module.category)}</span>
                    <span>${module.duration_minutes || 0} menit</span>
                </div>
                <h3>${this.escape(module.title)}</h3>
                <p>${this.escape(module.summary)}</p>
                <ul>
                    ${(module.objectives || []).map(item => `<li>${this.escape(item)}</li>`).join('')}
                </ul>
                <button class="secondary-btn" type="button" onclick="ITDV.completeModule('${module.slug}')">
                    ${module.completed ? 'Selesai' : 'Tandai selesai'}
                </button>
            </article>
        `).join('');
    },

    async completeModule(slug) {
        await API.post(`/learning/modules/${slug}/complete`, {});
        await this.loadModules();
        await this.loadProgress();
    },

    async loadProgress() {
        const response = await API.get('/learning/progress');
        const progress = response.data || {};
        document.getElementById('progressPercent').textContent = `${progress.percent || 0}%`;
        document.getElementById('progressBar').style.width = `${progress.percent || 0}%`;
        document.getElementById('progressText').textContent = `${progress.completed_modules || 0} dari ${progress.total_modules || 0} modul selesai`;
    },

    async loadSimulations() {
        const response = await API.get('/learning/simulations');
        this.simulations = response.data || [];
        const simulation = this.simulations[0];
        const card = document.getElementById('simulationCard');
        if (!simulation) {
            card.innerHTML = '<p>Belum ada simulasi.</p>';
            return;
        }
        card.innerHTML = `
            <h3>${this.escape(simulation.title)}</h3>
            <p>${this.escape(simulation.scenario)}</p>
            <div class="scenario-facts">
                <div class="fact-box"><span>Area</span><strong>${this.escape(simulation.area)}</strong></div>
                <div class="fact-box"><span>Target</span><strong>${simulation.target_c}&deg;C</strong></div>
                <div class="fact-box"><span>Aktual</span><strong>${simulation.actual_c}&deg;C</strong></div>
            </div>
            <div class="option-stack">
                ${(simulation.options || []).map(option => `
                    <button class="option-btn" type="button" onclick="ITDV.submitSimulation('${simulation.id}', '${option.key}')">
                        ${option.key}. ${this.escape(option.label)}
                    </button>
                `).join('')}
            </div>
        `;
    },

    async submitSimulation(id, selectedAction) {
        const response = await API.post(`/learning/simulations/${id}/submit`, { selected_action: selectedAction });
        const result = response.data || {};
        document.getElementById('simulationResult').innerHTML = `
            <div class="result-score">${result.score || 0}</div>
            <p>${this.escape(result.feedback || '')}</p>
            <p><strong>Aksi ideal:</strong> ${(result.best_actions || []).join(' lalu ')}</p>
        `;
    },

    async loadQuizzes() {
        const response = await API.get('/learning/quizzes');
        this.quizzes = response.data || [];
        const quiz = this.quizzes[0];
        const form = document.getElementById('quizForm');
        if (!quiz) {
            form.innerHTML = '<p>Belum ada quiz.</p>';
            return;
        }
        form.dataset.quizId = quiz.id;
        form.innerHTML = `
            <h3>${this.escape(quiz.title)}</h3>
            ${(quiz.questions || []).map((question, index) => `
                <div class="question-block">
                    <strong>${index + 1}. ${this.escape(question.text)}</strong>
                    ${(question.options || []).map(option => `
                        <label class="choice-label">
                            <input type="radio" name="${question.id}" value="${option.key}" required>
                            <span>${option.key}. ${this.escape(option.label)}</span>
                        </label>
                    `).join('')}
                </div>
            `).join('')}
            <button class="primary-btn quiz-submit" type="submit">Submit Quiz</button>
        `;
        form.addEventListener('submit', event => this.submitQuiz(event));
    },

    async submitQuiz(event) {
        event.preventDefault();
        const form = event.currentTarget;
        const answers = {};
        new FormData(form).forEach((value, key) => {
            answers[key] = value;
        });
        const response = await API.post(`/learning/quizzes/${form.dataset.quizId}/submit`, { answers });
        const result = response.data || {};
        document.getElementById('quizResult').innerHTML = `
            <div class="result-score">${result.score || 0}</div>
            <p>${result.correct || 0} dari ${result.total || 0} jawaban benar.</p>
            <p>${result.passed ? 'Lulus minimum score.' : 'Ulangi materi sebelum mencoba lagi.'}</p>
        `;
    },

    async generateCertificate() {
        try {
            const response = await API.post('/learning/certificate', {});
            const cert = response.data || {};
            document.getElementById('certificateName').textContent = cert.participant_name || 'Peserta';
            document.getElementById('certificateId').textContent = cert.certificate_id || 'ITDV';
            document.getElementById('certificateDate').textContent = new Date(cert.issued_at).toLocaleDateString('id-ID', {
                day: '2-digit',
                month: 'long',
                year: 'numeric'
            });
            document.getElementById('certificatePanel').hidden = false;
            document.getElementById('certificatePanel').scrollIntoView({ behavior: 'smooth' });
        } catch (error) {
            alert(error.message || 'Sertifikat belum bisa dibuat.');
        }
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

document.addEventListener('DOMContentLoaded', () => ITDV.init());
