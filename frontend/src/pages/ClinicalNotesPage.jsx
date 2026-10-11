import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Send, 
  Save, 
  Clock, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  AlertTriangle,
  ChevronDown, 
  ChevronUp, 
  RefreshCw,
  Copy,
  ShieldCheck
} from 'lucide-react';
import { PatientBanner } from '../components/PatientBanner';
import { fetchPatientNotes, createPatientNote, processPatientNote } from '../services/api';

// Pre-packaged demonstration narratives mapped from sample reports for one-click testing
const DEMO_TEMPLATES = {
  "PULSE-DEMO-001": "Bed eight, Michael I Wu. Forty-eight years under Dr Hanlen. He came in with headache and vertigo. He's got a history of headache, tinnitus, Bell's Palsy, severe neck pain. He is waiting for a CT scan of the head. Vitals: BP 124/82 mmHg, HR 78 bpm, afebrile. Digoxin 0.25mg mane. Plan neuro review in morning.",
  "PULSE-DEMO-002": "Vera Abbott, 93, bed four, under Dr Liu came in with chest pain with a history of stroke and previous chest pains, asthma, cataract and glaucoma. Given GTN sublingual with relief. Repeat troponin ordered for 0600. Keep on continuous ECG monitoring.",
  "PULSE-DEMO-003": "Leila sonya Da silva, bed 5, 34 under Dr Liu, came in for management of her diabetes. With history of type 1 DM since childhood and HPN. Blood glucose currently 11.4 mmol/L. Subcut Actrapid 6 units with dinner. Check BGL 2200.",
  "PULSE-DEMO-004": "Pierre cox, 77 years old under Dr Gregor, bed 2, came in with pain and swelling of the right leg query embolism. With a history of coronary artery disease. Ultrasound doppler scheduled for 0900. Clexane 80mg subcut commenced."
};

