const ModuleDetail = {
    module: null,
    miniQuizPassed: false,
    hasRead: false,

    async init() {
        if (!Auth.check()) {
            window.location.href = '/staff/login.html';
            return;
        }
        const slug = new URLSearchParams(window.location.search).get('slug');
        if (!slug) {
            window.location.href = '/learning/';
            return;
        }
        await this.load(slug);
        document.getElementById('miniQuizForm').addEventListener('submit', event => this.submitMiniQuiz(event));
        document.getElementById('completeModuleBtn').addEventListener('click', () => this.completeModule());
        document.getElementById('readConfirmation').addEventListener('change', event => {
            this.hasRead = event.currentTarget.checked;
            this.updateCompleteState();
        });
        window.addEventListener('scroll', () => this.markReadByScroll(), { passive: true });
    },

    async load(slug) {
        const response = await API.get(`/learning/modules/${slug}`);
        this.module = response.data || {};
        this.miniQuizPassed = Boolean(this.module.mini_quiz_passed);
        this.render();
    },

    render() {
        const module = this.module;
        document.getElementById('moduleCategory').textContent = module.category || 'Modul';
        document.getElementById('moduleTitle').textContent = module.title || 'Modul';
        document.getElementById('moduleSummary').textContent = module.summary || '-';
        document.getElementById('moduleStatus').textContent = module.completed ? 'Selesai' : (this.miniQuizPassed ? 'Quiz lulus' : 'Belum selesai');
        document.getElementById('moduleDuration').textContent = `${module.duration_minutes || 0} menit`;
        this.renderList('moduleObjectives', module.objectives || []);
        document.getElementById('moduleMaterial').textContent = module.learning_material || module.summary || '-';
        document.getElementById('moduleCase').textContent = module.case_study || '-';
        this.renderList('moduleCompetencies', module.competencies || module.objectives || []);
        this.renderList('moduleKeyPoints', module.key_points || module.objectives || []);
        this.renderQuiz(module.mini_quiz || []);
        if (module.completed) {
            document.getElementById('miniQuizResult').textContent = 'Modul sudah selesai. Kamu tetap bisa membaca ulang materi dan mengulang mini quiz.';
        } else if (this.miniQuizPassed) {
            document.getElementById('miniQuizResult').textContent = `Mini quiz sudah lulus dengan skor terbaik ${module.mini_quiz_score || 70}. Modul bisa diselesaikan setelah materi dibaca.`;
        }
        this.updateCompleteState();
    },

    renderList(id, items) {
        document.getElementById(id).innerHTML = (items || [])
            .map(item => `<li>${this.escape(item)}</li>`)
            .join('');
    },

    renderQuiz(questions) {
        const form = document.getElementById('miniQuizForm');
        form.innerHTML = questions.map((question, index) => `
            <div class="mini-question">
                <strong>${index + 1}. ${this.escape(question.text)}</strong>
                ${(question.options || []).map(option => `
                    <label class="choice-label">
                        <input type="radio" name="${this.escapeAttr(question.id)}" value="${this.escapeAttr(option.key)}" required>
                        <span>${this.escape(option.key)}. ${this.escape(option.label)}</span>
                    </label>
                `).join('')}
            </div>
        `).join('') + '<button class="primary-btn mini-quiz-submit" type="submit">Submit Mini Quiz</button>';
    },

    async submitMiniQuiz(event) {
        event.preventDefault();
        const answers = {};
        new FormData(event.currentTarget).forEach((value, key) => {
            answers[key] = value;
        });
        const response = await API.post(`/learning/modules/${this.module.slug}/mini-quiz`, { answers });
        const result = response.data || {};
        this.miniQuizPassed = Boolean(result.passed);
        const panel = document.getElementById('miniQuizResult');
        panel.className = `mini-quiz-result ${result.passed ? 'pass' : 'fail'}`;
        panel.innerHTML = `
            <strong>${result.passed ? 'Mini quiz lulus' : 'Mini quiz belum lulus'}</strong>
            <p>Skor ${result.score || 0}. ${result.passed ? 'Modul bisa diselesaikan setelah materi dibaca.' : 'Selesaikan mini quiz minimal 70 untuk menyelesaikan modul.'}</p>
            <div class="mini-review-list">
                ${(result.items || []).map((item, index) => this.renderReviewItem(item, index)).join('')}
            </div>
        `;
        this.updateCompleteState();
    },

    markReadByScroll() {
        if ((window.scrollY + window.innerHeight) >= (document.documentElement.scrollHeight - 120)) {
            this.markRead();
        }
    },

    markRead() {
        this.hasRead = true;
        const checkbox = document.getElementById('readConfirmation');
        if (checkbox) checkbox.checked = true;
        this.updateCompleteState();
    },

    updateCompleteState() {
        const button = document.getElementById('completeModuleBtn');
        const canComplete = this.hasRead && this.miniQuizPassed && !this.module.completed;
        button.disabled = !canComplete;
        button.textContent = this.module.completed
            ? 'Modul Selesai'
            : (canComplete ? 'Tandai Selesai' : 'Selesaikan mini quiz minimal 70 untuk menyelesaikan modul');
    },

    async completeModule() {
        try {
            const response = await API.post(`/learning/modules/${this.module.slug}/complete`, {});
            if (response.success) {
                window.location.href = '/learning/';
            }
        } catch (error) {
            const panel = document.getElementById('miniQuizResult');
            panel.className = 'mini-quiz-result fail';
            panel.textContent = error.message || 'Selesaikan mini quiz minimal 70 untuk menyelesaikan modul.';
        }
    },

    renderReviewItem(item, index) {
        const question = (this.module.mini_quiz || []).find(row => row.id === item.question_id) || {};
        return `
            <article class="mini-review-item ${item.is_correct ? 'correct' : 'incorrect'}">
                <strong>${index + 1}. ${item.is_correct ? 'Benar' : 'Salah'}</strong>
                <span>Jawaban kamu: ${this.escape(this.optionLabel(question, item.selected) || '-')}</span>
                <span>Jawaban benar: ${this.escape(this.optionLabel(question, item.correct_answer) || '-')}</span>
                <small>${this.escape(item.explanation || 'Baca ulang materi dan contoh kasus sebelum mengulang mini quiz.')}</small>
            </article>
        `;
    },

    optionLabel(question, key) {
        const option = (question.options || []).find(item => item.key === key);
        return option ? `${option.key}. ${option.label}` : key;
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

    escapeAttr(value) {
        return this.escape(value).replace(/\s+/g, '-');
    }
};

document.addEventListener('DOMContentLoaded', () => ModuleDetail.init());
