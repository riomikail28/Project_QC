// Google Apps Script Web App
// Deploy as Web App: Execute as ME, Access ANYONE (even anonymous)
// Paste this URL to backend/skills/gsheets_integration.py as APPSCRIPT_WEB_APP_URL

/**
 * Main Web App entry point
 * Receives POST JSON from FastAPI and appends to Google Spreadsheet
 */
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    
    // Target Spreadsheet ID (update with your sheet)
    const SPREADSHEET_ID = 'YOUR_SPREADSHEET_ID_HERE'; // Paste ID from browser URL
    const SHEET_NAME = 'QC_Batch_Log';  // Tab name
    
    const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_NAME);
    
    // Headers (add if first row)
    if (sheet.getLastRow() === 0) {
      sheet.getRange(1, 1, 1, 12).setValues([[
        'Timestamp', 'Batch Code', 'Product', 'Production Date', 'Shift',
        'Final Status', 'Report URL', 'Operator', 'QC Officer', 'Violations',
        'Facility Alerts', 'Notes'
      ]]);
    }
    
    // Append new row
    const row = [
      new Date(),
      data.batch_code || '',
      data.product_name || '',
      data.production_date || '',
      data.shift || '',
      data.final_status || '',
      data.report_pdf_url || '',
      data.operator_id || '',
      data.qc_officer_id || '',
      data.violations ? data.violations.join('; ') : '',
      '', // Facility alerts (populated by webhook if needed)
      ''  // Notes
    ];
    
    sheet.appendRow(row);
    
    return ContentService
      .createTextOutput(JSON.stringify({status: 'success', row: sheet.getLastRow()}))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({error: error.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// Test function (run in Apps Script editor)
function testWebhook() {
  const testData = {
    batch_code: 'MFG20260419-AY01',
    product_name: 'Ayam Teriyaki 90gr',
    final_status: 'PASS'
  };
  
  const payload = {
    'postData': {
      'contents': JSON.stringify(testData)
    }
  };
  
  console.log(doPost(payload));
}
