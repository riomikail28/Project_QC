from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_fast_qc_modal_prioritizes_temperature_status_submit():
    html = read("frontend/staff/inspection.html")
    js = read("frontend/js/inspection.js")

    temp_index = html.index('id="qcTemp"')
    status_index = html.index('id="statusField"')
    submit_index = html.index('id="submitQcBtn"')

    assert temp_index < status_index < submit_index
    assert "window.setTimeout(() => document.getElementById('qcTemp')?.focus()" in js


def test_pass_can_submit_without_photo_and_notes_frontend_contract():
    js = read("frontend/js/inspection.js")

    assert "requiresHoldFailEvidence()" in js
    assert "this.selectedStatus === 'hold' || this.selectedStatus === 'fail'" in js
    assert "const hasHoldFailNotes = !needsEvidence || Boolean(notes)" in js
    assert "const hasHoldFailPhoto = !needsEvidence || Boolean(cookingPhoto)" in js


def test_hold_fail_require_notes_and_photo_before_submit():
    html = read("frontend/staff/inspection.html")
    js = read("frontend/js/inspection.js")

    assert "Catatan dan foto wajib untuk HOLD/FAIL." in html
    assert "Foto evidence wajib untuk HOLD/FAIL." in html
    assert "if (this.requiresHoldFailEvidence())" in js
    assert "if (!notes)" in js
    assert "if (!cookingPhoto)" in js
    assert "button.disabled = isLocked || !validation.canSubmit" in js


def test_parameter_qc_is_collapsible_and_expands_for_hold_fail():
    html = read("frontend/staff/inspection.html")
    js = read("frontend/js/inspection.js")

    assert '<details class="qc-parameter-panel" id="qcParameterPanel">' in html
    assert "Parameter QC Tambahan" in html
    assert "isAdvancedPanelOpen" in js
    assert "productHasAdditionalStandards" in js


def test_summary_fast_pass_is_mini_and_hold_fail_full_summary():
    html = read("frontend/staff/inspection.html")
    js = read("frontend/js/inspection.js")

    assert "qcMiniSummary" in html
    assert "miniSummaryBatch" in html
    assert "const showFullSummary = hasContext && (this.requiresHoldFailEvidence() || Boolean(this.recheckParentInspection))" in js
    assert "panel.hidden = !showFullSummary" in js


def test_recheck_visual_mode_title_banner_round_and_previous_result():
    html = read("frontend/staff/inspection.html")
    js = read("frontend/js/inspection.js")

    assert "qcRecheckBanner" in html
    assert "Mode Re-check aktif. Hasil ini akan menjadi pemeriksaan lanjutan." in html
    assert "qcRecheckRound" in html
    assert "Status sebelumnya" in js
    assert "Suhu sebelumnya" in js
    assert "Catatan sebelumnya" in js
    assert "this.setText('qcFormTitle', this.recheckParentInspection ? 'RE-CHECK QC' : 'QC CHECK')" in js


def test_submit_button_copy_changes_by_status_and_recheck():
    js = read("frontend/js/inspection.js")

    assert "submitButtonCopy()" in js
    assert "return 'Simpan Re-check'" in js
    assert "return 'Simpan HOLD'" in js
    assert "return 'Simpan FAIL'" in js
    assert "return 'Simpan PASS'" in js
    assert "button.innerHTML = `<i class=\"fas fa-paper-plane\"></i>${this.submitButtonCopy()}`" in js


def test_qc_parameter_panel_stays_open_after_input_change():
    html = read("frontend/staff/inspection.html")
    js = read("frontend/js/inspection.js")

    # State variable let isAdvancedPanelOpen = false; should store the open state and be used on re-render.
    assert "let isAdvancedPanelOpen = false;" in js
    assert "isAdvancedPanelOpen" in js
    assert "classList.remove('collapsed')" in js
    assert "classList.add('collapsed')" in js
    assert "parameterPanel.open = true" in js
    assert "parameterPanel.open = false" in js
    assert "parameterPanel.addEventListener('toggle'" in js

    # Event listener for temperature does not trigger rendering/toggling functions
    assert "renderInspection" not in js
    assert "renderForm" not in js
    assert "toggleAdvancedParameters" not in js
