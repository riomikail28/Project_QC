/**
 * Admin Panel JS
 * Handles CRUD for staff, rooms, devices and rendering charts
 */

document.addEventListener("DOMContentLoaded", () => {
    // Check if user is admin
    const user = JSON.parse(localStorage.getItem("qc_user") || "{}");
    if (user.role !== 'admin') {
        alert("Akses Ditolak: Khusus Admin");
        window.location.href = "dashboard.html";
        return;
    }

    loadStaff();
    loadFacilities();
    initCharts();
});

function showSection(sectionId) {
    document.querySelectorAll('.admin-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    
    document.getElementById(`section-${sectionId}`).classList.add('active');
    event.currentTarget.classList.add('active');
}

// --- Staff Management ---
async function loadStaff() {
    try {
        const res = await fetch("/api/staff");
        const staff = await res.json();
        const body = document.getElementById("staff-table-body");
        body.innerHTML = staff.map(s => `
            <tr>
                <td>${s.full_name || s.username}</td>
                <td><span class="badge ${s.role}">${s.role.toUpperCase()}</span></td>
                <td>${s.username}</td>
                <td class="action-btns">
                    <button class="btn btn-sm btn-danger" onclick="deleteStaff('${s.id}')">Hapus</button>
                </td>
            </tr>
        `).join("");
    } catch (err) {
        console.error("Gagal memuat staf", err);
    }
}

async function deleteStaff(id) {
    if (!confirm("Hapus staf ini?")) return;
    try {
        const res = await fetch(`/api/staff/${id}`, { method: "DELETE" });
        const result = await res.json();
        if (result.success) loadStaff();
    } catch (err) {
        alert("Gagal menghapus staf");
    }
}

// --- Facility Management ---
async function loadFacilities() {
    try {
        const res = await fetch("/api/facility/structure");
        const rooms = await res.json();
        const container = document.getElementById("room-manage-list");
        
        container.innerHTML = rooms.map(room => `
            <div class="card mb-20">
                <div class="section-header">
                    <h3>${room.name}</h3>
                    <div class="action-btns">
                        <button class="btn btn-sm btn-primary" onclick="addDeviceToRoom('${room.id}')">+ Alat</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteRoom('${room.id}')">Hapus</button>
                    </div>
                </div>
                <ul class="device-list-admin">
                    ${room.devices.map(dev => `
                        <li>
                            ${dev.name} (${dev.type}) - ${dev.threshold_temp}°C
                            <button class="text-danger" onclick="deleteDevice('${dev.id}')"><i class="fas fa-trash"></i></button>
                        </li>
                    `).join("")}
                </ul>
            </div>
        `).join("");
    } catch (err) {
        console.error("Gagal memuat fasilitas", err);
    }
}

async function deleteRoom(id) {
    if (!confirm("Hapus ruangan ini dan semua alat di dalamnya?")) return;
    const res = await fetch(`/api/facility/rooms/${id}`, { method: "DELETE" });
    if (res.ok) loadFacilities();
}

async function deleteDevice(id) {
    if (!confirm("Hapus alat ini?")) return;
    const res = await fetch(`/api/facility/devices/${id}`, { method: "DELETE" });
    if (res.ok) loadFacilities();
}

// --- Modal Logic ---
const overlay = document.getElementById('modal-overlay');
const sheet = overlay.querySelector('.modal-sheet');
const formContent = document.getElementById('modal-form-content');
const modalTitle = document.getElementById('modal-title');
const adminForm = document.getElementById('admin-form');

let currentAction = '';

function openModal(title, contentHtml, action) {
    modalTitle.innerText = title;
    formContent.innerHTML = contentHtml;
    currentAction = action;
    
    overlay.style.display = 'flex';
    setTimeout(() => {
        sheet.style.transform = 'translateY(0)';
    }, 10);
}

function closeModal() {
    sheet.style.transform = 'translateY(100%)';
    setTimeout(() => {
        overlay.style.display = 'none';
    }, 300);
}

overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeModal();
});

// --- Action Handlers ---
function openAddStaff() {
    const html = `
        <div class="form-group">
            <label class="input-label">Nama Lengkap</label>
            <input type="text" id="staff-name" class="input-field" placeholder="Nama Lengkap" required>
        </div>
        <div class="form-group">
            <label class="input-label">Username</label>
            <input type="text" id="staff-username" class="input-field" placeholder="Username" required>
        </div>
        <div class="form-group">
            <label class="input-label">Role</label>
            <select id="staff-role" class="input-field">
                <option value="staff">QC Staff</option>
                <option value="admin">Administrator</option>
            </select>
        </div>
        <div class="form-group">
            <label class="input-label">Password</label>
            <input type="password" id="staff-password" class="input-field" placeholder="Minimal 6 karakter" required>
        </div>
    `;
    openModal('Tambah Staf Baru', html, 'ADD_STAFF');
}

function openAddRoom() {
    const html = `
        <div class="form-group">
            <label class="input-label">Nama Ruangan</label>
            <input type="text" id="room-name" class="input-field" placeholder="Contoh: Kitchen, PPIC" required>
        </div>
        <div class="form-group">
            <label class="input-label">Deskripsi (Opsional)</label>
            <input type="text" id="room-desc" class="input-field" placeholder="Deskripsi singkat">
        </div>
    `;
    openModal('Tambah Ruangan', html, 'ADD_ROOM');
}

function addDeviceToRoom(roomId) {
    const html = `
        <input type="hidden" id="device-room-id" value="${roomId}">
        <div class="form-group">
            <label class="input-label">Nama Alat</label>
            <input type="text" id="device-name" class="input-field" placeholder="Contoh: Chiller 1, Freezer A" required>
        </div>
        <div class="form-group">
            <label class="input-label">Tipe Alat</label>
            <select id="device-type" class="input-field">
                <option value="chiller">Chiller</option>
                <option value="freezer">Freezer</option>
                <option value="ambient">Suhu Ruangan</option>
            </select>
        </div>
        <div class="form-group">
            <label class="input-label">Ambang Batas Suhu (°C)</label>
            <input type="number" id="device-threshold" class="input-field" value="5.0" step="0.1">
        </div>
    `;
    openModal('Tambah Alat Baru', html, 'ADD_DEVICE');
}

adminForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    btn.disabled = true;
    btn.innerText = 'MENYIMPAN...';

    try {
        if (currentAction === 'ADD_STAFF') {
            await API.post('/staff', {
                full_name: document.getElementById('staff-name').value,
                username: document.getElementById('staff-username').value,
                role: document.getElementById('staff-role').value,
                password: document.getElementById('staff-password').value
            });
            loadStaff();
        } else if (currentAction === 'ADD_ROOM') {
            await API.post('/facility/rooms', {
                name: document.getElementById('room-name').value,
                description: document.getElementById('room-desc').value
            });
            loadFacilities();
        } else if (currentAction === 'ADD_DEVICE') {
            await API.post('/facility/devices', {
                room_id: document.getElementById('device-room-id').value,
                name: document.getElementById('device-name').value,
                type: document.getElementById('device-type').value,
                threshold: parseFloat(document.getElementById('device-threshold').value)
            });
            loadFacilities();
        }
        closeModal();
    } catch (err) {
        alert("Gagal menyimpan data: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerText = 'SIMPAN DATA';
    }
});
