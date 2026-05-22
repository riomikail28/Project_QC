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
            this.loadQuizzes(),
            this.loadMentorHistory()
        ]);
        document.getElementById('certificateBtn').addEventListener('click', () => this.generateCertificate());
        document.getElementById('mentorForm').addEventListener('submit', event => this.askMentor(event));
        if (window.lucide) lucide.createIcons();
    },

    async loadModules() {
        const response = await API.get('/learning/modules');
        this.modules = response.data || [];
        const grid = document.getElementById('moduleGrid');
        grid.innerHTML = this.modules.map(module => `
            <article class="module-card ${module.completed ? 'completed' : ''}">
                <div class="module-card-top">
                    <div class="module-icon">${this.escape(this.moduleInitial(module.title))}</div>
                    <div class="module-meta">
                        <span>Difficulty</span>
                        <strong>${this.escape(module.difficulty || this.moduleDifficulty(module.category))}</strong>
                    </div>
                </div>
                <h3>${this.escape(module.title)}</h3>
                <p>${this.escape(module.summary)}</p>
                <div class="module-detail-grid">
                    <div><span>Module</span><strong>${this.escape(module.category)}</strong></div>
                    <div><span>Estimated time</span><strong>${module.duration_minutes || 0} menit</strong></div>
                </div>
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
        const values = {
            learning: progress.learning_percent ?? progress.percent ?? 0,
            simulation: progress.simulation_percent ?? 0,
            quiz: progress.quiz_percent ?? 0,
            certificate: progress.certificate_percent ?? 0
        };
        const overall = Math.round((values.learning + values.simulation + values.quiz + values.certificate) / 4);
        document.getElementById('progressPercent').textContent = `${overall}%`;
        this.setProgressBar('learning', values.learning);
        this.setProgressBar('simulation', values.simulation);
        this.setProgressBar('quiz', values.quiz);
        this.setProgressBar('certificate', values.certificate);
        document.getElementById('progressText').textContent = `${progress.completed_modules || 0} dari ${progress.total_modules || 0} modul selesai`;
        const certificateBtn = document.getElementById('certificateBtn');
        const unlocked = values.learning >= 100 && values.simulation >= 100 && values.quiz >= 100;
        if (certificateBtn) {
            certificateBtn.disabled = !unlocked;
            certificateBtn.textContent = unlocked ? 'Generate Sertifikat PDF' : 'Sertifikat Terkunci';
            certificateBtn.title = unlocked ? 'Generate sertifikat PDF' : 'Selesaikan 100% modul, simulation, dan quiz';
        }
    },

    setProgressBar(key, value) {
        const percent = Math.max(0, Math.min(100, Number(value) || 0));
        const label = document.getElementById(`${key}Percent`);
        const bar = document.getElementById(`${key}ProgressBar`);
        if (label) label.textContent = `${percent}%`;
        if (bar) bar.style.width = `${percent}%`;
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
            <div class="case-header">
                <span>Studi Kasus</span>
                <h3>${this.escape(simulation.title)}</h3>
            </div>
            <p>${this.escape(simulation.scenario)}</p>
            <div class="scenario-facts">
                <div class="fact-box"><span>Case</span><strong>${this.escape(simulation.area || 'PPIC Chiller')}</strong></div>
                <div class="fact-box"><span>Target</span><strong>${simulation.target_c}&deg;C</strong></div>
                <div class="fact-box"><span>Aktual</span><strong>${simulation.actual_c}&deg;C</strong></div>
            </div>
            <h4>Pilih tindakan</h4>
            <div class="option-stack">
                ${(simulation.options || []).map(option => `
                    <button class="option-btn" type="button" onclick="ITDV.submitSimulation('${simulation.id}', '${option.key}')">
                        <span>${option.key}</span>
                        <strong>${this.escape(option.label)}</strong>
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
            <div class="feedback-card">
                <strong>Aksi ideal</strong>
                <span>${(result.best_actions || []).join(' lalu ')}</span>
            </div>
        `;
        await this.loadProgress();
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
            <div class="quiz-intro">
                <span>Assessment</span>
                <h3>${this.escape(quiz.title)}</h3>
                <p>Pilih satu jawaban terbaik untuk setiap pertanyaan.</p>
            </div>
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

    async askMentor(event) {
        event.preventDefault();
        const question = document.getElementById('mentorQuestion').value.trim();
        if (!question) return;
        const response = await API.post('/learning/mentor', { question });
        const data = response.data || {};
        this.renderMentorAnswer(data);
        await this.loadMentorHistory();
    },

    async loadMentorHistory() {
        try {
            const response = await API.get('/learning/mentor/history');
            this.renderMentorHistory(response.data || []);
        } catch (error) {
            this.renderMentorHistory([]);
        }
    },

    renderMentorAnswer(data) {
        document.getElementById('mentorAnswer').textContent = data.answer || 'Belum ada jawaban.';
        document.getElementById('mentorTopics').innerHTML = (data.topics || [])
            .map(topic => `<span>${this.escape(topic)}</span>`)
            .join('');
    },

    renderMentorHistory(items) {
        const list = document.getElementById('mentorHistoryList');
        if (!items.length) {
            list.textContent = 'Belum ada riwayat.';
            return;
        }
        list.innerHTML = items.map(item => `
            <article class="mentor-history-item">
                <strong>${this.escape(item.question)}</strong>
                <p>${this.escape(item.answer)}</p>
            </article>
        `).join('');
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
        await this.loadProgress();
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
            if (cert.pdf_base64) {
                this.downloadPdf(cert.pdf_base64, cert.pdf_filename || `${cert.certificate_id || 'ITDV-Certificate'}.pdf`);
            }
            await this.loadProgress();
        } catch (error) {
            alert(error.message || 'Sertifikat belum bisa dibuat.');
        }
    },

    downloadPdf(base64, filename) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let index = 0; index < binary.length; index += 1) {
            bytes[index] = binary.charCodeAt(index);
        }
        const blob = new Blob([bytes], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    },

    escape(value) {
        return String(value ?? '').replace(/[&<>"']/g, char => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[char]));
    },

    moduleInitial(title) {
        return String(title || 'QC')
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map(part => part.charAt(0).toUpperCase())
            .join('') || 'QC';
    },

    moduleDifficulty(category) {
        const value = String(category || '').toLowerCase();
        if (value.includes('haccp') || value.includes('trace')) return 'Intermediate';
        if (value.includes('suhu') || value.includes('monitor')) return 'Practical';
        return 'Beginner';
    }
};

document.addEventListener('DOMContentLoaded', () => ITDV.init());
