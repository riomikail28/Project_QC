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
let facilityStructure = [];
let selectedRoomId = null;
let selectedPhotoFiles = [];
let latestTemperatureLogs = [];
let activeUnitFilter = "all";
let todaySchedule = null;
const monitoringRoomOrder = ["PPIC", "Grouper", "Pack Basah", "Pack Kering", "Ruang Kopi", "Kitchen"];

document.addEventListener("DOMContentLoaded", () => {
    bindUnitFilters();
    restoreCache();
    loadTodaySchedule();
    loadFacilityStructure();
    loadRecentLogs();

    // Prefetch products for QC Check page
    if (window.requestIdleCallback) {
        requestIdleCallback(() => {
            API.getCached('/inspection/products', 1800000).catch(() => {});
        });
    } else {
        setTimeout(() => {
            API.getCached('/inspection/products', 1800000).catch(() => {});
        }, 1000);
    }
});

function authHeaders() {
    const token = localStorage.getItem("qc_token");
    return token ? { "Authorization": `Bearer ${token}` } : {};
}

async function loadFacilityStructure() {
    const started = performance.now();
    try {
        // PERFORMANCE_OPTIMIZED: reuse monitoring structure cache when returning to the page.
        const envelope = await API.getSWR("/facility/structure", {
            ttlMs: 600000,
            onUpdate: data => {
                const structure = Array.isArray(data) ? data : (data.data || []);
                facilityStructure = normalizeFacilityStructure(structure);
                renderRoomSelector();
                selectRoom(selectedRoomId || "all");
            }
        });
        const structure = Array.isArray(envelope) ? envelope : (envelope.data || []);
        facilityStructure = normalizeFacilityStructure(structure);
        renderRoomSelector();
        if (facilityStructure.length) selectRoom("all");
        console.info(`[PERFORMANCE_OPTIMIZED] Monitoring load time: ${Math.round(performance.now() - started)}ms`);
    } catch (err) {
        console.error("Gagal memuat struktur fasilitas", err);
        facilityStructure = [];
        renderRoomSelector();
        selectRoom("all");
    }
}

