/**
 * Monitoring Logic JS
 * Handles dynamic room/device loading, photo preview, and logging.
 */

const roomList = document.getElementById("room-list");
const deviceList = document.getElementById("device-list");
const modal = document.getElementById("log-modal");
const overlay = document.getElementById("overlay");
const deviceCountLabel = document.getElementById("deviceCount");
const currentRoomLabel = document.getElementById("currentRoomName");

let facilityStructure = [];
let selectedRoomId = null;
let selectedPhotoFile = null;

document.addEventListener("DOMContentLoaded", () => {
    loadFacilityStructure();
    loadRecentLogs();
});

function authHeaders() {
    const token = localStorage.getItem("qc_token");
    return token ? { "Authorization": `Bearer ${token}` } : {};
}

async function loadFacilityStructure() {
    try {
        const res = await fetch("/api/facility/structure", { headers: authHeaders() });
        if (res.status === 401) {
            window.location.href = "/login.html";
            return;
        }
        facilityStructure = await res.json();

        if (facilityStructure.some(room => String(room.id).startsWith("room-"))) {
            document.getElementById("offlineIndicator").style.display = "flex";
        }

        if (!facilityStructure.length) facilityStructure = getFallbackFacility();
        renderRoomSelector();
        if (facilityStructure.length > 0) selectRoom(facilityStructure[0].id);
    } catch (err) {
        console.error("Gagal memuat struktur fasilitas", err);
        facilityStructure = getFallbackFacility();
        renderRoomSelector();
        selectRoom(facilityStructure[0].id);
    }
}

function getFallbackFacility() {
    return [{
        id: "fallback-cold-kitchen",
        name: "Cold Kitchen",
        devices: [
            { id: "fallback-freezer-a", name: "Freezer Line A", type: "freezer", threshold_temp: -18 },
            { id: "fallback-chiller-prep", name: "Chiller Prep", type: "chiller", threshold_temp: 4 },
            { id: "fallback-room-temp", name: "Prep Room", type: "room_temp", threshold_temp: 22 }
        ]
    }];
}

function renderRoomSelector() {
    if (!facilityStructure.length) {
        roomList.innerHTML = `<div class="room-chip active">Belum ada ruangan</div>`;
        currentRoomLabel.innerText = "Setup fasilitas belum tersedia";
        return;
    }

    roomList.innerHTML = facilityStructure.map(room => `
        <div class="room-chip ${room.id === selectedRoomId ? "active" : ""}" onclick="selectRoom('${room.id}')">
            ${room.name}
        </div>
    `).join("");
}

function selectRoom(roomId) {
    selectedRoomId = roomId;
    const room = facilityStructure.find(item => item.id === roomId);
    if (!room) return;

    currentRoomLabel.innerText = room.name;
    renderRoomSelector();
    renderDevices(room.devices || []);
}

function iconForType(type) {
    if (type === "chiller") return "fa-temperature-low";
    if (type === "freezer") return "fa-icicles";
    if (type === "undercounter") return "fa-box";
    return "fa-thermometer-half";
}

