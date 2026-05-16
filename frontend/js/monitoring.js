/**
 * Monitoring Logic JS
 * Handles dynamic room/device loading, photo preview, and temperature logging.
 */

const roomList = document.getElementById("room-list");
const deviceList = document.getElementById("device-list");
const modal = document.getElementById("log-modal");
const overlay = document.getElementById("overlay");
const deviceCountLabel = document.getElementById("deviceCount");
const currentRoomLabel = document.getElementById("currentRoomName");
const DEFAULT_ROOMS = ["PPIC", "Grouper", "Pack Basah", "Pack Kering", "Ruang Kopi", "Kitchen"];
const DEFAULT_UNITS = [
    { type: "room_temp", name: "Suhu Ruangan", threshold_temp: 25 },
    { type: "chiller", name: "Chiller", threshold_temp: 5 },
    { type: "freezer", name: "Freezer", threshold_temp: -18 },
];

let facilityStructure = [];
let selectedRoomId = null;
let selectedPhotoFiles = [];
let latestTemperatureLogs = [];
let activeUnitFilter = "all";

document.addEventListener("DOMContentLoaded", () => {
    bindUnitFilters();
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
        const structure = await res.json();
        facilityStructure = ensureDefaultMatrix(Array.isArray(structure) ? structure : []);
        if (!facilityStructure.length && latestTemperatureLogs.length) {
            facilityStructure = structureFromLogs(latestTemperatureLogs);
        }
        renderRoomSelector();
        if (facilityStructure.length) selectRoom("all");
    } catch (err) {
        console.error("Gagal memuat struktur fasilitas", err);
        facilityStructure = ensureDefaultMatrix([]);
        renderRoomSelector();
        selectRoom("all");
    }
}

function renderRoomSelector() {
    if (!facilityStructure.length) {
        if (latestTemperatureLogs.length) {
            facilityStructure = structureFromLogs(latestTemperatureLogs);
            if (facilityStructure.length) {
                renderRoomSelector();
                selectRoom(preferredRoomId());
                return;
            }
        }
        roomList.innerHTML = `<div class="room-chip active">Belum ada unit</div>`;
        currentRoomLabel.innerText = "Belum ada unit monitoring";
        renderDevices([], { hasLogs: false });
        return;
    }
    roomList.innerHTML = `
        <div class="room-chip ${selectedRoomId === "all" ? "active" : ""}" onclick="selectRoom('all')">
            Semua Ruangan
        </div>
    ` + facilityStructure.map(room => `
        <div class="room-chip ${room.id === selectedRoomId ? "active" : ""}" onclick="selectRoom('${room.id}')">
            ${room.name}
        </div>
    `).join("");
}

function preferredRoomId() {
    const roomWithDevices = facilityStructure.find(room => (room.devices || []).length);
    return (roomWithDevices || facilityStructure[0])?.id;
}

function selectRoom(roomId) {
    selectedRoomId = roomId;
    if (roomId === "all") {
        currentRoomLabel.innerText = "Semua area monitoring";
        renderRoomSelector();
        renderDevices(filteredDevices());
        return;
    }
    const room = facilityStructure.find(item => item.id === roomId);
    if (!room) return;
    currentRoomLabel.innerText = room.name;
    renderRoomSelector();
    renderDevices(filteredDevices(room.devices || []));
}

function iconForType(type) {
    if (type === "chiller") return "fa-temperature-low";
    if (type === "freezer") return "fa-icicles";
    if (type === "undercounter") return "fa-box";
    return "fa-thermometer-half";
}