function renderRoomSelector() {
    if (!facilityStructure.length) {
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
    const totalDevices = allDevices().length;
    deviceCountLabel.innerText = `${devices.length} Unit`;
    document.getElementById("summaryUnitCount").innerText = totalDevices || devices.length;
    document.getElementById("summaryStatus").innerText = totalDevices || devices.length ? "Aktif" : "Kosong";
    renderNextDevice();
    renderRoomProgress();

    if (!devices.length) {
        const hasLogs = options.hasLogs ?? latestTemperatureLogs.length > 0;
        deviceList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-temperature-half"></i>
                <h4>Belum ada unit monitoring sesuai filter.</h4>
                <p>${hasLogs ? "Log suhu sudah tersedia, tetapi data unit belum punya room/device yang cocok dengan filter saat ini." : "Tambahkan freezer, chiller, atau titik suhu ruangan dari panel admin agar staff bisa mulai mencatat suhu."}</p>
                ${hasLogs ? "" : `<button class="btn-primary" type="button" onclick="window.location.href='dashboard.html'"><i class="fas fa-arrow-left"></i> Kembali Dashboard</button>`}
            </div>
        `;
        triggerSaveCache();
        return;
    }

    const visibleRooms = groupedRoomsForDevices(devices);
    deviceList.innerHTML = visibleRooms.map(room => renderMonitoringRoomGroup(room)).join("");
    triggerSaveCache();
}

function groupedRoomsForDevices(devices) {
    const selectedIds = new Set(devices.map(device => device.id));
    return facilityStructure
        .map(room => ({
            ...room,
            devices: sortMonitoringDevices((room.devices || []).filter(device => selectedIds.has(device.id))),
        }))
        .filter(room => room.devices.length)
        .sort((a, b) => monitoringRoomRank(a.name) - monitoringRoomRank(b.name) || String(a.name || "").localeCompare(String(b.name || "")));
}

function monitoringRoomRank(roomName) {
    const index = monitoringRoomOrder.findIndex(item => item.toLowerCase() === String(roomName || "").toLowerCase());
    return index === -1 ? monitoringRoomOrder.length : index;
}

function renderMonitoringRoomGroup(room) {
    const progress = roomProgress(room);
    return `
        <article class="monitoring-room-grid-section" data-room-id="${room.id}" data-room-name="${room.name}">
            <div class="monitoring-room-title">
                <h4>${room.name}</h4>
                <span>${progress.completed}/${progress.total} selesai</span>
            </div>
            <div class="monitoring-device-mini-grid">
                ${room.devices.map(device => renderMonitoringDeviceMiniCard(device, room)).join("")}
            </div>
        </article>
    `;
}

function renderMonitoringDeviceMiniCard(device, room) {
    const status = monitoringMiniCardStatus(device);
    const temperature = monitoringMiniCardTemperature(device);
    return `
        <button class="monitoring-device-mini-card ${device.type} ${status.isAlert ? "alert-required" : ""}" type="button" onclick="openLogModal('${device.id}')">
            <span class="monitoring-device-mini-name">${device.name || unitName(device.type)}</span>
            <span class="monitoring-device-mini-room">${room.name}</span>
            <strong class="monitoring-device-mini-temp">${temperature}</strong>
            <span class="monitoring-device-mini-status ${status.className}">${status.label}</span>
        </button>
    `;
}

function monitoringMiniCardStatus(device) {
    const scheduleStatus = deviceScheduleStatus(device.id);
    const alert = isDeviceAlert(device);
    if (alert) return { label: "ALERT", className: "is-alert", isAlert: true };
    if (scheduleStatus.status === "completed") return { label: "PASS", className: "is-pass", isAlert: false };
    if (scheduleStatus.status === "missed") return { label: "Terlewat", className: "is-warning", isAlert: false };
    if (scheduleStatus.status === "pending") return { label: "Pending", className: "is-pending", isAlert: false };
    return { label: "Belum Input", className: "is-pending", isAlert: false };
}

function monitoringMiniCardTemperature(device) {
    const activeStatus = todaySchedule?.device_statuses?.[device.id]?.active_status;
    const raw = activeStatus?.temperature_c ?? device.last_temperature_c ?? device.temperature_c;
    const value = Number(raw);
    if (!Number.isFinite(value)) return "--&deg;C";
    return `${Number.isInteger(value) ? value : value.toFixed(1)}&deg;C`;
}

function openLogModal(deviceId) {
    const activeSlot = activeMonitoringSlot();
    if (!activeSlot) {
        showMonitoringToast(scheduleUnavailableMessage(), true);
        return;
    }
    const room = facilityStructure.find(item => (item.devices || []).some(device => device.id === deviceId));
    const device = (room?.devices || []).find(item => item.id === deviceId);
    if (!device) return;
    const deviceStatus = deviceScheduleStatus(deviceId);
    if (deviceStatus.status === "completed") {
        showMonitoringToast(`Unit ini sudah diinput untuk slot ${activeSlot.time}.`, true);
        return;
    }
    if (!isUuid(room.id) || !isUuid(device.id) || !isUuid(device.room_id || room.id)) {
        showMonitoringToast("Data ruangan/unit belum sinkron. Refresh halaman.", true);
        return;
    }

    document.getElementById("modal-title").innerText = `Log ${device.display_name || device.name}`;
    document.getElementById("selected-device-id").value = deviceId;
    document.getElementById("selected-room-id").value = device.room_id || room.id;
    document.getElementById("selected-slot-time").value = activeSlot.time;
    const slotContext = document.getElementById("slotContext");
    if (slotContext) {
        slotContext.innerHTML = `
            <strong>Slot ${activeSlot.time}</strong>
            <span>${activeSlot.label}${activeSlot.status === "pending" ? " - input akan dicatat pada jadwal ini" : ""}</span>
        `;
    }

    const iconEl = document.getElementById("sheet-icon");
    if (iconEl) iconEl.className = `fas ${iconForType(device.type)}`;

    document.getElementById("humidity-group").style.display = device.type === "room_temp" ? "block" : "none";
    modal.classList.add("active");
    overlay.classList.add("active");
    document.body.classList.add("modal-open");
}

function closeModal() {
    modal.classList.remove("active");
    overlay.classList.remove("active");
    document.body.classList.remove("modal-open");
    document.getElementById("monitoring-form").reset();
    removePhoto();
}

document.addEventListener("keydown", event => {
    if (event.key === "Escape" && modal?.classList.contains("active")) {
        closeModal();
    }
});

function triggerPhoto() {
    document.getElementById("photo-input").click();
}

document.getElementById("photo-input").addEventListener("change", async event => {
    const incomingFiles = Array.from(event.target.files || []);
    selectedPhotoFiles = incomingFiles;
    if (selectedPhotoFiles.length === 0) return;
    const status = document.getElementById("photo-compression-status");
    try {
        selectedPhotoFiles.forEach(file => API.validatePhoto(file));
    } catch (err) {
        showMonitoringToast(err.message || "Upload foto gagal", true);
        removePhoto();
        return;
    }

    if (status) status.textContent = "Mengompres foto...";
    selectedPhotoFiles = await API.preparePhotos(incomingFiles, { filePrefix: "qc-monitoring" });
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
    if (status) {
        const totalSize = selectedPhotoFiles.reduce((sum, item) => sum + (item.size || 0), 0);
        status.textContent = `Foto siap dikirim (${ImageCompression.formatBytes(totalSize)}).`;
    }
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
    const status = document.getElementById("photo-compression-status");
    if (status) status.textContent = "Foto akan dikompres otomatis sebelum dikirim.";
}

document.getElementById("monitoring-form").addEventListener("submit", async event => {
    event.preventDefault();

    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;

    try {
        selectedPhotoFiles.forEach(file => API.validatePhoto(file));
    } catch (err) {
        showMonitoringToast(err.message || "Upload foto gagal", true);
        return;
    }

    const user = JSON.parse(localStorage.getItem("qc_user") || "{}");
    const deviceId = document.getElementById("selected-device-id").value;
    const roomId = document.getElementById("selected-room-id").value;
    if (!isUuid(roomId)) {
        showMonitoringToast("Data ruangan/unit belum sinkron. Refresh halaman.", true);
        return;
    }
    if (!isUuid(deviceId)) {
        showMonitoringToast("Data ruangan/unit belum sinkron. Refresh halaman.", true);
        return;
    }
    const formData = new FormData();
    formData.append("device_id", deviceId);
    formData.append("room_id", roomId);
    formData.append("staff_id", user.id || user.user_id || user.sub || "");
    formData.append("temperature", document.getElementById("input-temp").value);
    formData.append("humidity", document.getElementById("input-rh").value || "");
    formData.append("reason", document.getElementById("input-reason").value);
    formData.append("slot_time", document.getElementById("selected-slot-time").value);

    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Menyimpan...';

        selectedPhotoFiles.forEach(file => formData.append("photo", file));

        const result = await API.upload("/facility/monitoring/submit", formData);
        if (result.success) {
            showMonitoringToast("Data monitoring berhasil disimpan.");
            closeModal();
            await loadTodaySchedule();
            loadRecentLogs();
        } else {
            showMonitoringToast(result.message || result.error || "Gagal menyimpan log suhu", true);
        }
    } catch (err) {
        const message = String(err.message || "").includes("schema cache")
            ? "Gagal menyimpan log suhu: kolom database belum sinkron"
            : (err.message || "Gagal menyimpan log suhu: server tidak merespons");
        showMonitoringToast(message, true);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    }
});

async function loadRecentLogs() {
    try {
        // PERFORMANCE_OPTIMIZED: stale logs render immediately, then background refresh updates this panel.
        const logs = await API.getSWR("/monitoring/latest", {
            ttlMs: 30000,
            onUpdate: data => renderRecentLogsData(Array.isArray(data) ? data : [])
        });
        renderRecentLogsData(Array.isArray(logs) ? logs : []);
    } catch (err) {
        console.error("Gagal memuat log", err);
    }
}

function renderRecentLogsData(logs) {
        latestTemperatureLogs = Array.isArray(logs) ? logs : [];
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
                    <button class="btn-primary" type="button" onclick="document.querySelector('.monitoring-device-mini-card')?.click()">
                        <i class="fas fa-plus"></i> Input Suhu
                    </button>
                </div>
            `;
            triggerSaveCache();
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
        triggerSaveCache();
}

async function loadTodaySchedule() {
    try {
        // PERFORMANCE_OPTIMIZED: schedule uses 30s stale-while-revalidate cache for instant return navigation.
        const response = await API.getSWR("/facility/monitoring/schedule/today", {
            ttlMs: 30000,
            onUpdate: data => {
                todaySchedule = data.data || null;
                renderTodaySchedule();
            }
        });
        todaySchedule = response.data || null;
        renderTodaySchedule();
    } catch (err) {
        console.error("Gagal memuat jadwal monitoring", err);
        todaySchedule = null;
        renderTodaySchedule();
    }
}

function renderTodaySchedule() {
    const grid = document.getElementById("scheduleSlotGrid");
    const message = document.getElementById("scheduleMessage");
    const count = document.getElementById("scheduleProgressCount");
    const bar = document.getElementById("scheduleProgressBar");
    if (!grid || !message || !count || !bar) return;

    if (!todaySchedule) {
        message.textContent = "Jadwal belum bisa dimuat. Coba refresh halaman.";
        count.textContent = "0/4";
        bar.style.width = "0%";
        grid.innerHTML = ["07:00", "13:00", "16:00", "19:00"].map(time => `
            <article class="schedule-slot upcoming">
                <strong>${time}</strong>
                <span>Belum waktunya</span>
            </article>
        `).join("");
        renderNextDevice();
        renderRoomProgress();
        triggerSaveCache();
        return;
    }

    const completed = todaySchedule.completed_count || 0;
    const total = todaySchedule.total_required || todaySchedule.total_slots || 4;
    message.textContent = todaySchedule.message || todaySchedule.progress_text || `${completed}/${total} monitoring selesai hari ini.`;
    count.textContent = `${completed}/${total}`;
    bar.style.width = `${Math.max(0, Math.min(100, Math.round((completed / total) * 100)))}%`;
    grid.innerHTML = (todaySchedule.slots || []).map(slot => `
        <article class="schedule-slot ${slot.status}">
            <strong>${slot.time}</strong>
            <span>${slot.completed_count || 0}/${slot.total_devices || todaySchedule.total_devices || 0} unit selesai</span>
            ${slot.temperature_c !== null && slot.temperature_c !== undefined ? `<small>${slot.temperature_c}&deg;C</small>` : ""}
        </article>
    `).join("");
    renderNextDevice();
    renderRoomProgress();
    triggerSaveCache();
}

function activeMonitoringSlot() {
    if (!todaySchedule) return null;
    const current = todaySchedule.current_slot;
    if (current && current.status === "pending") return current;
    return null;
}

function scheduleUnavailableMessage() {
    if (!todaySchedule) return "Jadwal monitoring belum siap. Tunggu sebentar atau refresh halaman.";
    if ((todaySchedule.completed_count || 0) >= (todaySchedule.total_slots || 4)) {
        return "Monitoring hari ini selesai. Tugas berikutnya besok pukul 07:00.";
    }
    const next = todaySchedule.next_slot;
    if (next && next.status === "upcoming") return `Slot ${next.time} belum waktunya.`;
    return "Belum ada slot monitoring yang menunggu input.";
}

function deviceScheduleStatus(deviceId) {
    const activeSlot = activeMonitoringSlot();
    const status = todaySchedule?.device_statuses?.[deviceId]?.active_status;
    if (!activeSlot || !status) {
        return { status: "idle", label: "Belum ada slot aktif", className: "muted" };
    }
    if (status.status === "completed") {
        return { status: "completed", label: "Selesai", className: "success" };
    }
    if (status.status === "missed") {
        return { status: "missed", label: "Terlewat", className: "warning" };
    }
    return { status: "pending", label: "Belum input", className: "muted" };
}

function sortMonitoringDevices(devices) {
    return [...devices].sort((a, b) => monitoringRank(a) - monitoringRank(b) || String(a.name || "").localeCompare(String(b.name || "")));
}

function monitoringRank(device) {
    const scheduleStatus = deviceScheduleStatus(device.id).status;
    if (scheduleStatus === "pending") return 1;
    if (scheduleStatus === "missed" || scheduleStatus === "late") return 2;
    if (isDeviceAlert(device)) return 3;
    if (scheduleStatus === "completed") return 4;
    return 5;
}

function isDeviceAlert(device) {
    if (device.is_normal === false) return true;
    const temp = Number(device.last_temperature_c ?? device.temperature_c);
    if (!Number.isFinite(temp)) return false;
    const min = Number(device.min_temperature ?? device.threshold_min ?? device.min_temp);
    const max = Number(device.max_temperature ?? device.threshold_max ?? device.max_temp);
    if (Number.isFinite(min) && temp < min) return true;
    if (Number.isFinite(max) && temp > max) return true;
    return false;
}

function nextDeviceToCheck() {
    const candidates = facilityStructure.flatMap(room => (room.devices || []).map(device => ({ room, device })));
    return candidates
        .filter(item => ["pending", "missed", "late"].includes(deviceScheduleStatus(item.device.id).status))
        .sort((a, b) => monitoringRank(a.device) - monitoringRank(b.device))[0] || null;
}

function renderNextDevice() {
    const section = document.getElementById("nextDeviceSection");
    if (!section) return;
    const title = document.getElementById("nextDeviceTitle");
    const status = document.getElementById("nextDeviceStatus");
    const roomEl = document.getElementById("nextDeviceRoom");
    const nameEl = document.getElementById("nextDeviceName");
    const slotEl = document.getElementById("nextDeviceSlot");
    const action = document.getElementById("nextDeviceAction");
    const next = nextDeviceToCheck();
    const activeSlot = activeMonitoringSlot();

    if (!next) {
        title.textContent = activeSlot ? "Semua device slot aktif sudah dicek" : "Belum ada slot aktif";
        status.textContent = activeSlot ? "Lanjutkan tugas QC lain atau cek log terakhir." : scheduleUnavailableMessage();
        roomEl.textContent = "--";
        nameEl.textContent = "Tidak ada prioritas";
        slotEl.textContent = `Slot: ${activeSlot?.time || "--"}`;
        action.disabled = true;
        action.onclick = null;
        section.classList.toggle("is-clear", Boolean(activeSlot));
        return;
    }

    const deviceStatus = deviceScheduleStatus(next.device.id);
    title.textContent = `${next.room.name}`;
    status.textContent = `Status: ${deviceStatus.label}`;
    roomEl.textContent = next.room.name;
    nameEl.textContent = next.device.name || unitName(next.device.type);
    slotEl.textContent = `Slot: ${activeSlot?.time || "--"}`;
    action.disabled = false;
    action.onclick = () => openLogModal(next.device.id);
    section.classList.remove("is-clear");
}

function renderRoomProgress() {
    const container = document.getElementById("roomProgressList");
    if (!container) return;
    if (!facilityStructure.length) {
        container.innerHTML = '<div class="empty-state compact">Belum ada area monitoring</div>';
        return;
    }
    container.innerHTML = facilityStructure.map(room => {
        const progress = roomProgress(room);
        return `
            <div class="room-progress-item">
                <div>
                    <strong>${room.name}</strong>
                    <span>${progress.completed}/${progress.total} device selesai</span>
                </div>
                <div class="room-progress-track"><span style="width:${progress.percent}%"></span></div>
            </div>
        `;
    }).join("");
}

function roomProgress(room) {
    const devices = room.devices || [];
    const completed = devices.filter(device => deviceScheduleStatus(device.id).status === "completed").length;
    const total = devices.length;
    return {
        completed,
        total,
        percent: total ? Math.round((completed / total) * 100) : 0,
    };
}

function lastInputMeta(device) {
    const recordedAt = device.recorded_at || device.last_recorded_at || device.created_at;
    const staff = device.staff_name || device.staff || device.recorded_by || device.user_name || "Belum ada";
    return {
        staff: recordedAt ? staff : "Belum ada",
        time: recordedAt ? new Date(recordedAt).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }) : "--",
    };
}

