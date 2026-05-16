# Manual QA Mass Test

Date: 2026-05-16

Run this after applying migrations and redeploying Vercel.

## Staff Flow

1. Login as staff.
   - Expected: redirected to staff dashboard, no auth popup error.
2. Open `monitoring.html`.
   - Expected: rooms and devices load from `facility_rooms/facility_devices`.
3. Pick a room and device, input a numeric temperature.
   - Expected: submit button enables, validation accepts numeric value.
4. Upload a JPG/PNG/WEBP photo under 10 MB.
   - Expected: preview appears, no upload validation error.
5. Submit monitoring.
   - Expected: success message; row exists in `facility_logs`; photo metadata exists in `qc_evidence` if photo was uploaded.
6. Open `inspection.html`.
   - Expected: active batches/products load or empty states appear.
7. Input or scan barcode.
   - Expected: barcode field is accepted manually.
8. Input optional temperature, choose CCP stage and QC status.
   - Expected: no required-field error except missing barcode/batch identifier.
9. Upload product/barcode/evidence photos.
   - Expected: multiple photos are accepted if type/size valid.
10. Submit QC.
   - Expected: row exists in `qc_reports`; `barcode_labels` created; `qc_evidence` created for photos.
11. Create a new batch from `new_batch.html`.
   - Expected: batch is created even if no explicit product UUID is selected; backend uses `GENERAL-QC` when needed.

## Admin Flow

1. Login as admin.
   - Expected: `/admin/` is accessible.
2. Open `/admin/#section-facility`.
   - Expected: default rooms and devices are visible.
3. Add a room.
   - Expected: room appears after save without page reload.
4. Edit the room name/status.
   - Expected: updated values persist after refresh.
5. Delete the room.
   - Expected: row disappears or no-op succeeds for synthetic fallback rows.
6. Add a device/unit.
   - Fields: device name, device type, target temperature, min/max, active status.
   - Expected: device appears under the selected room.
7. Edit device type and thresholds.
   - Expected: values persist and monitoring target changes.
8. Delete a device, including a default device after confirmation.
   - Expected: no permanent lock; delete succeeds or synthetic fallback no-op succeeds.
9. Open temperature reports.
   - Expected: staff monitoring row appears with staff, room, device, temperature, status, photo/path, timestamp.
10. Open QC reports.
    - Expected: inspection row appears with barcode, batch, status, staff, notes, photo/path.
11. Open evidence report.
    - Expected: uploaded photos show `qc-evidence` storage paths.
12. Open approvals.
    - Expected: pending QC/alert items appear; approve/reject updates status.
13. Open dashboard.
    - Expected: real counts from Supabase; empty datasets show empty states, not fake numbers.

## Failure Checks

- Disable network and submit: expected clear API/network error, no double submit.
- Upload `.txt`: expected clear MIME error.
- Upload image over 10 MB: expected clear size error.
- Submit inspection without barcode: expected clear field error.
- Open console: expected no app-origin uncaught exceptions. Browser extension logs are ignored.
