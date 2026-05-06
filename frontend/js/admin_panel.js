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

// --- Analytics Charts ---
async function initCharts() {
    const res = await fetch("/api/monitoring/stats");
    const data = await res.json();
    
    // Placeholder data for demo if stats are empty
    const labels = ['06:00', '09:00', '12:00', '15:00', '18:00', '21:00'];
    const tempData = [4.2, 4.5, 5.1, 4.8, 4.3, 4.1];
    
    // Temp Trend
    new Chart(document.getElementById('tempTrendChart'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Suhu Chiller 1 (°C)',
                data: tempData,
                borderColor: '#0052cc',
                tension: 0.4,
                fill: true,
                backgroundColor: 'rgba(0, 82, 204, 0.1)'
            }]
        }
    });

    // Alert Dist
    new Chart(document.getElementById('alertDistChart'), {
        type: 'doughnut',
        data: {
            labels: ['Normal', 'Abnormal'],
            datasets: [{
                data: [85, 15],
                backgroundColor: ['#22c55e', '#ef4444']
            }]
        }
    });
}