function renderDevices(devices) {
    deviceCountLabel.innerText = `${devices.length} Unit`;
    document.getElementById("summaryUnitCount").innerText = devices.length;
    document.getElementById("summaryStatus").innerText = devices.length ? "Aktif" : "Kosong";

    if (!devices.length) {
        deviceList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-temperature-half"></i>
                <h4>Belum ada unit monitoring</h4>
                <p>Tambahkan freezer, chiller, atau titik suhu ruangan dari panel admin agar staff bisa mulai mencatat suhu.</p>
                <button class="btn-primary" type="button" onclick="window.location.href='dashboard.html'">
                    <i class="fas fa-arrow-left"></i> Kembali Dashboard
                </button>
            </div>
        `;
        return;
    }

    deviceList.innerHTML = devices.map(device => `
        <div class="device-card ${device.type}" onclick="openLogModal('${device.id}')">
            <div class="device-icon">
                <i class="fas ${iconForType(device.type)}"></i>
            </div>
            <div class="status-badge success device-status"><span class="online-dot"></span>Realtime</div>
            <div class="device-name">${device.name}</div>
            <div class="device-target">Target: ${device.threshold_temp || 0}&deg;C</div>
            <div class="device-temp">${device.threshold_temp || "--"}&deg;C</div>
            <div class="device-meta">Last update: just now - Staff checker: QC Team</div>
            <div class="sparkline"></div>
            <div class="health-bar"><span></span></div>
        </div>
    `).join("");
}

function openLogModal(deviceId) {
    const room = facilityStructure.find(item => item.id === selectedRoomId);
    const device = (room?.devices || []).find(item => item.id === deviceId);
    if (!device) return;

    document.getElementById("modal-title").innerText = `Log ${device.name}`;
    document.getElementById("selected-device-id").value = deviceId;
    document.getElementById("selected-room-id").value = selectedRoomId;

    const iconEl = document.getElementById("sheet-icon");
    if (iconEl) iconEl.className = `fas ${iconForType(device.type)}`;

    document.getElementById("humidity-group").style.display = device.type === "room_temp" ? "block" : "none";
    modal.classList.add("active");
    overlay.classList.add("active");
}

function closeModal() {
    modal.classList.remove("active");
    overlay.classList.remove("active");
    document.getElementById("monitoring-form").reset();
    removePhoto();
}

function triggerPhoto() {
    document.getElementById("photo-input").click();
}

let selectedPhotoFiles = [];

// ... (triggerPhoto, iconForType, etc. remain same)

document.getElementById("photo-input").addEventListener("change", event => {
    selectedPhotoFiles = Array.from(event.target.files);
    if (selectedPhotoFiles.length === 0) return;

    // Show preview of the first file
    const reader = new FileReader();
    reader.onload = loadEvent => {
        document.getElementById("preview-img").src = loadEvent.target.result;
        document.getElementById("photo-preview").style.display = "block";
        
        const badge = document.getElementById("multi-photo-badge");
        if (selectedPhotoFiles.length > 1) {
            badge.innerText = selectedPhotoFiles.length;
            badge.style.display = "flex";
        } else {
            badge.style.display = "none";
        }
    };
    reader.readAsDataURL(selectedPhotoFiles[0]);
});

function removePhoto() {
    selectedPhotoFiles = [];
    const input = document.getElementById("photo-input");
    const image = document.getElementById("preview-img");
    const preview = document.getElementById("photo-preview");
    const badge = document.getElementById("multi-photo-badge");
    if (input) input.value = "";
    if (image) image.src = "";
    if (preview) preview.style.display = "none";
    if (badge) badge.style.display = "none";
}

document.getElementById("monitoring-form").addEventListener("submit", async event => {
    event.preventDefault();

    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;

    // Validation
    for (const file of selectedPhotoFiles) {
        const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
            alert(`Format file ${file.name} tidak didukung. Gunakan JPG, PNG, atau WEBP.`);
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            alert(`Ukuran file ${file.name} terlalu besar. Maksimal 10MB.`);
            return;
        }
    }

    const user = JSON.parse(localStorage.getItem("qc_user") || "{}");

    // Parallel Upload using Promise.all
    let photoUrls = [];
    if (selectedPhotoFiles.length > 0) {
        try {
            const uploadPromises = selectedPhotoFiles.map(async (file) => {
                const fd = new FormData();
                fd.append("photo", file);
                const res = await fetch("/api/storage/upload", {
                    method: "POST",
                    body: fd,
                    headers: authHeaders()
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.error || "Upload failed");
                return data.url;
            });
            photoUrls = await Promise.all(uploadPromises);
        } catch (err) {
            alert(`✕ Gagal upload foto: ${err.message}`);
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
            return;
        }
    }

    const payload = {
        device_id: document.getElementById("selected-device-id").value,
        room_id: document.getElementById("selected-room-id").value,
        staff_id: user.id || "",
        temperature: document.getElementById("input-temp").value,
        humidity: document.getElementById("input-rh").value || "",
        reason: document.getElementById("input-reason").value,
        photo_url: photoUrls.join(';')
    };

    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Menyimpan...';

        const res = await fetch("/api/monitoring/log", { 
            method: "POST", 
            body: JSON.stringify(payload), 
            headers: {
                ...authHeaders(),
                "Content-Type": "application/json"
            } 
        });
        
        const result = await res.json();
        if (result.success) {
            alert(`✓ Berhasil! Status: ${result.status}`);
            closeModal();
            loadRecentLogs();
        } else {
            alert(`✕ Gagal: ${result.error}`);
        }
    } catch (err) {
        alert("✕ Gagal menghubungi server atau timeout");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    }
});

async function loadRecentLogs() {
    try {
        const res = await fetch("/api/monitoring/latest", { headers: authHeaders() });
        if (res.status === 401) {
            window.location.href = "/login.html";
            return;
        }
        const logs = await res.json();
        const container = document.getElementById("recent-logs");
        document.getElementById("summaryLogCount").innerText = logs.length || 0;

        if (!logs.length) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-clipboard-list"></i>
                    <h4>Belum ada log suhu</h4>
                    <p>Log terbaru akan muncul setelah staff menyimpan laporan suhu pertama.</p>
                    <button class="btn-primary" type="button" onclick="document.querySelector('.device-card')?.click()">
                        <i class="fas fa-plus"></i> Input Suhu
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = logs.map(log => `
            <div class="log-item ${log.is_normal ? "" : "alert"}">
                <div class="log-info">
                    <div class="log-title">${log.facility_rooms?.name || "Area"} - ${log.facility_devices?.name || "Suhu Ruang"}</div>
                    <div class="log-meta">${new Date(log.recorded_at).toLocaleTimeString()} - ${log.temperature_c}&deg;C ${log.humidity_rh ? `- ${log.humidity_rh}%RH` : ""}</div>
                </div>
                <div class="log-status ${log.is_normal ? "pass" : "fail"}">
                    ${log.is_normal ? "NORMAL" : "ABNORMAL"}
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Gagal memuat log", err);
    }
}
