(() => {
    if (window.StaffQuickActions) return;

    const actionHandlers = {
        photo() {
            if (typeof window.openQcFinding === 'function') {
                window.openQcFinding();
                if (typeof window.openFindingCamera === 'function') {
                    window.setTimeout(() => window.openFindingCamera(), 80);
                }
                return;
            }
            if (typeof window.triggerPhoto === 'function' && document.getElementById('log-modal')?.classList.contains('active')) {
                window.triggerPhoto();
                return;
            }
            const deviceCard = document.querySelector('.device-card');
            if (deviceCard && typeof window.triggerPhoto === 'function') {
                deviceCard.click();
                window.setTimeout(() => window.triggerPhoto(), 120);
                return;
            }
            const visibleInput = ['cookingPhoto', 'barcodePhoto', 'labelPhoto', 'photo-input']
                .map(id => document.getElementById(id))
                .find(input => input && !input.closest('[hidden]'));
            if (visibleInput) {
                visibleInput.click();
                return;
            }
            window.location.href = 'dashboard.html?openFinding=true';
        },
        batch() {
            window.location.href = 'new_batch.html';
        },
        qc() {
            window.location.href = 'inspection.html';
        },
        monitoring() {
            window.location.href = 'monitoring.html';
        }
    };

    function root() {
        return document.querySelector('[data-quick-actions]');
    }

    function menu() {
        return root()?.querySelector('[data-quick-actions-menu]');
    }

    function triggers() {
        return Array.from(document.querySelectorAll('[data-quick-actions-trigger]'));
    }

    function setOpen(open) {
        const actionRoot = root();
        const actionMenu = menu();
        if (!actionRoot || !actionMenu) return;
        actionRoot.classList.toggle('open', open);
        actionMenu.hidden = !open;
        triggers().forEach(trigger => {
            trigger.classList.toggle('rotated', open);
            trigger.setAttribute('aria-expanded', String(open));
        });
        actionMenu.querySelectorAll('[data-quick-action], .fab-mini').forEach((item, index) => {
            // Respect dynamic style.display set by init()
            if (item.style.display === 'none') return;
            window.setTimeout(() => item.classList.toggle('visible', open), index * 35);
        });
    }

    function onClick(event) {
        const trigger = event.target.closest('[data-quick-actions-trigger]');
        if (trigger) {
            event.preventDefault();
            setOpen(!root()?.classList.contains('open'));
            return;
        }

        const actionButton = event.target.closest('[data-quick-action]');
        if (actionButton) {
            event.preventDefault();
            setOpen(false);
            actionHandlers[actionButton.dataset.quickAction]?.();
            return;
        }

        const actionRoot = root();
        if (actionRoot && !actionRoot.contains(event.target)) {
            setOpen(false);
        }
    }

    window.StaffQuickActions = {
        init() {
            if (document.documentElement.dataset.quickActionsReady) return;
            document.documentElement.dataset.quickActionsReady = 'true';

            // Hide the action button for the current page to avoid redundancy
            const path = window.location.pathname;
            if (path.includes('monitoring.html')) {
                const btn = document.querySelector('[data-quick-action="monitoring"]');
                if (btn) btn.style.display = 'none';
            } else if (path.includes('inspection.html')) {
                const btn = document.querySelector('[data-quick-action="qc"]');
                if (btn) btn.style.display = 'none';
            } else if (path.includes('dashboard.html') || path.endsWith('/staff/') || path.endsWith('/staff')) {
                const btn = document.querySelector('[data-quick-action="photo"]');
                if (btn) btn.style.display = 'none';
            }

            document.addEventListener('click', onClick);
            document.addEventListener('keydown', event => {
                if (event.key === 'Escape') setOpen(false);
            });
        },
        setOpen
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => window.StaffQuickActions.init());
    } else {
        window.StaffQuickActions.init();
    }
})();