export function ClinicalNotesPage({ selectedPatient, onSwitchPatient, onNavigate }) {
  const [noteText, setNoteText] = useState('');
  const [author, setAuthor] = useState('Staff Nurse / Clinician (Demo)');
  const [notes, setNotes] = useState([]);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [processingNote, setProcessingNote] = useState(false);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', message: '' }
  const [expandedExtraction, setExpandedExtraction] = useState({}); // noteId -> boolean

  useEffect(() => {
    if (selectedPatient) {
      loadNotes();
    }
  }, [selectedPatient]);

  async function loadNotes() {
    if (!selectedPatient) return;
    setLoadingNotes(true);
    try {
      const data = await fetchPatientNotes(selectedPatient.display_id || selectedPatient.id);
      setNotes(data.notes || []);
    } catch (err) {
      console.warn("Could not load notes:", err);
    } finally {
      setLoadingNotes(false);
    }
  }

  function handleLoadTemplate() {
    const template = DEMO_TEMPLATES[selectedPatient?.display_id] || 
      `Handover note for ${selectedPatient?.name || 'patient'}. Admitted under ${selectedPatient?.consultant || 'team'} for observation. Vitals stable overnight. Continue planned care.`;
    setNoteText(template);
    setFeedback({ type: 'info', message: 'Demonstration handover narrative loaded into editor.' });
  }

  async function handleSaveDraft(e) {
    if (e) e.preventDefault();
    if (!noteText.trim()) {
      setFeedback({ type: 'error', message: 'Clinical note cannot be empty or whitespace only.' });
      return;
    }
    setSavingDraft(true);
    setFeedback(null);
    try {
      const newNote = await createPatientNote(
        selectedPatient.display_id || selectedPatient.id,
        noteText.trim(),
        author
      );
      setNoteText('');
      setFeedback({ type: 'success', message: `Draft note #${newNote.id} saved successfully.` });
      await loadNotes();
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Failed to save draft note.' });
    } finally {
      setSavingDraft(false);
    }
  }

  async function handleProcessImmediate(e) {
    if (e) e.preventDefault();
    if (!noteText.trim()) {
      setFeedback({ type: 'error', message: 'Clinical note cannot be empty or whitespace only.' });
      return;
    }
    setProcessingNote(true);
    setFeedback(null);
    try {
      // Step 1: Save draft
      const newNote = await createPatientNote(
        selectedPatient.display_id || selectedPatient.id,
        noteText.trim(),
        author
      );
      // Step 2: Process note via AI pipeline
      const processed = await processPatientNote(
        selectedPatient.display_id || selectedPatient.id,
        newNote.id
      );
      setNoteText('');
      setFeedback({ 
        type: 'success', 
        message: `Note #${processed.id} successfully processed with AI NLP models. See extracted structure below.` 
      });
      // Expand this extraction automatically
      setExpandedExtraction(prev => ({ ...prev, [processed.id]: true }));
      await loadNotes();
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Failed to process note.' });
    } finally {
      setProcessingNote(false);
    }
  }

  async function handleProcessExisting(noteId) {
    setProcessingNote(true);
    setFeedback(null);
    try {
      const processed = await processPatientNote(
        selectedPatient.display_id || selectedPatient.id,
        noteId
      );
      setFeedback({ 
        type: 'success', 
        message: `Draft note #${noteId} successfully processed with Bio_ClinicalBERT pipeline.` 
      });
      setExpandedExtraction(prev => ({ ...prev, [noteId]: true }));
      await loadNotes();
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Failed to process note.' });
    } finally {
      setProcessingNote(false);
    }
  }

  function toggleExpand(noteId) {
    setExpandedExtraction(prev => ({ ...prev, [noteId]: !prev[noteId] }));
  }

  return (
    <div className="page-container">
      {/* Patient Banner */}
      <PatientBanner patient={selectedPatient} onSwitchPatient={onSwitchPatient} />

      {/* Editor Card */}
      <div className="hospital-card" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', margin: '0 0 0.2rem 0' }}>
              Record Clinical Handover Note
            </h2>
            <div style={{ fontSize: '0.825rem', color: '#64748b' }}>
              Authoring notes for {selectedPatient ? selectedPatient.name : 'selected patient'}. Original text is preserved strictly without modification.
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button 
              type="button" 
              className="btn btn-outline"
              onClick={handleLoadTemplate}
              style={{ fontSize: '0.8rem', padding: '0.35rem 0.65rem' }}
            >
              <Copy size={13} style={{ marginRight: '4px' }} />
              Load Sample Demo Narrative
            </button>
          </div>
        </div>

        {/* Feedback Message */}
        {feedback && (
          <div style={{
            padding: '0.75rem 1rem',
            borderRadius: '6px',
            marginBottom: '1rem',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: feedback.type === 'success' ? '#ecfdf5' : feedback.type === 'error' ? '#fef2f2' : '#f0f9ff',
            color: feedback.type === 'success' ? '#065f46' : feedback.type === 'error' ? '#991b1b' : '#0369a1',
            border: `1px solid ${feedback.type === 'success' ? '#a7f3d0' : feedback.type === 'error' ? '#fca5a5' : '#bae6fd'}`
          }}>
            {feedback.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
            <span>{feedback.message}</span>
          </div>
        )}

        {/* Textarea */}
        <div style={{ marginBottom: '1rem' }}>
          <textarea
            className="form-input"
            rows={6}
            placeholder="Type or paste unstructured handover narrative, shift observations, treatments, and tasks here..."
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            disabled={savingDraft || processingNote}
            style={{ width: '100%', resize: 'vertical', fontSize: '0.95rem', lineHeight: '1.5' }}
          />
        </div>

        {/* Author & Action Controls */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#475569' }}>
            <span>Author Identifier:</span>
            <input 
              type="text"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              className="form-input"
              style={{ padding: '0.25rem 0.5rem', fontSize: '0.85rem', width: '220px' }}
              disabled={savingDraft || processingNote}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              type="button"
              className="btn btn-outline"
              onClick={handleSaveDraft}
              disabled={savingDraft || processingNote || !noteText.trim()}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', minHeight: '40px' }}
            >
              {savingDraft ? <RefreshCw size={15} className="spinner" /> : <Save size={15} />}
              Save Draft
            </button>

            <button
              type="button"
              className="btn btn-primary"
              onClick={handleProcessImmediate}
              disabled={savingDraft || processingNote || !noteText.trim()}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', minHeight: '40px' }}
            >
              {processingNote ? (
                <>
                  <RefreshCw size={15} className="spinner" />
                  Processing with AI...
                </>
              ) : (
                <>
                  <Sparkles size={15} />
                  Save & Process with AI
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Chronological Notes Section */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 800, color: '#0f172a', margin: '0 0 0.2rem 0' }}>
              Patient Notes & Extraction History
            </h2>
            <div style={{ fontSize: '0.825rem', color: '#64748b' }}>
              Chronological log of saved notes for {selectedPatient ? selectedPatient.name : 'this patient'}.
            </div>
          </div>

          <button 
            className="btn btn-outline"
            onClick={loadNotes}
            disabled={loadingNotes}
            style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <RefreshCw size={13} className={loadingNotes ? 'spinner' : ''} />
            Refresh Log
          </button>
        </div>

        {loadingNotes ? (
          <div className="hospital-card" style={{ textAlign: 'center', padding: '2rem' }}>
            <RefreshCw size={24} className="spinner" style={{ color: '#0284c7', margin: '0 auto 0.5rem auto' }} />
            <div style={{ color: '#64748b', fontSize: '0.9rem' }}>Loading patient notes...</div>
          </div>
        ) : notes.length === 0 ? (
          <div className="hospital-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <FileText size={32} color="#94a3b8" style={{ margin: '0 auto 1rem auto' }} />
            <h3 style={{ fontSize: '1.1rem', color: '#1e293b', marginBottom: '0.4rem' }}>
              No notes entered yet for {selectedPatient ? selectedPatient.name : 'this patient'}
            </h3>
            <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
              Use the editor above to save your first clinical draft or load a sample handover narrative.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {notes.map((note) => {
              const isDraft = note.status === 'Draft';
              const isProcessed = note.status === 'Processed';
              const isReviewed = note.status === 'Reviewed';
              const hasExtraction = !!note.extraction?.data;
              const isExpanded = !!expandedExtraction[note.id];
              const ext = note.extraction?.data;

              const borderLeftColor = isReviewed ? '4px solid #059669' : isProcessed ? '4px solid #0284c7' : '4px solid #94a3b8';
              const statusBg = isReviewed ? '#ecfdf5' : isProcessed ? '#e0f2fe' : '#f1f5f9';
              const statusColor = isReviewed ? '#065f46' : isProcessed ? '#0369a1' : '#475569';

              return (
                <div key={note.id} className="hospital-card" style={{ borderLeft: borderLeftColor }}>
                  {/* Note Card Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 700, color: '#0f172a', fontSize: '0.95rem' }}>
                        Note #{note.id}
                      </span>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        background: statusBg,
                        color: statusColor
                      }}>
                        {note.status}
                      </span>
                      {isReviewed && (
                        <span style={{
                          background: '#ecfdf5',
                          color: '#065f46',
                          border: '1px solid #a7f3d0',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '3px'
                        }}>
                          <ShieldCheck size={12} color="#059669" />
                          Clinician Verified
                        </span>
                      )}
                      {isProcessed && (
                        <span style={{
                          background: '#fef3c7',
                          color: '#92400e',
                          border: '1px solid #fde68a',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 700
                        }}>
                          AI-generated — not yet reviewed
                        </span>
                      )}
                    </div>

                    <div style={{ fontSize: '0.8rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <Clock size={13} />
                      <span>{new Date(note.created_at).toLocaleString()}</span>
                      <span>•</span>
                      <span>{note.author_identifier || 'Clinician'}</span>
                    </div>
                  </div>

                  {/* Verbatim Note Text */}
                  <div style={{
                    background: '#f8fafc',
                    padding: '0.85rem 1rem',
                    borderRadius: '6px',
                    fontSize: '0.925rem',
                    color: '#1e293b',
                    lineHeight: '1.5',
                    border: '1px solid #e2e8f0',
                    marginBottom: '0.75rem',
                    whiteSpace: 'pre-wrap'
                  }}>
                    {note.raw_text}
                  </div>

                  {/* Actions & Extraction Accordion */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {isDraft ? (
                      <button 
                        className="btn btn-primary"
                        onClick={() => handleProcessExisting(note.id)}
                        disabled={processingNote}
                        style={{ fontSize: '0.825rem', padding: '0.35rem 0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                      >
                        <Sparkles size={14} /> Process Note with AI
                      </button>
                    ) : (
                      <button 
                        className="btn btn-outline"
                        onClick={() => toggleExpand(note.id)}
                        style={{ fontSize: '0.825rem', padding: '0.35rem 0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                      >
                        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        {isExpanded ? 'Hide Structured Extraction' : isReviewed ? 'View Extraction Details' : 'View AI Structured Extraction'}
                      </button>
                    )}

                    {hasExtraction && (
                      <button
                        className="btn btn-outline"
                        onClick={() => onNavigate('summary')}
                        style={{ fontSize: '0.8rem', padding: '0.35rem 0.65rem' }}
                      >
                        Open in Handover Summary
                      </button>
                    )}
                  </div>

                  {/* Extracted Details Drawer */}
                  {hasExtraction && isExpanded && ext && (
                    <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #e2e8f0' }}>
                      {/* Explicit Unreviewed Disclaimer Banner */}
                      <div style={{
                        background: '#fffbeb',
                        border: '1px solid #fde68a',
                        borderRadius: '6px',
                        padding: '0.65rem 0.85rem',
                        marginBottom: '1rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        fontSize: '0.825rem',
                        color: '#92400e'
                      }}>
                        <AlertTriangle size={16} color="#d97706" style={{ flexShrink: 0 }} />
                        <span>
                          <strong>AI-generated — not yet reviewed.</strong> {ext.disclaimer || "Extracted information is generated by AI models and has not been verified by a clinician."}
                        </span>
                      </div>

                      {/* ISBAR Grid */}
                      {ext.isbar && (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
                          <div style={{ background: '#f8fafc', padding: '0.65rem 0.85rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Situation</div>
                            <div style={{ fontSize: '0.85rem', color: '#1e293b' }}>{ext.isbar.situation || 'Observation noted.'}</div>
                          </div>
                          <div style={{ background: '#f8fafc', padding: '0.65rem 0.85rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Background</div>
                            <div style={{ fontSize: '0.85rem', color: '#1e293b' }}>{ext.isbar.background || 'Medical history referenced in text.'}</div>
                          </div>
                          <div style={{ background: '#f8fafc', padding: '0.65rem 0.85rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Assessment</div>
                            <div style={{ fontSize: '0.85rem', color: '#1e293b' }}>{ext.isbar.assessment || 'Clinical assessment recorded.'}</div>
                          </div>
                          <div style={{ background: '#f8fafc', padding: '0.65rem 0.85rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Recommendation</div>
                            <div style={{ fontSize: '0.85rem', color: '#1e293b' }}>{ext.isbar.recommendation || 'Plan specified in note.'}</div>
                          </div>
                        </div>
                      )}

                      {/* Extracted Entities Pills */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem' }}>
                        {ext.entities?.conditions && ext.entities.conditions.length > 0 && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                            <span style={{ fontWeight: 600, color: '#475569', minWidth: '100px' }}>Conditions:</span>
                            {ext.entities.conditions.map((c, i) => (
                              <span key={i} style={{ background: '#e0f2fe', color: '#0369a1', padding: '2px 8px', borderRadius: '4px', fontSize: '0.8rem' }}>
                                {c.text} {c.assertion && c.assertion !== 'positive' ? `(${c.assertion})` : ''}
                              </span>
                            ))}
                          </div>
                        )}

                        {ext.entities?.medications && ext.entities.medications.length > 0 && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                            <span style={{ fontWeight: 600, color: '#475569', minWidth: '100px' }}>Medications:</span>
                            {ext.entities.medications.map((m, i) => (
                              <span key={i} style={{ background: '#f3e8ff', color: '#6b21a8', padding: '2px 8px', borderRadius: '4px', fontSize: '0.8rem' }}>
                                {m.text} {m.dosage ? `(${m.dosage})` : ''}
                              </span>
                            ))}
                          </div>
                        )}

                        {ext.pending_tasks && ext.pending_tasks.length > 0 && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                            <span style={{ fontWeight: 600, color: '#475569', minWidth: '100px' }}>Pending Tasks:</span>
                            {ext.pending_tasks.map((t, i) => (
                              <span key={i} style={{ background: '#fef3c7', color: '#92400e', padding: '2px 8px', borderRadius: '4px', fontSize: '0.8rem' }}>
                                {t.task}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default ClinicalNotesPage;
