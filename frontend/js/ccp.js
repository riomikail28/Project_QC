/**
 * QC Central Kitchen — CCP Controller
 * Handles dynamic stage rendering, OCR data extraction, and multipart submission.
 */

const CCP = {
    batch: null,
    product: null,
    stageInfo: {
        1: { name: 'Incoming', label: 'Material Incoming', instruction: 'Periksa suhu bahan baku saat diterima.' },
        2: { name: 'Cooking', label: 'Cooking / Processing', instruction: 'Periksa suhu core produk saat dimasak.' },
        3: { name: 'Cooling', label: 'Cooling / Storage', instruction: 'Periksa suhu penurunan setelah dimasak.' },
        4: { name: 'Packaging', label: 'Packaging & Quality', instruction: 'Periksa parameter kimia (Brix/pH/TDS).' }
    },

    async initStage(batchId, stageNum) {
        try {
            const detail = await API.get(`/batch/${batchId}`);
            this.batch = detail.batch;
            this.product = this.batch.products;

            document.getElementById('batchCodeLabel').innerText = `${this.batch.batch_code} • ${this.product?.product_name || 'Production'}`;
            
            const info = this.stageInfo[stageNum];
            document.getElementById('stageTitle').innerText = info.label;
            document.getElementById('stageInstruction').innerText = info.instruction;

            this.renderFields(stageNum);
        } catch (err) {
            console.error('Init stage failed', err);
        }
    },

    renderFields(stageNum) {
        const container = document.getElementById('dynamicFields');
        container.innerHTML = '';

        if (stageNum === 1) {
            container.innerHTML = this._input('temperature', 'Suhu Bahan Baku (°C)', 'number', '0.0');
        } else if (stageNum === 2) {
            container.innerHTML = this._input('core_temp', 'Suhu Core Produk (°C)', 'number', '0.0');
        } else if (stageNum === 3) {
            container.innerHTML = this._input('room_temp', 'Suhu Ruangan / Penyimpanan (°C)', 'number', '0.0');
        } else if (stageNum === 4) {
            if (this.product?.brix_min !== undefined) container.innerHTML += this._input('brix', 'Brix (%)', 'number', '0.0');
            if (this.product?.ph_min !== undefined) container.innerHTML += this._input('ph', 'pH Value', 'number', '0.0');
            if (this.product?.tds_min !== undefined) container.innerHTML += this._input('tds', 'TDS (ppm)', 'number', '0');
        }
    },

    _input(id, label, type, placeholder) {
        return `
            <div style="margin-bottom: 16px;">
                <label class="input-label">${label}</label>
                <input type="${type}" id="${id}" class="input-field" step="0.01" placeholder="${placeholder}" required>
            </div>
        `;
    },

    async runOCR(photoFile) {
        const formData = new FormData();
        formData.append('photo', photoFile);
        return await API.upload('/ccp/ocr', formData);
    },

    applyOCR(result) {
        const text = result.raw_text || '';
        // Heuristic extraction for common kitchen thermometer formats
        const tempMatch = text.match(/(\d{1,3}[\.,]\d)/);
        if (tempMatch) {
            const val = tempMatch[0].replace(',', '.');
            const input = document.querySelector('input[type="number"]');
            if (input) input.value = val;
            alert(`Ekstraksi Berhasil: ${val}`);
        } else {
            alert('Teks tidak terbaca dengan jelas. Masukkan nilai secara manual.');
        }
    },

    async submit(batchId, stageNum) {
        const info = this.stageInfo[stageNum];
        const photo = document.getElementById('photoInput').files[0];
        
        const metrics = {};
        document.querySelectorAll('#dynamicFields input').forEach(input => {
            metrics[input.id] = {
                value: parseFloat(input.value),
                status: 'PASS' // Status determined by backend
            };
        });

        const formData = new FormData();
        formData.append('batch_id', batchId);
        formData.append('stage', info.name);
        formData.append('operator_id', Auth.user().id);
        formData.append('metrics', JSON.stringify(metrics));
        if (photo) formData.append('photo', photo);

        return await API.upload('/ccp/submit-stage', formData);
    }
};
