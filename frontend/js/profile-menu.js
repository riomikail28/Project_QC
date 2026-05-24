/**
 * Shared avatar profile dropdown for admin and staff topbars.
 */

const ProfileMenu = {
    init() {
        const avatars = this.findAvatars();
        avatars.forEach(avatar => this.attach(avatar));
        document.addEventListener('click', event => {
            if (!event.target.closest('.profile-menu-wrap')) this.closeAll();
        });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape') this.closeAll();
        });
    },

    findAvatars() {
        const staffAvatars = Array.from(document.querySelectorAll('.user-avatar'));
        const adminAvatar = document.querySelector('.user-profile > div:first-child');
        return [...staffAvatars, ...(adminAvatar ? [adminAvatar] : [])]
            .filter((avatar, index, list) => avatar && !avatar.dataset.profileMenuBound && list.indexOf(avatar) === index);
    },

    attach(avatar) {
        avatar.dataset.profileMenuBound = 'true';
        avatar.classList.add('profile-menu-avatar');
        avatar.setAttribute('role', 'button');
        avatar.setAttribute('tabindex', '0');
        avatar.setAttribute('aria-haspopup', 'menu');
        avatar.setAttribute('aria-expanded', 'false');

        const wrap = document.createElement('div');
        wrap.className = 'profile-menu-wrap';
        avatar.parentNode.insertBefore(wrap, avatar);
        wrap.appendChild(avatar);

        const menu = this.createMenu();
        wrap.appendChild(menu);

        avatar.addEventListener('click', event => {
            event.stopPropagation();
            this.toggle(wrap);
        });
        avatar.addEventListener('keydown', event => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                this.toggle(wrap);
            }
        });
    },

    createMenu() {
        const user = this.userData();
        const isAdmin = Auth.canAccessAdmin(user.role);
        const menu = document.createElement('div');
        menu.className = 'profile-dropdown';
        menu.setAttribute('role', 'menu');
        menu.innerHTML = `
            <div class="profile-dropdown-head">
                <div class="profile-dropdown-avatar">${this.escape(this.initials(user.name))}</div>
                <div>
                    <strong>${this.escape(user.name)}</strong>
                    <span>${this.escape(user.roleLabel)}</span>
                    <small>${this.escape(user.status)}</small>
                </div>
            </div>
            <div class="profile-dropdown-divider"></div>
            <a class="profile-dropdown-item" role="menuitem" href="/staff/profile.html">
                <span class="profile-dropdown-icon">👤</span>
                <strong>Profile</strong>
            </a>
            ${isAdmin ? `
                <a class="profile-dropdown-item" role="menuitem" href="/admin/admin_panel.html#section-facility">
                    <span class="profile-dropdown-icon">⚙</span>
                    <strong>Settings</strong>
                </a>
            ` : ''}
            <button class="profile-dropdown-item logout" role="menuitem" type="button" data-profile-logout>
                <span class="profile-dropdown-icon">🚪</span>
                <strong>Logout</strong>
            </button>
        `;
        menu.querySelector('[data-profile-logout]').addEventListener('click', event => {
            event.preventDefault();
            Auth.logout();
        });
        return menu;
    },

    toggle(wrap) {
        const willOpen = !wrap.classList.contains('open');
        this.closeAll();
        if (willOpen) {
            const currentMenu = wrap.querySelector('.profile-dropdown');
            if (currentMenu) currentMenu.replaceWith(this.createMenu());
        }
        wrap.classList.toggle('open', willOpen);
        const avatar = wrap.querySelector('.profile-menu-avatar');
        if (avatar) avatar.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
    },

    closeAll() {
        document.querySelectorAll('.profile-menu-wrap.open').forEach(wrap => {
            wrap.classList.remove('open');
            const avatar = wrap.querySelector('.profile-menu-avatar');
            if (avatar) avatar.setAttribute('aria-expanded', 'false');
        });
    },

    userData() {
        const user = (window.Auth && Auth.user && Auth.user()) || {};
        const name = user.full_name || user.name || user.username || user.email || 'QC User';
        const role = Auth.normalizeRole(user.role || localStorage.getItem('qc_role'));
        return {
            name,
            role,
            roleLabel: this.roleLabel(role),
            status: user.status || user.account_status || 'Active',
        };
    },

    roleLabel(role) {
        if (Auth.canAccessAdmin(role)) return 'Admin';
        return 'Staff';
    },

    initials(name) {
        return String(name || 'QC')
            .trim()
            .split(/\s+/)
            .slice(0, 2)
            .map(part => part.charAt(0).toUpperCase())
            .join('') || 'QC';
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

document.addEventListener('DOMContentLoaded', () => ProfileMenu.init());
