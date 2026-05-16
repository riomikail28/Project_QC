/**
 * Simple mobile QC check.
 * One SKU/barcode submission creates one qc_report.
 */

const Inspection = {
    selectedStatus: 'pass',

    async init() {
        this.bindStatus();
        this.bindPhotoValidation();
        this.bindSubmit();
    },

    bindStatus() {
        document.querySelectorAll('.qc-status-option').forEach(button => {
            button.addEventListener('click', () => {
                this.selectedStatus = button.dataset.status || 'pass';
                document.querySelectorAll('.qc-status-option').forEach(item => {
                    item.classList.toggle('active', item === button);
                });
            });
        });
    },

    bindPhotoValidation() {
        const input = document.getElementById('qcPhoto');
        const zone = document.querySelector('.upload-zone');
        if (!input || !zone) return;
        input.addEventListener('change', event => {
            const file = (event.target.files || [])[0];
            if (!file) return;
            try {
                API.validatePhoto(file);
                zone.querySelector('span').textContent = file.name;
            } catch (err) {
                this.message(err.message || 'Upload gagal', true);
                input.value = '';
                zone.querySelector('span').textContent = 'Opsional, JPG/PNG/WEBP maksimal 10MB.';
            }
        });
    },

    bindSubmit() {
        const button = document.getElementById('submitQcBtn');
        if (!button) return;
        button.addEventListener('click', () => this.submitQc(button));
    },

    async submitQc(button) {
        const original = button.innerHTML;
        const sku = document.getElementById('qcSku')?.value?.trim();
        const notes = document.getElementById('qcNotes')?.value?.trim();
        const temperature = document.getElementById('qcTemp')?.value;
        const file = (document.getElementById('qcPhoto')?.files || [])[0];
        if (!sku) {
            this.message('SKU atau barcode wajib diisi.', true);
            return;
        }
        try {
            if (file) API.validatePhoto(file);
        } catch (err) {
            this.message(err.message || 'Upload gagal', true);
            return;
        }

        const user = Auth.user() || {};
        const formData = new FormData();
        formData.append('sku_code', sku);
        formData.append('barcode', sku);
        formData.append('qc_status', this.selectedStatus);
        formData.append('notes', notes || '');
        formData.append('temperature', temperature || '');
        formData.append('staff_id', user.id || user.user_id || user.sub || '');
        formData.append('staff_name', user.full_name || user.name || user.username || '');
        if (file) formData.append('photo', file);

        try {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>Menyimpan...';
            const response = await API.upload('/inspection/submit', formData);
            if (!response.success) throw new Error(response.message || response.error || 'Submit gagal');
            ['qcSku', 'qcTemp', 'qcNotes'].forEach(id => {
                localStorage.removeItem(id);
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            const photo = document.getElementById('qcPhoto');
            if (photo) photo.value = '';
            const zoneText = document.querySelector('.upload-zone span');
            if (zoneText) zoneText.textContent = 'Opsional, JPG/PNG/WEBP maksimal 10MB.';
            this.message('QC check berhasil disimpan.', false);
        } catch (error) {
            this.message(`Gagal menyimpan QC check: ${error.message || 'server tidak merespons'}`, true);
        } finally {
            button.disabled = false;
            button.innerHTML = original;
        }
    },

    message(text, isError = false) {
        const el = document.getElementById('qcSubmitMessage');
        if (!el) return;
        el.textContent = text;
        el.classList.toggle('error', isError);
    }
};
