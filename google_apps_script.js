/**
 * Google Apps Script untuk menerima data dari Project QC System
 * Paste kode ini di Extensions > Apps Script pada Google Sheet Anda.
 */

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = JSON.parse(e.postData.contents);
    
    // Setup Header jika sheet masih kosong
    if (sheet.getLastRow() == 0) {
      sheet.appendRow([
        "Timestamp", 
        "Batch ID", 
        "Batch Code", 
        "Final Status", 
        "Report URL", 
        "Violations"
      ]);
      // Format header
      sheet.getRange(1, 1, 1, 6).setFontWeight("bold").setBackground("#f3f3f3");
    }
    
    // Tambah Baris Data
    sheet.appendRow([
      new Date(),
      data.batch_id,
      data.batch_code,
      data.final_status,
      data.report_pdf_url,
      JSON.stringify(data.violations)
    ]);
    
    return ContentService.createTextOutput(JSON.stringify({
      "status": "success",
      "message": "Data saved to Google Sheets"
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      "status": "error",
      "message": err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
