/**
 * Mobile UI UX Enhancements
 * Includes Toast notifications, Speed Dial FAB, and Bottom Sheet logic.
 */

const UI = {
    // Toast Notification System
    toast(message, type = 'info', duration = 3000) {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = 'position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999; display: flex; flex-direction: column; gap: 10px; width: 90%; max-width: 400px; pointer-events: none;';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        const colors = {
            success: '#16a34a',
            error: '#dc2626',
            warning: '#d97706',
            info: '#2563eb'
        };
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };

        toast.style.cssText = `
            background: #ffffff;
            color: #1e293b;
            padding: 16px 20px;
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.05);
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 14px;
            font-weight: 600;
            border-left: 4px solid ${colors[type]};
            transform: translateY(-20px);
            opacity: 0;
            transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: auto;
        `;

        toast.innerHTML = `<i class="fas ${icons[type]}" style="color: ${colors[type]}; font-size: 18px;"></i> ${message}`;
        container.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.style.transform = 'translateY(0)';
            toast.style.opacity = '1';
        }, 10);

        // Remove after duration
        setTimeout(() => {
            toast.style.transform = 'translateY(-20px)';
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 400);
        }, duration);
    },

    // Bottom Sheet System
    showSheet(title, contentHtml) {
        let overlay = document.getElementById('sheet-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'sheet-overlay';
            overlay.className = 'sheet-overlay';
            overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 9000; opacity: 0; transition: opacity 0.3s ease;';
            overlay.onclick = () => this.hideSheet();
            document.body.appendChild(overlay);
        } else {
            overlay.className = 'sheet-overlay';
        }

        let sheet = document.getElementById('bottom-sheet');
        if (!sheet) {
            sheet = document.createElement('div');
            sheet.id = 'bottom-sheet';
            sheet.className = 'bottom-sheet';
            sheet.style.cssText = 'position: fixed; bottom: 0; left: 0; right: 0; background: #ffffff; border-radius: 24px 24px 0 0; z-index: 9001; transform: translateY(100%); transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1); padding: 20px 24px 40px;';
            document.body.appendChild(sheet);
        } else {
            sheet.className = 'bottom-sheet';
        }

        sheet.innerHTML = `
            <div style="width: 40px; height: 4px; background: #e2e8f0; border-radius: 2px; margin: 0 auto 20px;"></div>
            <h3 style="font-size: 18px; font-weight: 800; margin-bottom: 20px; color: #1e293b;">${title}</h3>
            <div id="sheet-content">${contentHtml}</div>
        `;

        // Show
        overlay.style.display = 'block';
        setTimeout(() => {
            overlay.style.opacity = '1';
            sheet.style.transform = 'translateY(0)';
        }, 10);
    },

    hideSheet() {
        const overlay = document.getElementById('sheet-overlay');
        const sheet = document.getElementById('bottom-sheet');
        if (sheet) sheet.style.transform = 'translateY(100%)';
        if (overlay) overlay.style.opacity = '0';
        setTimeout(() => {
            if (overlay) overlay.style.display = 'none';
        }, 300);
    },

    // Hybrid Photo Picker for Mobile Devices (Camera + Gallery/Upload)
    showPhotoSourcePicker(inputElement) {
        if (!inputElement) return;
        const title = 'Pilih Sumber Foto';
        const contentHtml = `
            <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 8px;">
                <button type="button" id="picker-source-camera" style="
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 16px;
                    background: #eff6ff;
                    color: #2563eb;
                    border: 1px solid rgba(59, 130, 246, 0.2);
                    border-radius: 12px;
                    font-size: 15px;
                    font-weight: 700;
                    cursor: pointer;
                    width: 100%;
                    text-align: left;
                    box-sizing: border-box;
                ">
                    <i class="fas fa-camera" style="font-size: 18px;"></i>
                    <span>Ambil Foto Baru (Kamera)</span>
                </button>
                <button type="button" id="picker-source-gallery" style="
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 16px;
                    background: #f8fafc;
                    color: #475569;
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                    font-size: 15px;
                    font-weight: 700;
                    cursor: pointer;
                    width: 100%;
                    text-align: left;
                    box-sizing: border-box;
                ">
                    <i class="fas fa-image" style="font-size: 18px;"></i>
                    <span>Pilih dari Galeri / Upload</span>
                </button>
            </div>
        `;
        
        this.showSheet(title, contentHtml);
        
        const camBtn = document.getElementById('picker-source-camera');
        const galBtn = document.getElementById('picker-source-gallery');
        
        if (camBtn) {
            camBtn.onclick = () => {
                this.hideSheet();
                inputElement.setAttribute('capture', 'environment');
                inputElement.click();
            };
        }
        
        if (galBtn) {
            galBtn.onclick = () => {
                this.hideSheet();
                inputElement.removeAttribute('capture');
                inputElement.click();
            };
        }
    },

    // Speed Dial FAB
    toggleSpeedDial() {
        const fab = document.querySelector('.fab');
        if (!fab) return;
        fab.classList.toggle('active');
        
        // Logic to show/hide child buttons would go here
        // For simplicity, we can just change the icon
        const icon = fab.querySelector('i');
        if (fab.classList.contains('active')) {
            icon.className = 'fas fa-times';
        } else {
            icon.className = 'fas fa-plus';
        }
    }
};

window.showToast = function showToast(message, type = 'info', duration = 3500) {
    UI.toast(message, type, duration);
};

// Global feedback for clicks
document.addEventListener('touchstart', (e) => {
    if (e.target.closest('button, .nav-item, .alert-card')) {
        e.target.style.opacity = '0.7';
        setTimeout(() => e.target.style.opacity = '1', 100);
    }
}, {passive: true});