function showMonitoringToast(message, isError = false) {
    const globalToast = window.showToast;
    if (typeof globalToast === "function" && globalToast !== showMonitoringToast) {
        globalToast(message, isError ? "error" : "success");
        return;
    }
    console[isError ? "error" : "log"](message);
}

function bindUnitFilters() {
    document.querySelectorAll(".filter-chip").forEach(button => {
        button.addEventListener("click", () => {
            const label = button.textContent.trim().toLowerCase();
            activeUnitFilter = label.startsWith("chiller") ? "chiller" : label.startsWith("freezer") ? "freezer" : label.includes("kritis") ? "critical" : label.includes("aktif") ? "active" : "all";
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
    if (activeUnitFilter === "critical") return source.filter(device => isDeviceAlert(device));
    if (activeUnitFilter === "active") return source.filter(device => Boolean(device.recorded_at));
    return source;
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

function normalizeFacilityStructure(structure) {
    return (structure || [])
        .filter(room => isUuid(room.id))
        .map(room => ({
            ...room,
            devices: (room.devices || [])
                .filter(device => isUuid(device.id) && isUuid(device.room_id || room.id))
                .map(device => {
                    const type = device.device_type || device.type || "room_temp";
                    return {
                        ...device,
                        room_id: device.room_id || room.id,
                        type,
                        device_type: type,
                        name: unitName(type, device.name),
                        display_name: `${room.name} - ${unitName(type, device.name)}`,
                        threshold_temp: device.threshold_temp ?? device.target_temperature ?? defaultThreshold(type),
                    };
                })
        }));
}

function isUuid(value) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || ""));
}

let saveCacheDebounce = null;
function triggerSaveCache() {
    clearTimeout(saveCacheDebounce);
    saveCacheDebounce = setTimeout(saveCache, 200);
}

function saveCache() {
    try {
        const data = {
            currentRoomName: document.getElementById('currentRoomName')?.textContent || '',
            scheduleMessage: document.getElementById('scheduleMessage')?.textContent || '',
            scheduleProgressCount: document.getElementById('scheduleProgressCount')?.textContent || '',
            scheduleProgressBarWidth: document.getElementById('scheduleProgressBar')?.style.width || '',
            scheduleSlotGrid: document.getElementById('scheduleSlotGrid')?.innerHTML || '',
            
            nextDeviceSectionClass: document.getElementById('nextDeviceSection')?.className || '',
            nextDeviceTitle: document.getElementById('nextDeviceTitle')?.textContent || '',
            nextDeviceStatus: document.getElementById('nextDeviceStatus')?.textContent || '',
            nextDeviceRoom: document.getElementById('nextDeviceRoom')?.textContent || '',
            nextDeviceName: document.getElementById('nextDeviceName')?.textContent || '',
            nextDeviceSlot: document.getElementById('nextDeviceSlot')?.textContent || '',
            nextDeviceActionDisabled: document.getElementById('nextDeviceAction')?.disabled ?? true,
            
            summaryUnitCount: document.getElementById('summaryUnitCount')?.textContent || '0',
            summaryStatus: document.getElementById('summaryStatus')?.textContent || '',
            summaryLogCount: document.getElementById('summaryLogCount')?.textContent || '0',
            deviceCount: document.getElementById('deviceCount')?.textContent || '0 Unit',
            
            deviceList: document.getElementById('device-list')?.innerHTML || '',
            roomProgressList: document.getElementById('roomProgressList')?.innerHTML || '',
            recentLogs: document.getElementById('recent-logs')?.innerHTML || '',
            roomList: document.getElementById('room-list')?.innerHTML || '',
            
            selectedRoomId: selectedRoomId,
            facilityStructure: facilityStructure,
            todaySchedule: todaySchedule,
            latestTemperatureLogs: latestTemperatureLogs
        };
        localStorage.setItem('page_cache:staff_monitoring', JSON.stringify(data));
    } catch (e) {
        console.error('Failed to save monitoring cache:', e);
    }
}

function restoreCache() {
    try {
        const dataStr = localStorage.getItem('page_cache:staff_monitoring');
        if (!dataStr) return false;
        const data = JSON.parse(dataStr);
        
        const setText = (id, val) => {
            const el = document.getElementById(id);
            if (el && val !== undefined) el.textContent = val;
        };
        const setHtml = (id, val) => {
            const el = document.getElementById(id);
            if (el && val !== undefined) el.innerHTML = val;
        };

        setText('currentRoomName', data.currentRoomName);
        setText('scheduleMessage', data.scheduleMessage);
        setText('scheduleProgressCount', data.scheduleProgressCount);
        const bar = document.getElementById('scheduleProgressBar');
        if (bar) bar.style.width = data.scheduleProgressBarWidth || '0%';
        setHtml('scheduleSlotGrid', data.scheduleSlotGrid);
        
        const nextSec = document.getElementById('nextDeviceSection');
        if (nextSec && data.nextDeviceSectionClass) nextSec.className = data.nextDeviceSectionClass;
        setText('nextDeviceTitle', data.nextDeviceTitle);
        setText('nextDeviceStatus', data.nextDeviceStatus);
        setText('nextDeviceRoom', data.nextDeviceRoom);
        setText('nextDeviceName', data.nextDeviceName);
        setText('nextDeviceSlot', data.nextDeviceSlot);
        const action = document.getElementById('nextDeviceAction');
        if (action) {
            action.disabled = data.nextDeviceActionDisabled;
        }
        
        setText('summaryUnitCount', data.summaryUnitCount);
        setText('summaryStatus', data.summaryStatus);
        setText('summaryLogCount', data.summaryLogCount);
        setText('deviceCount', data.deviceCount);
        
        setHtml('device-list', data.deviceList);
        setHtml('roomProgressList', data.roomProgressList);
        setHtml('recent-logs', data.recentLogs);
        setHtml('room-list', data.roomList);
        
        if (data.selectedRoomId !== undefined) selectedRoomId = data.selectedRoomId;
        if (data.facilityStructure !== undefined) facilityStructure = data.facilityStructure;
        if (data.todaySchedule !== undefined) todaySchedule = data.todaySchedule;
        if (data.latestTemperatureLogs !== undefined) latestTemperatureLogs = data.latestTemperatureLogs;
        
        renderNextDevice();
        if (window.lucide) lucide.createIcons();
        return true;
    } catch (e) {
        console.error('Failed to restore monitoring cache:', e);
        return false;
    }
}
