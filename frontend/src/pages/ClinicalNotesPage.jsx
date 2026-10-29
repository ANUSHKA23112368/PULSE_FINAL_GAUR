import React, { useState, useEffect, useRef } from 'react';
import { 
  FileText, 
  Save, 
  Clock, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  ChevronDown, 
  ChevronUp, 
  RefreshCw, 
  ShieldCheck,
  Mic,
  MicOff,
  BookOpen,
  Layers,
  Wand2
} from 'lucide-react';
import { PatientBanner } from '../components/PatientBanner';
import { fetchPatientNotes, createPatientNote, processPatientNote } from '../services/api';

const CLINICAL_SPECIALTY_TEMPLATES = [
  {
    category: 'General Medicine',
    title: 'Rahul Morning Handover (8 AM)',
    author: 'Morning Shift Staff Nurse (Ward 4B)',
    text: "Rahul, 55 years old, admitted with fever and cough. Temperature was 102°F in the morning. Paracetamol given at 8 AM. Blood test report is pending. Patient's temperature should be checked again at 12 PM."
  },
  {
    category: 'General Medicine',
    title: 'Rahul Evening Handover (12:30 PM)',
    author: 'Evening Shift Staff Nurse (Ward 4B)',
    text: "At 12 PM, Rahul's temperature was 100°F. Blood report received. Doctor reviewed the report and advised continued monitoring. Patient's cough persists."
  },
  {
    category: 'Cardiology',
    title: 'Chest Pain & Acute Coronary Observation',
    author: 'Cardiac Care Sister (CCU)',
    text: "Vera Abbott, 93, bed four, under Dr Liu came in with chest pain with a history of stroke, CAD and asthma. Given GTN sublingual with relief. Repeat troponin ordered for 0600. Keep on continuous ECG telemetry. Aspirin 100mg mane."
  },
  {
    category: 'Neurology',
    title: 'Acute Vertigo & Bell\'s Palsy Handover',
    author: 'Neuro Ward Staff Nurse',
    text: "Bed eight, Michael I Wu, 48 years under Dr Hanlen. Admitted with acute headache and vertigo. History of tinnitus, Bell's Palsy, severe neck pain. Waiting for CT scan head without contrast at 1000. Vitals: BP 124/82 mmHg, HR 78 bpm, afebrile. Digoxin 0.25mg mane. Plan neuro review in morning."
  },
  {
    category: 'Vascular Surgery',
    title: 'Suspected DVT & Anticoagulation Handover',
    author: 'Surgical Stepdown Nurse',
    text: "Pierre Cox, 77 years under Dr Gregor, bed 2. Admitted with acute pain and swelling right lower limb query DVT. History of CAD and hypertension. Ultrasound doppler lower limb booked for 0900. Clexane 80mg subcut commenced 2000. Elevate right leg."
  },
  {
    category: 'Endocrinology',
    title: 'Type 1 Diabetes & Glycemic Handover',
    author: 'Endocrine Specialist Nurse',
    text: "Leila Sonya Da Silva, 34, bed 5 under Dr Liu. Admitted for glycemic stabilization. History of Type 1 DM since childhood and hypertension. Blood glucose currently 11.4 mmol/L. Subcut Actrapid 6 units administered with dinner. Recheck BGL at 2200."
  }
];

const SHORTHAND_DICTIONARY = [
  { short: 'c/o', expanded: 'complains of', note: 'Chief presenting complaint' },
  { short: 'h/o', expanded: 'history of', note: 'Past medical history' },
  { short: 'pt', expanded: 'patient', note: 'Subject patient' },
  { short: 'BD / BID', expanded: 'bis in die (twice daily)', note: 'Medication frequency' },
  { short: 'TDS / TID', expanded: 'ter die sumendum (three times daily)', note: 'Medication frequency' },
  { short: 'SOS / PRN', expanded: 'pro re nata (as needed)', note: 'Emergency or symptomatic dose' },
  { short: 'BGL', expanded: 'blood glucose level', note: 'Capillary glucose measurement' },
  { short: 'GTN', expanded: 'glyceryl trinitrate', note: 'Sublingual vasodilator for angina' },
  { short: 'afebrile', expanded: 'no elevated temperature / normal', note: 'Core temperature observation' },
  { short: 'stat', expanded: 'statim (immediately)', note: 'Emergency medication urgency' }
];

