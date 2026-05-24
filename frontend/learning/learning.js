const ITDV = {
    modules: [],
    simulations: [],
    quizzes: [],
    progress: {},
    startedModules: new Set(JSON.parse(localStorage.getItem('itdv_started_modules') || '[]')),

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
            this.loadMentorHistory(),
            this.loadCareerPreview()
        ]);
        document.getElementById('certificateBtn').addEventListener('click', () => this.generateCertificate());
        document.getElementById('mentorForm').addEventListener('submit', event => this.askMentor(event));
        document.querySelectorAll('[data-prompt]').forEach(button => {
            button.addEventListener('click', () => {
                document.getElementById('mentorQuestion').value = button.dataset.prompt || '';
                document.getElementById('mentorQuestion').focus();
            });
        });
        if (window.lucide) lucide.createIcons();
    },

    async loadModules() {
        const response = await API.get('/learning/modules');
        this.modules = response.data || [];
        const grid = document.getElementById('moduleGrid');
        grid.innerHTML = this.modules.map((module, index) => {
            const status = this.moduleStatus(module);
            const actionLabel = status.key === 'new' ? 'Mulai Modul' : 'Lanjutkan';
            return `
            <article class="module-card ${module.completed ? 'completed' : ''} ${status.key === 'process' ? 'in-progress' : ''}">
                <div class="module-card-top">
                    <div class="module-icon">${String(index + 1).padStart(2, '0')}</div>
                    <div class="module-meta">
                        <span>Status</span>
                        <strong>${status.label}</strong>
                    </div>
                </div>
                <h3>${this.escape(module.title)}</h3>
                <p>${this.escape(module.summary)}</p>
                <div class="module-detail-grid">
                    <div><span>Kompetensi</span><strong>${this.escape(module.category)}</strong></div>
                    <div><span>Estimasi waktu</span><strong>${module.duration_minutes || 0} menit</strong></div>
                </div>
                <div class="module-competency-list">
                    ${this.moduleCompetencies(module).slice(0, 2).map(item => `<span>${this.escape(item)}</span>`).join('')}
                </div>
                <a class="secondary-btn module-start-link" data-module-slug="${this.escapeAttr(module.slug)}" href="module.html?slug=${encodeURIComponent(module.slug)}">${actionLabel}</a>
            </article>
        `; }).join('');
        grid.querySelectorAll('[data-module-slug]').forEach(link => {
            link.addEventListener('click', () => {
                this.startedModules.add(link.dataset.moduleSlug);
                localStorage.setItem('itdv_started_modules', JSON.stringify([...this.startedModules]));
            });
        });
    },

    async loadProgress() {
        const response = await API.get('/learning/progress');
        const progress = response.data || {};
        this.progress = progress;
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
        const certificateReady = values.learning >= 100 && values.simulation >= 100 && values.quiz >= 100;
        const certificateStatus = values.certificate >= 100 ? 'Terbit' : (certificateReady ? 'Siap' : 'Terkunci');
        this.setProgressBar('certificate', values.certificate, certificateStatus);
        document.getElementById('progressText').textContent = `${progress.completed_modules || 0} dari ${progress.total_modules || 0} modul selesai`;
        const certificateBtn = document.getElementById('certificateBtn');
        if (certificateBtn) {
            certificateBtn.disabled = !certificateReady;
            certificateBtn.textContent = certificateReady ? 'Generate Sertifikat Internal PDF' : 'Sertifikat Terkunci';
            certificateBtn.title = certificateReady
                ? 'Generate sertifikat PDF'
                : 'Selesaikan 100% modul, simulation, dan quiz minimal 75';
        }
    },

    setProgressBar(key, value, displayValue) {
        const percent = Math.max(0, Math.min(100, Number(value) || 0));
        const label = document.getElementById(`${key}Percent`);
        const bar = document.getElementById(`${key}ProgressBar`);
        if (label) label.textContent = displayValue || `${percent}%`;
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
                <div class="fact-box risk"><span>Risiko</span><strong>Pertumbuhan mikroba</strong></div>
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
        const simulation = this.simulations.find(item => item.id === id) || {};
        const details = this.simulationFeedbackDetails(simulation, result);
        document.getElementById('simulationResult').innerHTML = `
            <div class="result-status ${result.passed ? 'passed' : 'failed'}">${result.passed ? 'Benar' : 'Salah'}</div>
            <div class="result-score">${result.score || 0}</div>
            <div class="feedback-list">
                <div class="feedback-card"><strong>Keputusan ideal</strong><span>${this.escape(details.idealDecision)}</span></div>
                <div class="feedback-card"><strong>Alasan HACCP</strong><span>${this.escape(details.haccp)}</span></div>
                <div class="feedback-card"><strong>Tindakan korektif</strong><span>${this.escape(details.correctiveAction)}</span></div>
                <div class="feedback-card warning"><strong>Dokumentasi wajib</strong><span>${this.escape(details.documentation)}</span></div>
            </div>
        `;
        await this.loadProgress();
        await this.loadCareerPreview();
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
                <p>Satu pertanyaan per card. Pilih jawaban terbaik berdasarkan prinsip HACCP, GMP, dan food safety.</p>
            </div>
            ${(quiz.questions || []).map((question, index) => `
                <div class="question-block quiz-question-card">
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
        const userBubble = document.getElementById('mentorUserBubble');
        if (userBubble) userBubble.textContent = document.getElementById('mentorQuestion').value.trim();
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
        const quiz = this.quizzes.find(item => item.id === form.dataset.quizId) || {};
        document.getElementById('quizResult').innerHTML = `
            <div class="result-score">${result.score || 0}</div>
            <p>${result.correct || 0} dari ${result.total || 0} jawaban benar.</p>
            <p>${result.passed ? 'Lulus minimum score 75.' : 'Belum mencapai minimum score 75. Ulangi materi sebelum mencoba lagi.'}</p>
            <div class="feedback-card"><strong>Rekomendasi materi ulang</strong><span>${this.escape(this.quizRecommendation(result))}</span></div>
            <div class="quiz-review-list">
                ${(result.items || []).map((item, index) => this.renderQuizReviewItem(quiz, item, index)).join('')}
            </div>
        `;
        await this.loadProgress();
        await this.loadCareerPreview();
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
            await this.loadCareerPreview();
        } catch (error) {
            alert(error.message || 'Sertifikat belum bisa dibuat.');
        }
    },

    async loadCareerPreview() {
        try {
            const response = await API.get('/learning/career-recommendation');
            const items = (response.data || {}).recommendations || [];
            const grid = document.getElementById('careerPreviewGrid');
            if (!grid || !items.length) return;
            grid.innerHTML = items.slice(0, 6).map((item, index) => `
                <article class="${index === 0 ? 'primary-career' : ''}">
                    <strong>${this.escape(item.title)}</strong>
                    <span>${item.match_percent || 0}% match</span>
                    <small>${this.escape((item.reasons || [])[0] || 'Rekomendasi berdasarkan skor belajar.')}</small>
                </article>
            `).join('');
        } catch (error) {
            console.error('Career preview failed', error);
        }
    },

    renderQuizReviewItem(quiz, item, index) {
        const question = (quiz.questions || []).find(row => row.id === item.question_id) || {};
        const selected = this.optionLabel(question, item.selected);
        const correct = this.optionLabel(question, item.correct_answer);
        return `
            <article class="quiz-review-item ${item.is_correct ? 'correct' : 'incorrect'}">
                <strong>${index + 1}. ${item.is_correct ? 'Benar' : 'Salah'}</strong>
                <p>${this.escape(question.text || item.question_id)}</p>
                <span>Jawaban kamu: ${this.escape(selected || '-')}</span>
                <span>Jawaban benar: ${this.escape(correct || '-')}</span>
                <small>${this.escape(this.quizExplanation(question))}</small>
            </article>
        `;
    },

    optionLabel(question, key) {
        const option = (question.options || []).find(item => item.key === key);
        return option ? `${option.key}. ${option.label}` : key;
    },

    quizExplanation(question) {
        const text = String(question.text || '').toLowerCase();
        if (text.includes('suhu') || text.includes('chiller')) {
            return 'Deviasi suhu harus langsung diinvestigasi, produk terdampak ditahan, dan risiko keamanan pangan dikendalikan.';
        }
        if (text.includes('traceability') || text.includes('batch')) {
            return 'Traceability membantu menemukan jalur batch untuk audit, investigasi, dan recall jika ada risiko produk.';
        }
        if (text.includes('haccp') || text.includes('ccp')) {
            return 'CCP adalah titik kendali kritis untuk bahaya keamanan pangan signifikan, sehingga wajib dimonitor dan diverifikasi.';
        }
        return 'Pembahasan mengikuti prinsip QC industri: cek bukti, nilai risiko, dan ambil corrective action.';
    },

    simulationFeedbackDetails(simulation, result) {
        const target = simulation.target_c ?? 5;
        const actual = simulation.actual_c ?? 11;
        const idealDecision = result.passed
            ? 'Tahan produk terdampak, investigasi deviasi, dan lanjutkan corrective action sebelum keputusan rilis.'
            : 'Keputusan tidak ideal karena produksi tidak boleh dilanjutkan saat critical limit terlewati.';
        const documentation = 'Catat tanggal, jam, area, suhu aktual, target, produk terdampak, durasi deviasi, tindakan, PIC, foto evidence, dan hasil verifikasi.';
        return {
            idealDecision,
            haccp: `Suhu penyimpanan adalah titik kontrol. Aktual ${actual}°C melebihi target ${target}°C sehingga deviasi harus dicatat dan dikendalikan.`,
            risk: `Risiko mikroba meningkat bila produk tetap diproses pada suhu ${actual}°C tanpa evaluasi durasi deviasi dan kondisi produk.`,
            correctiveAction: result.passed
                ? 'Tahan produk terdampak, investigasi penyebab, pindahkan ke chiller aman, eskalasi maintenance, lalu lanjut hanya setelah risiko terkendali.'
                : 'Jangan lanjut produksi. Lakukan investigasi, hold product, corrective action, dan verifikasi suhu kembali ke batas aman.',
            documentation
        };
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

    escapeAttr(value) {
        return this.escape(value).replace(/\s+/g, '-');
    },

    moduleMaterial(module) {
        if (module.learning_material) return module.learning_material;
        const slug = String(module.slug || '').toLowerCase();
        const map = {
            haccp: 'Pelajari bahaya pangan, CCP, critical limit, monitoring, verifikasi, dan corrective action saat terjadi deviasi.',
            'food-safety': 'Fokus pada personal hygiene, sanitasi area, pencegahan kontaminasi silang, dan kontrol risiko produk.',
            'qc-dasar': 'Kenali parameter mutu, sampling, inspeksi visual, evidence foto, status PASS/HOLD/FAIL, dan pencatatan hasil QC.',
            traceability: 'Pahami pelacakan batch dari bahan baku sampai distribusi agar investigasi dan recall dapat dilakukan cepat.',
            'monitoring-suhu': 'Pelajari batas aman chiller/freezer, pembacaan alert, eskalasi, dan dokumentasi monitoring suhu.'
        };
        return map[slug] || module.summary || 'Materi ringkas Quality Control industri pangan.';
    },

    moduleCase(module) {
        if (module.case_study) return module.case_study;
        const slug = String(module.slug || '').toLowerCase();
        const map = {
            haccp: 'Produk berada di chiller 11°C. Tentukan apakah ini deviasi CCP dan tindakan korektif apa yang harus dicatat.',
            'food-safety': 'Area persiapan menerima bahan dengan kemasan basah. Nilai risiko kontaminasi dan tindakan sanitasi yang diperlukan.',
            'qc-dasar': 'Batch baru memiliki aroma tidak sesuai standar. Tentukan status HOLD dan evidence yang perlu dilampirkan.',
            traceability: 'Ada komplain produk. Telusuri batch, bahan baku, waktu produksi, dan jalur distribusi.',
            'monitoring-suhu': 'PPIC Chiller target 5°C tetapi aktual 11°C. Tentukan investigasi, hold product, dan eskalasi.'
        };
        return map[slug] || 'Gunakan kasus operasional central kitchen untuk menerapkan materi modul.';
    },

    moduleCompetencies(module) {
        if (Array.isArray(module.competencies) && module.competencies.length) return module.competencies;
        const objectives = Array.isArray(module.objectives) ? module.objectives : [];
        return objectives.length ? objectives : ['Mengambil keputusan QC berbasis risiko', 'Mencatat evidence proses'];
    },

    moduleStatus(module) {
        if (module.completed) return { key: 'done', label: 'Selesai' };
        if (module.mini_quiz_passed || this.startedModules.has(module.slug)) return { key: 'process', label: 'Proses' };
        return { key: 'new', label: 'Belum mulai' };
    },

    quizRecommendation(result) {
        if (result.passed) return 'Lanjutkan ke sertifikat dan career recommendation. Review singkat dokumentasi dan corrective action sebelum praktik lapangan.';
        return 'Ulangi modul Prinsip HACCP, Critical Limit, Monitoring CCP, dan Corrective Action sebelum mencoba lagi.';
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
