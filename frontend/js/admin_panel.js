/**
 * Admin Panel JS
 * Handles CRUD for staff, rooms, devices and rendering charts.
 */

let currentAction = "";
let currentId = null;
let adminToastTimer = null;

document.addEventListener("DOMContentLoaded", () => {
    const user = JSON.parse(localStorage.getItem("qc_user") || "{}");
    if (user.role !== "admin") {
        alert("Akses Ditolak: Khusus Admin");
        window.location.href = "dashboard.html";
        return;
    }

    loadStaff();
    loadFacilities();
    loadAnalytics();
});

function notify(message, type = "success") {
    const toast = document.getElementById("admin-toast");
    if (!toast) {
        alert(message);
        return;
    }

    clearTimeout(adminToastTimer);
    toast.textContent = message;
    toast.className = `admin-toast ${type} show`;
    adminToastTimer = setTimeout(() => {
        toast.className = `admin-toast ${type}`;
    }, 2600);
}

function showSection(sectionId) {
    document.querySelectorAll(".admin-section").forEach(section => section.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(button => button.classList.remove("active"));

    document.getElementById(`section-${sectionId}`).classList.add("active");
    const button = document.querySelector(`[data-section="${sectionId}"]`) || event.currentTarget;
    if (button) button.classList.add("active");
}

function safeJson(value) {
    return JSON.stringify(value).replace(/'/g, "&apos;");
}

async function loadStaff() {
    try {
        const staff = await API.get("/staff");
        const body = document.getElementById("staff-table-body");
        if (!staff.length) {
            body.innerHTML = `<tr><td colspan="4">Belum ada staf.</td></tr>`;
            return;
        }

        body.innerHTML = staff.map(item => `
            <tr>
                <td>${item.full_name || item.username}</td>
                <td><span class="badge ${item.role}">${(item.role || "staff").toUpperCase()}</span></td>
                <td>${item.username}</td>
                <td class="action-btns">
                    <button class="btn btn-sm btn-secondary" onclick='openEditStaff(${safeJson(item)})'>Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteStaff('${item.id}')">Hapus</button>
                </td>
            </tr>
        `).join("");
    } catch (err) {
        console.error("Gagal memuat staf", err);
        notify("Gagal memuat daftar staf", "error");
    }
}

async function deleteStaff(id) {
    if (!confirm("Hapus staf ini?")) return;
    try {
        const result = await API.delete(`/staff/${id}`);
        if (!result.success) throw new Error("Delete gagal");
        await loadStaff();
        notify("Staf berhasil dihapus");
    } catch (err) {
        notify("Gagal menghapus staf", "error");
    }
}

async function loadFacilities() {
    try {
        const rooms = await API.get("/facility/structure");
        const container = document.getElementById("room-manage-list");
        if (!rooms.length) {
            container.innerHTML = `<div class="chart-container">Belum ada fasilitas.</div>`;
            return;
        }

        container.innerHTML = rooms.map(room => `
            <div class="card mb-20 admin-room-card">
                <div class="section-header">
                    <h3>${room.name}</h3>
                    <div class="action-btns">
                        <button class="btn btn-sm btn-primary" onclick="addDeviceToRoom('${room.id}')">+ Alat</button>
                        <button class="btn btn-sm btn-secondary" onclick='openEditRoom(${safeJson(room)})'>Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteRoom('${room.id}')">Hapus</button>
                    </div>
                </div>
                <ul class="device-list-admin">
                    ${(room.devices || []).map(device => `
                        <li>
                            <span>${device.name} (${device.type}) - ${device.threshold_temp || 0}&deg;C</span>
                            <span class="action-btns">
                                <button class="icon-btn" onclick='openEditDevice(${safeJson(device)})'><i class="fas fa-pen"></i></button>
                                <button class="icon-btn danger" onclick="deleteDevice('${device.id}')"><i class="fas fa-trash"></i></button>
                            </span>
                        </li>
                    `).join("")}
                </ul>
            </div>
        `).join("");
    } catch (err) {
        console.error("Gagal memuat fasilitas", err);
        notify("Gagal memuat fasilitas", "error");
    }
}

async function deleteRoom(id) {
    if (!confirm("Hapus ruangan ini dan semua alat di dalamnya?")) return;
    try {
        const result = await API.delete(`/facility/rooms/${id}`);
        if (!result.success) throw new Error("Delete gagal");
        await loadFacilities();
        notify("Ruangan berhasil dihapus");
    } catch (err) {
        notify("Gagal menghapus ruangan", "error");
    }
}

async function deleteDevice(id) {
    if (!confirm("Hapus alat ini?")) return;
    try {
        const result = await API.delete(`/facility/devices/${id}`);
        if (!result.success) throw new Error("Delete gagal");
        await loadFacilities();
        notify("Unit berhasil dihapus");
    } catch (err) {
        notify("Gagal menghapus unit", "error");
    }
}

const overlay = document.getElementById("modal-overlay");
const sheet = overlay.querySelector(".modal-sheet");
const formContent = document.getElementById("modal-form-content");
const modalTitle = document.getElementById("modal-title");
const adminForm = document.getElementById("admin-form");

function openModal(title, contentHtml, action, id = null) {
    modalTitle.innerText = title;
    formContent.innerHTML = contentHtml;
    currentAction = action;
    currentId = id;

    overlay.style.display = "flex";
    setTimeout(() => {
        sheet.style.transform = "translateY(0)";
    }, 10);
}

function closeModal() {
    sheet.style.transform = "translateY(100%)";
    setTimeout(() => {
        overlay.style.display = "none";
    }, 300);
}

overlay.addEventListener("click", event => {
    if (event.target === overlay) closeModal();
});

function openAddStaff() {
    openModal("Tambah Staf Baru", staffForm(), "ADD_STAFF");
}

function openEditStaff(staff) {
    openModal("Edit Staf", staffForm(staff), "EDIT_STAFF", staff.id);
}

function staffForm(staff = {}) {
    return `
        <div class="form-group">
            <label class="input-label">Nama Lengkap</label>
            <input type="text" id="staff-name" class="input-field" value="${staff.full_name || staff.username || ""}" required>
        </div>
        <div class="form-group">
            <label class="input-label">Username</label>
            <input type="text" id="staff-username" class="input-field" value="${staff.username || ""}" required>
        </div>
        <div class="form-group">
            <label class="input-label">Role</label>
            <select id="staff-role" class="input-field">
                <option value="staff" ${staff.role === "staff" ? "selected" : ""}>QC Staff</option>
                <option value="admin" ${staff.role === "admin" ? "selected" : ""}>Administrator</option>
            </select>
        </div>
        <div class="form-group">
            <label class="input-label">${staff.id ? "Password Baru (Opsional)" : "Password"}</label>
            <input type="password" id="staff-password" class="input-field" placeholder="${staff.id ? "Kosongkan jika tidak diganti" : "Minimal 6 karakter"}" ${staff.id ? "" : "required"}>
        </div>
    `;
}

function openAddRoom() {
    openModal("Tambah Ruangan", roomForm(), "ADD_ROOM");
}

function openEditRoom(room) {
    openModal("Edit Ruangan", roomForm(room), "EDIT_ROOM", room.id);
}

function roomForm(room = {}) {
    return `
        <div class="form-group">
            <label class="input-label">Nama Ruangan</label>
            <input type="text" id="room-name" class="input-field" value="${room.name || ""}" required>
        </div>
        <div class="form-group">
            <label class="input-label">Deskripsi</label>
            <input type="text" id="room-desc" class="input-field" value="${room.description || ""}">
        </div>
    `;
}

function addDeviceToRoom(roomId) {
    openModal("Tambah Alat Baru", deviceForm({ room_id: roomId }), "ADD_DEVICE");
}

function openEditDevice(device) {
    openModal("Edit Alat", deviceForm(device), "EDIT_DEVICE", device.id);
}

function deviceForm(device = {}) {
    return `
        <input type="hidden" id="device-room-id" value="${device.room_id || ""}">
        <div class="form-group">
            <label class="input-label">Nama Alat</label>
            <input type="text" id="device-name" class="input-field" value="${device.name || ""}" required>
        </div>
        <div class="form-group">
            <label class="input-label">Tipe Alat</label>
            <select id="device-type" class="input-field">
                <option value="chiller" ${device.type === "chiller" ? "selected" : ""}>Chiller</option>
                <option value="freezer" ${device.type === "freezer" ? "selected" : ""}>Freezer</option>
                <option value="undercounter" ${device.type === "undercounter" ? "selected" : ""}>Undercounter</option>
                <option value="room_temp" ${device.type === "room_temp" ? "selected" : ""}>Suhu Ruangan</option>
            </select>
        </div>
        <div class="form-group">
            <label class="input-label">Ambang Batas Suhu (&deg;C)</label>
            <input type="number" id="device-threshold" class="input-field" value="${device.threshold_temp || 5}" step="0.1">
        </div>
    `;
}

adminForm.addEventListener("submit", async event => {
    event.preventDefault();
    const btn = event.target.querySelector("button");
    btn.disabled = true;
    btn.innerText = "MENYIMPAN...";

    try {
        let message = "Data berhasil disimpan";
        if (currentAction === "ADD_STAFF" || currentAction === "EDIT_STAFF") {
            const payload = {
                full_name: document.getElementById("staff-name").value,
                username: document.getElementById("staff-username").value,
                role: document.getElementById("staff-role").value,
            };
            const password = document.getElementById("staff-password").value;
            if (password) payload.password = password;
            if (currentAction === "ADD_STAFF") {
                await API.post("/staff", payload);
                message = "Staf berhasil ditambahkan";
            } else {
                await API.patch(`/staff/${currentId}`, payload);
                message = "Staf berhasil diperbarui";
            }
            await loadStaff();
        } else if (currentAction === "ADD_ROOM" || currentAction === "EDIT_ROOM") {
            const payload = {
                name: document.getElementById("room-name").value,
                description: document.getElementById("room-desc").value,
            };
            if (currentAction === "ADD_ROOM") {
                await API.post("/facility/rooms", payload);
                message = "Ruangan berhasil ditambahkan";
            } else {
                await API.patch(`/facility/rooms/${currentId}`, payload);
                message = "Ruangan berhasil diperbarui";
            }
            await loadFacilities();
        } else if (currentAction === "ADD_DEVICE" || currentAction === "EDIT_DEVICE") {
            const payload = {
                name: document.getElementById("device-name").value,
                type: document.getElementById("device-type").value,
                threshold: parseFloat(document.getElementById("device-threshold").value),
            };
            if (currentAction === "ADD_DEVICE") {
                payload.room_id = document.getElementById("device-room-id").value;
                await API.post("/facility/devices", payload);
                message = "Unit berhasil ditambahkan";
            } else {
                await API.patch(`/facility/devices/${currentId}`, payload);
                message = "Unit berhasil diperbarui";
            }
            await loadFacilities();
        }
        closeModal();
        notify(message);
    } catch (err) {
        notify(`Gagal menyimpan data: ${err.message}`, "error");
    } finally {
        btn.disabled = false;
        btn.innerText = "SIMPAN DATA";
    }
});

async function loadAnalytics() {
    try {
        const stats = await API.get("/monitoring/stats");
        const rows = Array.isArray(stats) ? stats : [];
        const recent = rows.slice(-12);
        const labels = recent.map(row => new Date(row.recorded_at).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }));
        const temps = recent.map(row => Number(row.temperature_c || 0));
        const normal = rows.filter(row => row.is_normal).length;
        const abnormal = Math.max(rows.length - normal, 0);

        new Chart(document.getElementById("tempTrendChart"), {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: "Suhu",
                    data: temps,
                    borderColor: "#0052cc",
                    backgroundColor: "rgba(0, 82, 204, .12)",
                    tension: .35,
                    fill: true,
                }],
            },
            options: { responsive: true, plugins: { legend: { display: false } } },
        });

        new Chart(document.getElementById("alertDistChart"), {
            type: "doughnut",
            data: {
                labels: ["Normal", "Abnormal"],
                datasets: [{ data: [normal, abnormal], backgroundColor: ["#22c55e", "#ef4444"] }],
            },
            options: { responsive: true, plugins: { legend: { position: "bottom" } } },
        });
    } catch (err) {
        console.error("Gagal memuat analytics", err);
    }
}
