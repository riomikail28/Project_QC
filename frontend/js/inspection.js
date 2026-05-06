/**
 * QC Central Kitchen — Inspection Controller
 */

const Inspection = {
    async init() {
        this.loadBatches();
        this.loadProducts();
    },

    async loadBatches() {
        const container = document.getElementById('activeBatchList');
        try {
            const batches = await API.get('/batches');
            container.innerHTML = '';

            if (batches.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-history" style="font-size: 32px; margin-bottom: 12px; opacity: 0.5;"></i>
                        <p>No active batches found.</p>
                    </div>
                `;
                return;
            }

            batches.forEach(batch => {
                const statusClass = (batch.final_qc_status || 'pending').toLowerCase();
                container.innerHTML += `
                    <div class="alert-card" onclick="window.location.href='batch_detail.html?id=${batch.id}'">
                        <div class="alert-icon" style="background: rgba(255,255,255,0.05);"><i class="fas fa-box"></i></div>
                        <div class="alert-info">
                            <h4>${batch.batch_code}</h4>
                            <p>${batch.products?.product_name || 'Unknown Product'}</p>
                        </div>
                        <div class="alert-status ${statusClass}">${statusClass}</div>
                    </div>
                `;
            });
        } catch (error) {
            container.innerHTML = '<p class="error">Gagal memuat batch.</p>';
        }
    },

    async loadProducts() {
        const container = document.getElementById('productGrid');
        try {
            const products = await API.get('/products');
            container.innerHTML = '';

            products.slice(0, 8).forEach(p => {
                container.innerHTML += `
                    <div class="metric-card" style="padding: 12px; text-align: left; cursor: pointer;">
                        <div style="font-size: 11px; color: var(--accent-blue); font-weight: 700;">${p.product_code}</div>
                        <div style="font-size: 12px; font-weight: 500; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                            ${p.product_name}
                        </div>
                    </div>
                `;
            });
        } catch (error) {
            console.error('Failed to load products:', error);
        }
    }
};