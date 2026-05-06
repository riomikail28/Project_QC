/**
 * Monitoring Logic JS
 * Handles dynamic room/device loading and logging
 */

let facilityStructure = [];
let selectedRoom = null;

document.addEventListener("DOMContentLoaded", () => {
    loadFacilityStructure();
    loadRecentLogs();
});

async function loadFacilityStructure() {
    try {
        const res = await fetch("/api/facility/structure");
        facilityStructure = await res.json();
        
        // Show offline warning if structure looks like fallback
        if (facilityStructure.some(r => r.id.startsWith('room-'))) {
            const header = document.querySelector('.header-content');
            const warn = document.createElement('div');
            warn.innerHTML = '<span style="background:#fff7e6; color:#d46b08; padding:4px 8px; border-radius:4px; font-size:12px; margin-left:10px;"><i class="fas fa-wifi-slash"></i> Offline Mode</span>';
            header.appendChild(warn);
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
    const container = document.getElementById("room-list");
    container.innerHTML = facilityStructure.map(room => `
        <div class="room-chip ${selectedRoom === room.id ? 'active' : ''}" 
             onclick="selectRoom('${room.id}')">
            ${room.name}
        </div>
    `).join("");
}

function selectRoom(roomId) {
    selectedRoom = roomId;
    renderRoomSelector();
    renderDevices();
}

function renderDevices() {
    const container = document.getElementById("device-list");
    const room = facilityStructure.find(r => r.id === selectedRoom);
    
    if (!room || !room.devices) {
        container.innerHTML = '<div class="empty-state">Tidak ada alat di ruangan ini</div>';
        return;
    }

    container.innerHTML = room.devices.map(dev => `
        <div class="device-card" onclick="openLogModal('${dev.id}', '${dev.name}', '${dev.type}')">
            <div class="device-icon">
                <i class="fas ${getDeviceIcon(dev.type)}"></i>
            </div>
            <div class="device-name">${dev.name}</div>
            <div class="device-status">Target: ${dev.threshold_temp}°C</div>
        </div>
    `).join("");
}

function getDeviceIcon(type) {
    switch(type) {
        case 'chiller': return 'fa-refrigerator';
        case 'freezer': return 'fa-snowflake';
        case 'undercounter': return 'fa-box-open';
        case 'room_temp': return 'fa-thermometer-half';
        default: return 'fa-hdd';
    }
}

function openLogModal(deviceId, deviceName, type) {
    document.getElementById("modal-title").innerText = `Log: ${deviceName}`;
    document.getElementById("selected-device-id").value = deviceId;
    document.getElementById("selected-room-id").value = selectedRoom;
    
    // Show/hide humidity based on type
    const humGroup = document.getElementById("humidity-group");
    humGroup.style.display = (type === 'room_temp') ? 'block' : 'none';

    document.getElementById("overlay").style.display = "block";
    document.getElementById("log-modal").style.display = "block";
}

function closeModal() {
    document.getElementById("overlay").style.display = "none";
    document.getElementById("log-modal").style.display = "none";
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