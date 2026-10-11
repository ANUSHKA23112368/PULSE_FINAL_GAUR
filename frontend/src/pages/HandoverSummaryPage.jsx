import React, { useState, useEffect } from 'react';
import { 
  Layers, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  FileText, 
  ArrowRight,
  ListOrdered,
  Pill,
  Activity,
  Calendar,
  AlertCircle,
  Edit3,
  Save,
  RotateCcw,
  Plus,
  Trash2,
  ShieldCheck,
  Eye,
  Check
} from 'lucide-react';
import { PatientBanner } from '../components/PatientBanner';
import { fetchPatientNotes, reviewPatientNote } from '../services/api';

export function HandoverSummaryPage({ selectedPatient, onSwitchPatient, onNavigate }) {
  const [notes, setNotes] = useState([]);
  const [selectedNoteId, setSelectedNoteId] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Tab view: 'handover' (Reviewed/Current Handover), 'original_ai' (Original AI Extraction), 'source_note' (Verbatim Source Note)
  const [activeTab, setActiveTab] = useState('handover');
  const [isEditing, setIsEditing] = useState(false);

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

  async function loadNotes() {
    setLoading(true);
    setSaveError(null);
    setSaveSuccess(null);
    try {
      const data = await fetchPatientNotes(selectedPatient.display_id || selectedPatient.id);
      // Support both Processed and Reviewed notes
      const validNotes = (data.notes || []).filter(
        n => (n.status === 'Processed' || n.status === 'Reviewed') && n.extraction?.data
      );
      setNotes(validNotes);
      if (validNotes.length > 0) {
        // Default to first note if not already selected or if selected is gone
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

    // If human review exists, initialize from latest review, else from AI extraction
    const sourceData = note.review?.reviewed_data || note.extraction?.data || {};
    const isbarData = sourceData.isbar || sourceData.structured_handover?.isbar || {};
    const conditionsData = sourceData.entities?.conditions || sourceData.conditions || [];
    const medicationsData = sourceData.entities?.medications || sourceData.medications || [];
    const tasksData = sourceData.pending_tasks || [];

    setEditedIsbar({
      situation: isbarData.situation || '',
      background: isbarData.background || '',
      assessment: isbarData.assessment || '',
      recommendation: isbarData.recommendation || ''
    });

    setEditedExecutiveSummary(
      sourceData.executive_summary || sourceData.structured_handover?.executive_summary || ''
    );

    setEditedConditions(
      conditionsData.map(c => ({
        text: typeof c === 'string' ? c : c.text || '',
        status: c.is_negated ? 'negated' : c.is_historical ? 'historical' : 'active',
        source_sentence: c.source_sentence || ''
      }))
    );

    setEditedMedications(
      medicationsData.map(m => ({
        text: typeof m === 'string' ? m : m.text || '',
        dosage: m.dosage || '',
        frequency: m.frequency || '',
        route: m.route || '',
        source_sentence: m.source_sentence || ''
      }))
    );

    setEditedTasks(
      tasksData.map(t => ({
        task: typeof t === 'string' ? t : t.task || '',
        source_sentence: t.source_sentence || ''
      }))
    );

    if (note.review) {
      setReviewerIdentifier(note.review.reviewer_identifier || 'Dr. Hanlen, MD (Attending Consultant)');
      setReviewNotes(note.review.review_notes || '');
    } else {
      setReviewerIdentifier('Dr. Hanlen, MD (Attending Consultant)');
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
    const aiData = activeNote.extraction?.data || {};
    const isbarData = aiData.isbar || aiData.structured_handover?.isbar || {};
    const conditionsData = aiData.entities?.conditions || [];
    const medicationsData = aiData.entities?.medications || [];
    const tasksData = aiData.pending_tasks || [];

    setEditedIsbar({
      situation: isbarData.situation || '',
      background: isbarData.background || '',
      assessment: isbarData.assessment || '',
      recommendation: isbarData.recommendation || ''
    });
    setEditedExecutiveSummary(aiData.executive_summary || aiData.structured_handover?.executive_summary || '');
    setEditedConditions(
      conditionsData.map(c => ({
        text: c.text || '',
        status: c.is_negated ? 'negated' : c.is_historical ? 'historical' : 'active',
        source_sentence: c.source_sentence || ''
      }))
    );
    setEditedMedications(
      medicationsData.map(m => ({
        text: m.text || '',
        dosage: m.dosage || '',
        frequency: m.frequency || '',
        route: m.route || '',
        source_sentence: m.source_sentence || ''
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

  // Handlers for modifying items
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

  function handleAddTask() {
    setEditedTasks(prev => [...prev, { task: '', source_sentence: '' }]);
  }
  function handleRemoveTask(index) {
    setEditedTasks(prev => prev.filter((_, i) => i !== index));
  }
  function handleTaskChange(index, value) {
    setEditedTasks(prev => prev.map((item, i) => i === index ? { ...item, task: value } : item));
  }

  // Save clinician review
  async function handleSaveReview() {
    if (!activeNote || !selectedPatient) return;
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    // Construct full reviewed structured extraction payload
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

      // Successfully saved review
      setSaveSuccess(`Clinician review saved successfully! Handover is now verified by ${res.reviewer_identifier}.`);
      setIsEditing(false);

      // Update local state without losing unsaved fields or resetting to original
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
      // Retain unsaved edits so user can retry or correct
      setSaveError(err.message || "Failed to save clinician review. Edits have been preserved.");
    } finally {
      setSaving(false);
    }
  }

  const activeNote = notes.find(n => n.id === selectedNoteId);
  const originalExt = activeNote?.extraction?.data || {};
  const isReviewed = activeNote?.status === 'Reviewed';
  const latestReview = activeNote?.review;

  return (
    <div className="page-container">
      {/* Patient Banner */}
      <PatientBanner patient={selectedPatient} onSwitchPatient={onSwitchPatient} />

      {/* Header and Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a', margin: 0 }}>
              Clinical Handover & Verification Workstation
            </h2>
            {activeNote && (
              <span style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: '9999px',
                background: isReviewed ? '#ecfdf5' : '#fffbeb',
                color: isReviewed ? '#065f46' : '#92400e',
                border: `1px solid ${isReviewed ? '#a7f3d0' : '#fde68a'}`,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                {isReviewed ? <ShieldCheck size={13} color="#059669" /> : <AlertTriangle size={13} color="#d97706" />}
                {isReviewed ? 'Clinician Verified' : 'AI-generated — not yet reviewed'}
              </span>
            )}
          </div>
          <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
            Standardized ISBAR clinical structure for {selectedPatient ? selectedPatient.name : 'patient'} with human-in-the-loop review and audit trail.
          </div>
        </div>

        {/* Note Selector & Edit Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {notes.length > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
              <span style={{ color: '#475569', fontWeight: 600 }}>Note:</span>
              <select 
                value={selectedNoteId || ''}
                onChange={(e) => handleSelectNote(Number(e.target.value))}
                className="form-input"
                style={{ padding: '0.35rem 0.65rem', fontSize: '0.85rem' }}
              >
                {notes.map(n => (
                  <option key={n.id} value={n.id}>
                    Note #{n.id} ({n.status}) — {new Date(n.created_at).toLocaleDateString()} {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </option>
                ))}
              </select>
            </div>
          )}

          {activeNote && activeTab === 'handover' && (
            <button
              className={`btn ${isEditing ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setIsEditing(!isEditing)}
              style={{ fontSize: '0.85rem', padding: '0.4rem 0.85rem', gap: '0.4rem' }}
            >
              <Edit3 size={14} />
              {isEditing ? 'Done Editing (Review Form)' : 'Edit Extracted Fields'}
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="hospital-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <div style={{ color: '#64748b', fontSize: '0.9rem' }}>Loading structured handover records...</div>
        </div>
      ) : !activeNote ? (
        <div className="hospital-card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem' }}>
          <Layers size={36} color="#94a3b8" style={{ margin: '0 auto 1rem auto' }} />
          <h3 style={{ fontSize: '1.15rem', color: '#0f172a', marginBottom: '0.5rem' }}>
            No processed handover notes available for this patient
          </h3>
          <p style={{ color: '#64748b', fontSize: '0.9rem', maxWidth: '500px', margin: '0 auto 1.5rem auto' }}>
            To generate a structured ISBAR handover summary, enter a clinical note and click "Save & Process with AI" on the Clinical Notes workstation.
          </p>
          <button 
            className="btn btn-primary"
            onClick={() => onNavigate('notes')}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            Go to Clinical Notes Workstation <ArrowRight size={15} />
          </button>
        </div>
      ) : (
        <>
          {/* View Mode Tabs */}
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
            <button
              onClick={() => setActiveTab('handover')}
              className="btn"
              style={{
                fontSize: '0.875rem',
                padding: '0.45rem 1rem',
                background: activeTab === 'handover' ? '#0284c7' : '#ffffff',
                color: activeTab === 'handover' ? '#ffffff' : '#475569',
                borderColor: activeTab === 'handover' ? '#0284c7' : '#cbd5e1',
                gap: '0.4rem'
              }}
            >
              {isReviewed ? <ShieldCheck size={15} /> : <FileText size={15} />}
              {isReviewed ? 'Clinician Verified Handover' : 'Structured Handover (Editable)'}
            </button>
            <button
              onClick={() => setActiveTab('original_ai')}
              className="btn"
              style={{
                fontSize: '0.875rem',
                padding: '0.45rem 1rem',
                background: activeTab === 'original_ai' ? '#0284c7' : '#ffffff',
                color: activeTab === 'original_ai' ? '#ffffff' : '#475569',
                borderColor: activeTab === 'original_ai' ? '#0284c7' : '#cbd5e1',
                gap: '0.4rem'
              }}
            >
              <Eye size={15} /> Original AI Extraction (Unedited Archive)
            </button>
            <button
              onClick={() => setActiveTab('source_note')}
              className="btn"
              style={{
                fontSize: '0.875rem',
                padding: '0.45rem 1rem',
                background: activeTab === 'source_note' ? '#0284c7' : '#ffffff',
                color: activeTab === 'source_note' ? '#ffffff' : '#475569',
                borderColor: activeTab === 'source_note' ? '#0284c7' : '#cbd5e1',
                gap: '0.4rem'
              }}
            >
              <FileText size={15} /> Verbatim Source Note & Evidence
            </button>
          </div>

          {/* Feedback Alerts */}
          {saveSuccess && (
            <div style={{
              background: '#ecfdf5',
              border: '1px solid #a7f3d0',
              borderRadius: '6px',
              padding: '0.75rem 1rem',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: '#065f46',
              fontSize: '0.875rem'
            }}>
              <CheckCircle2 size={18} color="#059669" />
              <span>{saveSuccess}</span>
            </div>
          )}

          {saveError && (
            <div style={{
              background: '#fef2f2',
              border: '1px solid #fca5a5',
              borderRadius: '6px',
              padding: '0.75rem 1rem',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: '#991b1b',
              fontSize: '0.875rem'
            }}>
              <AlertCircle size={18} color="#dc2626" />
              <div>
                <strong>Save Review Failed:</strong> {saveError}
                <div style={{ fontSize: '0.8rem', marginTop: '2px', color: '#b91c1c' }}>
                  Your entered corrections are safe and preserved on this screen.
                </div>
              </div>
            </div>
          )}

          {/* TAB 1: Handover Summary / Editable Review */}
          {activeTab === 'handover' && (
            <>
              {/* Status Header Banner */}
              {isReviewed ? (
                <div style={{
                  background: '#f0fdf4',
                  border: '1px solid #bbf7d0',
                  borderLeft: '5px solid #16a34a',
                  borderRadius: '8px',
                  padding: '0.85rem 1.25rem',
                  marginBottom: '1.25rem',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '1rem',
                  flexWrap: 'wrap'
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                    <ShieldCheck size={22} color="#16a34a" style={{ flexShrink: 0, marginTop: '2px' }} />
                    <div>
                      <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#166534' }}>
                        Clinician Verified Handover
                      </div>
                      <div style={{ fontSize: '0.825rem', color: '#15803d', marginTop: '2px' }}>
                        Reviewed by: <strong>{latestReview?.reviewer_identifier || activeNote.reviewer_identifier}</strong>
                        {activeNote.reviewed_at && (
                          <span> • Verified at: {new Date(activeNote.reviewed_at).toLocaleString()}</span>
                        )}
                      </div>
                      {latestReview?.review_notes && (
                        <div style={{ fontSize: '0.825rem', color: '#374151', background: '#ffffff', padding: '0.35rem 0.65rem', borderRadius: '4px', border: '1px solid #dcfce7', marginTop: '0.4rem' }}>
                          <strong>Audit Note:</strong> {latestReview.review_notes}
                        </div>
                      )}
                      {activeNote.review_history && activeNote.review_history.length > 1 && (
                        <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#166534' }}>
                          <details style={{ cursor: 'pointer' }}>
                            <summary style={{ fontWeight: 600 }}>
                              Review Audit History ({activeNote.review_history.length} reviews recorded)
                            </summary>
                            <div style={{ marginTop: '0.4rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                              {activeNote.review_history.map((rev, idx) => (
                                <div key={rev.id || idx} style={{ background: '#ffffff', padding: '0.35rem 0.6rem', borderRadius: '4px', border: '1px solid #dcfce7', fontSize: '0.775rem' }}>
                                  <strong>{idx === 0 ? 'Active / Latest: ' : `Prior Review: `}</strong>
                                  <span>{rev.reviewer_identifier}</span>
                                  <span style={{ color: '#64748b' }}> • {new Date(rev.reviewed_at).toLocaleString()}</span>
                                  {rev.review_notes && <div style={{ color: '#374151', fontStyle: 'italic', marginTop: '2px' }}>"{rev.review_notes}"</div>}
                                </div>
                              ))}
                            </div>
                          </details>
                        </div>
                      )}
                    </div>
                  </div>
                  {isEditing && (
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, background: '#fef3c7', color: '#92400e', padding: '2px 8px', borderRadius: '4px' }}>
                      Edit Mode Active
                    </span>
                  )}
                </div>
              ) : (
                <div style={{
                  background: '#fffbeb',
                  border: '1px solid #fde68a',
                  borderLeft: '5px solid #f59e0b',
                  borderRadius: '8px',
                  padding: '0.85rem 1.25rem',
                  marginBottom: '1.25rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem'
                }}>
                  <AlertTriangle size={20} color="#d97706" style={{ flexShrink: 0 }} />
                  <div style={{ fontSize: '0.875rem', color: '#92400e' }}>
                    <strong>AI-generated — not yet reviewed.</strong>
                    <span style={{ display: 'block', fontSize: '0.8rem', color: '#b45309', marginTop: '2px' }}>
                      Extracted information is generated by AI models and has not been verified by a clinician. Review and correct items below, then click "Save Review & Verify Handover".
                    </span>
                  </div>
                </div>
              )}

              {/* ISBAR Framework Cards (Editable or Read-Only) */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                {/* [S] Situation */}
                <div className="hospital-card" style={{ borderTop: '4px solid #0284c7' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.4rem' }}>
                    [S] Situation
                  </div>
                  {isEditing ? (
                    <textarea
                      value={editedIsbar.situation}
                      onChange={(e) => setEditedIsbar({ ...editedIsbar, situation: e.target.value })}
                      className="form-input"
                      rows={3}
                      style={{ width: '100%', fontSize: '0.875rem' }}
                      placeholder="Current patient clinical situation..."
                    />
                  ) : (
                    <div style={{ fontSize: '0.925rem', color: '#0f172a', lineHeight: '1.5' }}>
                      {editedIsbar.situation || 'Patient under observation.'}
                    </div>
                  )}
                </div>

                {/* [B] Background */}
                <div className="hospital-card" style={{ borderTop: '4px solid #6366f1' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#4338ca', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.4rem' }}>
                    [B] Background
                  </div>
                  {isEditing ? (
                    <textarea
                      value={editedIsbar.background}
                      onChange={(e) => setEditedIsbar({ ...editedIsbar, background: e.target.value })}
                      className="form-input"
                      rows={3}
                      style={{ width: '100%', fontSize: '0.875rem' }}
                      placeholder="Clinical background and context..."
                    />
                  ) : (
                    <div style={{ fontSize: '0.925rem', color: '#0f172a', lineHeight: '1.5' }}>
                      {editedIsbar.background || 'Clinical history referenced in handover narrative.'}
                    </div>
                  )}
                </div>

                {/* [A] Assessment */}
                <div className="hospital-card" style={{ borderTop: '4px solid #0d9488' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#0f766e', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.4rem' }}>
                    [A] Assessment
                  </div>
                  {isEditing ? (
                    <textarea
                      value={editedIsbar.assessment}
                      onChange={(e) => setEditedIsbar({ ...editedIsbar, assessment: e.target.value })}
                      className="form-input"
                      rows={3}
                      style={{ width: '100%', fontSize: '0.875rem' }}
                      placeholder="Ongoing shift assessment and vitals..."
                    />
                  ) : (
                    <div style={{ fontSize: '0.925rem', color: '#0f172a', lineHeight: '1.5' }}>
                      {editedIsbar.assessment || 'Ongoing shift observations and clinical monitoring.'}
                    </div>
                  )}
                </div>

                {/* [R] Recommendation */}
                <div className="hospital-card" style={{ borderTop: '4px solid #f59e0b' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#b45309', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.4rem' }}>
                    [R] Recommendation
                  </div>
                  {isEditing ? (
                    <textarea
                      value={editedIsbar.recommendation}
                      onChange={(e) => setEditedIsbar({ ...editedIsbar, recommendation: e.target.value })}
                      className="form-input"
                      rows={3}
                      style={{ width: '100%', fontSize: '0.875rem' }}
                      placeholder="Next steps, monitoring, pending tasks..."
                    />
                  ) : (
                    <div style={{ fontSize: '0.925rem', color: '#0f172a', lineHeight: '1.5' }}>
                      {editedIsbar.recommendation || 'Continue routine care and observe.'}
                    </div>
                  )}
                </div>
              </div>

              {/* Structured Entities: Conditions, Medications, Tasks */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                {/* Conditions & Observations */}
                <div className="hospital-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a', margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Activity size={16} color="#0284c7" /> Clinical Conditions & Observations
                    </h3>
                    {isEditing && (
                      <button 
                        onClick={handleAddCondition}
                        className="btn btn-outline"
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', gap: '2px' }}
                      >
                        <Plus size={12} /> Add Condition
                      </button>
                    )}
                  </div>

                  {editedConditions.length === 0 ? (
                    <div style={{ color: '#64748b', fontSize: '0.85rem' }}>None recorded.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {editedConditions.map((c, i) => (
                        <div key={i} style={{ background: '#f8fafc', padding: '0.5rem 0.6rem', borderRadius: '4px', border: '1px solid #e2e8f0', fontSize: '0.85rem' }}>
                          {isEditing ? (
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                              <input
                                type="text"
                                value={c.text}
                                onChange={(e) => handleConditionChange(i, 'text', e.target.value)}
                                className="form-input"
                                style={{ flex: 1, padding: '0.3rem 0.5rem', fontSize: '0.85rem' }}
                                placeholder="Condition description"
                              />
                              <select
                                value={c.status}
                                onChange={(e) => handleConditionChange(i, 'status', e.target.value)}
                                className="form-input"
                                style={{ padding: '0.3rem 0.5rem', fontSize: '0.8rem', width: '95px' }}
                              >
                                <option value="active">Active</option>
                                <option value="historical">Historical</option>
                                <option value="negated">Negated</option>
                              </select>
                              <button
                                onClick={() => handleRemoveCondition(i)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626', padding: '2px' }}
                                title="Remove condition"
                              >
                                <Trash2 size={15} />
                              </button>
                            </div>
                          ) : (
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontWeight: 600, color: '#1e293b' }}>{c.text}</span>
                              <span style={{
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                padding: '1px 6px',
                                borderRadius: '3px',
                                background: c.status === 'negated' ? '#fee2e2' : c.status === 'historical' ? '#f1f5f9' : '#e0f2fe',
                                color: c.status === 'negated' ? '#991b1b' : c.status === 'historical' ? '#475569' : '#0369a1'
                              }}>
                                {c.status === 'negated' ? 'Negated' : c.status === 'historical' ? 'Historical' : 'Active'}
                              </span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Medications & Dosages */}
                <div className="hospital-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a', margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Pill size={16} color="#9333ea" /> Medications & Dosages
                    </h3>
                    {isEditing && (
                      <button 
                        onClick={handleAddMedication}
                        className="btn btn-outline"
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', gap: '2px' }}
                      >
                        <Plus size={12} /> Add Medication
                      </button>
                    )}
                  </div>

                  {editedMedications.length === 0 ? (
                    <div style={{ color: '#64748b', fontSize: '0.85rem' }}>None recorded.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {editedMedications.map((m, i) => (
                        <div key={i} style={{ background: '#f8fafc', padding: '0.5rem 0.6rem', borderRadius: '4px', border: '1px solid #e2e8f0', fontSize: '0.85rem' }}>
                          {isEditing ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                <input
                                  type="text"
                                  value={m.text}
                                  onChange={(e) => handleMedicationChange(i, 'text', e.target.value)}
                                  className="form-input"
                                  style={{ flex: 1, padding: '0.3rem 0.5rem', fontSize: '0.85rem' }}
                                  placeholder="Medication name"
                                />
                                <button
                                  onClick={() => handleRemoveMedication(i)}
                                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626', padding: '2px' }}
                                  title="Remove medication"
                                >
                                  <Trash2 size={15} />
                                </button>
                              </div>
                              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.35rem' }}>
                                <input
                                  type="text"
                                  value={m.dosage}
                                  onChange={(e) => handleMedicationChange(i, 'dosage', e.target.value)}
                                  className="form-input"
                                  style={{ padding: '0.25rem 0.45rem', fontSize: '0.8rem' }}
                                  placeholder="Dose (e.g. 50mg)"
                                />
                                <input
                                  type="text"
                                  value={m.frequency}
                                  onChange={(e) => handleMedicationChange(i, 'frequency', e.target.value)}
                                  className="form-input"
                                  style={{ padding: '0.25rem 0.45rem', fontSize: '0.8rem' }}
                                  placeholder="Freq (e.g. BD)"
                                />
                                <input
                                  type="text"
                                  value={m.route}
                                  onChange={(e) => handleMedicationChange(i, 'route', e.target.value)}
                                  className="form-input"
                                  style={{ padding: '0.25rem 0.45rem', fontSize: '0.8rem' }}
                                  placeholder="Route (e.g. IV)"
                                />
                              </div>
                            </div>
                          ) : (
                            <div>
                              <div style={{ fontWeight: 600, color: '#1e293b' }}>{m.text}</div>
                              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                                Dose: {m.dosage || 'Unspecified'} • Freq: {m.frequency || 'Unspecified'} • Route: {m.route || 'Unspecified'}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Pending Actions & Tasks */}
                <div className="hospital-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a', margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <ListOrdered size={16} color="#d97706" /> Pending Actions & Tasks
                    </h3>
                    {isEditing && (
                      <button 
                        onClick={handleAddTask}
                        className="btn btn-outline"
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', gap: '2px' }}
                      >
                        <Plus size={12} /> Add Task
                      </button>
                    )}
                  </div>

                  {editedTasks.length === 0 ? (
                    <div style={{ color: '#64748b', fontSize: '0.85rem' }}>No pending tasks recorded.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {editedTasks.map((t, i) => (
                        <div key={i} style={{ background: '#fffbeb', border: '1px solid #fde68a', padding: '0.4rem 0.6rem', borderRadius: '4px', fontSize: '0.85rem' }}>
                          {isEditing ? (
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                              <input
                                type="text"
                                value={t.task}
                                onChange={(e) => handleTaskChange(i, e.target.value)}
                                className="form-input"
                                style={{ flex: 1, padding: '0.3rem 0.5rem', fontSize: '0.85rem' }}
                                placeholder="Task description..."
                              />
                              <button
                                onClick={() => handleRemoveTask(i)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626', padding: '2px' }}
                                title="Remove task"
                              >
                                <Trash2 size={15} />
                              </button>
                            </div>
                          ) : (
                            <div style={{ color: '#92400e' }}>
                              • {t.task}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Clinician Review & Verification Action Card */}
              <div className="hospital-card" style={{ border: '2px solid #0284c7', background: '#f8fafc', marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.85rem' }}>
                  <ShieldCheck size={20} color="#0284c7" />
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#0f172a', margin: 0 }}>
                    Clinician Review & Handover Verification
                  </h3>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: '#334155', marginBottom: '0.3rem' }}>
                      Reviewer Identifier (Name / Role):
                    </label>
                    <input
                      type="text"
                      value={reviewerIdentifier}
                      onChange={(e) => setReviewerIdentifier(e.target.value)}
                      className="form-input"
                      style={{ width: '100%', fontSize: '0.875rem' }}
                      placeholder="e.g. Dr. Hanlen, MD (Attending Consultant)"
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: '#334155', marginBottom: '0.3rem' }}>
                      Clinical Review Audit Notes (Optional):
                    </label>
                    <input
                      type="text"
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                      className="form-input"
                      style={{ width: '100%', fontSize: '0.875rem' }}
                      placeholder="e.g. Corrected medication dose; verified respiratory observations."
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <button
                    onClick={handleSaveReview}
                    disabled={saving}
                    className="btn btn-primary"
                    style={{ gap: '0.5rem', padding: '0.65rem 1.25rem', fontSize: '0.925rem' }}
                  >
                    <Save size={16} />
                    {saving ? 'Saving Review...' : 'Save Review & Verify Handover'}
                  </button>

                  <button
                    onClick={handleResetToAI}
                    disabled={saving}
                    className="btn btn-outline"
                    style={{ gap: '0.4rem', fontSize: '0.85rem' }}
                    title="Restore unedited AI extraction content"
                  >
                    <RotateCcw size={14} /> Reset to Original AI Output
                  </button>
                </div>
              </div>
            </>
          )}

          {/* TAB 2: Original AI Extraction Archive */}
          {activeTab === 'original_ai' && (
            <div className="hospital-card" style={{ marginBottom: '1.5rem', background: '#ffffff', border: '1px solid #cbd5e1' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.75rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0f172a', margin: 0 }}>
                    Original AI Extraction (Unedited Archive)
                  </h3>
                  <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                    Engine: <strong>{activeNote.extraction?.engine_used || 'Bio_ClinicalBERT Pipeline'}</strong> • Processed at: {activeNote.extraction?.extracted_at || activeNote.created_at}
                  </div>
                </div>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, background: '#f1f5f9', color: '#475569', padding: '3px 8px', borderRadius: '4px' }}>
                  Read-Only System Archive
                </span>
              </div>

              {/* ISBAR AI Original */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
                <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <strong style={{ fontSize: '0.8rem', color: '#0369a1', display: 'block', marginBottom: '4px' }}>[S] Situation:</strong>
                  <div style={{ fontSize: '0.85rem', color: '#1e293b' }}>{originalExt.isbar?.situation || 'None'}</div>
                </div>
                <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <strong style={{ fontSize: '0.8rem', color: '#4338ca', display: 'block', marginBottom: '4px' }}>[B] Background:</strong>
                  <div style={{ fontSize: '0.85rem', color: '#1e293b' }}>{originalExt.isbar?.background || 'None'}</div>
                </div>
                <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <strong style={{ fontSize: '0.8rem', color: '#0f766e', display: 'block', marginBottom: '4px' }}>[A] Assessment:</strong>
                  <div style={{ fontSize: '0.85rem', color: '#1e293b' }}>{originalExt.isbar?.assessment || 'None'}</div>
                </div>
                <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <strong style={{ fontSize: '0.8rem', color: '#b45309', display: 'block', marginBottom: '4px' }}>[R] Recommendation:</strong>
                  <div style={{ fontSize: '0.85rem', color: '#1e293b' }}>{originalExt.isbar?.recommendation || 'None'}</div>
                </div>
              </div>

              {/* Conditions & Medications AI Original */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
                <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <strong style={{ fontSize: '0.8rem', color: '#0284c7', display: 'block', marginBottom: '6px' }}>Extracted Conditions:</strong>
                  {(originalExt.entities?.conditions || []).length === 0 ? (
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>None</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {originalExt.entities.conditions.map((c, i) => (
                        <div key={i} style={{ fontSize: '0.825rem', color: '#1e293b' }}>
                          • {c.text} {c.is_negated ? '(Negated)' : c.is_historical ? '(Historical)' : '(Active)'}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <strong style={{ fontSize: '0.8rem', color: '#9333ea', display: 'block', marginBottom: '6px' }}>Extracted Medications:</strong>
                  {(originalExt.entities?.medications || []).length === 0 ? (
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>None</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {originalExt.entities.medications.map((m, i) => (
                        <div key={i} style={{ fontSize: '0.825rem', color: '#1e293b' }}>
                          • {m.text} {m.dosage ? `[${m.dosage}]` : ''} {m.frequency ? `[${m.frequency}]` : ''}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Verbatim Source Note & Evidence */}
          {activeTab === 'source_note' && (
            <div className="hospital-card" style={{ marginBottom: '1.5rem', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.9rem', fontWeight: 700, color: '#334155' }}>
                  Source Clinical Note #{activeNote.id} (Verbatim Record)
                </span>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Author: {activeNote.author_identifier || 'Staff Clinician'} • Recorded: {new Date(activeNote.created_at).toLocaleString()}
                </span>
              </div>
              <div style={{ fontSize: '0.9rem', color: '#1e293b', whiteSpace: 'pre-wrap', lineHeight: '1.6', background: '#ffffff', padding: '1rem', borderRadius: '6px', border: '1px solid #cbd5e1', marginBottom: '1rem' }}>
                {activeNote.raw_text}
              </div>

              {/* Source Sentence Evidence Linking */}
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#475569', marginBottom: '0.5rem' }}>
                Source Evidence Map (Sentence Attribution)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {(originalExt.entities?.conditions || []).filter(c => c.source_sentence).map((c, i) => (
                  <div key={`cond-ev-${i}`} style={{ background: '#ffffff', padding: '0.5rem 0.75rem', borderRadius: '4px', border: '1px solid #e2e8f0', fontSize: '0.8rem' }}>
                    <span style={{ fontWeight: 600, color: '#0284c7' }}>Condition: "{c.text}"</span>
                    <div style={{ color: '#475569', marginTop: '2px', fontStyle: 'italic' }}>
                      "{c.source_sentence}"
                    </div>
                  </div>
                ))}
                {(originalExt.entities?.medications || []).filter(m => m.source_sentence).map((m, i) => (
                  <div key={`med-ev-${i}`} style={{ background: '#ffffff', padding: '0.5rem 0.75rem', borderRadius: '4px', border: '1px solid #e2e8f0', fontSize: '0.8rem' }}>
                    <span style={{ fontWeight: 600, color: '#9333ea' }}>Medication: "{m.text}"</span>
                    <div style={{ color: '#475569', marginTop: '2px', fontStyle: 'italic' }}>
                      "{m.source_sentence}"
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default HandoverSummaryPage;