export function ClinicalNotesPage({ selectedPatient, onSwitchPatient, onNavigate, allPatients, onSelectPatient }) {
  const [noteText, setNoteText] = useState('');
  const [author, setAuthor] = useState('Staff Nurse / Clinician (Shift Handover)');
  const [notes, setNotes] = useState([]);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [processingNote, setProcessingNote] = useState(false);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error' | 'info', message: '' }
  const [expandedExtraction, setExpandedExtraction] = useState({});
  const [showShorthandGuide, setShowShorthandGuide] = useState(false);

  // Simulated Voice Dictation
  const [isDictating, setIsDictating] = useState(false);
  const [dictationTime, setDictationTime] = useState(0);
  const dictationTimerRef = useRef(null);

  useEffect(() => {
    if (selectedPatient) {
      loadNotes();
    }
  }, [selectedPatient]);

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (dictationTimerRef.current) clearInterval(dictationTimerRef.current);
    };
  }, []);

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

  function handleSelectTemplate(tpl) {
    setNoteText(tpl.text);
    setAuthor(tpl.author);
    setFeedback({
      type: 'info',
      message: `Loaded template: "${tpl.title}" into the clinical handover editor.`
    });
  }

  // Voice Dictation Simulation
  function toggleDictation() {
    if (isDictating) {
      // Stop dictating
      clearInterval(dictationTimerRef.current);
      setIsDictating(false);
      
      const speechSample = `${selectedPatient?.name || 'Patient'} in bed ${selectedPatient?.bed_number || '4'}. Vitals stable overnight. Temperature 37.1 degrees. Morning medications administered. Continue routine neurological and vital observation.`;
      
      setNoteText(prev => prev ? `${prev}\n${speechSample}` : speechSample);
      setFeedback({
        type: 'success',
        message: `Voice dictation transcribed (${dictationTime.toFixed(1)}s speech audio processed).`
      });
      setDictationTime(0);
    } else {
      // Start dictating
      setIsDictating(true);
      setDictationTime(0);
      dictationTimerRef.current = setInterval(() => {
        setDictationTime(t => t + 0.1);
      }, 100);
    }
  }

  // Automatically Expand Shorthand in text
  function handleExpandShorthand() {
    if (!noteText.trim()) return;
    let expanded = noteText;
    expanded = expanded.replace(/\bc\/o\b/gi, 'complains of');
    expanded = expanded.replace(/\bh\/o\b/gi, 'history of');
    expanded = expanded.replace(/\bpt\b/gi, 'patient');
    expanded = expanded.replace(/\bTDS\b/gi, 'three times daily (TDS)');
    expanded = expanded.replace(/\bBD\b/gi, 'twice daily (BD)');
    expanded = expanded.replace(/\bSOS\b/gi, 'as needed (SOS)');
    expanded = expanded.replace(/\bafebrile\b/gi, 'afebrile (normal body temperature)');
    setNoteText(expanded);
    setFeedback({
      type: 'success',
      message: 'Standardized clinical shorthand abbreviations expanded successfully.'
    });
  }

  async function handleSaveDraft(e) {
    if (e) e.preventDefault();
    if (!noteText.trim()) {
      setFeedback({ type: 'error', message: 'Clinical handover note cannot be empty.' });
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
      setFeedback({ type: 'success', message: `Draft note #${newNote.id} saved to patient record.` });
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
      setFeedback({ type: 'error', message: 'Clinical handover note cannot be empty.' });
      return;
    }
    setProcessingNote(true);
    setFeedback(null);
    try {
      const newNote = await createPatientNote(
        selectedPatient.display_id || selectedPatient.id,
        noteText.trim(),
        author
      );
      const processed = await processPatientNote(
        selectedPatient.display_id || selectedPatient.id,
        newNote.id
      );
      setNoteText('');
      setFeedback({ 
        type: 'success', 
        message: `Handover note #${processed.id} structured via Bio_ClinicalBERT & ISBAR neural pipeline.` 
      });
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
        message: `Note #${noteId} successfully structured into ISBAR format.` 
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
      <PatientBanner 
        patient={selectedPatient} 
        onSwitchPatient={onSwitchPatient}
        allPatients={allPatients}
        onSelectPatient={onSelectPatient}
        onNavigate={onNavigate}
      />

      {/* Handover Authoring Card */}
      <div className="hospital-card clinical-editor-card">
        <div className="editor-header-row">
          <div>
            <h2 className="editor-title">
              Record Nursing & Clinical Handover Note
            </h2>
            <div className="editor-subtitle">
              Authoring verbatim handover narrative for {selectedPatient ? selectedPatient.name : 'patient'}. Full original text is preserved without alteration.
            </div>
          </div>

          <div className="editor-header-actions">
            {/* Shorthand Guide Toggle */}
            <button 
              type="button" 
              className={`btn btn-outline ${showShorthandGuide ? 'btn-active-tool' : ''}`}
              onClick={() => setShowShorthandGuide(prev => !prev)}
              title="Medical shorthand and acronyms glossary"
            >
              <BookOpen size={14} />
              <span>Shorthand Glossary</span>
            </button>

            {/* Voice Dictation Button */}
            <button 
              type="button"
              className={`dictation-btn ${isDictating ? 'dictating-active' : ''}`}
              onClick={toggleDictation}
              title={isDictating ? "Stop voice dictation" : "Simulate speech handover dictation"}
            >
              {isDictating ? (
                <>
                  <MicOff size={15} />
                  <span>Stop ({dictationTime.toFixed(1)}s)</span>
                  <span className="audio-wave-anim">
                    <span /><span /><span /><span />
                  </span>
                </>
              ) : (
                <>
                  <Mic size={15} />
                  <span>Voice Dictation</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Shorthand Dictionary Pop-down */}
        {showShorthandGuide && (
          <div className="shorthand-drawer">
            <div className="shorthand-drawer-header">
              <span className="drawer-title">
                <BookOpen size={14} className="text-primary" /> Indian Clinical Shorthand & Abbreviations Normalizer
              </span>
              <button 
                type="button" 
                className="btn btn-outline btn-xs"
                onClick={handleExpandShorthand}
                title="Expand acronyms in the current note"
              >
                <Wand2 size={12} /> Auto-Expand in Note
              </button>
            </div>
            <div className="shorthand-grid">
              {SHORTHAND_DICTIONARY.map((sh, idx) => (
                <div key={idx} className="shorthand-item">
                  <span className="sh-badge">{sh.short}</span>
                  <span className="sh-expanded">{sh.expanded}</span>
                  <span className="sh-note">{sh.note}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Clinical Scenario Presets Strip */}
        <div className="preset-templates-bar">
          <span className="preset-label">Handover Scenarios:</span>
          <div className="preset-chips-scroll">
            {CLINICAL_SPECIALTY_TEMPLATES.map((tpl, idx) => (
              <button
                key={idx}
                type="button"
                className="preset-chip"
                onClick={() => handleSelectTemplate(tpl)}
                title={tpl.author}
              >
                <Sparkles size={12} className="chip-sparkle" />
                <span>{tpl.title}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div className={`feedback-alert feedback-${feedback.type}`}>
            {feedback.type === 'success' && <CheckCircle2 size={16} className="text-emerald" />}
            {feedback.type === 'error' && <AlertCircle size={16} className="text-rose" />}
            {feedback.type === 'info' && <Sparkles size={16} className="text-sky" />}
            <span className="feedback-text">{feedback.message}</span>
            <button className="feedback-close" onClick={() => setFeedback(null)}>×</button>
          </div>
        )}

        {/* Note Textarea & Author Input */}
        <div className="editor-form-body">
          <div className="textarea-wrapper">
            <textarea
              className="clinical-textarea"
              rows={6}
              placeholder="Dictate or type clinical shift handover note (e.g. 'Patient 55yo, fever 102F in morning, paracetamol given at 0800, blood report pending, recheck temp 1200...')"
              value={noteText}
              onChange={e => setNoteText(e.target.value)}
            />
            {noteText && (
              <div className="textarea-character-counter">
                {noteText.split(/\s+/).filter(Boolean).length} words • {noteText.length} chars
              </div>
            )}
          </div>

          <div className="editor-actions-row">
            <div className="author-field">
              <label className="author-label">Author Credentials:</label>
              <input
                type="text"
                className="form-input author-input"
                value={author}
                onChange={e => setAuthor(e.target.value)}
              />
            </div>

            <div className="editor-buttons-group">
              <button
                type="button"
                className="btn btn-outline"
                onClick={handleSaveDraft}
                disabled={savingDraft || processingNote || !noteText.trim()}
              >
                <Save size={15} />
                <span>{savingDraft ? 'Saving Draft...' : 'Save Draft'}</span>
              </button>

              <button
                type="button"
                className="btn btn-primary"
                onClick={handleProcessImmediate}
                disabled={processingNote || savingDraft || !noteText.trim()}
              >
                <Sparkles size={15} />
                <span>{processingNote ? 'Structuring with AI...' : 'Save & Structure (ISBAR)'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Notes & Extraction History Log */}
      <div className="notes-log-section">
        <div className="section-title-row">
          <div>
            <h3 className="section-title">Patient Handover Notes & Extraction Runs</h3>
            <div className="section-subtitle">
              Chronological ledger of notes authoring, AI structuring, and clinician review for {selectedPatient ? selectedPatient.name : 'this patient'}.
            </div>
          </div>

          <button 
            type="button"
            className="btn btn-outline btn-sm"
            onClick={loadNotes}
            disabled={loadingNotes}
          >
            <RefreshCw size={13} className={loadingNotes ? 'animate-spin' : ''} />
            <span>Refresh Ledger</span>
          </button>
        </div>

        {loadingNotes ? (
          <div className="hospital-card loading-state-card">
            <RefreshCw size={24} className="animate-spin text-primary" />
            <span>Loading patient handover notes...</span>
          </div>
        ) : notes.length === 0 ? (
          <div className="hospital-card empty-state-card">
            <FileText size={32} className="text-muted" />
            <h4>No handover notes recorded for this patient yet</h4>
            <p>Use the editor above or select one of the specialty clinical scenarios to record the first shift note.</p>
          </div>
        ) : (
          <div className="notes-accordion-list">
            {notes.map(note => {
              const isDraft = note.status === 'Draft';
              const isProcessed = note.status === 'Processed';
              const isReviewed = note.status === 'Reviewed';
              const hasExtraction = !!(note.extraction?.data || note.extracted_data || note.latest_extraction?.extracted_data || note.latest_extraction?.data);
              const isExpanded = !!expandedExtraction[note.id];
              const ext = note.extraction?.data || note.extracted_data || note.latest_extraction?.extracted_data || note.latest_extraction?.data;

              return (
                <div key={note.id} className={`hospital-card note-card note-status-${note.status.toLowerCase()}`}>
                  {/* Note Header */}
                  <div className="note-card-header">
                    <div className="note-badge-group">
                      <span className="note-id-tag">Note #{note.id}</span>
                      <span className={`status-pill status-${note.status.toLowerCase()}`}>
                        {note.status}
                      </span>
                      {isReviewed && (
                        <span className="status-pill status-verified">
                          <ShieldCheck size={12} /> Clinician Verified
                        </span>
                      )}
                      {isProcessed && (
                        <span className="status-pill status-ai">
                          <Sparkles size={11} /> Bio_ClinicalBERT Structured
                        </span>
                      )}
                    </div>

                    <div className="note-timestamp">
                      <Clock size={13} />
                      <span>{new Date(note.created_at).toLocaleString()}</span>
                      <span>•</span>
                      <span>{note.author_identifier || 'Clinician'}</span>
                    </div>
                  </div>

                  {/* Verbatim Note Text */}
                  <div className="note-verbatim-text">
                    {note.raw_text}
                  </div>

                  {/* Action Bar */}
                  <div className="note-card-footer">
                    {isDraft ? (
                      <button 
                        className="btn btn-primary btn-sm"
                        onClick={() => handleProcessExisting(note.id)}
                        disabled={processingNote}
                      >
                        <Sparkles size={13} /> Structure with Bio_ClinicalBERT
                      </button>
                    ) : (
                      <button 
                        className="btn btn-outline btn-sm"
                        onClick={() => toggleExpand(note.id)}
                      >
                        {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                        <span>{isExpanded ? 'Hide Structured Extraction' : 'View AI Structured Extraction'}</span>
                      </button>
                    )}

                    {hasExtraction && (
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => onNavigate('summary')}
                      >
                        <Layers size={13} /> Open in ISBAR Summary
                      </button>
                    )}
                  </div>

                  {/* Expanded AI Extraction Details */}
                  {isExpanded && ext && (
                    <div className="extraction-details-pane">
                      <div className="extraction-pane-header">
                        <div className="pane-title">
                          <Sparkles size={14} className="text-primary" />
                          <span>Extracted Clinical Entities & ISBAR Attributes</span>
                        </div>
                        <span className="model-chip">Engine: Bio_ClinicalBERT</span>
                      </div>

                      {/* ISBAR Structured Cards Grid */}
                      <div className="isbar-breakdown-grid">
                        <div className="isbar-tile isbar-s">
                          <span className="isbar-letter">S</span>
                          <div className="isbar-content">
                            <strong>Situation:</strong>
                            <p>{ext.isbar?.situation || ext.structured_handover?.isbar?.situation || 'No acute situation identified.'}</p>
                          </div>
                        </div>

                        <div className="isbar-tile isbar-b">
                          <span className="isbar-letter">B</span>
                          <div className="isbar-content">
                            <strong>Background:</strong>
                            <p>{ext.isbar?.background || ext.structured_handover?.isbar?.background || 'No background factors identified.'}</p>
                          </div>
                        </div>

                        <div className="isbar-tile isbar-a">
                          <span className="isbar-letter">A</span>
                          <div className="isbar-content">
                            <strong>Assessment:</strong>
                            <p>{ext.isbar?.assessment || ext.structured_handover?.isbar?.assessment || 'No clinical assessment synthesized.'}</p>
                          </div>
                        </div>

                        <div className="isbar-tile isbar-r">
                          <span className="isbar-letter">R</span>
                          <div className="isbar-content">
                            <strong>Recommendation:</strong>
                            <p>{ext.isbar?.recommendation || ext.structured_handover?.isbar?.recommendation || 'No pending recommendations.'}</p>
                          </div>
                        </div>
                      </div>

                      {/* Named Clinical Spans Cloud */}
                      {ext.entities && (
                        <div className="named-entities-cloud">
                          <span className="cloud-label">Extracted Clinical Entities:</span>
                          <div className="chips-wrap">
                            {(ext.entities.medications || []).map((m, idx) => (
                              <span key={`med-${idx}`} className="span-chip chip-medication">
                                💊 {typeof m === 'object' ? `${m.name || m.text} ${m.dose || ''}` : m}
                              </span>
                            ))}
                            {(ext.entities.conditions || []).map((c, idx) => (
                              <span key={`cond-${idx}`} className="span-chip chip-condition">
                                🩺 {typeof c === 'object' ? (c.name || c.text) : c}
                              </span>
                            ))}
                            {(ext.entities.investigations || []).map((inv, idx) => (
                              <span key={`inv-${idx}`} className="span-chip chip-investigation">
                                🧪 {typeof inv === 'object' ? (inv.test || inv.name || inv.text) : inv}
                              </span>
                            ))}
                            {(ext.entities.tasks || []).map((t, idx) => (
                              <span key={`tsk-${idx}`} className="span-chip chip-task">
                                📋 {typeof t === 'object' ? (t.task_description || t.text) : t}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
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
