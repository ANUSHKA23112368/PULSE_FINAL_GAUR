import React, { useState, useEffect } from 'react';
import { 
  Layers, 
  AlertTriangle, 
  CheckCircle2, 
  FileText, 
  ArrowRight,
  AlertCircle,
  Edit3,
  RotateCcw,
  ShieldCheck,
  Eye,
  Check,
  Volume2,
  VolumeX,
  Printer,
  Copy,
  FileCode,
  Download
} from 'lucide-react';
import { PatientBanner } from '../components/PatientBanner';
import { fetchPatientNotes, reviewPatientNote } from '../services/api';

export function HandoverSummaryPage({ selectedPatient, onSwitchPatient, onNavigate, allPatients, onSelectPatient }) {
  const [notes, setNotes] = useState([]);
  const [selectedNoteId, setSelectedNoteId] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Tab view: 'handover' (Reviewed/Current Handover), 'original_ai' (Original AI Extraction), 'source_note' (Verbatim Source Note)
  const [activeTab, setActiveTab] = useState('handover');
  const [isEditing, setIsEditing] = useState(false);

  // Audio Readout (TTS) State
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  // FHIR Export Modal State
  const [showFhirModal, setShowFhirModal] = useState(false);
  const [copiedFhir, setCopiedFhir] = useState(false);
  const [copiedIsbar, setCopiedIsbar] = useState(false);

  // Editable review state
  const [reviewerIdentifier, setReviewerIdentifier] = useState('Dr. Hanlen, MD (Attending Consultant)');
  const [reviewNotes, setReviewNotes] = useState('');
  const [editedIsbar, setEditedIsbar] = useState({
    situation: '',
    background: '',
    assessment: '',
    recommendation: ''
  });
  const [editedExecutiveSummary, setEditedExecutiveSummary] = useState('');
  const [editedConditions, setEditedConditions] = useState([]);
  const [editedMedications, setEditedMedications] = useState([]);
  const [editedInvestigations, setEditedInvestigations] = useState([]);
  const [editedTasks, setEditedTasks] = useState([]);

  // Submission state
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(null);

  useEffect(() => {
    if (selectedPatient) {
      loadNotes();
    }
  }, [selectedPatient]);

  // Clean up audio on unmount
  useEffect(() => {
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  async function loadNotes() {
    setLoading(true);
    setSaveError(null);
    setSaveSuccess(null);
    try {
      const data = await fetchPatientNotes(selectedPatient.display_id || selectedPatient.id);
      const validNotes = (data.notes || []).filter(
        n => (n.status === 'Processed' || n.status === 'Reviewed') &&
             (n.extraction?.data || n.extracted_data || n.latest_extraction?.extracted_data || n.latest_extraction?.data)
      );
      setNotes(validNotes);
      if (validNotes.length > 0) {
        if (!selectedNoteId || !validNotes.some(n => n.id === selectedNoteId)) {
          setSelectedNoteId(validNotes[0].id);
          initFormData(validNotes[0]);
        } else {
          const current = validNotes.find(n => n.id === selectedNoteId);
          initFormData(current);
        }
      } else {
        setSelectedNoteId(null);
      }
    } catch (err) {
      console.warn("Could not load handover summary:", err);
    } finally {
      setLoading(false);
    }
  }

  function initFormData(note) {
    if (!note) return;
    setSaveError(null);
    setSaveSuccess(null);

    const sourceData = note.review?.reviewed_data || note.extraction?.data || note.extracted_data || note.latest_extraction?.extracted_data || note.latest_extraction?.data || {};
    const isbarData = sourceData.isbar || sourceData.structured_handover?.isbar || {};
    const conditionsList = sourceData.entities?.conditions || sourceData.conditions || [];
    const symptomsList = sourceData.entities?.symptoms || sourceData.symptoms || [];
    const combinedConditions = [...conditionsList, ...symptomsList];
    const medicationsData = sourceData.entities?.medications || sourceData.medications || [];
    const investigationsData = sourceData.entities?.investigations || sourceData.investigations || [];
    const tasksData = sourceData.pending_tasks || [];

    const formatSection = (val) => Array.isArray(val) ? val.join('\n') : (val || '');

    setEditedIsbar({
      situation: formatSection(isbarData.situation),
      background: formatSection(isbarData.background),
      assessment: formatSection(isbarData.assessment),
      recommendation: formatSection(isbarData.recommendation)
    });

    setEditedExecutiveSummary(
      sourceData.executive_summary || sourceData.structured_handover?.executive_summary || ''
    );

    let initialConditions = combinedConditions.map(c => ({
      text: typeof c === 'string' ? c : c.text || c.normalized || '',
      status: c.is_negated ? 'negated' : c.is_historical ? 'historical' : 'active',
      source_sentence: c.source_sentence || ''
    }));
    if (initialConditions.length === 0 && selectedPatient?.admitting_diagnosis) {
      initialConditions = [{
        text: selectedPatient.admitting_diagnosis,
        status: 'active',
        source_sentence: 'Admitting Presentation'
      }];
    }
    setEditedConditions(initialConditions);

    setEditedMedications(
      medicationsData.map(m => ({
        text: typeof m === 'string' ? m : m.text || m.normalized || '',
        dosage: m.dosage || '',
        frequency: m.frequency || '',
        route: m.route || '',
        source_sentence: m.source_sentence || ''
      }))
    );

    setEditedInvestigations(
      investigationsData.map(i => ({
        text: typeof i === 'string' ? i : i.text || i.normalized || '',
        status: i.is_planned ? 'planned' : 'completed',
        source_sentence: i.source_sentence || ''
      }))
    );

    setEditedTasks(
      tasksData.map(t => ({
        task: typeof t === 'string' ? t : t.task || '',
        source_sentence: t.source_sentence || ''
      }))
    );

    const defaultReviewer = selectedPatient?.consultant 
      ? `${selectedPatient.consultant} (Attending Consultant)` 
      : 'Dr. Sarah Hanlen (Attending Consultant)';

    if (note.review) {
      setReviewerIdentifier(note.review.reviewer_identifier || defaultReviewer);
      setReviewNotes(note.review.review_notes || '');
    } else {
      setReviewerIdentifier(defaultReviewer);
      setReviewNotes('');
    }
  }

  function handleSelectNote(noteId) {
    setSelectedNoteId(noteId);
    setIsEditing(false);
    const note = notes.find(n => n.id === noteId);
    initFormData(note);
  }

  function handleResetToAI() {
    if (!activeNote) return;
    const sourceData = activeNote.extraction?.data || activeNote.extracted_data || activeNote.latest_extraction?.extracted_data || activeNote.latest_extraction?.data || {};
    const isbarData = sourceData.isbar || sourceData.structured_handover?.isbar || {};
    const conditionsList = sourceData.entities?.conditions || sourceData.conditions || [];
    const symptomsList = sourceData.entities?.symptoms || sourceData.symptoms || [];
    const combinedConditions = [...conditionsList, ...symptomsList];
    const medicationsData = sourceData.entities?.medications || sourceData.medications || [];
    const investigationsData = sourceData.entities?.investigations || sourceData.investigations || [];
    const tasksData = sourceData.pending_tasks || [];

    const formatSection = (val) => Array.isArray(val) ? val.join('\n') : (val || '');

    setEditedIsbar({
      situation: formatSection(isbarData.situation),
      background: formatSection(isbarData.background),
      assessment: formatSection(isbarData.assessment),
      recommendation: formatSection(isbarData.recommendation)
    });
    setEditedExecutiveSummary(sourceData.executive_summary || sourceData.structured_handover?.executive_summary || '');
    setEditedConditions(
      combinedConditions.map(c => ({
        text: c.text || c.normalized || '',
        status: c.is_negated ? 'negated' : c.is_historical ? 'historical' : 'active',
        source_sentence: c.source_sentence || ''
      }))
    );
    setEditedMedications(
      medicationsData.map(m => ({
        text: m.text || m.normalized || '',
        dosage: m.dosage || '',
        frequency: m.frequency || '',
        route: m.route || '',
        source_sentence: m.source_sentence || ''
      }))
    );
    setEditedInvestigations(
      investigationsData.map(i => ({
        text: i.text || i.normalized || '',
        status: i.is_planned ? 'planned' : 'completed',
        source_sentence: i.source_sentence || ''
      }))
    );
    setEditedTasks(
      tasksData.map(t => ({
        task: t.task || '',
        source_sentence: t.source_sentence || ''
      }))
    );
    setSaveSuccess('Reset fields to original AI extraction output.');
    setTimeout(() => setSaveSuccess(null), 3000);
  }

  // Audio Readout Toggle (TTS)
  function toggleAudioBriefing() {
    if (!('speechSynthesis' in window)) {
      alert("Speech synthesis is not supported by this browser.");
      return;
    }
    if (isPlayingAudio) {
      window.speechSynthesis.cancel();
      setIsPlayingAudio(false);
      return;
    }

    const narrative = `Clinical Shift Handover for ${selectedPatient?.name || 'patient'}. ` +
      `Ward: ${selectedPatient?.ward || 'General Medical'}, Bed ${selectedPatient?.bed_number || 'unassigned'}. ` +
      `Situation: ${editedIsbar.situation || 'Not recorded'}. ` +
      `Background: ${editedIsbar.background || 'Not recorded'}. ` +
      `Assessment: ${editedIsbar.assessment || 'Not recorded'}. ` +
      `Recommendation: ${editedIsbar.recommendation || 'Not recorded'}.`;

    const utterance = new SpeechSynthesisUtterance(narrative);
    utterance.rate = 0.95;
    utterance.onend = () => setIsPlayingAudio(false);
    utterance.onerror = () => setIsPlayingAudio(false);
    setIsPlayingAudio(true);
    window.speechSynthesis.speak(utterance);
  }

  // FHIR R4 Generation
  function generateFhirBundle() {
    return {
      resourceType: "Bundle",
      type: "document",
      id: `pulse-handover-${selectedPatient?.display_id || 'demo'}-${Date.now()}`,
      timestamp: new Date().toISOString(),
      entry: [
        {
          resource: {
            resourceType: "Composition",
            id: `comp-${activeNote?.id || 1}`,
            status: isReviewed ? "final" : "preliminary",
            type: {
              coding: [{
                system: "http://loinc.org",
                code: "28651-8",
                display: "Nurse Transfer note"
              }]
            },
            subject: {
              reference: `Patient/${selectedPatient?.display_id || selectedPatient?.id}`,
              display: selectedPatient?.name
            },
            date: new Date().toISOString(),
            author: [{
              display: reviewerIdentifier || activeNote?.author_identifier || "Staff Clinician"
            }],
            title: "PULSE Structured ISBAR Shift Handover Record",
            section: [
              {
                title: "Identify",
                code: { coding: [{ system: "http://loinc.org", code: "55188-7", display: "Patient summary" }] },
                text: { status: "generated", div: `<div>Patient: ${selectedPatient?.name}, MRN: ${selectedPatient?.display_id}, Ward: ${selectedPatient?.ward}, Bed: ${selectedPatient?.bed_number}</div>` }
              },
              {
                title: "Situation",
                code: { coding: [{ system: "http://loinc.org", code: "46241-6", display: "Hospital admission reason" }] },
                text: { status: "generated", div: `<div>${editedIsbar.situation}</div>` }
              },
              {
                title: "Background",
                code: { coding: [{ system: "http://loinc.org", code: "11348-0", display: "History of Past illness" }] },
                text: { status: "generated", div: `<div>${editedIsbar.background}</div>` }
              },
              {
                title: "Assessment",
                code: { coding: [{ system: "http://loinc.org", code: "51848-0", display: "Evaluation note" }] },
                text: { status: "generated", div: `<div>${editedIsbar.assessment}</div>` }
              },
              {
                title: "Recommendation",
                code: { coding: [{ system: "http://loinc.org", code: "18776-5", display: "Plan of treatment" }] },
                text: { status: "generated", div: `<div>${editedIsbar.recommendation}</div>` }
              }
            ]
          }
        }
      ]
    };
  }

  function handleCopyFhir() {
    const json = JSON.stringify(generateFhirBundle(), null, 2);
    navigator.clipboard.writeText(json).then(() => {
      setCopiedFhir(true);
      setTimeout(() => setCopiedFhir(false), 2000);
    });
  }

  function handleDownloadFhir() {
    const json = JSON.stringify(generateFhirBundle(), null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `FHIR_ISBAR_${selectedPatient?.display_id || 'HANDOVER'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleCopyIsbar() {
    const isbarText = `=== PULSE ISBAR CLINICAL SHIFT HANDOVER ===\n` +
      `PATIENT: ${selectedPatient?.name} (${selectedPatient?.display_id})\n` +
      `WARD / BED: ${selectedPatient?.ward} / ${selectedPatient?.bed_number || 'Bed 4'}\n` +
      `ATTENDING: ${selectedPatient?.consultant}\n` +
      `TIMESTAMP: ${new Date().toLocaleString()}\n\n` +
      `[I - IDENTIFY]\n${selectedPatient?.name}, ${selectedPatient?.age || ''}, ${selectedPatient?.gender || ''}\n\n` +
      `[S - SITUATION]\n${editedIsbar.situation}\n\n` +
      `[B - BACKGROUND]\n${editedIsbar.background}\n\n` +
      `[A - ASSESSMENT]\n${editedIsbar.assessment}\n\n` +
      `[R - RECOMMENDATION]\n${editedIsbar.recommendation}\n` +
      `==========================================`;

    navigator.clipboard.writeText(isbarText).then(() => {
      setCopiedIsbar(true);
      setTimeout(() => setCopiedIsbar(false), 2000);
    });
  }

  function handlePrint() {
    window.print();
  }

  // Modifiers for condition/med/task items
  function handleAddCondition() {
    setEditedConditions(prev => [...prev, { text: '', status: 'active', source_sentence: '' }]);
  }
  function handleRemoveCondition(index) {
    setEditedConditions(prev => prev.filter((_, i) => i !== index));
  }
  function handleConditionChange(index, field, value) {
    setEditedConditions(prev => prev.map((item, i) => i === index ? { ...item, [field]: value } : item));
  }

  function handleAddMedication() {
    setEditedMedications(prev => [...prev, { text: '', dosage: '', frequency: '', route: '', source_sentence: '' }]);
  }
  function handleRemoveMedication(index) {
    setEditedMedications(prev => prev.filter((_, i) => i !== index));
  }
  function handleMedicationChange(index, field, value) {
    setEditedMedications(prev => prev.map((item, i) => i === index ? { ...item, [field]: value } : item));
  }

  function handleAddInvestigation() {
    setEditedInvestigations(prev => [...prev, { text: '', status: 'planned', source_sentence: '' }]);
  }
  function handleRemoveInvestigation(index) {
    setEditedInvestigations(prev => prev.filter((_, i) => i !== index));
  }
  function handleInvestigationChange(index, field, value) {
    setEditedInvestigations(prev => prev.map((item, i) => i === index ? { ...item, [field]: value } : item));
  }

  function handleAddTask() {
    setEditedTasks(prev => [...prev, { task: '', source_sentence: '' }]);
  }
  function handleRemoveTask(index) {
    setEditedTasks(prev => prev.filter((_, i) => i !== index));
  }
  function handleTaskChange(index, value) {
    setEditedTasks(prev => prev.map((item, i) => i === index ? { ...item, task: value } : item));
  }

  async function handleSaveReview() {
    if (!activeNote || !selectedPatient) return;
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    const reviewedPayload = {
      isbar: {
        situation: editedIsbar.situation,
        background: editedIsbar.background,
        assessment: editedIsbar.assessment,
        recommendation: editedIsbar.recommendation
      },
      executive_summary: editedExecutiveSummary,
      structured_handover: {
        isbar: {
          situation: editedIsbar.situation,
          background: editedIsbar.background,
          assessment: editedIsbar.assessment,
          recommendation: editedIsbar.recommendation
        },
        executive_summary: editedExecutiveSummary
      },
      entities: {
        conditions: editedConditions.map(c => ({
          text: c.text,
          is_negated: c.status === 'negated',
          is_historical: c.status === 'historical',
          source_sentence: c.source_sentence || ''
        })),
        medications: editedMedications.map(m => ({
          text: m.text,
          dosage: m.dosage,
          frequency: m.frequency,
          route: m.route,
          source_sentence: m.source_sentence || ''
        })),
        investigations: editedInvestigations.map(inv => ({
          text: inv.text,
          is_planned: inv.status === 'planned',
          source_sentence: inv.source_sentence || ''
        }))
      },
      pending_tasks: editedTasks.map(t => ({
        task: t.task,
        source_sentence: t.source_sentence || ''
      })),
      review_metadata: {
        is_human_reviewed: true,
        reviewer_identifier: reviewerIdentifier.trim() || 'Staff Clinician (Demo)',
        review_notes: reviewNotes.trim() || null,
        reviewed_at: new Date().toISOString()
      }
    };

    try {
      const patientId = selectedPatient.display_id || selectedPatient.id;
      const res = await reviewPatientNote(
        patientId,
        activeNote.id,
        reviewedPayload,
        reviewerIdentifier.trim() || 'Staff Clinician (Demo)',
        reviewNotes.trim() || null
      );

      setSaveSuccess(`Clinician review saved! Handover verified by ${res.reviewer_identifier}.`);
      setIsEditing(false);

      const updatedReview = {
        id: res.review_id,
        reviewer_identifier: res.reviewer_identifier,
        reviewed_data: reviewedPayload,
        review_notes: res.review_notes,
        reviewed_at: res.reviewed_at
      };

      setNotes(prev => prev.map(n => {
        if (n.id === activeNote.id) {
          return {
            ...n,
            status: 'Reviewed',
            reviewer_identifier: res.reviewer_identifier,
            reviewed_at: res.reviewed_at,
            review: updatedReview,
            review_history: [updatedReview, ...(n.review_history || [])]
          };
        }
        return n;
      }));
    } catch (err) {
      console.error("Save review failed:", err);
      setSaveError(err.message || "Failed to save clinician review. Edits have been preserved.");
    } finally {
      setSaving(false);
    }
  }

  const activeNote = notes.find(n => n.id === selectedNoteId);
  const originalExt = activeNote?.extraction?.data || activeNote?.extracted_data || activeNote?.latest_extraction?.extracted_data || activeNote?.latest_extraction?.data || {};
  const isReviewed = activeNote?.status === 'Reviewed';
  const latestReview = activeNote?.review;

  return (
    <div className="page-container printable-summary-root">
      {/* Patient Banner */}
      <PatientBanner 
        patient={selectedPatient} 
        onSwitchPatient={onSwitchPatient}
        allPatients={allPatients}
        onSelectPatient={onSelectPatient}
        onNavigate={onNavigate}
      />

      {/* Header and Controls */}
      <div className="handover-header-row">
        <div>
          <div className="handover-title-group">
            <h2 className="page-heading">
              Structured ISBAR Clinical Handover Workstation
            </h2>
            {activeNote && (
              <span className={`status-pill ${isReviewed ? 'status-verified' : 'status-ai'}`}>
                {isReviewed ? <ShieldCheck size={13} className="text-emerald" /> : <AlertTriangle size={13} className="text-amber" />}
                <span>{isReviewed ? 'Clinician Verified' : 'AI-generated — not yet reviewed'}</span>
              </span>
            )}
          </div>
          <div className="page-subheading">
            Interoperable ISBAR handover record for {selectedPatient ? selectedPatient.name : 'patient'} with digital verification & EHR export tools.
          </div>
        </div>

        {/* Global Handover Action Suite */}
        <div className="handover-toolbar-actions">
          {/* Note Selector */}
          {notes.length > 1 && (
            <div className="note-select-group">
              <label>Note:</label>
              <select 
                value={selectedNoteId || ''}
                onChange={(e) => handleSelectNote(Number(e.target.value))}
                className="form-input note-select"
              >
                {notes.map(n => (
                  <option key={n.id} value={n.id}>
                    Note #{n.id} ({n.status})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Audio TTS Briefing Button */}
          <button
            type="button"
            className={`btn btn-outline ${isPlayingAudio ? 'btn-audio-active' : ''}`}
            onClick={toggleAudioBriefing}
            title={isPlayingAudio ? "Stop audio briefing" : "Listen to audio handover briefing"}
          >
            {isPlayingAudio ? <VolumeX size={14} /> : <Volume2 size={14} />}
            <span>{isPlayingAudio ? "Stop Audio" : "Listen Briefing"}</span>
          </button>

          {/* Copy ISBAR Button */}
          <button
            type="button"
            className="btn btn-outline"
            onClick={handleCopyIsbar}
            title="Copy formatted ISBAR note to clipboard"
          >
            {copiedIsbar ? <Check size={14} className="text-emerald" /> : <Copy size={14} />}
            <span>{copiedIsbar ? "Copied!" : "Copy ISBAR"}</span>
          </button>

          {/* FHIR Export Button */}
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => setShowFhirModal(true)}
            title="Export standard HL7 FHIR R4 JSON Bundle"
          >
            <FileCode size={14} />
            <span>FHIR R4</span>
          </button>

          {/* Print Button */}
          <button
            type="button"
            className="btn btn-outline"
            onClick={handlePrint}
            title="Print or save PDF shift handover sheet"
          >
            <Printer size={14} />
            <span>Print Sheet</span>
          </button>

          {/* Edit Toggle Button */}
          {activeNote && activeTab === 'handover' && (
            <button
              className={`btn ${isEditing ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setIsEditing(!isEditing)}
            >
              <Edit3 size={14} />
              <span>{isEditing ? 'Close Editor' : 'Edit Handover'}</span>
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="hospital-card loading-state-card">
          <div className="animate-spin text-primary">⟳</div>
          <span>Loading structured handover records...</span>
        </div>
      ) : !activeNote ? (
        <div className="hospital-card empty-state-card">
          <Layers size={36} className="text-muted" />
          <h3>No structured handover notes available for this patient</h3>
          <p>
            To generate a structured ISBAR handover summary, enter a clinical note and click "Save & Process with AI" on the Clinical Notes page.
          </p>
          <button 
            className="btn btn-primary"
            onClick={() => onNavigate('notes')}
          >
            Go to Clinical Notes <ArrowRight size={15} />
          </button>
        </div>
      ) : (
        <>
          {/* View Mode Navigation Tabs */}
          <div className="handover-tabs-nav">
            <button
              onClick={() => setActiveTab('handover')}
              className={`tab-btn ${activeTab === 'handover' ? 'active' : ''}`}
            >
              {isReviewed ? <ShieldCheck size={14} /> : <FileText size={14} />}
              <span>{isReviewed ? 'Clinician Verified Handover' : 'Structured Handover (ISBAR)'}</span>
            </button>
            <button
              onClick={() => setActiveTab('original_ai')}
              className={`tab-btn ${activeTab === 'original_ai' ? 'active' : ''}`}
            >
              <Eye size={14} />
              <span>Original AI Extraction (Archive)</span>
            </button>
            <button
              onClick={() => setActiveTab('source_note')}
              className={`tab-btn ${activeTab === 'source_note' ? 'active' : ''}`}
            >
              <FileText size={14} />
              <span>Verbatim Source Note</span>
            </button>
          </div>

          {/* Feedback Alerts */}
          {saveSuccess && (
            <div className="feedback-alert feedback-success">
              <CheckCircle2 size={18} className="text-emerald" />
              <span className="feedback-text">{saveSuccess}</span>
            </div>
          )}

          {saveError && (
            <div className="feedback-alert feedback-error">
              <AlertCircle size={18} className="text-rose" />
              <div className="feedback-text">
                <strong>Save Failed:</strong> {saveError}
              </div>
            </div>
          )}

          {/* TAB 1: Structured ISBAR Handover */}
          {activeTab === 'handover' && (
            <>
              {/* Clinician Verified Badge Banner */}
              {isReviewed && (
                <div className="verified-banner-card">
                  <ShieldCheck size={24} className="text-emerald" />
                  <div>
                    <div className="verified-banner-title">
                      Clinician Verified Shift Handover Record
                    </div>
                    <div className="verified-banner-sub">
                      Signed off by <strong>{latestReview?.reviewer_identifier || activeNote.reviewer_identifier}</strong>
                      {activeNote.reviewed_at && (
                        <span> • Verified at {new Date(activeNote.reviewed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      )}
                    </div>
                    {latestReview?.review_notes && (
                      <div className="verified-audit-note">
                        <strong>Audit Note:</strong> {latestReview.review_notes}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ISBAR Structured Cards Grid */}
              <div className="isbar-dashboard-grid">
                {/* Identify (I) */}
                <div className="hospital-card isbar-quadrant isbar-quadrant-i">
                  <div className="quadrant-header">
                    <span className="quadrant-letter">I</span>
                    <div>
                      <h4 className="quadrant-title">IDENTIFY</h4>
                      <span className="quadrant-sub">Patient, Location & Team</span>
                    </div>
                  </div>
                  <div className="quadrant-body">
                    <div className="isbar-fact-row">
                      <strong>Patient:</strong> <span>{selectedPatient?.name} ({selectedPatient?.display_id})</span>
                    </div>
                    <div className="isbar-fact-row">
                      <strong>Location:</strong> <span>{selectedPatient?.ward} • Bed {selectedPatient?.bed_number || 'Bed 4'}</span>
                    </div>
                    <div className="isbar-fact-row">
                      <strong>Consultant:</strong> <span>{selectedPatient?.consultant}</span>
                    </div>
                    <div className="isbar-fact-row">
                      <strong>Handover Author:</strong> <span>{activeNote.author_identifier || 'Staff Clinician'}</span>
                    </div>
                  </div>
                </div>

                {/* Situation (S) */}
                <div className="hospital-card isbar-quadrant isbar-quadrant-s">
                  <div className="quadrant-header">
                    <span className="quadrant-letter">S</span>
                    <div>
                      <h4 className="quadrant-title">SITUATION</h4>
                      <span className="quadrant-sub">Acute admission reason & current status</span>
                    </div>
                  </div>
                  <div className="quadrant-body">
                    {isEditing ? (
                      <textarea
                        className="form-input isbar-edit-area"
                        rows={3}
                        value={editedIsbar.situation}
                        onChange={e => setEditedIsbar({ ...editedIsbar, situation: e.target.value })}
                        placeholder="Current clinical situation..."
                      />
                    ) : (
                      <p className="quadrant-text">
                        {editedIsbar.situation || 'No acute clinical situation documented.'}
                      </p>
                    )}
                  </div>
                </div>

                {/* Background (B) */}
                <div className="hospital-card isbar-quadrant isbar-quadrant-b">
                  <div className="quadrant-header">
                    <span className="quadrant-letter">B</span>
                    <div>
                      <h4 className="quadrant-title">BACKGROUND</h4>
                      <span className="quadrant-sub">Clinical history & co-morbidities</span>
                    </div>
                  </div>
                  <div className="quadrant-body">
                    {isEditing ? (
                      <textarea
                        className="form-input isbar-edit-area"
                        rows={3}
                        value={editedIsbar.background}
                        onChange={e => setEditedIsbar({ ...editedIsbar, background: e.target.value })}
                        placeholder="Past medical history..."
                      />
                    ) : (
                      <p className="quadrant-text">
                        {editedIsbar.background || 'No background factors identified.'}
                      </p>
                    )}
                  </div>
                </div>

                {/* Assessment (A) */}
                <div className="hospital-card isbar-quadrant isbar-quadrant-a">
                  <div className="quadrant-header">
                    <span className="quadrant-letter">A</span>
                    <div>
                      <h4 className="quadrant-title">ASSESSMENT</h4>
                      <span className="quadrant-sub">Clinical findings & current trajectory</span>
                    </div>
                  </div>
                  <div className="quadrant-body">
                    {isEditing ? (
                      <textarea
                        className="form-input isbar-edit-area"
                        rows={3}
                        value={editedIsbar.assessment}
                        onChange={e => setEditedIsbar({ ...editedIsbar, assessment: e.target.value })}
                        placeholder="Clinical assessment and findings..."
                      />
                    ) : (
                      <p className="quadrant-text">
                        {editedIsbar.assessment || 'No clinical assessment synthesized.'}
                      </p>
                    )}
                  </div>
                </div>

                {/* Recommendation (R) */}
                <div className="hospital-card isbar-quadrant isbar-quadrant-r isbar-quadrant-full">
                  <div className="quadrant-header">
                    <span className="quadrant-letter">R</span>
                    <div>
                      <h4 className="quadrant-title">RECOMMENDATION</h4>
                      <span className="quadrant-sub">Next actions, pending orders & escalation triggers</span>
                    </div>
                  </div>
                  <div className="quadrant-body">
                    {isEditing ? (
                      <textarea
                        className="form-input isbar-edit-area"
                        rows={3}
                        value={editedIsbar.recommendation}
                        onChange={e => setEditedIsbar({ ...editedIsbar, recommendation: e.target.value })}
                        placeholder="Recommended actions for incoming shift..."
                      />
                    ) : (
                      <p className="quadrant-text">
                        {editedIsbar.recommendation || 'No pending recommendations.'}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Clinical Entities Breakdown (Conditions, Medications, Investigations, Tasks) */}
              <div className="entities-summary-grid">
                {/* Conditions Tile */}
                <div className="hospital-card entity-breakdown-card">
                  <div className="entity-card-header">
                    <span className="entity-title text-rose">🩺 Clinical Conditions</span>
                    {isEditing && (
                      <button className="btn btn-outline btn-xs" onClick={handleAddCondition}>
                        + Add
                      </button>
                    )}
                  </div>
                  <div className="entity-items-list">
                    {editedConditions.length === 0 ? (
                      <span className="empty-text">No active conditions recorded</span>
                    ) : (
                      editedConditions.map((c, idx) => (
                        <div key={idx} className="entity-item-row">
                          {isEditing ? (
                            <div className="item-edit-row">
                              <input 
                                type="text"
                                className="form-input input-xs"
                                value={c.text}
                                onChange={e => handleConditionChange(idx, 'text', e.target.value)}
                                placeholder="Condition name"
                              />
                              <select 
                                className="form-input input-xs select-xs"
                                value={c.status}
                                onChange={e => handleConditionChange(idx, 'status', e.target.value)}
                              >
                                <option value="active">Active</option>
                                <option value="historical">Past / History</option>
                                <option value="negated">Negated / Ruled Out</option>
                              </select>
                              <button className="btn-delete-item" onClick={() => handleRemoveCondition(idx)}>×</button>
                            </div>
                          ) : (
                            <div className="item-view-row">
                              <strong>{c.text}</strong>
                              <span className={`pill-mini pill-${c.status}`}>{c.status}</span>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Medications Tile */}
                <div className="hospital-card entity-breakdown-card">
                  <div className="entity-card-header">
                    <span className="entity-title text-sky">💊 Active Medications</span>
                    {isEditing && (
                      <button className="btn btn-outline btn-xs" onClick={handleAddMedication}>
                        + Add
                      </button>
                    )}
                  </div>
                  <div className="entity-items-list">
                    {editedMedications.length === 0 ? (
                      <span className="empty-text">No medications documented</span>
                    ) : (
                      editedMedications.map((m, idx) => (
                        <div key={idx} className="entity-item-row">
                          {isEditing ? (
                            <div className="item-edit-row">
                              <input 
                                type="text"
                                className="form-input input-xs"
                                value={m.text}
                                onChange={e => handleMedicationChange(idx, 'text', e.target.value)}
                                placeholder="Drug name"
                              />
                              <input 
                                type="text"
                                className="form-input input-xs"
                                value={m.dosage}
                                onChange={e => handleMedicationChange(idx, 'dosage', e.target.value)}
                                placeholder="Dose (e.g. 100mg)"
                              />
                              <button className="btn-delete-item" onClick={() => handleRemoveMedication(idx)}>×</button>
                            </div>
                          ) : (
                            <div className="item-view-row">
                              <strong>{m.text}</strong>
                              <span className="item-details">{m.dosage} {m.frequency} {m.route}</span>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Investigations Tile */}
                <div className="hospital-card entity-breakdown-card">
                  <div className="entity-card-header">
                    <span className="entity-title text-teal">🧪 Investigations & Diagnostics</span>
                    {isEditing && (
                      <button className="btn btn-outline btn-xs" onClick={handleAddInvestigation}>
                        + Add
                      </button>
                    )}
                  </div>
                  <div className="entity-items-list">
                    {editedInvestigations.length === 0 ? (
                      <span className="empty-text">No diagnostics requested</span>
                    ) : (
                      editedInvestigations.map((inv, idx) => (
                        <div key={idx} className="entity-item-row">
                          {isEditing ? (
                            <div className="item-edit-row">
                              <input 
                                type="text"
                                className="form-input input-xs"
                                value={inv.text}
                                onChange={e => handleInvestigationChange(idx, 'text', e.target.value)}
                                placeholder="Investigation name"
                              />
                              <select 
                                className="form-input input-xs select-xs"
                                value={inv.status}
                                onChange={e => handleInvestigationChange(idx, 'status', e.target.value)}
                              >
                                <option value="planned">Planned / Pending</option>
                                <option value="completed">Completed / Received</option>
                              </select>
                              <button className="btn-delete-item" onClick={() => handleRemoveInvestigation(idx)}>×</button>
                            </div>
                          ) : (
                            <div className="item-view-row">
                              <strong>{inv.text}</strong>
                              <span className={`pill-mini pill-${inv.status}`}>{inv.status}</span>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Pending Actions Tile */}
                <div className="hospital-card entity-breakdown-card">
                  <div className="entity-card-header">
                    <span className="entity-title text-amber">📋 Shift Actions & Orders</span>
                    {isEditing && (
                      <button className="btn btn-outline btn-xs" onClick={handleAddTask}>
                        + Add
                      </button>
                    )}
                  </div>
                  <div className="entity-items-list">
                    {editedTasks.length === 0 ? (
                      <span className="empty-text">No pending actions</span>
                    ) : (
                      editedTasks.map((t, idx) => (
                        <div key={idx} className="entity-item-row">
                          {isEditing ? (
                            <div className="item-edit-row">
                              <input 
                                type="text"
                                className="form-input input-xs"
                                value={t.task}
                                onChange={e => handleTaskChange(idx, e.target.value)}
                                placeholder="Task description"
                              />
                              <button className="btn-delete-item" onClick={() => handleRemoveTask(idx)}>×</button>
                            </div>
                          ) : (
                            <div className="item-view-row">
                              <strong>{t.task}</strong>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Clinician Review & Verification Form (When in Edit Mode) */}
              {isEditing && (
                <div className="hospital-card review-signing-panel">
                  <div className="panel-header">
                    <ShieldCheck size={20} className="text-emerald" />
                    <h4>Clinician Sign-off & Audit Attribution</h4>
                  </div>
                  <div className="form-grid-2col">
                    <div className="form-group">
                      <label className="form-label">Reviewing Clinician Credentials *</label>
                      <input 
                        type="text"
                        className="form-input"
                        value={reviewerIdentifier}
                        onChange={e => setReviewerIdentifier(e.target.value)}
                        placeholder="e.g. Dr. A. Gupta, MD (Attending Consultant)"
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Audit Notes & Clinical Remarks</label>
                      <input 
                        type="text"
                        className="form-input"
                        value={reviewNotes}
                        onChange={e => setReviewNotes(e.target.value)}
                        placeholder="e.g. Handover verified during ward multidisciplinary rounds."
                      />
                    </div>
                  </div>

                  <div className="review-actions-bar">
                    <button 
                      type="button" 
                      className="btn btn-outline"
                      onClick={handleResetToAI}
                    >
                      <RotateCcw size={14} /> Reset to Original AI
                    </button>
                    <button 
                      type="button" 
                      className="btn btn-primary"
                      onClick={handleSaveReview}
                      disabled={saving}
                    >
                      <ShieldCheck size={15} />
                      <span>{saving ? 'Verifying & Signing...' : 'Verify & Sign-off Handover'}</span>
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          {/* TAB 2: Original AI Extraction Archive */}
          {activeTab === 'original_ai' && (
            <div className="hospital-card ai-archive-panel">
              <div className="archive-header">
                <Eye size={18} className="text-primary" />
                <h4>Original Bio_ClinicalBERT Structured Extraction Archive</h4>
              </div>
              <p className="archive-sub">
                Immutable snapshot of the AI model's automated extraction prior to any human clinician edits.
              </p>
              <pre className="archive-json-preview">
                {JSON.stringify(originalExt, null, 2)}
              </pre>
            </div>
          )}

          {/* TAB 3: Verbatim Source Note */}
          {activeTab === 'source_note' && (
            <div className="hospital-card verbatim-panel">
              <div className="verbatim-header">
                <span>Source Note #{activeNote.id} (Verbatim Record)</span>
                <span className="verbatim-meta">
                  Author: {activeNote.author_identifier || 'Staff Clinician'} • {new Date(activeNote.created_at).toLocaleString()}
                </span>
              </div>
              <div className="verbatim-box">
                {activeNote.raw_text}
              </div>
            </div>
          )}
        </>
      )}

      {/* FHIR R4 JSON Export Modal */}
      {showFhirModal && (
        <div className="modal-backdrop" onClick={() => setShowFhirModal(false)}>
          <div className="fhir-modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <FileCode size={20} className="modal-icon text-primary" />
                <h3>HL7® FHIR® R4 Clinical Document Bundle</h3>
              </div>
              <button className="modal-close-btn" onClick={() => setShowFhirModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <p className="fhir-description">
                Interoperable FHIR R4 Composition Bundle formatted for Epic, Cerner, or NHS electronic health record ingestion.
              </p>
              <pre className="fhir-code-preview">
                {JSON.stringify(generateFhirBundle(), null, 2)}
              </pre>
            </div>
            <div className="modal-footer">
              <button className="modal-action-btn secondary" onClick={handleCopyFhir}>
                {copiedFhir ? <Check size={14} className="text-emerald" /> : <Copy size={14} />}
                <span>{copiedFhir ? "Copied to Clipboard!" : "Copy FHIR JSON"}</span>
              </button>
              <button className="modal-action-btn primary" onClick={handleDownloadFhir}>
                <Download size={14} />
                <span>Download .json Bundle</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default HandoverSummaryPage;
