# Integrations

Folder ini berisi koneksi layanan luar yang dipakai backend.

## Google Apps Script ke Google Sheets

File:
- `google_apps_script.js`: kode yang ditempel ke Apps Script.
- `google_sheets_service.py`: service backend Flask yang mengirim event ke Apps Script.

Yang diperlukan untuk connect:
- Google Spreadsheet aktif.
- `SPREADSHEET_ID` dari URL Google Sheets.
- Apps Script sudah di-deploy sebagai Web App.
- Web App URL `/exec` dimasukkan ke `.env`:

```env
APPSCRIPT_WEB_APP_URL=https://script.google.com/macros/s/DEPLOYMENT_ID/exec
```

Deploy Apps Script:
1. Buka `script.google.com`, buat project baru.
2. Tempel isi `integrations/google_apps_script.js`.
3. Ganti `YOUR_SPREADSHEET_ID_HERE` dengan ID spreadsheet.
4. Klik Deploy > New deployment > Web app.
5. Execute as: `Me`.
6. Who has access: `Anyone with the link`.
7. Salin Web App URL yang berakhiran `/exec`.

Tes koneksi dari backend:

```bash
curl http://127.0.0.1:5000/api/integrations/google-sheets/test
```

Sheet yang otomatis dibuat:
- `QC_Batch_Log`
- `Facility_Monitoring`
- `QC_Findings`
- `Integration_Test`

---
© 2026 PT Astro Teknologi Indonesia

