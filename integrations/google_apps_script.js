// Google Apps Script Web App for QC Central Kitchen
// Deploy: Web app, Execute as Me, Access Anyone with the link.
// Set APPSCRIPT_WEB_APP_URL in backend .env to the deployed /exec URL.

const SPREADSHEET_ID = 'YOUR_SPREADSHEET_ID_HERE';

const SHEETS = {
  batch_created: {
    name: 'QC_Batch_Log',
    headers: [
      'Timestamp',
      'Event',
      'Batch ID',
      'Batch Code',
      'Product ID',
      'Production Date',
      'Status',
      'Operator ID',
      'QC Officer ID',
      'Report URL',
      'Photo URL',
      'Raw JSON'
    ]
  },
  monitoring_log: {
    name: 'Facility_Monitoring',
    headers: [
      'Timestamp',
      'Event',
      'Log ID',
      'Room ID',
      'Device ID',
      'Temperature C',
      'Humidity RH',
      'Normal',
      'Reason',
      'Photo URL',
      'Alert',
      'Raw JSON'
    ]
  },
  qc_finding: {
    name: 'QC_Findings',
    headers: [
      'Timestamp',
      'Event',
      'Finding ID',
      'Staff ID',
      'Reason',
      'Photo URL',
      'Status',
      'Raw JSON'
    ]
  },
  connection_test: {
    name: 'Integration_Test',
    headers: ['Timestamp', 'Event', 'Message', 'Source', 'Raw JSON']
  }
};

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents || '{}');
    const eventType = data.event_type || 'batch_created';
    const config = SHEETS[eventType] || SHEETS.batch_created;
    const sheet = getOrCreateSheet_(config.name, config.headers);
    const row = buildRow_(eventType, data);

    sheet.appendRow(row);

    return json_({
      status: 'success',
      event_type: eventType,
      sheet: config.name,
      row: sheet.getLastRow()
    });
  } catch (err) {
    return json_({ status: 'error', error: String(err) });
  }
}

function doGet() {
  return json_({
    status: 'ok',
    message: 'QC Google Apps Script Web App is running'
  });
}

function getOrCreateSheet_(sheetName, headers) {
  const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
  let sheet = spreadsheet.getSheetByName(sheetName);
  if (!sheet) sheet = spreadsheet.insertSheet(sheetName);

  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.setFrozenRows(1);
  }

  return sheet;
}

function buildRow_(eventType, data) {
  const raw = JSON.stringify(data);

  if (eventType === 'monitoring_log') {
    const log = data.log || {};
    const alert = data.alert || {};
    return [
      data.sent_at || new Date(),
      eventType,
      log.id || '',
      log.room_id || '',
      log.device_id || '',
      log.temperature_c || '',
      log.humidity_rh || '',
      log.is_normal === undefined ? '' : log.is_normal,
      log.reason || '',
      log.photo_url || '',
      alert.message || '',
      raw
    ];
  }

  if (eventType === 'qc_finding') {
    const finding = data.finding || {};
    return [
      data.sent_at || new Date(),
      eventType,
      finding.id || '',
      finding.staff_id || '',
      finding.reason || '',
      finding.photo_url || '',
      finding.status || '',
      raw
    ];
  }

  if (eventType === 'connection_test') {
    return [
      data.sent_at || new Date(),
      eventType,
      data.message || '',
      data.source || '',
      raw
    ];
  }

  const batch = data.batch || data;
  return [
    data.sent_at || new Date(),
    eventType,
    batch.id || '',
    batch.batch_code || '',
    batch.product_id || '',
    batch.production_date || '',
    batch.final_qc_status || batch.status || '',
    batch.operator_id || '',
    batch.qc_officer_id || '',
    batch.report_url || '',
    batch.photo_url || '',
    raw
  ];
}

function json_(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}

function testWebhook() {
  const payload = {
    postData: {
      contents: JSON.stringify({
        event_type: 'connection_test',
        message: 'Manual Apps Script test',
        source: 'Apps Script editor'
      })
    }
  };

  Logger.log(doPost(payload).getContent());
}
