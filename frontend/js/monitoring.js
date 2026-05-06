/**
 * Monitoring Logic JS
 * Handles dynamic room/device loading and logging
 */

// DOM Elements
const roomList = document.getElementById("room-list");
const deviceList = document.getElementById("device-list");
const modal = document.getElementById("log-modal");
const overlay = document.getElementById("overlay");
const deviceCountLabel = document.getElementById("deviceCount");
const currentRoomLabel = document.getElementById("currentRoomName");

let facilityStructure = [];
let selectedRoomId = null;

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    loadFacilityStructure();
    loadRecentLogs();
});

async function loadFacilityStructure() {
    try {
        const res = await fetch("/api/facility/structure");
        facilityStructure = await res.json();
        
        // Show offline warning
        if (facilityStructure.some(r => r.id.startsWith('room-'))) {
            document.getElementById('offlineIndicator').style.display = 'flex';
        }

        renderRoomSelector();
        if (facilityStructure.length > 0) {
            selectRoom(facilityStructure[0].id);
        }
    } catch (err) {
        console.error("Gagal memuat struktur fasilitas", err);
    }
}

function renderRoomSelector() {
    roomList.innerHTML = facilityStructure.map(room => `
        <div class="room-chip ${room.id === selectedRoomId ? 'active' : ''}" 
             onclick="selectRoom('${room.id}')">
            ${room.name}
        </div>
    `).join("");
}

function selectRoom(roomId) {
    selectedRoomId = roomId;
    const room = facilityStructure.find(r => r.id === roomId);
    if (!room) return;

    currentRoomLabel.innerText = room.name;
    renderRoomSelector(); // Update active chip
    renderDevices(room.devices);
}

function renderDevices(devices) {
    deviceCountLabel.innerText = `${devices.length} Unit`;
    deviceList.innerHTML = devices.map(device => {
        let icon = "fa-thermometer-half";
        if (device.type === 'chiller') icon = "fa-refrigerator";
        if (device.type === 'freezer') icon = "fa-icicles";
        if (device.type === 'undercounter') icon = "fa-box";

        return `
            <div class="device-card ${device.type}" onclick="openLogModal('${device.id}')">
                <div class="device-icon">
                    <i class="fas ${icon}"></i>
                </div>
                <div class="device-name">${device.name}</div>
                <div class="device-target">Target: ${device.threshold_temp}°C</div>
            </div>
        `;
    }).join("");
}

function openLogModal(deviceId) {
    const room = facilityStructure.find(r => r.id === selectedRoomId);
    const device = room.devices.find(d => d.id === deviceId);
    if (!device) return;

    document.getElementById("modal-title").innerText = `Log ${device.name}`;
    document.getElementById("selected-device-id").value = deviceId;
    document.getElementById("selected-room-id").value = selectedRoomId;
    
    // Icon mapping
    const iconEl = document.getElementById("sheet-icon");
    if(iconEl) {
        iconEl.className = "fas";
        if (device.type === 'chiller') iconEl.classList.add("fa-refrigerator");
        else if (device.type === 'freezer') iconEl.classList.add("fa-icicles");
        else iconEl.classList.add("fa-thermometer-half");
    }

    // Hide/Show humidity for non-room devices
    document.getElementById("humidity-group").style.display = device.type === 'room_temp' ? 'block' : 'none';

    modal.classList.add("active");
    overlay.classList.add("active");
}

function closeModal() {
    modal.classList.remove("active");
    overlay.classList.remove("active");
    document.getElementById("monitoring-form").reset();
}

function triggerPhoto() {
    document.getElementById("photo-input").click();
}

document.getElementById("monitoring-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const user = JSON.parse(localStorage.getItem("qc_user") || "{}");
    const payload = {
        device_id: document.getElementById("selected-device-id").value,
        room_id: document.getElementById("selected-room-id").value,
        staff_id: user.id || null,
        temperature: document.getElementById("input-temp").value,
        humidity: document.getElementById("input-rh").value || null,
        reason: document.getElementById("input-reason").value,
        photo_url: "" // To be implemented with actual upload
    };

    try {
        const res = await fetch("/api/monitoring/log", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        const result = await res.json();
        if (result.success) {
            alert(`Berhasil! Status: ${result.status}`);
            closeModal();
            loadRecentLogs();
        } else {
            alert("Gagal menyimpan data: " + result.error);
        }
    } catch (err) {
        alert("Gagal menghubungi server");
    }
});

async function loadRecentLogs() {
    try {
        const res = await fetch("/api/monitoring/latest");
        const logs = await res.json();
        const container = document.getElementById("recent-logs");
        
        container.innerHTML = logs.map(log => `
            <div class="log-item ${log.is_normal ? '' : 'alert'}">
                <div class="log-info">
                    <div class="log-title">${log.facility_rooms?.name} - ${log.facility_devices?.name || 'Suhu Ruang'}</div>
                    <div class="log-meta">${new Date(log.recorded_at).toLocaleTimeString()} • ${log.temperature_c}°C ${log.humidity_rh ? ' • ' + log.humidity_rh + '%RH' : ''}</div>
                </div>
                <div class="log-status ${log.is_normal ? 'pass' : 'fail'}">
                    ${log.is_normal ? 'NORMAL' : 'ABNORMAL'}
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Gagal memuat log", err);
    }
}