function renderDevices(devices, options = {}) {
    if (!devices.length && latestTemperatureLogs.length && !facilityStructure.length) {
        facilityStructure = structureFromLogs(latestTemperatureLogs);
        if (facilityStructure.length) {
            selectRoom(preferredRoomId());
            return;
        }
    }
    const totalDevices = allDevices().length;
    deviceCountLabel.innerText = `${devices.length} Unit`;
    document.getElementById("summaryUnitCount").innerText = totalDevices || devices.length;
    document.getElementById("summaryStatus").innerText = totalDevices || devices.length ? "Aktif" : "Kosong";

    if (!devices.length) {
        const hasLogs = options.hasLogs ?? latestTemperatureLogs.length > 0;
        deviceList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-temperature-half"></i>
                <h4>${hasLogs ? "Unit belum terpetakan" : "Belum ada unit monitoring"}</h4>
                <p>${hasLogs ? "Log suhu sudah tersedia, tetapi data unit belum punya room/device yang bisa ditampilkan." : "Tambahkan freezer, chiller, atau titik suhu ruangan dari panel admin agar staff bisa mulai mencatat suhu."}</p>
                ${hasLogs ? "" : `<button class="btn-primary" type="button" onclick="window.location.href='dashboard.html'"><i class="fas fa-arrow-left"></i> Kembali Dashboard</button>`}
            </div>
        `;
        return;
    }

    deviceList.innerHTML = devices.map(device => `
        <div class="device-card ${device.type}" onclick="openLogModal('${device.id}')">
            <div class="device-icon"><i class="fas ${iconForType(device.type)}"></i></div>
            <div class="status-badge ${device.recorded_at ? "success" : "muted"} device-status">${device.recorded_at ? '<span class="online-dot"></span>Realtime' : 'No data'}</div>
            <div class="device-name">${device.display_name || device.name}</div>
            <div class="device-target">Target: ${device.threshold_temp || 0}&deg;C</div>
            <div class="device-temp">${device.last_temperature_c ?? "--"}&deg;C</div>
            <div class="device-meta">${device.recorded_at ? `Last update: ${new Date(device.recorded_at).toLocaleTimeString()} - Staff checker: QC Team` : "Belum ada log"}</div>
            <div class="sparkline"></div>
            <div class="health-bar"><span></span></div>
        </div>
    `).join("");
}

function openLogModal(deviceId) {
    const room = facilityStructure.find(item => (item.devices || []).some(device => device.id === deviceId));
    const device = (room?.devices || []).find(item => item.id === deviceId);
    if (!device) return;

    document.getElementById("modal-title").innerText = `Log ${device.display_name || device.name}`;
    document.getElementById("selected-device-id").value = deviceId;
    document.getElementById("selected-room-id").value = device.room_id || room.id;

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

document.getElementById("photo-input").addEventListener("change", event => {
    selectedPhotoFiles = Array.from(event.target.files || []);
    if (selectedPhotoFiles.length === 0) return;
    try {
        selectedPhotoFiles.forEach(file => API.validatePhoto(file));
    } catch (err) {
        alert(err.message || "Upload gagal");
        removePhoto();
        return;
    }

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

    try {
        selectedPhotoFiles.forEach(file => API.validatePhoto(file));
    } catch (err) {
        alert(err.message || "Upload gagal");
        return;
    }

    const user = JSON.parse(localStorage.getItem("qc_user") || "{}");
    const formData = new FormData();
    formData.append("device_id", document.getElementById("selected-device-id").value);
    formData.append("room_id", document.getElementById("selected-room-id").value);
    formData.append("staff_id", user.id || user.user_id || user.sub || "");
    formData.append("temperature", document.getElementById("input-temp").value);
    formData.append("humidity", document.getElementById("input-rh").value || "");
    formData.append("reason", document.getElementById("input-reason").value);

    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';

        const uploadedPhotos = await Promise.all(selectedPhotoFiles.map((file, index) => {
            return API.uploadPhotoToSupabase(file, {
                staffId: user.id || user.user_id || user.sub || user.username || "staff",
                source: `temperature-log-${index + 1}`
            });
        }));

        if (uploadedPhotos.length) {
            formData.append("photo_url", uploadedPhotos.map(photo => photo.url).join(";"));
            formData.append("storage_path", uploadedPhotos.map(photo => photo.storage_path).join(";"));
        }

        const result = await API.upload("/monitoring/log", formData);
        if (result.success) {
            alert("Log suhu berhasil disimpan");
            closeModal();
            loadRecentLogs();
        } else {
            alert("Gagal menyimpan log suhu: kolom database belum sinkron");
        }
    } catch (err) {
        const message = String(err.message || "").includes("schema cache")
            ? "Gagal menyimpan log suhu: kolom database belum sinkron"
            : "Gagal menyimpan log suhu: server tidak merespons";
        alert(message);
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
        latestTemperatureLogs = Array.isArray(logs) ? logs : [];
        const fallbackStructure = structureFromLogs(latestTemperatureLogs);
        facilityStructure = mergeLogStructure(ensureDefaultMatrix(facilityStructure), fallbackStructure);
        renderRoomSelector();
        selectRoom(selectedRoomId || "all");
        const container = document.getElementById("recent-logs");
        document.getElementById("summaryLogCount").innerText = latestTemperatureLogs.length || 0;

        if (!latestTemperatureLogs.length) {
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

        container.innerHTML = latestTemperatureLogs.map(log => `
            <div class="log-item ${log.is_normal ? "" : "alert"}">
                <div class="log-info">
                    <div class="log-title">${log.zone || log.facility_rooms?.name || log.room_name || "Area"} - ${log.facility_devices?.name || log.device_name || log.device_type || "Suhu Ruang"}</div>
                    <div class="log-meta">${new Date(log.recorded_at || log.created_at).toLocaleTimeString()} - ${log.temperature_c}&deg;C ${log.humidity_rh ? `- ${log.humidity_rh}%RH` : ""}</div>
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

function structureFromLogs(logs) {
    const grouped = new Map(DEFAULT_ROOMS.map(roomName => [
        roomName,
        { id: `default-room-${safeId(roomName)}`, name: roomName, devices: new Map(DEFAULT_UNITS.map(unit => [unit.type, defaultDevice(roomName, unit)])) }
    ]));
    (logs || []).forEach(log => {
        const roomName = log.zone || log.facility_rooms?.name || log.room_name || "QC Area";
        const deviceType = log.device_type || log.facility_devices?.type || "room_temp";
        const normalizedType = deviceType === "ambient" ? "room_temp" : deviceType;
        const deviceName = unitName(normalizedType, log.facility_devices?.name || log.device_name || log.unit_name);
        const roomId = log.room_id || `log-room-${safeId(roomName)}`;
        if (!grouped.has(roomName)) {
            grouped.set(roomName, { id: roomId, name: roomName, devices: new Map() });
        }
        grouped.get(roomName).devices.set(normalizedType, {
            id: log.device_id || `${roomId}-${safeId(normalizedType)}`,
            room_id: roomId,
            name: deviceName,
            display_name: `${roomName} - ${deviceName}`,
            type: normalizedType,
            threshold_temp: log.threshold_temp || log.threshold_c || log.facility_devices?.threshold_temp || (normalizedType === "freezer" ? -18 : normalizedType === "chiller" ? 5 : 25),
            last_temperature_c: log.temperature_c,
            recorded_at: log.recorded_at || log.created_at,
        });
    });
    const preferred = ["PPIC", "Grouper", "Pack Basah", "Pack Kering", "Ruang Kopi", "Kitchen"];
    const orderedNames = [
        ...preferred.filter(name => grouped.has(name)),
        ...Array.from(grouped.keys()).filter(name => !preferred.includes(name)).sort(),
    ];
    return orderedNames.map(name => {
        const room = grouped.get(name);
        return { id: room.id, name: room.name, devices: Array.from(room.devices.values()) };
    });
}

function bindUnitFilters() {
    document.querySelectorAll(".filter-chip").forEach(button => {
        button.addEventListener("click", () => {
            const label = button.textContent.trim().toLowerCase();
            activeUnitFilter = label.startsWith("chiller") ? "chiller" : label.startsWith("freezer") ? "freezer" : label.startsWith("critical") ? "critical" : label.startsWith("active") ? "active" : "all";
            document.querySelectorAll(".filter-chip").forEach(item => item.classList.toggle("active", item === button));
            renderDevices(filteredDevices(selectedRoomId === "all" || !selectedRoomId ? null : (facilityStructure.find(room => room.id === selectedRoomId)?.devices || [])));
        });
    });
}

function allDevices() {
    return facilityStructure.flatMap(room => room.devices || []);
}

function filteredDevices(devices = null) {
    const source = devices || allDevices();
    if (activeUnitFilter === "chiller") return source.filter(device => device.type === "chiller" || device.type === "undercounter");
    if (activeUnitFilter === "freezer") return source.filter(device => device.type === "freezer");
    if (activeUnitFilter === "critical") return source.filter(device => device.is_normal === false);
    if (activeUnitFilter === "active") return source.filter(device => Boolean(device.recorded_at));
    return source;
}

function ensureDefaultMatrix(structure) {
    const byName = new Map((structure || []).map(room => [room.name, { ...room, devices: normalizeRoomDevices(room) }]));
    DEFAULT_ROOMS.forEach(roomName => {
        if (!byName.has(roomName)) {
            byName.set(roomName, {
                id: `default-room-${safeId(roomName)}`,
                name: roomName,
                devices: DEFAULT_UNITS.map(unit => defaultDevice(roomName, unit)),
            });
        }
    });
    return [
        ...DEFAULT_ROOMS.map(name => byName.get(name)),
        ...Array.from(byName.values()).filter(room => !DEFAULT_ROOMS.includes(room.name)).sort((a, b) => a.name.localeCompare(b.name)),
    ];
}

function normalizeRoomDevices(room) {
    const byType = new Map(DEFAULT_UNITS.map(unit => [unit.type, defaultDevice(room.name, unit, room.id)]));
    (room.devices || []).forEach(device => {
        const type = device.type === "ambient" ? "room_temp" : device.type;
        byType.set(type, {
            ...device,
            id: device.id || `${room.id || `default-room-${safeId(room.name)}`}-${safeId(type)}`,
            room_id: device.room_id || room.id || `default-room-${safeId(room.name)}`,
            name: unitName(type, device.name),
            display_name: `${room.name} - ${unitName(type, device.name)}`,
            type,
            threshold_temp: device.threshold_temp ?? defaultThreshold(type),
        });
    });
    return Array.from(byType.values());
}

function mergeLogStructure(baseStructure, logStructure) {
    const byName = new Map(baseStructure.map(room => [room.name, { ...room, devices: [...(room.devices || [])] }]));
    (logStructure || []).forEach(logRoom => {
        const room = byName.get(logRoom.name) || { ...logRoom, devices: normalizeRoomDevices(logRoom) };
        const byType = new Map((room.devices || []).map(device => [device.type, device]));
        (logRoom.devices || []).forEach(device => byType.set(device.type, device));
        room.devices = Array.from(byType.values());
        byName.set(logRoom.name, room);
    });
    return [
        ...DEFAULT_ROOMS.map(name => byName.get(name)).filter(Boolean),
        ...Array.from(byName.values()).filter(room => !DEFAULT_ROOMS.includes(room.name)).sort((a, b) => a.name.localeCompare(b.name)),
    ];
}

function defaultDevice(roomName, unit, roomId = null) {
    const resolvedRoomId = roomId || `default-room-${safeId(roomName)}`;
    return {
        id: `${resolvedRoomId}-${safeId(unit.type)}`,
        room_id: resolvedRoomId,
        name: unit.name,
        display_name: `${roomName} - ${unit.name}`,
        type: unit.type,
        threshold_temp: unit.threshold_temp,
        is_default: true,
        last_temperature_c: null,
        recorded_at: null,
    };
}

function unitName(type, fallback) {
    if (type === "room_temp") return "Suhu Ruangan";
    if (type === "chiller" || type === "undercounter") return "Chiller";
    if (type === "freezer") return "Freezer";
    return fallback || "Suhu Ruangan";
}

function defaultThreshold(type) {
    if (type === "freezer") return -18;
    if (type === "chiller" || type === "undercounter") return 5;
    return 25;
}

function safeId(value) {
    return String(value || "unit").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "unit";
}
