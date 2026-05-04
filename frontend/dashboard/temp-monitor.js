// Temperature & Storage Monitoring Module
// Fetches rooms/devices, polls latest temps, handles +/- controls

const API_BASE = '/';
const POLL_INTERVAL = 30000; // 30s
let pollTimer = null;

export async function initTempMonitoring() {
  try {
    await loadRooms();
    startPolling();
    console.log('[TempMonitor] Initialized');
  } catch (err) {
    console.error('[TempMonitor] Init failed:', err);
  }
}

async function loadRooms() {
  const roomsEl = document.getElementById('temp-rooms-container');
  if (!roomsEl) return;

  try {
    const res = await fetch(`${API_BASE}facility/rooms`);
    const rooms = await res.json();
    
    roomsEl.innerHTML = rooms.map(room => createRoomCard(room)).join('');
    
    // Bind +/- buttons
    document.querySelectorAll('.adjust-btn').forEach(btn => {
      btn.addEventListener('click', handleAdjust);
    });
  } catch (err) {
    roomsEl.innerHTML = '<div class="alert alert-error">Gagal memuat data suhu</div>';
  }
}

function createRoomCard(room) {
  const chillers = room.devices.filter(d => d.type === 'chiller' && d.is_active).length;
  const freezers = room.devices.filter(d => d.type === 'freezer' && d.is_active).length;
  
  return `
    <div class="room-card" data-room-id="${room.id}">
      <h3>${room.name}</h3>
      
      <div class="device-group">
        <div class="device-info">
          <label>Chiller: <span class="count">${chillers}</span></label>
          <div class="temp-display">--°C</div>
        </div>
        <div class="controls">
          <button class="adjust-btn" data-type="chiller" data-action="+1" title="Tambah Chiller">+</button>
          <button class="adjust-btn" data-type="chiller" data-action="-1" title="Kurang Chiller">-</button>
        </div>
      </div>
      
      <div class="device-group">
        <div class="device-info">
          <label>Freezer: <span class="count">${freezers}</span></label>
          <div class="temp-display">--°C</div>
        </div>
        <div class="controls">
          <button class="adjust-btn" data-type="freezer" data-action="+1" title="Tambah Freezer">+</button>
          <button class="adjust-btn" data-type="freezer" data-action="-1" title="Kurang Freezer">-</button>
        </div>
      </div>
      
      <div class="status-alert" style="display:none"></div>
    </div>
  `;
}

async function handleAdjust(ev) {
  const btn = ev.target;
  const roomId = btn.closest('.room-card').dataset.roomId;
  const type = btn.dataset.type;
  const action = btn.dataset.action;
  
  btn.disabled = true;
  btn.textContent = '⏳';
  
  try {
    const formData = new FormData();
    formData.append('device_type', type);
    formData.append('action', action);
    
    const res = await fetch(`${API_BASE}facility/${roomId}/devices/adjust`, {
      method: 'POST',
      body: formData
    });
    
    if (res.ok) {
      await loadRooms(); // Refresh display
      showStatus(roomId, `✅ ${type} ${action === '+1' ? 'ditambah' : 'dikurangi'}`);
    } else {
      throw new Error(await res.text());
    }
  } catch (err) {
    showStatus(roomId, `❌ ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = btn.dataset.action === '+1' ? '+' : '-';
  }
}

function showStatus(roomId, message) {
  const roomEl = document.querySelector(`[data-room-id="${roomId}"] .status-alert`);
  roomEl.textContent = message;
  roomEl.style.display = 'block';
  setTimeout(() => roomEl.style.display = 'none', 3000);
}

function startPolling() {
  updateTemps();
  pollTimer = setInterval(updateTemps, POLL_INTERVAL);
}

async function updateTemps() {
  try {
    // Use analytics/summary for latest facility logs or direct logs query
    const res = await fetch(`${API_BASE}api/analytics/summary`);
    const data = await res.json();
    
    data.latest_facility.forEach(log => {
      const roomEl = document.querySelector(`[data-room-id] .temp-display`);
      // Match by zone/device - simplified
      const tempEl = document.querySelector('.temp-display'); // TODO: match properly
      if (tempEl && log.temperature_c !== undefined) {
        const color = log.is_normal ? '#28a745' : '#dc3545';
        tempEl.textContent = `${log.temperature_c.toFixed(1)}°C`;
        tempEl.style.color = color;
      }
    });
  } catch (err) {
    console.warn('[TempMonitor] Poll failed:', err);
  }
}

// Auto-init when loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTempMonitoring);
} else {
  initTempMonitoring();
}
